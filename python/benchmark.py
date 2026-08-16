#!/usr/bin/env python3
"""
PQC OPERATION BENCHMARK  (reproduces Table 6 of the paper)

Runs each cryptographic operation N times (default 1,000) and reports
mean / min / max / standard deviation in milliseconds:

    Kyber-768   key generation, encapsulation, decapsulation
    Dilithium3  key generation, signing, verification
    Falcon-512  key generation, signing, verification
    keccak256   commitment hashing

Falcon-512 key generation is deliberately measured over the full sample because
its Gaussian trapdoor sampler is not constant-time; the reported sigma captures
that spread (see Section 7.1).

Run:  python python/benchmark.py            # 1,000 iterations (paper default)
      python python/benchmark.py 200        # custom iteration count (quick run)
"""
import os
import sys
import json
import time
import statistics
import oqs
from web3 import Web3

os.makedirs('keys', exist_ok=True)

# ── Configuration ──────────────────────────────────────────────────────────
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
MESSAGE = b'benchmark message payload for PQC operation latency measurement'
w3 = Web3()  # keccak256 only

print('=' * 68)
print(f'  PQC OPERATION BENCHMARK  ({N:,} iterations per operation)')
print('=' * 68)


def bench(label, setup, op):
    """Time `op` N times. `setup` runs once and returns the context handed to op.

    Only the timed region around op() is measured; setup cost is excluded so the
    numbers isolate the operation itself (matching the paper's methodology).
    """
    ctx = setup()
    samples = []
    for _ in range(N):
        t0 = time.perf_counter()
        op(ctx)
        samples.append((time.perf_counter() - t0) * 1000.0)  # ms
    row = {
        'operation': label,
        'mean': statistics.fmean(samples),
        'min':  min(samples),
        'max':  max(samples),
        'sigma': statistics.pstdev(samples),
    }
    print(f'  {label:<32} mean={row["mean"]:8.3f}  min={row["min"]:8.3f}  '
          f'max={row["max"]:8.3f}  sigma={row["sigma"]:7.3f}')
    return row


results = []

# ── Kyber-768 ──────────────────────────────────────────────────────────────
# key generation: fresh keypair each iteration
def kyber_kg_op(_):
    with oqs.KeyEncapsulation('Kyber768') as k:
        k.generate_keypair()

results.append(bench('Kyber-768 key generation', lambda: None, kyber_kg_op))

# encapsulation: reuse one recipient public key, encapsulate each iteration
def kyber_enc_setup():
    with oqs.KeyEncapsulation('Kyber768') as k:
        pk = k.generate_keypair()
    return {'pk': pk, 'kem': oqs.KeyEncapsulation('Kyber768')}

def kyber_enc_op(ctx):
    ctx['kem'].encap_secret(ctx['pk'])

results.append(bench('Kyber-768 encapsulation', kyber_enc_setup, kyber_enc_op))

# decapsulation: fixed keypair + fixed ciphertext, decapsulate each iteration
def kyber_dec_setup():
    kem = oqs.KeyEncapsulation('Kyber768')
    pk  = kem.generate_keypair()
    with oqs.KeyEncapsulation('Kyber768') as sender:
        ct, _ = sender.encap_secret(pk)
    return {'kem': kem, 'ct': ct}

def kyber_dec_op(ctx):
    ctx['kem'].decap_secret(ctx['ct'])

results.append(bench('Kyber-768 decapsulation', kyber_dec_setup, kyber_dec_op))

# ── Dilithium3 ─────────────────────────────────────────────────────────────
def dil_kg_op(_):
    with oqs.Signature('Dilithium3') as s:
        s.generate_keypair()

results.append(bench('Dilithium3 key generation', lambda: None, dil_kg_op))

def dil_sign_setup():
    s = oqs.Signature('Dilithium3')
    s.generate_keypair()
    return {'signer': s}

def dil_sign_op(ctx):
    ctx['signer'].sign(MESSAGE)

results.append(bench('Dilithium3 signing', dil_sign_setup, dil_sign_op))

def dil_verify_setup():
    s = oqs.Signature('Dilithium3')
    pk = s.generate_keypair()
    sig = s.sign(MESSAGE)
    return {'verifier': oqs.Signature('Dilithium3'), 'pk': pk, 'sig': sig}

def dil_verify_op(ctx):
    ctx['verifier'].verify(MESSAGE, ctx['sig'], ctx['pk'])

results.append(bench('Dilithium3 verification', dil_verify_setup, dil_verify_op))

# ── Falcon-512 ─────────────────────────────────────────────────────────────
def fal_kg_op(_):
    with oqs.Signature('Falcon-512') as s:
        s.generate_keypair()

results.append(bench('Falcon-512 key generation', lambda: None, fal_kg_op))

def fal_sign_setup():
    s = oqs.Signature('Falcon-512')
    s.generate_keypair()
    return {'signer': s}

def fal_sign_op(ctx):
    ctx['signer'].sign(MESSAGE)

results.append(bench('Falcon-512 signing', fal_sign_setup, fal_sign_op))

def fal_verify_setup():
    s = oqs.Signature('Falcon-512')
    pk = s.generate_keypair()
    sig = s.sign(MESSAGE)
    return {'verifier': oqs.Signature('Falcon-512'), 'pk': pk, 'sig': sig}

def fal_verify_op(ctx):
    ctx['verifier'].verify(MESSAGE, ctx['sig'], ctx['pk'])

results.append(bench('Falcon-512 verification', fal_verify_setup, fal_verify_op))

# ── keccak256 commitment ───────────────────────────────────────────────────
def keccak_op(_):
    w3.keccak(MESSAGE)

results.append(bench('keccak256 commitment', lambda: None, keccak_op))

# ── Save Table 6 ───────────────────────────────────────────────────────────
out = {'iterations': N, 'unit': 'ms', 'results': results}
with open('keys/benchmark_table6.json', 'w') as f:
    json.dump(out, f, indent=2)

print('=' * 68)
print(f'  Table 6 data saved to keys/benchmark_table6.json ({N:,} iterations)')
print('=' * 68)
