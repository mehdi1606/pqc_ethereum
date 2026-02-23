#!/usr/bin/env python3
"""
ON-CHAIN ANCHORING SCRIPT
Submits commitment H to the PQCAnchor smart contract on local Hardhat network
PREREQUISITE: Hardhat node must be running (npx hardhat node)
Run: python python/anchor_onchain.py
"""
import json
from web3 import Web3
from eth_account import Account

# ── Load signing data ─────────────────────────────────────────────────────
with open('keys/signing_data.json') as f:
    data = json.load(f)

H = data['commitment_H']        # '0x...' 32-byte hex string
algorithm = data['algorithm_primary']
ipfs_cid  = 'bafkreiexample123fakecidfordemopurposesonly'  # in real use: actual IPFS CID

# ── Connect to local Hardhat node ─────────────────────────────────────────
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
assert w3.is_connected(), 'ERROR: Cannot connect to Hardhat node!'
print(f'Connected to Hardhat. Chain ID: {w3.eth.chain_id}')

# ── Load contract address and ABI ─────────────────────────────────────────
with open('python/contract_address.txt') as f:
    contract_address = f.read().strip()

# Minimal ABI (only the functions we need)
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
    },
    {
        'name': 'SignatureAnchored',
        'type': 'event',
        'inputs': [
            {'name': 'signer',     'type': 'address', 'indexed': True},
            {'name': 'commitment', 'type': 'bytes32', 'indexed': True},
            {'name': 'ipfsCID',    'type': 'string',  'indexed': False},
            {'name': 'algorithm',  'type': 'string',  'indexed': False},
            {'name': 'timestamp',  'type': 'uint256', 'indexed': False}
        ]
    }
]

contract = w3.eth.contract(address=contract_address, abi=ABI)

# ── Use first Hardhat test account as signer ────────────────────────────────
# Hardhat account #0 private key (public, fixed for local dev only)
HARDHAT_PK = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
account = Account.from_key(HARDHAT_PK)
print(f'Sender address: {account.address}')
print(f'Balance       : {w3.from_wei(w3.eth.get_balance(account.address), "ether"):.4f} ETH')

# ── Estimate gas ──────────────────────────────────────────────────────────
h_bytes32 = bytes.fromhex(H[2:])   # strip '0x', convert to bytes
estimated_gas = contract.functions.anchorCommitment(
    h_bytes32, ipfs_cid, algorithm
).estimate_gas({'from': account.address})
print(f'\nEstimated gas : {estimated_gas:,}')

# ── Build and send transaction ────────────────────────────────────────────
nonce = w3.eth.get_transaction_count(account.address)
txn = contract.functions.anchorCommitment(
    h_bytes32, ipfs_cid, algorithm
).build_transaction({
    'from':     account.address,
    'nonce':    nonce,
    'gas':      estimated_gas + 10000,   # small buffer
    'gasPrice': w3.to_wei('1', 'gwei')
})

signed = account.sign_transaction(txn)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
print(f'Transaction sent. Hash: 0x{tx_hash.hex()}')

# ── Wait for receipt ──────────────────────────────────────────────────────
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
print(f'\n=== TRANSACTION CONFIRMED ===')
print(f'  Block number : {receipt["blockNumber"]}')
print(f'  Gas used     : {receipt["gasUsed"]:,}')
print(f'  Status       : {"SUCCESS" if receipt["status"]==1 else "FAILED"}')
print(f'  Tx hash      : {receipt["transactionHash"].hex()}')

# ── Verify on-chain storage ───────────────────────────────────────────────
exists, signer, timestamp, algo = contract.functions.checkCommitment(h_bytes32).call()
print(f'\n=== ON-CHAIN VERIFICATION ===')
print(f'  Commitment exists : {exists}')
print(f'  Anchored by       : {signer}')
print(f'  Timestamp         : {timestamp}')
print(f'  Algorithm         : {algo}')

# Save receipt
receipt_data = {
    'tx_hash':      receipt['transactionHash'].hex(),
    'block_number': receipt['blockNumber'],
    'gas_used':     receipt['gasUsed'],
    'commitment_H': H
}
with open('keys/tx_receipt.json', 'w') as f:
    json.dump(receipt_data, f, indent=2)

print('\nReceipt saved to keys/tx_receipt.json')
print('NEXT STEP: run verify_offline.py')
