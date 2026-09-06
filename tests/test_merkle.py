"""
tests/test_merkle.py

Unit tests for the Merkle-tree helpers in python/batch_anchor.py.
The helpers are extracted here so they can be tested without a Hardhat
connection or a real Ethereum account.
"""
import sys
import os
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from commitment import keccak256


# ---------------------------------------------------------------------------
# Re-implement the helpers from batch_anchor.py as pure functions
# (same logic, no Web3 / eth_account dependency so tests run anywhere)
# ---------------------------------------------------------------------------

def build_merkle_tree(leaves: list) -> tuple:
    """
    Binary Merkle tree from 32-byte leaf hashes.
    Pads to the next power-of-2 by repeating the last leaf.
    Returns (root_bytes, layers).
    """
    n = len(leaves)
    size = 1 << math.ceil(math.log2(max(n, 2)))
    layer = list(leaves) + [leaves[-1]] * (size - n)

    layers = [layer]
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            parent = keccak256(layer[i] + layer[i + 1])
            next_layer.append(parent)
        layer = next_layer
        layers.append(layer)

    return layers[-1][0], layers


def generate_commitments(n: int, seed: int = 0) -> list:
    return [keccak256(f'pqc_commitment_{seed}_{i}'.encode()) for i in range(n)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateCommitments:
    def test_correct_count(self):
        leaves = generate_commitments(5)
        assert len(leaves) == 5

    def test_each_leaf_32_bytes(self):
        for leaf in generate_commitments(10):
            assert len(leaf) == 32

    def test_deterministic(self):
        assert generate_commitments(5, seed=1) == generate_commitments(5, seed=1)

    def test_different_seed_different_leaves(self):
        assert generate_commitments(5, seed=0) != generate_commitments(5, seed=1)

    def test_all_leaves_distinct(self):
        leaves = generate_commitments(100)
        assert len(set(leaves)) == 100


class TestBuildMerkleTree:
    def test_single_leaf_root_is_leaf(self):
        leaf = keccak256(b'only leaf')
        root, layers = build_merkle_tree([leaf])
        # With padding to size 2, root = keccak(leaf || leaf)
        expected = keccak256(leaf + leaf)
        assert root == expected
        assert len(root) == 32

    def test_two_leaves(self):
        a = keccak256(b'a')
        b = keccak256(b'b')
        root, layers = build_merkle_tree([a, b])
        expected = keccak256(a + b)
        assert root == expected

    def test_root_is_32_bytes(self):
        leaves = generate_commitments(8)
        root, _ = build_merkle_tree(leaves)
        assert len(root) == 32

    def test_deterministic(self):
        leaves = generate_commitments(16)
        r1, _ = build_merkle_tree(leaves)
        r2, _ = build_merkle_tree(leaves)
        assert r1 == r2

    def test_different_leaves_different_root(self):
        leaves_a = generate_commitments(4, seed=0)
        leaves_b = generate_commitments(4, seed=1)
        root_a, _ = build_merkle_tree(leaves_a)
        root_b, _ = build_merkle_tree(leaves_b)
        assert root_a != root_b

    @pytest.mark.parametrize('n', [1, 2, 3, 4, 7, 8, 10, 50, 100])
    def test_various_batch_sizes_produce_32_byte_root(self, n):
        leaves = generate_commitments(n)
        root, _ = build_merkle_tree(leaves)
        assert len(root) == 32

    def test_layers_structure(self):
        leaves = generate_commitments(8)
        root, layers = build_merkle_tree(leaves)
        # 8 leaves → 4 → 2 → 1 root  (4 layers total)
        assert len(layers) == 4
        assert layers[0] == leaves
        assert layers[-1] == [root]

    def test_tampered_leaf_changes_root(self):
        leaves = generate_commitments(8)
        root_original, _ = build_merkle_tree(leaves)

        tampered = list(leaves)
        tampered[3] = keccak256(b'tampered')
        root_tampered, _ = build_merkle_tree(tampered)

        assert root_original != root_tampered
