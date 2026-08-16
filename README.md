# PQC + Ethereum

Post-Quantum Cryptography anchored to Ethereum using CRYSTALS-Dilithium, Falcon, and Kyber via the Open Quantum Safe (liboqs) library.

## What This Project Does

Signs messages with quantum-resistant algorithms off-chain, computes a compact 32-byte commitment hash, and anchors it on an Ethereum smart contract — providing a tamper-evident, publicly verifiable record.

```
Off-chain (Python/liboqs)                 On-chain (Solidity/Ethereum)
─────────────────────────                 ────────────────────────────
Dilithium3 + Falcon-512 sign          →   PQCAnchor.anchorCommitment()
Kyber-768 key encapsulation               stores commitment => signer (1 SSTORE)
H = keccak256(sigD||sigF||pkD||pkF||H(m)) →   ~46,000 gas per anchor
```

The commitment binds **both** PQC signatures and **both** public keys (Theorem 1),
so the joint quantum-forgery bound covers the exact object anchored on-chain.

## Algorithms

| Algorithm | Role | PK Size | Sig/CT | Security |
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
│   ├── test_anchor.js         <- Hardhat JavaScript tests
│   └── test_merkle_batch.js   <- Merkle batch gas tests (Table 8)
├── python/
│   ├── keygen.py              <- PQC key generation
│   ├── sign_message.py        <- Dual-signature hash commitment
│   ├── verify_offline.py      <- Off-chain verification
│   ├── kyber_exchange.py      <- Key encapsulation demo
│   ├── anchor_onchain.py      <- Submit to Ethereum
│   ├── benchmark.py           <- 1,000-iteration latency benchmark (Table 6)
│   ├── merkle_batch.py        <- Merkle batch anchoring sweep (Table 8)
│   └── full_simulation.py     <- Complete end-to-end run
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

### Step 1 — Install Python dependencies

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install liboqs web3 eth-account pysha3
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
python python/sign_message.py     # Step 2: sign & compute commitment
python python/anchor_onchain.py   # Step 3: anchor on Ethereum
python python/verify_offline.py   # Step 4: verify off-chain
python python/kyber_exchange.py   # Step 5: Kyber KEM demo
```

Or run everything at once:
```bash
python python/full_simulation.py
```

### Reproduce the paper tables

```bash
python python/benchmark.py           # Table 6: latencies over 1,000 iterations
                                     # (pass a smaller count for a quick run, e.g. 200)
python python/merkle_batch.py        # Table 8: Merkle batch gas / cost per signature
                                     # (needs a running node + deployed contract)
```

Table 8 is also reproduced purely on-chain (no Python/liboqs needed) by:
```bash
npx hardhat test test/test_merkle_batch.js
```

## Gas Costs

Per-anchor storage is a single `commitment => signer` slot (one cold SSTORE), so a
full anchoring transaction costs ~46,000 gas (see paper Table 7). Auxiliary data
(algorithm, IPFS CID, timestamp) is carried in events only.

| Operation | Gas | @ 20 Gwei |
|---|---|---|
| anchorCommitment | ~46,000 | ~$2.78 |
| anchorMerkleRoot (any N) | ~46,000 | ~$2.78 total |
| Merkle batch, per signature (N=100) | ~460 | ~$0.03 |
| Merkle batch, per signature (N=1000) | ~46 | ~$0.003 |
| On L2 (Arbitrum/Optimism) | same gas | ~$0.03–$0.40 |

## Troubleshooting

| Error | Fix |
|---|---|
| `ModuleNotFoundError: oqs` | `pip install liboqs` (not 'oqs') |
| `ConnectionRefusedError` | Run `npx hardhat node` in another terminal |
| `FileNotFoundError: contract_address.txt` | Deploy first: `npx hardhat run scripts/deploy.js --network localhost` |
| `CommitmentAlreadyExists` | Change message content or restart Hardhat node |
| Falcon keygen takes minutes | Normal on some systems; wait or use Dilithium3 only |
