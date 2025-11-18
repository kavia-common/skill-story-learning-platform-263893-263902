from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlmodel import select

from ..modules.db import get_session, User
from ..modules.errors import ApplicationError, ErrorCode, success

router = APIRouter(tags=["profile"])


class ProfileResponse(BaseModel):
    username: str
    display_name: str
    xp: int


class ProfilePatchRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100, description="New display name")


async def get_demo_user(x_demo_user: Optional[str] = Header(None, alias="X-Demo-User")) -> User:
    if not x_demo_user:
        raise ApplicationError("Missing X-Demo-User header", ErrorCode.AUTHENTICATION_ERROR, status_code=401)
    async with get_session() as session:
        res = await session.exec(select(User).where(User.username == x_demo_user))
        user = res.first()
        if not user:
            raise ApplicationError("User not found", ErrorCode.AUTHENTICATION_ERROR, status_code=401)
        return user


# PUBLIC_INTERFACE
@router.get("/profile", summary="Get current profile", description="Returns the profile for the demo user")
async def get_profile(user: User = Depends(get_demo_user)):
    return success(ProfileResponse(username=user.username, display_name=user.display_name, xp=user.xp).model_dump())


# PUBLIC_INTERFACE
@router.patch("/profile", summary="Update profile", description="Updates profile fields for the demo user")
async def patch_profile(payload: ProfilePatchRequest, user: User = Depends(get_demo_user)):
    async with get_session() as session:
        db_user = await session.get(User, user.id)
        if payload.display_name is not None:
            db_user.display_name = payload.display_name
        await session.commit()
        return success(ProfileResponse(username=db_user.username, display_name=db_user.display_name, xp=db_user.xp).model_dump())
