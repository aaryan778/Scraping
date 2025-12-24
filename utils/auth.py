"""
Authentication utilities
Provides secure password hashing and verification
"""
import hashlib
import hmac
import os
import secrets
from typing import Tuple


def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """
    Hash a password using SHA-256 with salt

    Args:
        password: Plain text password
        salt: Optional salt (will generate if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)

    # Combine password and salt, then hash
    pwd_bytes = (password + salt).encode('utf-8')
    hashed = hashlib.sha256(pwd_bytes).hexdigest()

    return hashed, salt


def verify_password(input_password: str, stored_hash: str, salt: str) -> bool:
    """
    Verify a password against stored hash and salt

    Args:
        input_password: Password to verify
        stored_hash: Stored password hash
        salt: Salt used when hashing

    Returns:
        True if password matches
    """
    input_hash, _ = hash_password(input_password, salt)

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(input_hash, stored_hash)


def generate_password_hash(password: str) -> str:
    """
    Generate a combined hash:salt string for storage

    Args:
        password: Plain text password

    Returns:
        String in format "hash:salt"
    """
    hashed, salt = hash_password(password)
    return f"{hashed}:{salt}"


def verify_password_hash(input_password: str, stored_hash_salt: str) -> bool:
    """
    Verify password against combined hash:salt string

    Args:
        input_password: Password to verify
        stored_hash_salt: Stored string in format "hash:salt"

    Returns:
        True if password matches
    """
    try:
        stored_hash, salt = stored_hash_salt.split(':', 1)
        return verify_password(input_password, stored_hash, salt)
    except ValueError:
        # Invalid format
        return False


def generate_api_key() -> str:
    """
    Generate a secure random API key

    Returns:
        Secure random API key (64 characters)
    """
    return secrets.token_urlsafe(48)  # 48 bytes = 64 chars in base64


# CLI helper to generate password hashes
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        password = sys.argv[1]
        hash_salt = generate_password_hash(password)
        print(f"\nPassword: {password}")
        print(f"Hash:Salt: {hash_salt}")
        print(f"\nAdd this to your .env file:")
        print(f"DASHBOARD_PASSWORD_HASH={hash_salt}")
        print()

        # Test verification
        is_valid = verify_password_hash(password, hash_salt)
        print(f"Verification test: {'✓ PASS' if is_valid else '✗ FAIL'}")
    else:
        print("Usage: python utils/auth.py <password>")
        print("Example: python utils/auth.py mysecurepassword")
        print("\nOr generate an API key:")
        api_key = generate_api_key()
        print(f"API Key: {api_key}")
        print(f"\nAdd to .env:")
        print(f"API_KEY={api_key}")
