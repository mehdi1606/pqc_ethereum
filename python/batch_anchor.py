#!/usr/bin/env python3
"""
MERKLE-TREE BATCH ANCHORING SCRIPT
Batches N PQC commitments into a single Merkle root and anchors it on-chain.
Reproduces Table 8 from the paper (Section 7.3).
PREREQUISITE: Hardhat node must be running and contract deployed.
Run: python python/batch_anchor.py
"""
import json
import os
import math
import time
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ─────────────────────────────────────────────────────────
GAS_PRICE_GWEI = 20       # reference gas price for USD cost calculation
ETH_USD        = 3000     # reference ETH/USD price
BATCH_SIZES    = [10, 50, 100, 500, 1000]

# ── Connect to Hardhat ────────────────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
assert w3.is_connected(), 'ERROR: Cannot connect to Hardhat node (npx hardhat node)'

with open('python/contract_address.txt') as f:
    contract_address = f.read().strip()

ABI = [
    {
        'name': 'anchorCommitment',
        'type': 'function',
        'inputs': [
            {'name': 'commitment', 'type': 'bytes32'},
            {'name': 'ipfsCID',    'type': 'string'},
            {'name': 'algorithm',  'type': 'string'}
        ],
        'outputs': [],
        'stateMutability': 'nonpayable'
    },
    {
        'name': 'checkCommitment',
        'type': 'function',
        'inputs': [{'name': 'commitment', 'type': 'bytes32'}],
        'outputs': [
            {'name': 'exists',    'type': 'bool'},
            {'name': 'signer',    'type': 'address'},
            {'name': 'timestamp', 'type': 'uint256'},
            {'name': 'algo',      'type': 'string'}
        ],
        'stateMutability': 'view'
    }
]
contract = w3.eth.contract(address=contract_address, abi=ABI)

HARDHAT_PK = os.environ['HARDHAT_PK']
account    = Account.from_key(HARDHAT_PK)
print(f'Connected to Hardhat. Chain ID : {w3.eth.chain_id}')
print(f'Sender address                 : {account.address}')


# ── Merkle tree helpers ───────────────────────────────────────────────────

def keccak(data: bytes) -> bytes:
    """Return raw 32-byte keccak256 hash."""
    return bytes(w3.keccak(data))


def build_merkle_tree(leaves: list[bytes]) -> tuple[bytes, list[list[bytes]]]:
    """
    Build a binary Merkle tree from a list of 32-byte leaf hashes.
    Pads to the next power-of-2 by repeating the last leaf.
    Returns (root_bytes, layers) where layers[0] = leaves, layers[-1] = [root].
    """
    # Pad to power of 2
    n = len(leaves)
    size = 1 << math.ceil(math.log2(max(n, 2)))
    layer = list(leaves) + [leaves[-1]] * (size - n)

    layers = [layer]
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            parent = keccak(layer[i] + layer[i + 1])
            next_layer.append(parent)
        layer = next_layer
        layers.append(layer)

    return layers[-1][0], layers  # (root, all layers)


def generate_commitments(n: int, seed: int = 0) -> list[bytes]:
    """Generate n deterministic fake PQC commitment hashes."""
    return [keccak(f'pqc_commitment_{seed}_{i}'.encode()) for i in range(n)]


def send_anchor(root_bytes: bytes, nonce: int, batch_size: int) -> dict:
    """Anchor a Merkle root on-chain and return gas info."""
    root_hex     = '0x' + root_bytes.hex()
    ipfs_cid     = f'bafkrei_merkle_batch_{batch_size}'
    algorithm    = 'Dilithium3+Falcon512-MerkleRoot'

    txn = contract.functions.anchorCommitment(
        root_bytes, ipfs_cid, algorithm
    ).build_transaction({
        'from':     account.address,
        'nonce':    nonce,
        'gas':      250000,
        'gasPrice': w3.to_wei(str(GAS_PRICE_GWEI), 'gwei')
    })
    signed  = account.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    gas_used = receipt['gasUsed']
    cost_eth = gas_used * GAS_PRICE_GWEI * 1e-9
    cost_usd = cost_eth * ETH_USD

    return {
        'tx_hash':       '0x' + tx_hash.hex(),
        'status':        receipt['status'],
        'gas_used':      gas_used,
        'gas_per_sig':   gas_used / batch_size,
        'cost_usd_total': round(cost_usd, 6),
        'cost_usd_per_sig': round(cost_usd / batch_size, 6),
    }


# ── Main benchmark loop ───────────────────────────────────────────────────
print('\n' + '='*65)
print('  MERKLE-TREE BATCH ANCHORING BENCHMARK')
print('='*65)

batch_results = []
nonce = w3.eth.get_transaction_count(account.address)

for N in BATCH_SIZES:
    print(f'\n-> Batch size N = {N} ...')

    commitments = generate_commitments(N, seed=N)
    root, _     = build_merkle_tree(commitments)

    info = send_anchor(root, nonce, N)
    nonce += 1

    print(f'   Gas used        : {info["gas_used"]:,}')
    print(f'   Gas per sig     : {info["gas_per_sig"]:.1f}')
    print(f'   Cost per sig    : ${info["cost_usd_per_sig"]:.4f}')
    print(f'   Merkle root     : 0x{root.hex()[:16]}...')

    batch_results.append({
        'batch_size':         N,
        'merkle_root':        '0x' + root.hex(),
        'total_gas':          info['gas_used'],
        'gas_per_sig':        round(info['gas_per_sig'], 2),
        'cost_per_sig_usd':   info['cost_usd_per_sig'],
        'tx_hash':            info['tx_hash'],
    })

# ── Print Table 8 ─────────────────────────────────────────────────────────
print('\n' + '='*65)
print('  TABLE 8 — MERKLE-TREE BATCH ANCHORING GAS COSTS')
print(f'  Reference: {GAS_PRICE_GWEI} Gwei, ETH/USD ${ETH_USD:,}')
print('='*65)

hdr = '{:>14}  {:>12}  {:>14}  {:>22}'
row = '{:>14}  {:>12,}  {:>14.1f}  {:>22.4f}'
print(hdr.format('Batch size N', 'Total gas', 'Gas per sig', 'Cost per sig (USD)'))
print('-'*65)
for r in batch_results:
    print(row.format(r['batch_size'], r['total_gas'],
                     r['gas_per_sig'], r['cost_per_sig_usd']))
print('-'*65)

# ── Save results ──────────────────────────────────────────────────────────
os.makedirs('keys', exist_ok=True)
output = {
    'gas_price_gwei': GAS_PRICE_GWEI,
    'eth_usd':        ETH_USD,
    'batches':        batch_results
}
with open('keys/batch_results.json', 'w') as f:
    json.dump(output, f, indent=2)

print('\nResults saved to keys/batch_results.json')
