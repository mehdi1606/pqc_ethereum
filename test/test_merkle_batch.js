// test/test_merkle_batch.js
// Reproduces Table 8: Merkle-tree batch anchoring gas / cost per signature.
// A single 32-byte root is anchored per batch, so on-chain cost is ~constant in N
// and the amortised cost per signature falls as 1/N.
const { expect } = require('chai');
const { ethers } = require('hardhat');

// ── keccak256 Merkle root (Ethereum-style; duplicate last node if odd) ──────
function merkleRoot(leaves) {
  if (leaves.length === 1) return leaves[0];
  let level = leaves.slice();
  while (level.length > 1) {
    if (level.length % 2 === 1) level.push(level[level.length - 1]);
    const next = [];
    for (let i = 0; i < level.length; i += 2) {
      next.push(ethers.keccak256(ethers.concat([level[i], level[i + 1]])));
    }
    level = next;
  }
  return level[0];
}

// Reference economics (paper Table 5)
const GAS_PRICE_GWEI = 20n;
const ETH_USD        = 3000;

describe('PQCAnchor Merkle batch anchoring (Table 8)', function () {
  let contract;
  const BATCH_SIZES = [1, 10, 50, 100, 500, 1000];

  beforeEach(async function () {
    const PQCAnchor = await ethers.getContractFactory('PQCAnchor');
    contract = await PQCAnchor.deploy();
    await contract.waitForDeployment();
  });

  it('anchors one Merkle root per batch and drives cost/signature below 1 cent', async function () {
    // Build 1,000 distinct leaves once (stand-in for per-signature commitments).
    const allLeaves = [];
    for (let i = 0; i < 1000; i++) {
      allLeaves.push(ethers.keccak256(ethers.toUtf8Bytes(`leaf_${i}`)));
    }

    console.log(`    ${'Batch N'.padStart(8)} | ${'Total gas'.padStart(10)} | ` +
                `${'Gas/sig'.padStart(10)} | ${'USD/sig'.padStart(12)}`);
    console.log('    ' + '-'.repeat(52));

    let subCentReached = null;
    for (const n of BATCH_SIZES) {
      const root = merkleRoot(allLeaves.slice(0, n));
      const tx   = await contract.anchorMerkleRoot(root, n, `ipfs://batch-${n}`);
      const r    = await tx.wait();

      const totalGas = Number(r.gasUsed);
      const gasPer   = totalGas / n;
      // USD/sig = gas * gasPrice(wei) * (ETH_USD / 1e18) / n
      const usdPer   = Number(BigInt(totalGas) * GAS_PRICE_GWEI * 1000000000n) *
                       (ETH_USD / 1e18) / n;

      console.log(`    ${String(n).padStart(8)} | ${String(totalGas).padStart(10)} | ` +
                  `${gasPer.toFixed(1).padStart(10)} | ${usdPer.toFixed(6).padStart(12)}`);

      // Root anchoring is a single SSTORE regardless of N -> ~46k-ish gas.
      expect(totalGas).to.be.lessThan(70000);
      if (subCentReached === null && usdPer < 0.01) subCentReached = n;
    }

    // The paper's core batching claim: per-signature cost drops below one cent.
    expect(subCentReached).to.not.equal(null);
    console.log(`    Cost per signature falls below $0.01 at batch size N = ${subCentReached}`);
  });
});
