"""Tests for eximel"""
from importlib import metadata

from eximel import __version__


def test_version():
    """Assert the version matches what's expected"""
    assert __version__ == metadata.version("eximel")
