"""
tests/test_no_hardcoded_secrets.py

Regression test: assert that no 0x-prefixed 64-hex-char private key literal
appears in any python/*.py source file.

This catches future accidental re-introduction of the Hardhat test key or any
other raw private key in source, regardless of whether it is a "known-safe"
test key — the hygiene rule is: keys in source == fail.
"""
import re
import os
import glob

# Pattern: 0x followed by exactly 64 hex characters (a raw 256-bit private key)
_PRIVATE_KEY_RE = re.compile(r'0x[0-9a-fA-F]{64}')

PYTHON_SOURCE_DIR = os.path.join(os.path.dirname(__file__), '..', 'python')


def _python_sources():
    """Return all .py files under python/."""
    return glob.glob(os.path.join(PYTHON_SOURCE_DIR, '*.py'))


def test_no_private_key_literals_in_python_sources():
    """No 64-hex private key literal should appear in any python/*.py file."""
    violations = []
    for path in _python_sources():
        with open(path, encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                if _PRIVATE_KEY_RE.search(line):
                    violations.append(f'{os.path.basename(path)}:{lineno}: {line.rstrip()}')

    assert not violations, (
        'Hardcoded private key literal(s) found in Python source files.\n'
        'Move the key to .env and load it with os.environ[\'KEY_NAME\'].\n'
        'Violations:\n' + '\n'.join(violations)
    )


def test_python_sources_found():
    """Sanity check: the glob must find at least one source file."""
    assert len(_python_sources()) >= 5, (
        'Expected at least 5 python/*.py files; check PYTHON_SOURCE_DIR path'
    )
