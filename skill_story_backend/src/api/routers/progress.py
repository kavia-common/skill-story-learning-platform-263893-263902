from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..modules.db import get_session, User, Story
from ..modules.errors import success
from ..modules.security import get_current_user

router = APIRouter(tags=["progress"])


class ProgressResponse(BaseModel):
    xp: int
    current_story_id: Optional[int]
    current_story_title: Optional[str]
    current_episode_index: Optional[int]


# PUBLIC_INTERFACE
@router.get("/progress", summary="Get progress", description="Returns XP and current story/episode position (auth required)")
async def get_progress(user: User = Depends(get_current_user)):
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
