from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..modules.db import get_session, User
from ..modules.errors import success
from ..modules.security import get_current_user

router = APIRouter(tags=["profile"])


class ProfileResponse(BaseModel):
    username: str
    display_name: str
    xp: int


class ProfilePatchRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100, description="New display name")


# PUBLIC_INTERFACE
@router.get("/profile", summary="Get current profile", description="Returns the profile for the current user (auth required)")
async def get_profile(user: User = Depends(get_current_user)):
    return success(ProfileResponse(username=user.username, display_name=user.display_name, xp=user.xp).model_dump())


# PUBLIC_INTERFACE
@router.patch("/profile", summary="Update profile", description="Updates profile fields for the current user (auth required)")
async def patch_profile(payload: ProfilePatchRequest, user: User = Depends(get_current_user)):
    async with get_session() as session:
        db_user = await session.get(User, user.id)
        if payload.display_name is not None:
            db_user.display_name = payload.display_name
        await session.commit()
        return success(ProfileResponse(username=db_user.username, display_name=db_user.display_name, xp=db_user.xp).model_dump())
