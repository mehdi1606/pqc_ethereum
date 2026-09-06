#!/usr/bin/env python3
"""
commitment.py — Pure functions for hybrid PQC commitment computation.

Extracted from sign_message.py so they can be imported and unit-tested
without requiring a live Hardhat node or real oqs key material.
"""
from web3 import Web3

_w3 = Web3()  # used only for keccak256; no network needed


def compute_commitment(
    sig_dilithium: bytes,
    sig_falcon: bytes,
    pk_dilithium: bytes,
    pk_falcon: bytes,
    message: bytes,
) -> bytes:
    """
    Compute the hybrid PQC commitment hash.

    H = keccak256(sig_D || sig_F || pk_D || pk_F || keccak256(message))

    All inputs are raw bytes.  Returns a 32-byte commitment digest.
    """
    msg_hash = bytes(_w3.keccak(message))
    commit_data = sig_dilithium + sig_falcon + pk_dilithium + pk_falcon + msg_hash
    return bytes(_w3.keccak(commit_data))


def keccak256(data: bytes) -> bytes:
    """Return raw 32-byte keccak256 of *data*."""
    return bytes(_w3.keccak(data))
