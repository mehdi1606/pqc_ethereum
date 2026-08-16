#!/usr/bin/env python3
"""
MERKLE-TREE BATCH ANCHORING  (reproduces Table 8 of the paper)

Instead of anchoring N commitments in N transactions, we build a single keccak256
Merkle tree over the N per-signature commitments and anchor only its 32-byte root
in ONE transaction. The on-chain cost is therefore (almost) independent of N, so the
amortised gas/USD cost per signature falls as 1/N and drops below one cent for large
batches.

For each batch size N in {1, 10, 50, 100, 500, 1000} the script:
  1. produces N real dual-signature commitments (Dilithium3 + Falcon-512),
  2. builds the keccak256 Merkle tree and takes the root,
  3. anchors the root via PQCAnchor.anchorMerkleRoot(root, N, cid),
  4. measures the on-chain gas and computes gas + USD per signature.

PREREQUISITE: Hardhat node running + contract deployed (address in
python/contract_address.txt). Run keygen is not required — keys are made in-memory.
Run:  python python/merkle_batch.py
"""
import os
import json
import oqs
from web3 import Web3
from eth_account import Account

os.makedirs('keys', exist_ok=True)

# ── Reference economics (paper Table 5) ────────────────────────────────────
GAS_PRICE_GWEI = 20        # mainnet benchmark reference
ETH_USD        = 3000      # reference price only
BATCH_SIZES    = [1, 10, 50, 100, 500, 1000]
MAX_N          = max(BATCH_SIZES)

w3_hash = Web3()  # keccak256 only


# ── Merkle tree over keccak256 (Ethereum-style, duplicate last if odd) ──────
def merkle_root(leaves):
    """Compute a keccak256 Merkle root. Leaves are 32-byte digests.

    At each level, adjacent nodes are hashed as keccak256(left || right); if a
    level has an odd node count the last node is duplicated. A single leaf is its
    own root.
    """
    if len(leaves) == 1:
        return leaves[0]
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])          # duplicate last node
        level = [bytes(w3_hash.keccak(level[i] + level[i + 1]))
                 for i in range(0, len(level), 2)]
    return level[0]


# ── Build MAX_N dual-signature commitment leaves once ──────────────────────
print(f'Generating {MAX_N:,} dual-signature commitment leaves (one keypair reused)...')
dil = oqs.Signature('Dilithium3'); dil_pk = dil.generate_keypair()
fal = oqs.Signature('Falcon-512'); fal_pk = fal.generate_keypair()

leaves = []
for i in range(MAX_N):
    msg      = f'batch asset transfer #{i}'.encode()
    sig_dil  = dil.sign(msg)
    sig_fal  = fal.sign(msg)
    msg_hash = bytes(w3_hash.keccak(msg))
    # leaf = H = keccak256(sigD || sigF || pkD || pkF || keccak256(msg))  (Theorem 1)
    leaf = bytes(w3_hash.keccak(sig_dil + sig_fal + dil_pk + fal_pk + msg_hash))
    leaves.append(leaf)
print('  Leaves ready.\n')

# ── Connect to Hardhat + load contract ─────────────────────────────────────
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
assert w3.is_connected(), 'ERROR: Hardhat node not running (npx hardhat node)!'

with open('python/contract_address.txt') as f:
    contract_address = f.read().strip()

ABI = [{
    'name': 'anchorMerkleRoot', 'type': 'function',
    'inputs': [
        {'name': 'merkleRoot', 'type': 'bytes32'},
        {'name': 'leafCount',  'type': 'uint256'},
        {'name': 'ipfsCID',    'type': 'string'}
    ], 'outputs': [], 'stateMutability': 'nonpayable'
}]
contract = w3.eth.contract(address=contract_address, abi=ABI)

HARDHAT_PK = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
acct = Account.from_key(HARDHAT_PK)


def anchor_root(root_bytes, n):
    nonce = w3.eth.get_transaction_count(acct.address)
    txn = contract.functions.anchorMerkleRoot(
        root_bytes, n, f'ipfs://batch-{n}'
    ).build_transaction({
        'from': acct.address, 'nonce': nonce,
        'gas': 200000, 'gasPrice': w3.to_wei(GAS_PRICE_GWEI, 'gwei')
    })
    signed  = acct.sign_transaction(txn)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt['status'] == 1, 'anchorMerkleRoot transaction failed'
    return receipt['gasUsed']


def usd(gas):
    return gas * GAS_PRICE_GWEI * 1e-9 * ETH_USD


# ── Run the batch sweep and print Table 8 ──────────────────────────────────
print('=' * 78)
print(f'  MERKLE BATCH ANCHORING  (gas price {GAS_PRICE_GWEI} Gwei, '
      f'ETH/USD {ETH_USD})')
print('=' * 78)
print(f'  {"Batch N":>8} | {"Total gas":>10} | {"Gas/sig":>10} | '
      f'{"USD/sig":>12}')
print('  ' + '-' * 52)

table8 = []
for n in BATCH_SIZES:
    root      = merkle_root(leaves[:n])
    total_gas = anchor_root(root, n)
    gas_per   = total_gas / n
    usd_per   = usd(total_gas) / n
    table8.append({
        'batch_size': n, 'total_gas': total_gas,
        'gas_per_signature': round(gas_per, 2),
        'usd_per_signature': round(usd_per, 6),
    })
    print(f'  {n:>8} | {total_gas:>10,} | {gas_per:>10,.1f} | '
          f'{usd_per:>12.6f}')

print('=' * 78)

with open('keys/merkle_table8.json', 'w') as f:
    json.dump({'gas_price_gwei': GAS_PRICE_GWEI, 'eth_usd': ETH_USD,
               'results': table8}, f, indent=2)
print('  Table 8 data saved to keys/merkle_table8.json')
print('  Note: anchoring cost is ~constant in N, so USD/signature scales as 1/N.')
