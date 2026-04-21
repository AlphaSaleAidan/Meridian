"""
Token Encryption — AES-256-GCM for OAuth token storage.

All POS tokens are encrypted before DB persistence and decrypted
on retrieval. Uses a symmetric key from the ENCRYPTION_KEY env var.

Key format: 32-byte hex string (64 hex chars) → 256-bit AES key.

Usage:
    from src.security.encryption import encrypt_token, decrypt_token

    # Encrypt before storing
    encrypted = encrypt_token("sq0atp-xxxxx...")
    # → "v1:base64_nonce:base64_ciphertext:base64_tag"

    # Decrypt when reading
    plaintext = decrypt_token(encrypted)
    # → "sq0atp-xxxxx..."
"""
import base64
import logging
import os
import secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger("meridian.security.encryption")

# ─── Key Management ───────────────────────────────────────────

_ENCRYPTION_KEY_HEX: str | None = None
_AESGCM_INSTANCE: AESGCM | None = None

# Versioned prefix so we can rotate encryption schemes
_CURRENT_VERSION = "v1"


def _get_key() -> bytes:
    """
    Load encryption key from env. Cached after first call.
    
    Raises RuntimeError if ENCRYPTION_KEY is not set or invalid.
    """
    global _ENCRYPTION_KEY_HEX, _AESGCM_INSTANCE

    if _AESGCM_INSTANCE is not None:
        return _ENCRYPTION_KEY_HEX  # type: ignore

    key_hex = os.environ.get("ENCRYPTION_KEY", "")
    if not key_hex:
        raise RuntimeError(
            "ENCRYPTION_KEY env var not set. "
            "Generate one: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    try:
        key_bytes = bytes.fromhex(key_hex)
    except ValueError:
        raise RuntimeError("ENCRYPTION_KEY must be a 64-character hex string (32 bytes)")

    if len(key_bytes) != 32:
        raise RuntimeError(
            f"ENCRYPTION_KEY must be 32 bytes (64 hex chars), got {len(key_bytes)} bytes"
        )

    _ENCRYPTION_KEY_HEX = key_hex
    _AESGCM_INSTANCE = AESGCM(key_bytes)
    return key_bytes


def _get_cipher() -> AESGCM:
    """Get or initialize the AESGCM cipher."""
    _get_key()
    assert _AESGCM_INSTANCE is not None
    return _AESGCM_INSTANCE


# ─── Encrypt / Decrypt ───────────────────────────────────────

def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token string using AES-256-GCM.
    
    Returns a versioned string: "v1:<nonce_b64>:<ciphertext_b64>:<tag_b64>"
    
    The nonce is 12 bytes (96 bits), randomly generated per encryption.
    GCM mode provides both confidentiality and integrity (authentication tag).
    """
    if not plaintext:
        return ""

    cipher = _get_cipher()

    # 12-byte random nonce (recommended for GCM)
    nonce = secrets.token_bytes(12)

    # Encrypt (GCM appends 16-byte auth tag to ciphertext)
    ciphertext_with_tag = cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Split ciphertext and tag (tag is last 16 bytes)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]

    # Encode components as base64
    nonce_b64 = base64.urlsafe_b64encode(nonce).decode("ascii")
    ct_b64 = base64.urlsafe_b64encode(ciphertext).decode("ascii")
    tag_b64 = base64.urlsafe_b64encode(tag).decode("ascii")

    return f"{_CURRENT_VERSION}:{nonce_b64}:{ct_b64}:{tag_b64}"


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt a token string encrypted with encrypt_token().
    
    Raises ValueError if the encrypted string is malformed or tampered with.
    """
    if not encrypted:
        return ""

    parts = encrypted.split(":")
    if len(parts) != 4:
        raise ValueError(
            f"Invalid encrypted token format: expected 4 parts (v:n:c:t), got {len(parts)}"
        )

    version, nonce_b64, ct_b64, tag_b64 = parts

    if version != _CURRENT_VERSION:
        raise ValueError(f"Unsupported encryption version: {version}")

    cipher = _get_cipher()

    try:
        nonce = base64.urlsafe_b64decode(nonce_b64)
        ciphertext = base64.urlsafe_b64decode(ct_b64)
        tag = base64.urlsafe_b64decode(tag_b64)
    except Exception as e:
        raise ValueError(f"Invalid base64 in encrypted token: {e}")

    # Reconstruct ciphertext+tag for GCM decryption
    ciphertext_with_tag = ciphertext + tag

    try:
        plaintext_bytes = cipher.decrypt(nonce, ciphertext_with_tag, None)
    except Exception:
        raise ValueError("Token decryption failed — wrong key or tampered data")

    return plaintext_bytes.decode("utf-8")


# ─── Key Generation Helper ───────────────────────────────────

def generate_encryption_key() -> str:
    """Generate a new 256-bit encryption key as hex string."""
    return secrets.token_hex(32)


if __name__ == "__main__":
    # Quick key generation helper
    print(f"New ENCRYPTION_KEY: {generate_encryption_key()}")
