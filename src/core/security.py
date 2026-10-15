from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from src.core.database import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Standard Bcrypt algorithm processes up to 72 bytes. Input longer than 72 bytes
# must not be silently truncated to prevent distinct passwords from becoming equivalent.
MAX_PASSWORD_BYTES = 72

# Minimum key entropy for HS256 as required by RFC 7518 Section 3.2 (256 bits = 32 bytes)
MIN_JWT_SECRET_BYTES = 32

# Reserved JWT claims defined in RFC 7519 that cannot be overwritten by extra_claims
RESERVED_JWT_CLAIMS: frozenset[str] = frozenset(
    {"sub", "exp", "iat", "nbf", "iss", "aud", "jti"}
)

# ---------------------------------------------------------------------------
# Configuration Validation
# ---------------------------------------------------------------------------


def validate_jwt_configuration() -> str:
    """Validate that JWT settings are present, supported, and sufficiently strong.

    HS256 requires at least 256 bits (32 bytes) of secret key entropy per RFC 7518.
    Fails explicitly instead of silently using insecure defaults.
    Never prints or logs the secret key in error messages.
    """
    secret = getattr(settings, "jwt_secret_key", None)
    if not secret or not isinstance(secret, str) or not secret.strip():
        raise RuntimeError("JWT secret key is missing or not configured.")

    secret_bytes = secret.encode("utf-8")
    if len(secret_bytes) < MIN_JWT_SECRET_BYTES:
        raise RuntimeError(
            f"JWT secret key is insecure. HS256 requires at least {MIN_JWT_SECRET_BYTES} "
            f"bytes (256 bits), but configured secret is only {len(secret_bytes)} bytes."
        )

    algorithm = getattr(settings, "jwt_algorithm", None)
    if not algorithm or not isinstance(algorithm, str) or not algorithm.strip():
        raise RuntimeError("JWT algorithm is missing or not configured.")

    if algorithm != "HS256":
        raise RuntimeError(
            f"Unsupported JWT algorithm '{algorithm}'. Only 'HS256' is currently supported."
        )

    return secret


# Validate configuration on module import to ensure fail-fast startup behavior
validate_jwt_configuration()

# ---------------------------------------------------------------------------
# Password Hashing Setup (Passlib with bcrypt backend)
# ---------------------------------------------------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt via Passlib.

    Enforces explicit string type validation and a strict 72-byte UTF-8 limit.
    Raises ValueError for non-string passwords, empty passwords, or passwords
    exceeding 72 UTF-8 bytes. Plaintext passwords are never logged or stored.
    """
    if not isinstance(password, str):
        raise ValueError("Password must be a valid string.")

    if not password:
        raise ValueError("Password cannot be empty.")

    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password cannot exceed {MAX_PASSWORD_BYTES} UTF-8 bytes."
        )

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that a plaintext password matches a stored bcrypt hash.

    Safely handles and returns False for:
    - Non-string or empty plain_password or hashed_password
    - Plain passwords exceeding 72 UTF-8 bytes (prevents silent truncation / equivalence attacks)
    - Corrupted, unrecognized, or malformed hashes without leaking internal exceptions

    Returns True if valid, False otherwise.
    """
    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False

    if not plain_password or not hashed_password:
        return False

    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Catch any passlib/bcrypt decoding, malformed hash, or security errors safely
        return False


# ---------------------------------------------------------------------------
# OAuth2 Scheme & JWT Utilities
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters:
    - subject: The unique identifier for the token subject (must be non-empty string or int).
    - expires_delta: Optional custom lifetime (must be strictly positive).
    - extra_claims: Optional dictionary with custom claims (cannot override reserved claims).

    Plaintext passwords must never be placed inside the token payload.
    """
    if subject is None:
        raise ValueError("JWT subject (sub) cannot be None.")

    if not isinstance(subject, (str, int)):
        raise ValueError("JWT subject (sub) must be a non-empty string or integer.")

    subject_str = str(subject).strip()
    if not subject_str:
        raise ValueError("JWT subject (sub) cannot be empty or whitespace.")

    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        if not isinstance(expires_delta, timedelta):
            raise TypeError("expires_delta must be an instance of datetime.timedelta.")
        if expires_delta.total_seconds() <= 0:
            raise ValueError("Token lifetime (expires_delta) must be strictly positive.")
        expire = now + expires_delta
    else:
        if settings.access_token_expire_minutes <= 0:
            raise ValueError(
                "Configured access_token_expire_minutes must be strictly positive."
            )
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    if extra_claims:
        overlapping = RESERVED_JWT_CLAIMS.intersection(extra_claims.keys())
        if overlapping:
            raise ValueError(
                f"extra_claims cannot override reserved JWT claims: {sorted(overlapping)}"
            )

    payload: dict[str, Any] = {}
    if extra_claims:
        payload.update(extra_claims)

    payload.update(
        {
            "sub": subject_str,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
        }
    )

    secret_key = validate_jwt_configuration()

    return jwt.encode(
        payload,
        secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str | None) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Safely handles:
    - Missing, empty, or whitespace-only tokens
    - Expired signatures (ExpiredSignatureError)
    - Tampered or malformed tokens (JWTError)
    - Tokens missing or having a non-string / empty 'sub' claim

    Raises HTTPException(401) on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token or not isinstance(token, str) or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    secret_key = validate_jwt_configuration()

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        token_sub = payload.get("sub")
        if not isinstance(token_sub, str) or not token_sub.strip():
            raise credentials_exception
        return payload
    except ExpiredSignatureError:
        raise expired_exception
    except JWTError:
        raise credentials_exception
