# Security Policy

## Scope

This repository is a **research and demonstration project** implementing hybrid
post-quantum signatures anchored on Ethereum.  It is not a production security
service; the default configuration uses a well-known public Hardhat test key
(`0xac0974...`) that is safe for local development **only**.

---

## Trust Boundaries

| Boundary | Local dev | Real deployment |
|---|---|---|
| Ethereum signer key | Hardhat account #0 (public key, zero value) | HSM / KMS — never in source |
| PQC private keys (`keys/*.bin`) | Generated locally, git-ignored | Secret manager (Vault / AWS KMS) |
| IPFS content | Simulated CID, no real data | Pinning service with integrity check |
| RPC endpoint | `http://127.0.0.1:8545` (Hardhat) | Authenticated provider (Infura, Alchemy) |

---

## Threat Model

### Assets

1. **PQC private keys** (`keys/dilithium3_sk.bin`, `keys/falcon512_sk.bin`)
   - Compromise allows forging signatures attributed to the key owner.
   - *Protection*: Git-ignored. In real deployments, store in a secret manager
     and load at runtime; never write to disk in plaintext.

2. **Ethereum signer key** (`HARDHAT_PK`)
   - Compromise allows anyone to anchor commitments as the key owner.
   - *Protection*: Loaded from `.env` via `python-dotenv`, never committed.
     In real deployments, use a hardware wallet or KMS signer.

3. **IPFS content**
   - The on-chain CID is the tamper-evident reference to off-chain data.
     An attacker who can replace IPFS content can substitute forged material.
   - *Protection*: The commitment hash `H` binds the signatures and public
     keys; a content swap is detectable by recomputing `H` from the retrieved
     data and comparing it to the on-chain value.

### Attack vectors considered

| Vector | Mitigation |
|---|---|
| Key material committed to git | `.gitignore` covers `keys/*.bin`, `.env` |
| Replay of a previous commitment | Smart contract rejects duplicate `bytes32` commitments |
| Commitment hash collision | `keccak256` provides 256-bit collision resistance |
| Weak classical / quantum signature | Dual-algorithm scheme: both Dilithium3 and Falcon-512 must be broken simultaneously |
| On-chain data tampering | Ethereum immutability; `CommitmentAlreadyExists` guard |
| IPFS content swap | Detectable by recomputing `H` from fetched data |

---

## Using This Code in a Real Deployment

> **Warning:** The default `.env.example` ships with the public Hardhat test
> private key.  This key has **no real value** on local networks, but if copied
> to a mainnet deployment it would be immediately drained.

Checklist before any non-local use:

- [ ] Generate a fresh Ethereum key; store it in KMS / HSM, never in `.env`
- [ ] Replace the IPFS CID placeholder with a real pinned CID
- [ ] Remove the `keys/` directory from any deployment artifact
- [ ] Audit `requirements.txt` and `package.json` transitive deps
- [ ] Point `RPC_URL` to an authenticated provider endpoint
- [ ] Review the Solidity contract for reentrancy and access-control needs

---

## Reporting Vulnerabilities

This is a research demo.  If you find a conceptual flaw in the cryptographic
construction or a code-level bug with security implications, please open a
GitHub issue or contact the author directly.
