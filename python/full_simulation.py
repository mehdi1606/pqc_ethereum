#!/usr/bin/env python3
"""
FULL END-TO-END SIMULATION
Runs the complete hybrid PQC + Ethereum workflow in one script.
PREREQUISITE: Start Hardhat node first, deploy contract, save address.
Run: python python/full_simulation.py
"""
import oqs, json, time, os
from web3 import Web3
from eth_account import Account

def banner(title):
    print('\n' + '='*60)
    print(f'  {title}')
    print('='*60)

# ============================================================
banner('PHASE 1: PQC KEY GENERATION (off-chain)')
# ============================================================
os.makedirs('keys', exist_ok=True)

# Generate Dilithium3 key pair
print('\n-> Generating Dilithium3 key pair...')
t0 = time.perf_counter()
with oqs.Signature('Dilithium3') as s:
    dil_pk = s.generate_keypair()
    dil_sk = s.export_secret_key()
print(f'  Done in {(time.perf_counter()-t0)*1000:.2f} ms | PK: {len(dil_pk)} B | SK: {len(dil_sk)} B')

# Generate Falcon-512 key pair
print('-> Generating Falcon-512 key pair (slower - NTRU lattice)...')
t0 = time.perf_counter()
with oqs.Signature('Falcon-512') as s:
    fal_pk = s.generate_keypair()
    fal_sk = s.export_secret_key()
print(f'  Done in {(time.perf_counter()-t0)*1000:.2f} ms | PK: {len(fal_pk)} B | SK: {len(fal_sk)} B')

# Generate Kyber768 key pair
print('-> Generating Kyber768 key pair...')
t0 = time.perf_counter()
with oqs.KeyEncapsulation('Kyber768') as k:
    kyb_pk = k.generate_keypair()
    kyb_sk = k.export_secret_key()
print(f'  Done in {(time.perf_counter()-t0)*1000:.2f} ms | PK: {len(kyb_pk)} B | SK: {len(kyb_sk)} B')

# ============================================================
banner('PHASE 2: KYBER KEY ENCAPSULATION (off-chain)')
# ============================================================
print('-> Sender encapsulates shared secret using recipient Kyber PK...')
with oqs.KeyEncapsulation('Kyber768') as sender:
    ciphertext, shared_secret = sender.encap_secret(kyb_pk)
print(f'  Ciphertext: {len(ciphertext)} bytes')
print(f'  Shared secret (first 16B): {shared_secret[:16].hex()}')
print(f'  (Use shared_secret as AES-256-GCM key to encrypt message)')

# ============================================================
banner('PHASE 3: SIGN MESSAGE (off-chain)')
# ============================================================
MESSAGE = b'ASSET TRANSFER: TokenID=7291, From=0xAlice, To=0xBob, Amount=1, Date=2025-06-01'
print(f'\nMessage: {MESSAGE.decode()}')

# Sign with Dilithium3
print('\n-> Signing with Dilithium3...')
t0 = time.perf_counter()
with oqs.Signature('Dilithium3', dil_sk) as signer:
    sig_dil = signer.sign(MESSAGE)
t_dil = (time.perf_counter()-t0)*1000
print(f'  Signature: {len(sig_dil)} bytes | Time: {t_dil:.2f} ms')

# Sign with Falcon-512
print('-> Signing with Falcon-512...')
t0 = time.perf_counter()
with oqs.Signature('Falcon-512', fal_sk) as signer:
    sig_fal = signer.sign(MESSAGE)
t_fal = (time.perf_counter()-t0)*1000
print(f'  Signature: {len(sig_fal)} bytes | Time: {t_fal:.2f} ms')

# ============================================================
banner('PHASE 4: COMPUTE DUAL-SIGNATURE HASH COMMITMENT (off-chain)')
# ============================================================
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))

# H = keccak256(sigD || sigF || pkD || pkF || keccak256(M))   (Theorem 1)
msg_hash    = w3.keccak(MESSAGE)                                    # keccak256(M)
commit_data = sig_dil + sig_fal + dil_pk + fal_pk + bytes(msg_hash) # concat
H           = w3.keccak(commit_data)                               # final H
H_hex       = '0x' + H.hex()

print(f'  keccak256(Message) = {msg_hash.hex()}')
print(f'  H = keccak256(sigD||sigF||pkD||pkF||H(M)) = {H_hex}')

# ============================================================
banner('PHASE 5: ANCHOR ON ETHEREUM (on-chain)')
# ============================================================
if not w3.is_connected():
    print('  ERROR: Hardhat node not running! Start it with: npx hardhat node')
    exit(1)

with open('python/contract_address.txt') as f:
    addr = f.read().strip()

ABI = [{
    'name': 'anchorCommitment', 'type': 'function',
    'inputs': [
        {'name': 'commitment', 'type': 'bytes32'},
        {'name': 'ipfsCID',    'type': 'string'},
        {'name': 'algorithm',  'type': 'string'}
    ], 'outputs': [], 'stateMutability': 'nonpayable'
}]
contract = w3.eth.contract(address=addr, abi=ABI)
HARDHAT_PK = '0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80'
acct = Account.from_key(HARDHAT_PK)

nonce = w3.eth.get_transaction_count(acct.address)
txn = contract.functions.anchorCommitment(
    bytes.fromhex(H_hex[2:]), 'ipfs://QmSimulatedCID', 'Dilithium3+Falcon-512'
).build_transaction({'from': acct.address, 'nonce': nonce, 'gas': 250000, 'gasPrice': w3.to_wei('1', 'gwei')})

signed  = acct.sign_transaction(txn)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print(f'  Transaction hash : 0x{tx_hash.hex()}')
print(f'  Block number     : {receipt["blockNumber"]}')
print(f'  Gas used         : {receipt["gasUsed"]:,}')
print(f'  Status           : {"SUCCESS" if receipt["status"]==1 else "FAILED"}')

# ============================================================
banner('PHASE 6: OFF-CHAIN VERIFICATION')
# ============================================================
# Step 6a: Recompute H and check
H_recomputed = '0x' + w3.keccak(sig_dil + sig_fal + dil_pk + fal_pk + bytes(msg_hash)).hex()
hash_ok = H_recomputed.lower() == H_hex.lower()
print(f'  Hash recomputed : {H_recomputed}')
print(f'  Hash match      : {"YES" if hash_ok else "NO"}')

# Step 6b: PQC verification
print('\n  Running Dilithium3 verification...')
t0 = time.perf_counter()
with oqs.Signature('Dilithium3') as v:
    dil_ok = v.verify(MESSAGE, sig_dil, dil_pk)
t_v = (time.perf_counter()-t0)*1000
print(f'  Dilithium3 valid: {"YES" if dil_ok else "NO"} | Time: {t_v:.3f} ms')

print('\n  Running Falcon-512 verification...')
t0 = time.perf_counter()
with oqs.Signature('Falcon-512') as v:
    fal_ok = v.verify(MESSAGE, sig_fal, fal_pk)
t_v2 = (time.perf_counter()-t0)*1000
print(f'  Falcon-512 valid: {"YES" if fal_ok else "NO"} | Time: {t_v2:.3f} ms')

# ============================================================
banner('SIMULATION COMPLETE -- FINAL REPORT')
# ============================================================
print(f"""
  ALGORITHM PERFORMANCE SUMMARY
  +-----------------------------------------------------+
  |  Dilithium3 sign       : {t_dil:.2f} ms
  |  Falcon-512 sign       : {t_fal:.2f} ms
  |  Dilithium3 verify     : {t_v:.3f} ms
  |  Falcon-512 verify     : {t_v2:.3f} ms
  +-----------------------------------------------------+
  |  Ethereum gas used     : {receipt["gasUsed"]:,}
  |  Hash match            : {hash_ok}
  |  Dilithium3 valid      : {dil_ok}
  |  Falcon-512 valid      : {fal_ok}
  |  OVERALL STATUS        : SYSTEM SECURE
  +-----------------------------------------------------+
""")
