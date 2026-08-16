#!/usr/bin/env python3
"""
OFF-CHAIN VERIFICATION SCRIPT
Simulates a verifier who:
  1. Reads commitment H from the blockchain
  2. Fetches PQC signature + public key from off-chain storage
  3. Recomputes the hash and checks it matches
  4. Runs full PQC signature verification
Run: python python/verify_offline.py
"""
import oqs
import json
import time
from web3 import Web3

print('=' * 55)
print('  OFF-CHAIN PQC VERIFICATION')
print('=' * 55)

# ── Step 1: Read commitment H from blockchain ─────────────────────────────
print('\n[STEP 1] Reading commitment from blockchain...')
with open('keys/tx_receipt.json') as f:
    receipt = json.load(f)
H_onchain = receipt['commitment_H']  # '0x...' from Ethereum
print(f'  H (on-chain): {H_onchain}')

# ── Step 2: Fetch PQC data from off-chain storage ─────────────────────────
# In production: fetch from IPFS using CID stored in the event log
# For simulation: load from local files (simulates IPFS retrieval)
print('\n[STEP 2] Loading PQC data from off-chain storage (simulated IPFS)...')
with open('keys/signing_data.json') as f:
    signing_data = json.load(f)

MESSAGE       = bytes.fromhex(signing_data['message_hex'])
sig_dil_bytes = bytes.fromhex(signing_data['sig_dilithium_hex'])
sig_fal_bytes = bytes.fromhex(signing_data['sig_falcon_hex'])
dil_pk_bytes  = bytes.fromhex(signing_data['dil_pk_hex'])
fal_pk_bytes  = bytes.fromhex(signing_data['fal_pk_hex'])

print(f'  Message ({len(MESSAGE)} bytes): {MESSAGE[:50]}...')
print(f'  Dilithium3 sig / pk : {len(sig_dil_bytes):,} B / {len(dil_pk_bytes):,} B')
print(f'  Falcon-512 sig / pk : {len(sig_fal_bytes):,} B / {len(fal_pk_bytes):,} B')

# ── Step 3: Recompute dual-signature commitment and compare to on-chain H ──
print('\n[STEP 3] Recomputing hybrid dual-signature commitment hash...')
w3 = Web3()
msg_hash    = w3.keccak(MESSAGE)
# H = keccak256(sigD || sigF || pkD || pkF || keccak256(msg))   (Theorem 1)
commit_data = sig_dil_bytes + sig_fal_bytes + dil_pk_bytes + fal_pk_bytes + bytes(msg_hash)
H_computed  = '0x' + w3.keccak(commit_data).hex()

print(f'  H (computed) : {H_computed}')
print(f'  H (on-chain) : {H_onchain}')

hash_match = (H_computed.lower() == H_onchain.lower())
print(f'  Hash match   : {"MATCH" if hash_match else "MISMATCH -- DATA TAMPERED!"}')

if not hash_match:
    print('ABORT: Hash mismatch -- signature data has been modified!')
    exit(1)

# ── Step 4: PQC signature verification (both schemes) ─────────────────────
print('\n[STEP 4] Running PQC signature verification (Dilithium3 + Falcon-512)...')
t0 = time.perf_counter()
with oqs.Signature('Dilithium3') as verifier:
    dil_valid = verifier.verify(MESSAGE, sig_dil_bytes, dil_pk_bytes)
t_dil = (time.perf_counter() - t0) * 1000

t0 = time.perf_counter()
with oqs.Signature('Falcon-512') as verifier:
    fal_valid = verifier.verify(MESSAGE, sig_fal_bytes, fal_pk_bytes)
t_fal = (time.perf_counter() - t0) * 1000

is_valid = dil_valid and fal_valid
print(f'  Dilithium3 verification : {"VALID" if dil_valid else "INVALID"} ({t_dil:.3f} ms)')
print(f'  Falcon-512 verification : {"VALID" if fal_valid else "INVALID"} ({t_fal:.3f} ms)')

# ── Final summary ─────────────────────────────────────────────────────────
print('\n' + '=' * 55)
print('  VERIFICATION SUMMARY')
print('=' * 55)
print(f'  Hash commitment match : {hash_match}')
print(f'  Dilithium3 valid      : {dil_valid}')
print(f'  Falcon-512 valid      : {fal_valid}')
print(f'  OVERALL RESULT        : {"TRUSTED" if (hash_match and is_valid) else "UNTRUSTED"}')
print('=' * 55)
