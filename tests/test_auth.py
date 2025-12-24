"""
Tests for Authentication Utilities
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.auth import (
    hash_password,
    verify_password,
    generate_password_hash,
    verify_password_hash,
    generate_api_key
)


class TestAuthentication:
    """Test authentication utilities"""

    def test_hash_password_with_salt(self):
        """Test password hashing with provided salt"""
        password = "mysecretpassword"
        salt = "testsalt123"

        hashed, returned_salt = hash_password(password, salt)

        assert returned_salt == salt
        assert hashed != password  # Should be hashed
        assert len(hashed) == 64  # SHA-256 produces 64 hex chars

    def test_hash_password_generates_salt(self):
        """Test that hash_password generates salt when not provided"""
        password = "mysecretpassword"

        hashed1, salt1 = hash_password(password)
        hashed2, salt2 = hash_password(password)

        # Different salts should produce different hashes
        assert salt1 != salt2
        assert hashed1 != hashed2

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "mysecretpassword"
        hashed, salt = hash_password(password)

        is_valid = verify_password(password, hashed, salt)

        assert is_valid == True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        correct_password = "mysecretpassword"
        wrong_password = "wrongpassword"

        hashed, salt = hash_password(correct_password)
        is_valid = verify_password(wrong_password, hashed, salt)

        assert is_valid == False

    def test_generate_password_hash(self):
        """Test generating combined hash:salt string"""
        password = "testpassword123"

        hash_salt = generate_password_hash(password)

        # Should be in format "hash:salt"
        assert ':' in hash_salt
        parts = hash_salt.split(':')
        assert len(parts) == 2
        assert len(parts[0]) == 64  # SHA-256 hash
        assert len(parts[1]) == 64  # 32 byte salt in hex

    def test_verify_password_hash_correct(self):
        """Test verifying password against combined hash:salt"""
        password = "testpassword123"
        hash_salt = generate_password_hash(password)

        is_valid = verify_password_hash(password, hash_salt)

        assert is_valid == True

    def test_verify_password_hash_incorrect(self):
        """Test verifying wrong password against combined hash:salt"""
        correct_password = "testpassword123"
        wrong_password = "wrongpassword"

        hash_salt = generate_password_hash(correct_password)
        is_valid = verify_password_hash(wrong_password, hash_salt)

        assert is_valid == False

    def test_verify_password_hash_invalid_format(self):
        """Test verifying with invalid hash:salt format"""
        password = "testpassword"
        invalid_hash = "not_a_valid_hash"

        is_valid = verify_password_hash(password, invalid_hash)

        assert is_valid == False

    def test_generate_api_key(self):
        """Test API key generation"""
        api_key = generate_api_key()

        # Should be a secure random string
        assert len(api_key) == 64
        assert api_key.isalnum() or '-' in api_key or '_' in api_key  # base64 chars

        # Multiple calls should produce different keys
        api_key2 = generate_api_key()
        assert api_key != api_key2

    def test_password_hash_consistency(self):
        """Test that same password with same salt produces same hash"""
        password = "consistent_password"
        salt = "fixed_salt_123"

        hash1, _ = hash_password(password, salt)
        hash2, _ = hash_password(password, salt)

        assert hash1 == hash2

    def test_password_case_sensitivity(self):
        """Test that password verification is case-sensitive"""
        password_lower = "password"
        password_upper = "PASSWORD"

        hash_salt = generate_password_hash(password_lower)

        # Should not match different case
        is_valid = verify_password_hash(password_upper, hash_salt)
        assert is_valid == False

    def test_empty_password(self):
        """Test hashing empty password"""
        password = ""
        hashed, salt = hash_password(password)

        # Should still work
        assert len(hashed) == 64
        assert len(salt) == 64

        # Should be verifiable
        is_valid = verify_password(password, hashed, salt)
        assert is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
