"""Unit tests for password hashing: bcrypt + per-password salt + pepper."""

from __future__ import annotations

import bcrypt

from app.core.config import settings
from app.core.security import _pepper, hash_password, verify_password


def test_hash_is_bcrypt_and_verifies() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_same_password_hashes_differently_each_time() -> None:
    """A fresh random salt per call means identical passwords never collide."""
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b
    assert verify_password("same-password", a)
    assert verify_password("same-password", b)


def test_pepper_is_required_for_verification() -> None:
    """A hash made with the real pepper must not verify once the pepper changes."""
    hashed = hash_password("s3cret")
    original = settings.PASSWORD_PEPPER
    try:
        settings.PASSWORD_PEPPER = original + "-rotated"
        assert verify_password("s3cret", hashed) is False
    finally:
        settings.PASSWORD_PEPPER = original
    assert verify_password("s3cret", hashed) is True


def test_pepper_removes_bcrypt_72_byte_limit() -> None:
    """Raw bcrypt truncates at 72 bytes; the HMAC pre-hash means long
    passwords that share a 72-byte prefix still get distinct hashes."""
    long_a = "x" * 72 + "AAAA"
    long_b = "x" * 72 + "BBBB"
    assert _pepper(long_a) != _pepper(long_b)

    hashed = hash_password(long_a)
    assert verify_password(long_a, hashed) is True
    assert verify_password(long_b, hashed) is False


def test_pepper_output_is_bcrypt_safe() -> None:
    """The value handed to bcrypt is base64 text: no NUL bytes, well under 72."""
    peppered = _pepper("anything")
    assert b"\x00" not in peppered
    assert len(peppered) <= 72
    # sanity: bcrypt accepts it without raising
    bcrypt.hashpw(peppered, bcrypt.gensalt(rounds=4))
