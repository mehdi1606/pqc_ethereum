// test/test_anchor.js
const { expect }  = require('chai');
const { ethers }  = require('hardhat');

describe('PQCAnchor Contract Tests', function () {
  let contract, owner, addr1;

  // ── Fake PQC data for Ethereum-only testing ──────────────────────────
  // In real integration, these come from the Python signing scripts.
  // Here we simulate the 32-byte commitment hash.
  const fakeCommitment = ethers.keccak256(
    ethers.toUtf8Bytes('fake_sig_bytes || fake_pk_bytes || keccak256(msg)')
  );
  const ipfsCID   = 'bafkreiexamplecidhashfordemopurposes';
  const algorithm = 'Dilithium3';

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const PQCAnchor = await ethers.getContractFactory('PQCAnchor');
    contract = await PQCAnchor.deploy();
    await contract.waitForDeployment();
  });

  // ── TEST 1: Basic anchoring ───────────────────────────────────────────
  it('Should anchor a commitment and emit event', async function () {
    const tx = await contract.anchorCommitment(fakeCommitment, ipfsCID, algorithm);
    const receipt = await tx.wait();

    // Verify event was emitted
    const events = receipt.logs.map(log => {
      try { return contract.interface.parseLog(log); } catch { return null; }
    }).filter(Boolean);

    expect(events[0].name).to.equal('SignatureAnchored');
    expect(events[0].args.signer).to.equal(owner.address);
    expect(events[0].args.commitment).to.equal(fakeCommitment);
    expect(events[0].args.algorithm).to.equal('Dilithium3');

    console.log(`    Gas used: ${receipt.gasUsed.toString()}`);
  });

  // ── TEST 2: Gas cost measurement ─────────────────────────────────────
  it('Should measure exact gas cost for anchoring', async function () {
    const gasEstimate = await contract.anchorCommitment.estimateGas(
      fakeCommitment, ipfsCID, algorithm
    );
    console.log(`    Estimated gas: ${gasEstimate.toString()}`);

    const tx      = await contract.anchorCommitment(fakeCommitment, ipfsCID, algorithm);
    const receipt = await tx.wait();
    console.log(`    Actual gas:    ${receipt.gasUsed.toString()}`);

    // Gas should be under 250,000 for a simple commitment
    expect(Number(receipt.gasUsed)).to.be.lessThan(250000);
  });

  // ── TEST 3: Prevent duplicate commitments ────────────────────────────
  it('Should revert on duplicate commitment', async function () {
    await contract.anchorCommitment(fakeCommitment, ipfsCID, algorithm);
    await expect(
      contract.anchorCommitment(fakeCommitment, ipfsCID, algorithm)
    ).to.be.revertedWithCustomError(contract, 'CommitmentAlreadyExists');
  });

  // ── TEST 4: Batch anchoring gas analysis ─────────────────────────────
  it('Should measure gas for 10 different commitments (batch simulation)', async function () {
    const gasValues = [];
    for (let i = 0; i < 10; i++) {
      const c = ethers.keccak256(ethers.toUtf8Bytes(`commitment_${i}`));
      const tx = await contract.anchorCommitment(c, `ipfs_cid_${i}`, 'Dilithium3');
      const r  = await tx.wait();
      gasValues.push(Number(r.gasUsed));
    }
    const avg = gasValues.reduce((a,b)=>a+b,0) / gasValues.length;
    const first = gasValues[0]; // first SSTORE is cold (expensive)
    const rest  = gasValues.slice(1);
    const avgWarm = rest.reduce((a,b)=>a+b,0) / rest.length;
    console.log(`    Gas for commitment #1 (cold SSTORE): ${first}`);
    console.log(`    Average gas for commits #2-10:       ${Math.round(avgWarm)}`);
    console.log(`    All gas values: [${gasValues.join(', ')}]`);
  });

  // ── TEST 5: On-chain hash computation helper ─────────────────────────
  it('Should compute commitment hash on-chain matching off-chain Python', async function () {
    const fakeSig = ethers.toUtf8Bytes('fake_dilithium3_signature_bytes');
    const fakePK  = ethers.toUtf8Bytes('fake_dilithium3_public_key_bytes');
    const msgHash = ethers.keccak256(ethers.toUtf8Bytes('test message'));

    const onchainH = await contract.computeCommitment(fakeSig, fakePK, msgHash);

    // Verify this matches what Python computes:
    // H = keccak256(sig_bytes || pk_bytes || msg_hash_bytes)
    const offchainH = ethers.keccak256(
      ethers.concat([fakeSig, fakePK, msgHash])
    );
    expect(onchainH).to.equal(offchainH);
    console.log(`    Commitment H: ${onchainH}`);
  });
});
