#!/usr/bin/env python3
"""
KEY GENERATION SCRIPT
Generates: Dilithium3, Falcon-512, Kyber-768 key pairs
Run: python python/keygen.py
"""
import oqs
import os
import json
import time

os.makedirs('keys', exist_ok=True)

def generate_and_save(alg_name, alg_type='sig'):
    print(f'\n=== Generating {alg_name} keys ===')
    start = time.perf_counter()

    if alg_type == 'sig':
        with oqs.Signature(alg_name) as signer:
            public_key  = signer.generate_keypair()
            private_key = signer.export_secret_key()
            details = signer.details
    elif alg_type == 'kem':
        with oqs.KeyEncapsulation(alg_name) as kem:
            public_key  = kem.generate_keypair()
            private_key = kem.export_secret_key()
            details = kem.details

    elapsed = (time.perf_counter() - start) * 1000

    # Save keys as binary files
    safe_name = alg_name.lower().replace('-', '').replace('_', '')
    with open(f'keys/{safe_name}_pk.bin', 'wb') as f: f.write(public_key)
    with open(f'keys/{safe_name}_sk.bin', 'wb') as f: f.write(private_key)

    print(f'  Algorithm  : {alg_name}')
    print(f'  Public key : {len(public_key):,} bytes  ->  keys/{safe_name}_pk.bin')
    print(f'  Private key: {len(private_key):,} bytes  ->  keys/{safe_name}_sk.bin')
    print(f'  Time       : {elapsed:.2f} ms')

    return {'alg': alg_name, 'pk_size': len(public_key), 'sk_size': len(private_key), 'keygen_ms': round(elapsed, 2)}

# ── Generate all key pairs ─────────────────────────────────────────────────
results = []
results.append(generate_and_save('Dilithium3',  'sig'))
results.append(generate_and_save('Falcon-512',  'sig'))
results.append(generate_and_save('Kyber768',    'kem'))

# Save summary
with open('keys/keygen_summary.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\n=== KEY GENERATION COMPLETE ===')
print('All keys saved to keys/ directory')
print('Summary saved to keys/keygen_summary.json')
