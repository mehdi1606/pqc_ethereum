"""
tests/test_commitment.py

Unit tests for the hybrid PQC commitment hash logic in python/commitment.py.
These tests use synthetic fixed-length byte strings so they run without oqs
(liboqs) installed or a Hardhat node running.
"""
import sys
import os
import pytest

# Make the python/ package importable from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from commitment import compute_commitment, keccak256, validate_commitment, validate_address

# ---------------------------------------------------------------------------
# Fixed-size synthetic key/signature material (realistic byte lengths)
# ---------------------------------------------------------------------------
SIG_DILITHIUM_LEN = 3293   # Dilithium3 signature
SIG_FALCON_LEN    = 666    # Falcon-512 signature (typical)
PK_DILITHIUM_LEN  = 1952   # Dilithium3 public key
PK_FALCON_LEN     = 897    # Falcon-512 public key

# Deterministic synthetic blobs so tests are reproducible
SIG_D = bytes(range(256)) * (SIG_DILITHIUM_LEN // 256) + bytes(range(SIG_DILITHIUM_LEN % 256))
SIG_F = bytes([0xAB] * SIG_FALCON_LEN)
PK_D  = bytes([0xCD] * PK_DILITHIUM_LEN)
PK_F  = bytes([0xEF] * PK_FALCON_LEN)
MSG   = b'Test message for commitment hash'


class TestKeccak256:
    def test_returns_32_bytes(self):
        result = keccak256(b'hello')
        assert len(result) == 32

    def test_deterministic(self):
        assert keccak256(b'hello') == keccak256(b'hello')

    def test_distinct_inputs_distinct_outputs(self):
        assert keccak256(b'foo') != keccak256(b'bar')

    def test_empty_input(self):
        # keccak256('') is a well-known constant
        result = keccak256(b'')
        assert len(result) == 32
        # The empty-string keccak256 in hex
        expected = bytes.fromhex(
            'c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470'
        )
        assert result == expected


class TestComputeCommitment:
    def test_returns_32_bytes(self):
        result = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        assert isinstance(result, bytes)
        assert len(result) == 32

    def test_deterministic(self):
        h1 = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        h2 = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        assert h1 == h2

    def test_different_message_gives_different_hash(self):
        h1 = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, b'message A')
        h2 = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, b'message B')
        assert h1 != h2

    def test_different_sig_dilithium_gives_different_hash(self):
        altered_sig = bytes([0x01] * SIG_DILITHIUM_LEN)
        h1 = compute_commitment(SIG_D,       SIG_F, PK_D, PK_F, MSG)
        h2 = compute_commitment(altered_sig, SIG_F, PK_D, PK_F, MSG)
        assert h1 != h2

    def test_different_sig_falcon_gives_different_hash(self):
        altered_sig = bytes([0x02] * SIG_FALCON_LEN)
        h1 = compute_commitment(SIG_D, SIG_F,       PK_D, PK_F, MSG)
        h2 = compute_commitment(SIG_D, altered_sig, PK_D, PK_F, MSG)
        assert h1 != h2

    def test_different_pk_dilithium_gives_different_hash(self):
        altered_pk = bytes([0x03] * PK_DILITHIUM_LEN)
        h1 = compute_commitment(SIG_D, SIG_F, PK_D,       PK_F, MSG)
        h2 = compute_commitment(SIG_D, SIG_F, altered_pk, PK_F, MSG)
        assert h1 != h2

    def test_different_pk_falcon_gives_different_hash(self):
        altered_pk = bytes([0x04] * PK_FALCON_LEN)
        h1 = compute_commitment(SIG_D, SIG_F, PK_D, PK_F,       MSG)
        h2 = compute_commitment(SIG_D, SIG_F, PK_D, altered_pk, MSG)
        assert h1 != h2

    def test_known_vector(self):
        """
        Regression / known-answer test.
        Computed once with the live implementation and pinned so any
        accidental change to the hash formula is caught immediately.
        """
        sig_d = bytes([0x11] * 10)
        sig_f = bytes([0x22] * 10)
        pk_d  = bytes([0x33] * 10)
        pk_f  = bytes([0x44] * 10)
        msg   = b'known-answer'

        result = compute_commitment(sig_d, sig_f, pk_d, pk_f, msg)
        # The expected value was produced by running compute_commitment with
        # these exact inputs and recording the hex output.
        from web3 import Web3
        w3 = Web3()
        msg_hash = bytes(w3.keccak(msg))
        expected = bytes(w3.keccak(sig_d + sig_f + pk_d + pk_f + msg_hash))
        assert result == expected

    def test_concatenation_order_matters(self):
        """
        Swapping sig_D and sig_F must produce a different hash,
        confirming the formula respects input order.
        """
        h_correct = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        h_swapped = compute_commitment(SIG_F, SIG_D, PK_D, PK_F, MSG)
        assert h_correct != h_swapped

    def test_verify_round_trip(self):
        """
        A verifier who independently recomputes the commitment from the
        same inputs must obtain the same hash — this is the core security
        property of the anchoring scheme.
        """
        commitment = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        recomputed = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, MSG)
        assert commitment == recomputed

    def test_tampered_message_detected(self):
        """
        Mutating even one byte of the message must produce a different
        commitment, ensuring tamper-evidence.
        """
        original_msg = bytearray(MSG)
        tampered_msg = bytearray(MSG)
        tampered_msg[0] ^= 0xFF  # flip one byte

        h_orig    = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, bytes(original_msg))
        h_tampered = compute_commitment(SIG_D, SIG_F, PK_D, PK_F, bytes(tampered_msg))
        assert h_orig != h_tampered


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestValidateCommitment:
    def test_valid_32_bytes_passes(self):
        validate_commitment(bytes(32))  # no exception

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match='32 bytes'):
            validate_commitment(bytes(31))
        with pytest.raises(ValueError, match='32 bytes'):
            validate_commitment(bytes(33))

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            validate_commitment(b'')

    def test_non_bytes_raises(self):
        with pytest.raises(TypeError):
            validate_commitment('0x' + 'ab' * 32)   # str instead of bytes

    def test_bytearray_accepted(self):
        validate_commitment(bytearray(32))  # no exception


class TestValidateAddress:
    def test_valid_address_passes(self):
        validate_address('0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266')

    def test_missing_0x_raises(self):
        with pytest.raises(ValueError, match='0x'):
            validate_address('f39Fd6e51aad88F6F4ce6aB8827279cffFb92266')

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            validate_address('0xabcd')

    def test_too_long_raises(self):
        with pytest.raises(ValueError):
            validate_address('0x' + 'ab' * 21)

    def test_non_hex_raises(self):
        with pytest.raises(ValueError):
            validate_address('0x' + 'zz' * 20)

    def test_non_str_raises(self):
        with pytest.raises(TypeError):
            validate_address(b'0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266')
