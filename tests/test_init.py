"""Tests for the package initialization."""

import importlib
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import src.embedded_cereal_bowl as init_mod


def test_init_version_not_found():
    """Test __version__ when package is not installed."""
    with patch("importlib.metadata.version", side_effect=PackageNotFoundError):
        # We need to re-import or re-execute the module to test this
        importlib.reload(init_mod)
        assert init_mod.__version__ == "0.0.0.dev0+unknown"

    # Reload again to restore correct version for other tests
    importlib.reload(init_mod)


def test_module_metadata():
    """Test module metadata is present."""
    assert hasattr(init_mod, "__version__")
    assert hasattr(init_mod, "__author__")
    assert "monitor" in init_mod.__all__
