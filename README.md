# PQC + Ethereum

Post-Quantum Cryptography anchored to Ethereum using CRYSTALS-Dilithium, Falcon, and Kyber via the Open Quantum Safe (liboqs) library.

## What This Project Does

Signs messages with quantum-resistant algorithms off-chain, computes a compact 32-byte commitment hash, and anchors it on an Ethereum smart contract — providing a tamper-evident, publicly verifiable record.

```
Off-chain (Python/liboqs)               On-chain (Solidity/Ethereum)
──────────────────────────────────────  ────────────────────────────────────
Dilithium3 + Falcon-512 sign        →   PQCAnchor.anchorCommitment()
Kyber-768 key encapsulation             stores H on-chain (~184,000 gas cold)
H = keccak256(sig_D||sig_F||pk_D||pk_F||H(msg))
                                    →   Merkle-tree batching: ~122,000 gas
                                        per-sig cost drops >99% at N≥500
```

## Algorithms

| Algorithm | Role | PK Size | Sig / CT | Security |
|---|---|---|---|---|
| CRYSTALS-Dilithium3 | Signature | 1,952 B | 3,293 B | NIST Level 3 |
| Falcon-512 | Signature | 897 B | ~666 B | NIST Level 1 |
| CRYSTALS-Kyber-768 | KEM | 1,184 B | 1,088 B CT | NIST Level 3 |

## Project Structure

```
pqc_ethereum/
├── contracts/
│   └── PQCAnchor.sol          <- Ethereum smart contract
├── scripts/
│   └── deploy.js              <- Hardhat deployment script
├── test/
│   ├── test_anchor.js         <- Hardhat tests (gas, events, duplicates)
│   └── test_batch.js          <- Merkle-tree batch anchoring tests
├── python/
│   ├── keygen.py              <- PQC key generation
│   ├── sign_message.py        <- Dual-sig (Dilithium3 + Falcon-512) & commitment
│   ├── verify_offline.py      <- Verifies both signatures + commitment hash
│   ├── kyber_exchange.py      <- Full KEM: encapsulation + decapsulation
│   ├── anchor_onchain.py      <- Submit commitment H to Ethereum
│   ├── full_simulation.py     <- Complete end-to-end run
│   ├── benchmark.py           <- 1,000-iteration benchmark (Table 6)
│   └── batch_anchor.py        <- Merkle-tree batch anchoring (Table 8)
├── keys/                      <- Generated keys (git-ignored)
├── hardhat.config.js
└── package.json
```

## Prerequisites

- Python 3.10+
- Node.js 18+
- liboqs Python bindings
- Hardhat

## Setup

### Step 0 — Create your local `.env`

```bash
cp .env.example .env
# The default .env.example ships with the public Hardhat test key,
# which is safe for local dev. See SECURITY.md before any real deployment.
```

### Step 1 — Install Python dependencies

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### Step 2 — Verify liboqs

```bash
python -c "
import oqs
print('liboqs version:', oqs.oqs_version())
print('Dilithium3:', 'Dilithium3' in oqs.get_enabled_sig_mechanisms())
print('Falcon-512:', 'Falcon-512' in oqs.get_enabled_sig_mechanisms())
print('Kyber-768:', 'Kyber-768' in oqs.get_enabled_kem_mechanisms())
"
```

### Step 3 — Install Node.js dependencies

```bash
npm install
```

## Running the Simulation

### Python unit tests (no Hardhat node required)

```bash
pytest tests/ -v
```

### Ethereum-only tests (no Python required)

```bash
npx hardhat compile
npx hardhat test
```

### Full end-to-end simulation

**Terminal A** — Start local Ethereum node:
```bash
npx hardhat node
```

**Terminal B** — Deploy contract:
```bash
npx hardhat run scripts/deploy.js --network localhost
```

**Terminal B** — Run each step:
```bash
python python/keygen.py           # Step 1: generate PQC keys
python python/sign_message.py     # Step 2: dual-sign & compute commitment
python python/anchor_onchain.py   # Step 3: anchor H on Ethereum
python python/verify_offline.py   # Step 4: verify both sigs off-chain
python python/kyber_exchange.py   # Step 5: Kyber KEM demo
```

Or run everything at once:
```bash
python python/full_simulation.py
```

### Benchmark (Table 6)

```bash
python python/benchmark.py
```

Run 1,000 independent iterations per operation and reproduce Table 6 from the paper.

### Merkle-tree batch anchoring (Table 8)

```bash
# Requires Hardhat node running and contract deployed (see above)
python python/batch_anchor.py
```

## Gas Costs

Measured on Hardhat with Solidity optimizer (200 runs), 20 Gwei gas price, ETH = $3,000.

| Operation | Gas (measured) | @ 20 Gwei |
|---|---|---|
| anchorCommitment — cold (first anchor, long ipfsCID) | ~184,000 | ~$11.04 |
| anchorCommitment — warm (same contract, short ipfsCID) | ~122,000 | ~$7.32 |
| Merkle root anchor (N=1) | ~140,000 | ~$8.40 |
| Per-sig cost via Merkle batching (N=500) | ~246 gas | ~$0.015 |
| Per-sig cost via Merkle batching (N=1,000) | ~123 gas | ~$0.007 |
| On L2 (Arbitrum/Optimism) | same gas | ~$0.05–$1.00 |

> **Note:** The paper's Table 7 cites ~46,000 gas based on a minimal bytes32-only store.
> The deployed contract stores two dynamic strings (ipfsCID + algorithm name) on-chain,
> each string requiring one or two additional cold SSTORE operations.
> The cost drops dramatically with Merkle-tree batching (Table 8).

## Simulation Results

Run `python python/benchmark.py` to reproduce. Example output format (Table 6):

| Operation | Mean (ms) | Min (ms) | Max (ms) | σ (ms) |
|---|---|---|---|---|
| Kyber768 key generation | — | — | — | — |
| Kyber768 encapsulation | — | — | — | — |
| Kyber768 decapsulation | — | — | — | — |
| Dilithium3 key generation | — | — | — | — |
| Dilithium3 sign (32 B) | — | — | — | — |
| Dilithium3 sign (256 B) | — | — | — | — |
| Dilithium3 sign (1024 B) | — | — | — | — |
| Dilithium3 verification | — | — | — | — |
| Falcon-512 key generation | — | — | — | — |
| Falcon-512 signing (256 B) | — | — | — | — |
| Falcon-512 verification | — | — | — | — |
| keccak256 commitment (dual-sig) | — | — | — | — |

Hardware reference (paper): Intel Core i7-12700K, 32 GB RAM, Ubuntu 22.04 LTS, liboqs 0.9.0 AVX2.

## Security Metrics

| Metric | Value | Meaning |
|---|---|---|
| QARL | > 99.9% | Joint attack probability = 2^−231; resistance = (1 − 2^−231) × 100% |
| QSM | 100% | Dilithium3 offers 128-bit post-quantum security; ECDSA offers 0-bit |
| COE | ~0.92 | Cryptographic overhead efficiency vs. SSCA baseline [11] |

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: oqs` | `pip install liboqs` (not 'oqs') |
| `ConnectionRefusedError` | Run `npx hardhat node` in another terminal |
| `FileNotFoundError: contract_address.txt` | Deploy first: `npx hardhat run scripts/deploy.js --network localhost` |
| `CommitmentAlreadyExists` | Change message content or restart Hardhat node |
| Falcon keygen takes minutes | Normal on some systems; wait or use Dilithium3 only |
