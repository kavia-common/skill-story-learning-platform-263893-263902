from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

from ..modules.db import get_session, User
from ..modules.auth_utils import hash_password, verify_password, issue_token_pair, decode_token
from ..modules.security import get_current_user

router = APIRouter(tags=["auth"])


class TokenPairResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Unique email")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., min_length=8, max_length=128, description="Password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token")


class MeResponse(BaseModel):
    username: str
    email: Optional[str]
    display_name: str
    xp: int


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# PUBLIC_INTERFACE
@router.post(
    "/auth/register",
    summary="Register",
    description="Create a new user with email/password and return token pair.",
    response_model=TokenPairResponse,
)
async def register(payload: RegisterRequest):
    """Register a new user (email unique).

    Request body:
      - email (EmailStr): Unique email for login
      - password (str): 8-128 characters
      - display_name (str, optional)

    Returns:
      200: TokenPairResponse { access_token, refresh_token, token_type }
      409: Email already registered (Conflict)
      422: Validation error for payload
    """
    try:
        async with get_session() as session:
            # Proactively enforce unique email to avoid DB-level IntegrityError surfacing as 500.
            res = await session.exec(select(User).where(User.email == payload.email))
            if res.first():
                # Return 409 Conflict per requirement for duplicate email
                raise HTTPException(status_code=409, detail="Email already registered")
            # Create username from email local part if not conflicting
            base_username = payload.email.split("@")[0]
            username = base_username
            # ensure uniqueness on username as well
            idx = 1
            while True:
                res_u = await session.exec(select(User).where(User.username == username))
                if not res_u.first():
                    break
                idx += 1
                username = f"{base_username}{idx}"
            user = User(
                username=username,
                display_name=payload.display_name or username,
                email=payload.email,
                password_hash=hash_password(payload.password),
                is_active=True,
                created_at=_now_iso(),
                updated_at=_now_iso(),
                xp=0,
            )
            session.add(user)
            await session.commit()
    except SQLAlchemyError as e:
        # Convert DB errors to a clearer 503 for operators (e.g., migrations missing or DB down)
        raise HTTPException(status_code=503, detail=f"Database unavailable or schema error: {str(e)}")
    except Exception:
        # Let FastAPI's global handler wrap unexpected issues
        raise

    access, refresh = issue_token_pair(subject=username)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


# PUBLIC_INTERFACE
@router.post(
    "/auth/login",
    summary="Login",
    description="Login with email/password and receive token pair.",
    response_model=TokenPairResponse,
)
async def login(payload: LoginRequest):
    """Authenticate using email/password.

    Request body:
      - email (EmailStr)
      - password (str): 8-128 characters

    Returns:
      200: TokenPairResponse on success
      401: Invalid credentials
      403: User inactive
      422: Validation error for payload
    """
    try:
        async with get_session() as session:
            res = await session.exec(select(User).where(User.email == payload.email))
            user = res.first()
            if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
                # Per requirement, ensure improper credentials return 401
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if getattr(user, "is_active", True) is False:
                raise HTTPException(status_code=403, detail="User inactive")
    except SQLAlchemyError as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable or schema error: {str(e)}")
    except Exception:
        raise

    access, refresh = issue_token_pair(subject=user.username)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


# PUBLIC_INTERFACE
@router.post(
    "/auth/token",
    summary="Login (alias)",
    description="Alias for /auth/login to maintain backward compatibility with older clients expecting /api/auth/token.",
    response_model=TokenPairResponse,
)
async def login_alias(payload: LoginRequest):
    """Alias endpoint that behaves like /auth/login for compatibility.

    Request body:
      - email (EmailStr)
      - password (str)

    Returns:
      200: TokenPairResponse identical to /auth/login
      4xx/422: Same semantics as /auth/login
    """
    return await login(payload)


# PUBLIC_INTERFACE
@router.post(
    "/auth/refresh",
    summary="Refresh access token",
    description="Use refresh token to obtain a new access token.",
    response_model=AccessTokenResponse,
)
async def refresh(payload: RefreshRequest):
    """Exchange a valid refresh token for a new access token.

    Request body:
      - refresh_token (str): A previously issued refresh token

    Returns:
      200: AccessTokenResponse with a new access_token and token_type
      401: Invalid/expired token or wrong token type
      422: Validation error for payload
    """
    try:
        claims = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token")
    access, _ = issue_token_pair(subject=subject)
    return {"access_token": access, "token_type": "bearer"}


# PUBLIC_INTERFACE
@router.get(
    "/auth/me",
    summary="Current user",
    description="Return profile of the authenticated user.",
    response_model=MeResponse,
)
async def me(user: User = Depends(get_current_user)):
    """Return current user info.

    Headers:
      - Authorization: Bearer <access_token>

    Returns:
      200: MeResponse { username, email, display_name, xp }
      401/403: If token invalid/expired or user inactive
    """
    return MeResponse(username=user.username, email=getattr(user, "email", None), display_name=user.display_name, xp=user.xp)
