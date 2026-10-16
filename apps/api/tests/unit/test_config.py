"""
Unit Tests for Configuration & Security Validators
"""

import pytest
from app.core.config import Settings


def test_production_secret_key_validation():
    """Raises error if production environment uses the insecure default secret."""
    with pytest.raises(ValueError, match="Insecure default APP_SECRET_KEY"):
        Settings(
            APP_ENV="production",
            APP_SECRET_KEY="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7",
        )


def test_production_valid_secret_key():
    """Accepts custom strong secret key in production environment."""
    cfg = Settings(
        APP_ENV="production",
        APP_SECRET_KEY="a" * 64,
    )
    assert cfg.APP_SECRET_KEY == "a" * 64
