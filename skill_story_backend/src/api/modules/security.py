from typing import Optional

from fastapi import Header
from sqlmodel import select

from .auth_utils import decode_token
from .db import get_session, User
from .errors import ApplicationError, ErrorCode


# PUBLIC_INTERFACE
async def get_current_user(authorization: Optional[str] = Header(None, alias="Authorization")) -> User:
    """Resolve the current authenticated user from Authorization: Bearer <token>.

    Raises 401 on missing/invalid token, 403 if user inactive.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApplicationError("Missing or invalid Authorization header", ErrorCode.AUTHENTICATION_ERROR, status_code=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise ApplicationError("Invalid or expired token", ErrorCode.AUTHENTICATION_ERROR, status_code=401)

    if payload.get("type") != "access":
        raise ApplicationError("Invalid token type", ErrorCode.AUTHENTICATION_ERROR, status_code=401)

    subject = payload.get("sub")
    if not subject:
        raise ApplicationError("Token missing subject", ErrorCode.AUTHENTICATION_ERROR, status_code=401)

    # subject is the username for this app
    async with get_session() as session:
        res = await session.exec(select(User).where(User.username == subject))
        user = res.first()
        if not user:
            raise ApplicationError("User not found", ErrorCode.AUTHENTICATION_ERROR, status_code=401)
        if getattr(user, "is_active", True) is False:
            raise ApplicationError("User inactive", ErrorCode.AUTHORIZATION_ERROR, status_code=403)
        return user
