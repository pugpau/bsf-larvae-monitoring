"""
Unit tests for authentication security functions.
"""

from datetime import timedelta

import pytest

from src.auth.security import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password,
    validate_password_strength,
)


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordHashing:
    def test_hash_returns_different_string(self):
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_correct_password(self):
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = get_password_hash("TestPassword123!")
        assert verify_password("WrongPassword456!", hashed) is False

    def test_different_hashes_for_same_password(self):
        password = "TestPassword123!"
        h1 = get_password_hash(password)
        h2 = get_password_hash(password)
        assert h1 != h2  # bcrypt uses random salt


@pytest.mark.unit
@pytest.mark.auth
class TestPasswordStrength:
    def test_strong_password_passes(self):
        result = validate_password_strength("StrongP@ss1")
        assert result["valid"] is True
        assert result["errors"] == []

    def test_short_password_fails(self):
        result = validate_password_strength("Sh0rt!")
        assert result["valid"] is False
        assert any("8 characters" in e for e in result["errors"])

    def test_no_uppercase_fails(self):
        result = validate_password_strength("nouppercase1!")
        assert result["valid"] is False

    def test_no_lowercase_fails(self):
        result = validate_password_strength("NOLOWERCASE1!")
        assert result["valid"] is False

    def test_no_number_fails(self):
        result = validate_password_strength("NoNumberHere!")
        assert result["valid"] is False

    def test_no_special_char_fails(self):
        result = validate_password_strength("NoSpecialChar1")
        assert result["valid"] is False


@pytest.mark.unit
@pytest.mark.auth
class TestJWTTokens:
    def test_create_access_token(self):
        token = create_access_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_custom_expiry(self):
        token = create_access_token({"sub": "testuser"}, timedelta(minutes=5))
        assert isinstance(token, str)

    def test_verify_valid_token(self):
        token = create_access_token({"sub": "testuser"})
        payload = verify_token(token, "access")
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["type"] == "access"

    def test_verify_invalid_token(self):
        payload = verify_token("invalid.token.here", "access")
        assert payload is None

    def test_verify_expired_token(self):
        token = create_access_token({"sub": "testuser"}, timedelta(seconds=-1))
        payload = verify_token(token, "access")
        assert payload is None

    def test_verify_wrong_token_type(self):
        token = create_access_token({"sub": "testuser"})
        payload = verify_token(token, "refresh")
        assert payload is None

    def test_token_preserves_custom_claims(self):
        token = create_access_token({"sub": "user1", "permissions": ["read", "write"]})
        payload = verify_token(token, "access")
        assert payload["permissions"] == ["read", "write"]


# ===========================================================================
# Refresh Token
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestRefreshToken:
    def test_create_refresh_token(self):
        from src.auth.security import create_refresh_token
        token = create_refresh_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token_with_custom_expiry(self):
        from src.auth.security import create_refresh_token
        token = create_refresh_token({"sub": "testuser"}, timedelta(days=1))
        assert isinstance(token, str)

    def test_verify_refresh_token(self):
        from src.auth.security import create_refresh_token
        token = create_refresh_token({"sub": "testuser"})
        payload = verify_token(token, "refresh")
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["type"] == "refresh"

    def test_refresh_token_rejected_as_access(self):
        from src.auth.security import create_refresh_token
        token = create_refresh_token({"sub": "testuser"})
        payload = verify_token(token, "access")
        assert payload is None


# ===========================================================================
# API Key Generation
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestAPIKeyGeneration:
    def test_generate_api_key_returns_tuple(self):
        from src.auth.security import generate_api_key
        result = generate_api_key()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_generate_api_key_format(self):
        from src.auth.security import generate_api_key
        full_key, hashed_key = generate_api_key()
        assert full_key.startswith("bsf_")
        assert len(full_key) > 12
        assert hashed_key != full_key

    def test_generate_api_key_unique(self):
        from src.auth.security import generate_api_key
        key1, _ = generate_api_key()
        key2, _ = generate_api_key()
        assert key1 != key2

    def test_verify_generated_api_key(self):
        from src.auth.security import generate_api_key, verify_api_key
        full_key, hashed_key = generate_api_key()
        assert verify_api_key(full_key, hashed_key) is True

    def test_verify_wrong_api_key(self):
        from src.auth.security import generate_api_key, verify_api_key
        _, hashed_key = generate_api_key()
        assert verify_api_key("bsf_wrong_key", hashed_key) is False


# ===========================================================================
# Dev User
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestDevUser:
    def test_create_dev_user(self):
        from src.auth.security import _create_dev_user
        user = _create_dev_user()
        assert user.username == "dev_user"
        assert user.email == "dev@example.com"
        assert user.is_active is True
        assert user.is_superuser is True
        assert user.is_verified is True
        assert user.role == "admin"
        assert user.id is not None


# ===========================================================================
# Data Masking and Sanitization
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestMaskSensitiveData:
    def test_mask_long_string(self):
        from src.auth.security import mask_sensitive_data
        result = mask_sensitive_data("bsf_abc12345_secretkey")
        assert result.startswith("bsf_")
        assert "*" in result
        assert len(result) == len("bsf_abc12345_secretkey")

    def test_mask_short_string(self):
        from src.auth.security import mask_sensitive_data
        result = mask_sensitive_data("ab")
        assert result == "**"

    def test_mask_exact_visible_chars(self):
        from src.auth.security import mask_sensitive_data
        result = mask_sensitive_data("abcd")
        assert result == "****"

    def test_mask_custom_visible_chars(self):
        from src.auth.security import mask_sensitive_data
        result = mask_sensitive_data("abcdefghij", visible_chars=6)
        assert result == "abcdef****"

    def test_mask_custom_char(self):
        from src.auth.security import mask_sensitive_data
        result = mask_sensitive_data("secretdata", mask_char="#", visible_chars=3)
        assert result == "sec#######"


@pytest.mark.unit
@pytest.mark.auth
class TestSanitizeUserInput:
    def test_sanitize_normal_input(self):
        from src.auth.security import sanitize_user_input
        assert sanitize_user_input("hello world") == "hello world"

    def test_sanitize_null_bytes(self):
        from src.auth.security import sanitize_user_input
        assert sanitize_user_input("hello\x00world") == "helloworld"

    def test_sanitize_carriage_return(self):
        from src.auth.security import sanitize_user_input
        assert sanitize_user_input("hello\rworld") == "helloworld"

    def test_sanitize_newline(self):
        from src.auth.security import sanitize_user_input
        assert sanitize_user_input("hello\nworld") == "hello world"

    def test_sanitize_whitespace_trimming(self):
        from src.auth.security import sanitize_user_input
        assert sanitize_user_input("  hello  ") == "hello"


# ===========================================================================
# SecurityHeaders
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestSecurityHeaders:
    def test_get_security_headers_returns_dict(self):
        from src.auth.security import SecurityHeaders
        headers = SecurityHeaders.get_security_headers()
        assert isinstance(headers, dict)

    def test_security_headers_content(self):
        from src.auth.security import SecurityHeaders
        headers = SecurityHeaders.get_security_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age" in headers["Strict-Transport-Security"]
        assert "default-src" in headers["Content-Security-Policy"]
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_security_headers_has_six_entries(self):
        from src.auth.security import SecurityHeaders
        headers = SecurityHeaders.get_security_headers()
        assert len(headers) == 6


# ===========================================================================
# SecurityConfig
# ===========================================================================


@pytest.mark.unit
@pytest.mark.auth
class TestSecurityConfig:
    def test_config_defaults(self):
        from src.auth.security import SecurityConfig
        assert SecurityConfig.MIN_PASSWORD_LENGTH == 8
        assert SecurityConfig.MAX_LOGIN_ATTEMPTS == 5
        assert SecurityConfig.LOCKOUT_DURATION_MINUTES == 30
        assert SecurityConfig.SESSION_TIMEOUT_MINUTES == 60
        assert SecurityConfig.API_KEY_PREFIX_LENGTH == 8
        assert SecurityConfig.API_KEY_LENGTH == 32

    def test_config_password_policy(self):
        from src.auth.security import SecurityConfig
        assert SecurityConfig.REQUIRE_UPPERCASE is True
        assert SecurityConfig.REQUIRE_LOWERCASE is True
        assert SecurityConfig.REQUIRE_NUMBERS is True
        assert SecurityConfig.REQUIRE_SPECIAL_CHARS is True
