from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(plain_password)


# PUBLIC_INTERFACE
def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    if not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


# PUBLIC_INTERFACE
def create_access_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    """Create a short-lived access token (HS256)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp()), "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.APP_SECRET, algorithm="HS256")


# PUBLIC_INTERFACE
def create_refresh_token(subject: str, extra_claims: Optional[dict] = None) -> str:
    """Create a long-lived refresh token (HS256)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "iat": int(now.timestamp()), "exp": int(exp.timestamp()), "type": "refresh"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.APP_SECRET, algorithm="HS256")


# PUBLIC_INTERFACE
def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    return jwt.decode(token, settings.APP_SECRET, algorithms=["HS256"])


# PUBLIC_INTERFACE
def issue_token_pair(subject: str) -> Tuple[str, str]:
    """Convenience: returns (access, refresh)."""
    return create_access_token(subject), create_refresh_token(subject)
