"""Password hashing and login tokens.

Passwords: we store only a bcrypt hash, a one-way scramble. We can check a password against it,
but nobody (including us) can turn the hash back into the password.

Tokens: after login the user gets a JWT, a small signed note saying "this is user 7, valid until X".
The signature uses JWT_SECRET, so any edit to the token makes it invalid.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings

JWT_ALGORITHM = "HS256"

# bcrypt only reads the first 72 bytes of a password, and bcrypt 5 rejects anything longer.
# Validation keeps passwords within this limit (see app/schemas/auth.py).
BCRYPT_MAX_PASSWORD_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Return a salted bcrypt hash safe to store in the database."""
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, password_hash: str) -> bool:
    """True if the password matches the stored hash."""
    password_bytes = plain_password.encode()
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(password_bytes, password_hash.encode())


def create_access_token(user_id: int, expires_in: timedelta | None = None) -> str:
    """Create a signed token that identifies the user until it expires."""
    settings = get_settings()
    lifetime = expires_in or timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the user id inside a valid token, or None if the token is invalid or expired."""
    try:
        payload = jwt.decode(token, get_settings().jwt_secret, algorithms=[JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
