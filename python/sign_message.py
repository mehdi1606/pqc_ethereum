#!/usr/bin/env python3
"""
SIGNING SCRIPT
Loads keys, signs a message with Dilithium3 + Falcon-512,
computes hybrid commitment H = keccak256(sig || pk || keccak256(msg))
Run: python python/sign_message.py
"""
import oqs
import json
import time
from web3 import Web3

# ── The message to sign ────────────────────────────────────────────────────
MESSAGE = b'This document certifies the transfer of asset #4721 from Alice to Bob. Date: 2025-01-01'

# ── Load keys from disk ────────────────────────────────────────────────────
def load_key(path):
    with open(path, 'rb') as f: return f.read()

dil_pk = load_key('keys/dilithium3_pk.bin')
dil_sk = load_key('keys/dilithium3_sk.bin')
fal_pk = load_key('keys/falcon512_pk.bin')
fal_sk = load_key('keys/falcon512_sk.bin')

print(f'Message ({len(MESSAGE)} bytes): {MESSAGE[:60]}...')

# ── Sign with Dilithium3 ──────────────────────────────────────────────────
print('\n[1] Signing with Dilithium3...')
t0 = time.perf_counter()
with oqs.Signature('Dilithium3', dil_sk) as signer:
    sig_dilithium = signer.sign(MESSAGE)
t_dil = (time.perf_counter() - t0) * 1000
print(f'    Signature size : {len(sig_dilithium):,} bytes')
print(f'    Signing time   : {t_dil:.2f} ms')
print(f'    Sig (first 32B): {sig_dilithium[:32].hex()}')

# ── Sign with Falcon-512 ──────────────────────────────────────────────────
print('\n[2] Signing with Falcon-512...')
t0 = time.perf_counter()
with oqs.Signature('Falcon-512', fal_sk) as signer:
    sig_falcon = signer.sign(MESSAGE)
t_fal = (time.perf_counter() - t0) * 1000
print(f'    Signature size : {len(sig_falcon):,} bytes')
print(f'    Signing time   : {t_fal:.2f} ms')

# ── Compute hybrid hash commitment ────────────────────────────────────────
print('\n[3] Computing hybrid commitment H...')
w3 = Web3()  # used only for keccak256

# H = keccak256(sigma_dilithium || pk_dilithium || keccak256(MESSAGE))
msg_hash    = w3.keccak(MESSAGE)                          # 32 bytes
commit_data = sig_dilithium + dil_pk + bytes(msg_hash)    # concatenate
H           = w3.keccak(commit_data)                      # final 32-byte hash

print(f'    keccak256(message)    : {msg_hash.hex()}')
print(f'    Commitment H (32B)    : {H.hex()}')
print(f'    H as bytes32 (0x...)  : 0x{H.hex()}')

# ── Save all data for later use ───────────────────────────────────────────
signing_data = {
    'message_hex':       MESSAGE.hex(),
    'message_hash_hex':  msg_hash.hex(),
    'commitment_H':      '0x' + H.hex(),
    'sig_dilithium_hex': sig_dilithium.hex(),
    'sig_falcon_hex':    sig_falcon.hex(),
    'dil_pk_hex':        dil_pk.hex(),
    'fal_pk_hex':        fal_pk.hex(),
    'algorithm_primary': 'Dilithium3',
    'timing': {
        'dilithium3_sign_ms': round(t_dil, 3),
        'falcon512_sign_ms':  round(t_fal, 3)
    }
}
with open('keys/signing_data.json', 'w') as f:
    json.dump(signing_data, f, indent=2)

print('\nAll signing data saved to keys/signing_data.json')
print('NEXT STEP: run anchor_onchain.py')
