// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title  PQCAnchor — On-chain commitment registry for hybrid PQC signatures
/// @notice Anchors the hybrid dual-signature commitment
///         H = keccak256(sigD || sigF || pkD || pkF || keccak256(message))
///         as described in the paper (Theorem 1). Per-anchor storage is kept to a
///         SINGLE cold SSTORE (commitment => signer, ~20,000 gas) so that a full
///         anchoring transaction costs ~46,000 gas, matching Table 7. All auxiliary
///         data (algorithm, IPFS CID, timestamp) is carried in events only — events
///         are not part of contract storage and cost far less than SSTORE.
contract PQCAnchor {

    // ── Events ─────────────────────────────────────────────────
    event SignatureAnchored(
        address indexed signer,       // Ethereum address of anchorer
        bytes32 indexed commitment,   // H = keccak256(sigD||sigF||pkD||pkF||H(msg))
        string  ipfsCID,              // IPFS CID pointing to full signature data
        string  algorithm,            // e.g. 'Dilithium3+Falcon-512'
        uint256 timestamp             // block.timestamp
    );

    event BatchAnchored(
        address indexed signer,       // Ethereum address of anchorer
        bytes32 indexed merkleRoot,   // Merkle root committing to `leafCount` signatures
        uint256 leafCount,            // number of signatures batched under this root
        string  ipfsCID,              // IPFS CID pointing to the batch of full signatures
        uint256 timestamp             // block.timestamp
    );

    // ── State ──────────────────────────────────────────────────
    // A single storage slot per anchor: commitment (or Merkle root) => anchorer.
    // This is the only SSTORE performed per anchoring, which is what keeps the
    // gas cost at ~46,000 (see Table 7 decomposition).
    mapping(bytes32 => address) public anchoredBy;  // commitment => signer

    // ── Errors ─────────────────────────────────────────────────
    error CommitmentAlreadyExists(bytes32 commitment);
    error EmptyCommitment();

    // ── Single-signature / single-commitment anchor ───────────
    /**
     * @notice Anchor one hybrid PQC commitment on-chain.
     * @param commitment  keccak256(sigD || sigF || pkD || pkF || keccak256(message))
     * @param ipfsCID     IPFS CIDv1 where the full signature data is stored
     * @param algorithm   Name(s) of the PQC scheme(s) used ('Dilithium3+Falcon-512')
     */
    function anchorCommitment(
        bytes32 commitment,
        string calldata ipfsCID,
        string calldata algorithm
    ) external {
        if (commitment == bytes32(0)) revert EmptyCommitment();
        if (anchoredBy[commitment] != address(0))
            revert CommitmentAlreadyExists(commitment);

        anchoredBy[commitment] = msg.sender;   // single cold SSTORE (~20,000 gas)

        emit SignatureAnchored(
            msg.sender, commitment, ipfsCID, algorithm, block.timestamp
        );
    }

    // ── Merkle-root batch anchor (Table 8) ─────────────────────
    /**
     * @notice Anchor a single Merkle root that commits to `leafCount` signatures.
     *         The on-chain cost is independent of `leafCount` (still one SSTORE), so
     *         the amortised cost per signature is total_gas / leafCount. This is what
     *         drives the per-signature cost below one cent for large batches (Table 8).
     * @param merkleRoot  keccak256 Merkle root over the per-signature commitments
     * @param leafCount   number of signatures represented by this root
     * @param ipfsCID     IPFS CID where the full batch (leaves + signatures) is stored
     */
    function anchorMerkleRoot(
        bytes32 merkleRoot,
        uint256 leafCount,
        string calldata ipfsCID
    ) external {
        if (merkleRoot == bytes32(0)) revert EmptyCommitment();
        if (anchoredBy[merkleRoot] != address(0))
            revert CommitmentAlreadyExists(merkleRoot);

        anchoredBy[merkleRoot] = msg.sender;   // single cold SSTORE (~20,000 gas)

        emit BatchAnchored(
            msg.sender, merkleRoot, leafCount, ipfsCID, block.timestamp
        );
    }

    // ── Views ──────────────────────────────────────────────────
    /**
     * @notice Check whether a commitment (or Merkle root) is registered.
     * @return exists true if the commitment is registered
     * @return signer Ethereum address that anchored it (zero if not registered)
     * @dev    Algorithm, IPFS CID and timestamp are available from the emitted
     *         SignatureAnchored / BatchAnchored events (kept out of storage for gas).
     */
    function checkCommitment(bytes32 commitment)
        external view
        returns (bool exists, address signer)
    {
        signer = anchoredBy[commitment];
        exists = (signer != address(0));
    }

    // ── On-chain hash helper (convenience) ────────────────────
    /**
     * @notice Recompute the hybrid dual-signature commitment on-chain so any verifier
     *         can confirm the exact hash formula used off-chain.
     *         H = keccak256(sigD || sigF || pkD || pkF || keccak256(message))
     */
    function computeCommitment(
        bytes calldata sigD,          // Dilithium3 signature
        bytes calldata sigF,          // Falcon-512 signature
        bytes calldata pkD,           // Dilithium3 public key
        bytes calldata pkF,           // Falcon-512 public key
        bytes32 messageHash           // keccak256(message)
    ) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(sigD, sigF, pkD, pkF, messageHash));
    }
}
