"""
tests/test_verify_logic.py

Tests for the hash-match verification logic from verify_offline.py.
Uses fixed synthetic bytes — no oqs or Hardhat node required.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from commitment import compute_commitment, keccak256


def verify_commitment_hash(
    commitment_onchain: bytes,
    sig_dilithium: bytes,
    sig_falcon: bytes,
    pk_dilithium: bytes,
    pk_falcon: bytes,
    message: bytes,
) -> bool:
    """
    Mirror of the hash-match logic in verify_offline.py, extracted as a
    pure function for testing.  Returns True if the recomputed commitment
    matches the on-chain value.
    """
    recomputed = compute_commitment(sig_dilithium, sig_falcon,
                                    pk_dilithium, pk_falcon, message)
    return recomputed == commitment_onchain


# Synthetic material
MSG   = b'Asset transfer document payload'
SIG_D = bytes([0xAA] * 3293)
SIG_F = bytes([0xBB] * 666)
PK_D  = bytes([0xCC] * 1952)
PK_F  = bytes([0xDD] * 897)


@pytest.fixture
def valid_commitment():
    return compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)


class TestVerifyCommitmentHash:
    def test_valid_inputs_pass(self, valid_commitment):
        assert verify_commitment_hash(
            valid_commitment, SIG_D, SIG_F, PK_D, PK_F, MSG
        ) is True

    def test_tampered_message_fails(self, valid_commitment):
        bad_msg = MSG[:-1] + bytes([MSG[-1] ^ 0xFF])
        assert verify_commitment_hash(
            valid_commitment, SIG_D, SIG_F, PK_D, PK_F, bad_msg
        ) is False

    def test_tampered_sig_dilithium_fails(self, valid_commitment):
        bad_sig = bytes([0x00] * len(SIG_D))
        assert verify_commitment_hash(
            valid_commitment, bad_sig, SIG_F, PK_D, PK_F, MSG
        ) is False

    def test_tampered_sig_falcon_fails(self, valid_commitment):
        bad_sig = bytes([0x00] * len(SIG_F))
        assert verify_commitment_hash(
            valid_commitment, SIG_D, bad_sig, PK_D, PK_F, MSG
        ) is False

    def test_tampered_pk_dilithium_fails(self, valid_commitment):
        bad_pk = bytes([0x00] * len(PK_D))
        assert verify_commitment_hash(
            valid_commitment, SIG_D, SIG_F, bad_pk, PK_F, MSG
        ) is False

    def test_tampered_pk_falcon_fails(self, valid_commitment):
        bad_pk = bytes([0x00] * len(PK_F))
        assert verify_commitment_hash(
            valid_commitment, SIG_D, SIG_F, PK_D, bad_pk, MSG
        ) is False

    def test_wrong_commitment_fails(self):
        wrong_commitment = bytes([0x00] * 32)
        assert verify_commitment_hash(
            wrong_commitment, SIG_D, SIG_F, PK_D, PK_F, MSG
        ) is False

    def test_correct_commitment_length_is_32_bytes(self, valid_commitment):
        assert len(valid_commitment) == 32
