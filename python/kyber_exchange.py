#!/usr/bin/env python3
"""
KYBER KEY ENCAPSULATION DEMO
Demonstrates a full Kyber768 key exchange between Alice (sender) and Bob (receiver)
Shows how a shared secret is established for encrypting the signed message
Run: python python/kyber_exchange.py
"""
import oqs
import os
import time

print('=== KYBER-768 KEY ENCAPSULATION DEMO ===')

# ── BOB: Key Generation (done once, public key distributed to Alice) ──────
print('\n[BOB] Generating Kyber768 key pair...')
t0 = time.perf_counter()
with oqs.KeyEncapsulation('Kyber768') as bob:
    bob_pk = bob.generate_keypair()    # Bob's public key (shared with Alice)
    bob_sk = bob.export_secret_key()   # Bob's private key (kept secret)
    t_kg = (time.perf_counter() - t0) * 1000

print(f'  Bob public key size  : {len(bob_pk):,} bytes ({t_kg:.2f} ms)')
print(f'  Bob private key size : {len(bob_sk):,} bytes')
print(f'  Bob PK (first 32B)   : {bob_pk[:32].hex()}')

# ── ALICE: Encapsulate (generates ciphertext + shared secret) ─────────────
print("\n[ALICE] Encapsulating shared secret using Bob's public key...")
t0 = time.perf_counter()
with oqs.KeyEncapsulation('Kyber768') as alice:
    ciphertext, ss_alice = alice.encap_secret(bob_pk)
    t_enc = (time.perf_counter() - t0) * 1000

print(f'  Ciphertext size       : {len(ciphertext):,} bytes')
print(f'  Alice shared secret   : {ss_alice.hex()}')
print(f'  Encapsulation time    : {t_enc:.2f} ms')

# ── BOB: Decapsulate (recovers the same shared secret) ────────────────────
print('\n[BOB] Decapsulating to recover shared secret...')
t0 = time.perf_counter()
with oqs.KeyEncapsulation('Kyber768', bob_sk) as bob_dec:
    ss_bob = bob_dec.decap_secret(ciphertext)
    t_dec = (time.perf_counter() - t0) * 1000

print(f'  Bob shared secret     : {ss_bob.hex()}')
print(f'  Decapsulation time    : {t_dec:.2f} ms')

# ── Verify shared secrets match ───────────────────────────────────────────
match = (ss_alice == ss_bob)
print(f'\n  Shared secrets match  : {"YES -- secure channel established" if match else "NO -- ERROR"}')

if match:
    print(f'  Shared secret (32B)   : {ss_alice.hex()}')
    print('  This 32-byte key can now be used as AES-256-GCM key')
    print('  to encrypt the signed message payload.')
