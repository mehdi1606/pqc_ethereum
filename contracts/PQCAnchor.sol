// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/// @title PQCAnchor — On-chain commitment registry for PQC signatures
/// @notice Stores keccak256(pqc_signature || pqc_pubkey || keccak256(message))
contract PQCAnchor {

    // ── Events ─────────────────────────────────────────────────
    event SignatureAnchored(
        address indexed signer,       // Ethereum address of anchorer
        bytes32 indexed commitment,   // H = keccak256(sig||pk||H(msg))
        string  ipfsCID,              // IPFS CID pointing to full sig
        string  algorithm,            // e.g. 'Dilithium3' or 'Falcon-512'
        uint256 timestamp             // block.timestamp
    );

    // ── State ──────────────────────────────────────────────────
    struct Anchor {
        address signer;
        uint256 timestamp;
        string  algorithm;
        string  ipfsCID;
    }

    mapping(bytes32 => Anchor) public anchors;  // commitment => Anchor
    uint256 public totalAnchors;

    // ── Errors ─────────────────────────────────────────────────
    error CommitmentAlreadyExists(bytes32 commitment);
    error EmptyCommitment();

    // ── Main function ──────────────────────────────────────────
    /**
     * @notice Anchor a PQC signature commitment on-chain
     * @param commitment  keccak256(sigma_pqc || pk_pqc || keccak256(message))
     * @param ipfsCID     IPFS CIDv1 where full signature data is stored
     * @param algorithm   Name of PQC algorithm used ('Dilithium3', etc.)
     */
    function anchorCommitment(
        bytes32 commitment,
        string calldata ipfsCID,
        string calldata algorithm
    ) external {
        if (commitment == bytes32(0)) revert EmptyCommitment();
        if (anchors[commitment].signer != address(0))
            revert CommitmentAlreadyExists(commitment);

        anchors[commitment] = Anchor({
            signer:    msg.sender,
            timestamp: block.timestamp,
            algorithm: algorithm,
            ipfsCID:   ipfsCID
        });
        totalAnchors++;

        emit SignatureAnchored(
            msg.sender, commitment, ipfsCID, algorithm, block.timestamp
        );
    }

    // ── Verification helper ────────────────────────────────────
    /**
     * @notice Check if a commitment exists and who anchored it
     * @return exists    true if commitment is registered
     * @return signer    Ethereum address that anchored it
     * @return timestamp Block time when anchored
     * @return algo      Algorithm name used
     */
    function checkCommitment(bytes32 commitment)
        external view
        returns (bool exists, address signer, uint256 timestamp, string memory algo)
    {
        Anchor memory a = anchors[commitment];
        exists    = (a.signer != address(0));
        signer    = a.signer;
        timestamp = a.timestamp;
        algo      = a.algorithm;
    }

    // ── On-chain hash helper (convenience) ────────────────────
    /**
     * @notice Compute the commitment hash on-chain for verification
     *         Useful for verifiers who want to confirm the hash formula
     */
    function computeCommitment(
        bytes calldata pqcSignature,
        bytes calldata pqcPublicKey,
        bytes32 messageHash
    ) external pure returns (bytes32) {
        return keccak256(abi.encodePacked(pqcSignature, pqcPublicKey, messageHash));
    }
}
