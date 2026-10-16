from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from src.core.database import settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_jwt_configuration,
    verify_password,
)

# ---------------------------------------------------------------------------
# Password Hashing & Verification Tests
# ---------------------------------------------------------------------------


def test_hash_and_verify_password_standard():
    password = "MySecurePassword123!"
    hashed = hash_password(password)

    # Must be hashed, not plaintext
    assert hashed != password
    assert hashed.startswith("$2b$")

    # Correct password verifies
    assert verify_password(password, hashed) is True

    # Wrong password fails verification
    assert verify_password("WrongPassword123!", hashed) is False


def test_password_hashes_use_unique_salts():
    password = "IdenticalPassword"
    hash1 = hash_password(password)
    hash2 = hash_password(password)

    assert hash1 != hash2
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_hash_password_rejects_non_string_inputs():
    for non_str in [None, 12345, 3.14, ["secret"], {"password": "pwd"}, True]:
        with pytest.raises(ValueError, match="Password must be a valid string"):
            hash_password(non_str)  # type: ignore


def test_password_empty_rejected():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")

    assert verify_password("", "$2b$12$somehash") is False
    assert verify_password("password", "") is False


def test_verify_password_rejects_non_string_inputs():
    valid_hash = hash_password("ValidPassword123!")

    for non_str_pwd in [None, 12345, ["pwd"], False]:
        assert verify_password(non_str_pwd, valid_hash) is False  # type: ignore

    for non_str_hash in [None, 12345, ["hash"], True]:
        assert verify_password("ValidPassword123!", non_str_hash) is False  # type: ignore


def test_verify_password_handles_malformed_hashes_safely():
    # Various malformed, invalid, or corrupted hashes should return False rather than crash
    malformed_hashes = [
        "not_a_valid_bcrypt_hash",
        "$2b$12$tooshort",
        "$2b$99$invalidroundsformat",
        "$2b$12$invalid_chars_in_salt_or_hash_1234567890!",
        "plaintextpassword",
        None,
    ]
    for bad_hash in malformed_hashes:
        assert verify_password("my_secret_password", bad_hash) is False  # type: ignore


# ---------------------------------------------------------------------------
# Password 72-Byte Boundary & Truncation Regression Tests
# ---------------------------------------------------------------------------


def test_password_exactly_72_bytes_succeeds():
    pwd_72 = "a" * 72
    hashed = hash_password(pwd_72)
    assert verify_password(pwd_72, hashed) is True


def test_password_longer_than_72_bytes_rejected():
    pwd_73 = "a" * 73
    with pytest.raises(ValueError, match="Password cannot exceed 72 UTF-8 bytes"):
        hash_password(pwd_73)


def test_password_multibyte_utf8_length_validation():
    # 🔒 is 4 bytes in UTF-8. 20 emojis = 80 bytes, though len(str) is only 20
    multibyte_long_pwd = "🔒" * 20
    assert len(multibyte_long_pwd) == 20
    assert len(multibyte_long_pwd.encode("utf-8")) == 80

    with pytest.raises(ValueError, match="Password cannot exceed 72 UTF-8 bytes"):
        hash_password(multibyte_long_pwd)

    # 18 emojis = 72 bytes exactly -> should succeed
    multibyte_72_bytes = "🔒" * 18
    assert len(multibyte_72_bytes.encode("utf-8")) == 72
    hashed = hash_password(multibyte_72_bytes)
    assert verify_password(multibyte_72_bytes, hashed) is True


def test_two_distinct_long_passwords_never_become_equivalent():
    """Bcrypt naturally only inspects the first 72 bytes.

    Our implementation must reject passwords > 72 bytes on hash and verify so
    that 'pwd + 1' and 'pwd + 2' never falsely match each other or a 72-byte
    hash.
    """
    base_72 = "x" * 72
    long_pwd_a = base_72 + "1"
    long_pwd_b = base_72 + "2"

    hash_72 = hash_password(base_72)

    # Neither long password can be hashed
    with pytest.raises(ValueError):
        hash_password(long_pwd_a)
    with pytest.raises(ValueError):
        hash_password(long_pwd_b)

    # Neither long password matches the 72-byte base hash (no silent truncation match)
    assert verify_password(long_pwd_a, hash_72) is False
    assert verify_password(long_pwd_b, hash_72) is False


# ---------------------------------------------------------------------------
# JWT Configuration Validation Tests
# ---------------------------------------------------------------------------


def test_validate_jwt_configuration_success():
    # Currently configured secret is valid and >= 32 bytes
    secret = validate_jwt_configuration()
    assert isinstance(secret, str)
    assert len(secret.encode("utf-8")) >= 32


def test_validate_jwt_configuration_rejects_weak_secret(monkeypatch):
    short_secret = "weak_secret_under_32_bytes"
    monkeypatch.setattr(settings, "jwt_secret_key", short_secret)

    with pytest.raises(RuntimeError, match="HS256 requires at least 32 bytes") as exc_info:
        validate_jwt_configuration()

    # Crucial security guarantee: plaintext secret must never be exposed in error messages
    assert short_secret not in str(exc_info.value)


def test_validate_jwt_configuration_rejects_missing_secret(monkeypatch):
    for empty_secret in ["", "   ", None]:
        monkeypatch.setattr(settings, "jwt_secret_key", empty_secret)
        with pytest.raises(RuntimeError, match="JWT secret key is missing"):
            validate_jwt_configuration()


def test_validate_jwt_configuration_rejects_unsupported_algorithm(monkeypatch):
    monkeypatch.setattr(settings, "jwt_algorithm", "none")
    with pytest.raises(RuntimeError, match="Unsupported JWT algorithm 'none'"):
        validate_jwt_configuration()


# ---------------------------------------------------------------------------
# JWT Access Token Creation & Validation Tests
# ---------------------------------------------------------------------------


def test_create_and_decode_token_success():
    subject = "user123"
    token = create_access_token(subject=subject)

    assert isinstance(token, str)
    payload = decode_access_token(token)

    assert payload["sub"] == subject
    assert "exp" in payload
    assert "iat" in payload


def test_create_access_token_with_integer_subject():
    token = create_access_token(subject=42)
    payload = decode_access_token(token)
    assert payload["sub"] == "42"


def test_create_access_token_empty_subject_rejected():
    for invalid_sub in [None, "", "   ", "\t\n", [123], {"a": 1}]:
        with pytest.raises(ValueError, match="JWT subject"):
            create_access_token(subject=invalid_sub)  # type: ignore


def test_create_access_token_rejects_reserved_claims_override():
    reserved_attempts = [
        {"sub": "attacker"},
        {"exp": 9999999999},
        {"iat": 1234567890},
        {"nbf": 1234567890},
    ]
    for bad_claim in reserved_attempts:
        with pytest.raises(
            ValueError, match="extra_claims cannot override reserved JWT claims"
        ):
            create_access_token(
                subject="legit_user",
                extra_claims=bad_claim,
            )


def test_create_access_token_allows_valid_custom_claims():
    custom_claims = {"role": "admin", "tenant_id": "cust_99"}
    token = create_access_token(
        subject="admin_user",
        extra_claims=custom_claims,
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "admin_user"
    assert payload["role"] == "admin"
    assert payload["tenant_id"] == "cust_99"


def test_create_access_token_rejects_non_positive_lifetimes():
    # Zero or negative delta must be rejected
    with pytest.raises(ValueError, match="lifetime .* must be strictly positive"):
        create_access_token(
            subject="user",
            expires_delta=timedelta(seconds=0),
        )

    with pytest.raises(ValueError, match="lifetime .* must be strictly positive"):
        create_access_token(
            subject="user",
            expires_delta=timedelta(seconds=-10),
        )

    with pytest.raises(TypeError, match="instance of datetime.timedelta"):
        create_access_token(
            subject="user",
            expires_delta=100,  # type: ignore
        )


# ---------------------------------------------------------------------------
# JWT Access Token Decoding & Claim Validation Tests
# ---------------------------------------------------------------------------


def test_decode_access_token_expired():
    # Construct an already expired token directly using jose
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "user_expired",
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(expired_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"


def test_decode_access_token_invalid_signature():
    tampered_token = jwt.encode(
        {"sub": "attacker"},
        "wrong_secret_key_12345_longer_than_32_bytes!",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(tampered_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_decode_access_token_malformed():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("this.is.not.a.valid.jwt")

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


def test_decode_access_token_missing_or_empty():
    for empty_val in [None, "", "   ", "\t"]:
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(empty_val)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Authentication token is missing"


def test_decode_access_token_missing_or_empty_sub():
    # Valid signature, but 'sub' is missing
    token_no_sub = jwt.encode(
        {"role": "user"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token_no_sub)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

    # Valid signature, but 'sub' is empty or whitespace
    for blank_sub in ["", "   "]:
        token_blank_sub = jwt.encode(
            {"sub": blank_sub},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token_blank_sub)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"


def test_decode_access_token_rejects_non_string_sub():
    # Token crafted with integer, boolean, list, or dict 'sub'
    non_string_subs = [42, True, ["user"], {"id": 1}]
    for bad_sub in non_string_subs:
        crafted_token = jwt.encode(
            {"sub": bad_sub},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(crafted_token)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"
