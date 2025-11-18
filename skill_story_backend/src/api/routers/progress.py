from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlmodel import select

from ..modules.db import get_session, User, Story
from ..modules.errors import ApplicationError, ErrorCode, success

router = APIRouter(tags=["progress"])


class ProgressResponse(BaseModel):
    xp: int
    current_story_id: Optional[int]
    current_story_title: Optional[str]
    current_episode_index: Optional[int]


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
@router.get("/progress", summary="Get progress", description="Returns XP and current story/episode position for the demo user")
async def get_progress(user: User = Depends(get_demo_user)):
    async with get_session() as session:
        db_user = await session.get(User, user.id)
        title = None
        if db_user.current_story_id:
            story = await session.get(Story, db_user.current_story_id)
            title = story.title if story else None
        return success(
            ProgressResponse(
                xp=db_user.xp,
                current_story_id=db_user.current_story_id,
                current_story_title=title,
                current_episode_index=db_user.current_episode_index,
            ).model_dump()
        )
