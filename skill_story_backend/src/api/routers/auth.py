from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from ..modules.config import settings
from ..modules.db import get_session, User
from sqlmodel import select

router = APIRouter(tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token for demo use")
    token_type: str = "bearer"


# PUBLIC_INTERFACE
@router.post(
    "/auth/token",
    summary="Issue demo token",
    description="Issues a short-lived JWT for demo purposes if X-Demo-User is provided.",
    response_model=TokenResponse,
)
async def issue_token(x_demo_user: Optional[str] = Header(None, alias="X-Demo-User")):
    """Issue a JWT for the provided demo user header."""
    if not x_demo_user:
        raise HTTPException(status_code=400, detail="X-Demo-User header required")
    # Ensure user exists
    async with get_session() as session:
        res = await session.exec(select(User).where(User.username == x_demo_user))
        user = res.first()
        if not user:
            # Create a simple user record
            user = User(username=x_demo_user, display_name=x_demo_user, xp=0)
            session.add(user)
            await session.commit()
    now = datetime.utcnow()
    payload = {"sub": x_demo_user, "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=1)).timestamp())}
    token = jwt.encode(payload, settings.APP_SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}
