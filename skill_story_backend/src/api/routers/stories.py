from typing import List, Optional

from fastapi import APIRouter, Depends, Header, Path
from pydantic import BaseModel, Field
from sqlmodel import select

from ..modules.db import get_session, Story, Episode, Choice, User
from ..modules.errors import ApplicationError, ErrorCode, success

router = APIRouter(tags=["stories"])


class ChoiceModel(BaseModel):
    id: int
    text: str
    next_episode_index: Optional[int]
    xp_delta: int


class EpisodeModel(BaseModel):
    id: int
    index: int
    content: str
    choices: List[ChoiceModel] = []


class StoryModel(BaseModel):
    id: int
    title: str
    description: str


class StoryDetailModel(StoryModel):
    episodes: List[EpisodeModel] = []


class SubmitChoiceRequest(BaseModel):
    choice_id: int = Field(..., description="Selected choice id")


class SubmitChoiceResponse(BaseModel):
    story_id: int
    next_episode_index: Optional[int]
    current_xp: int
    reached_end: bool
    next_episode: Optional[EpisodeModel] = None


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
@router.get(
    "/stories",
    summary="List stories",
    description="Returns all available stories.",
)
async def list_stories():
    async with get_session() as session:
        res = await session.exec(select(Story))
        stories = res.all()
        payload = [StoryModel(id=s.id, title=s.title, description=s.description).model_dump() for s in stories]
        return success(payload)


# PUBLIC_INTERFACE
@router.get(
    "/stories/{story_id}",
    summary="Get story by ID",
    description="Returns a story and its episodes metadata.",
)
async def get_story(story_id: int = Path(..., ge=1)):
    async with get_session() as session:
        s = await session.get(Story, story_id)
        if not s:
            raise ApplicationError("Story not found", ErrorCode.RESOURCE_NOT_FOUND, status_code=404)
        eps_res = await session.exec(select(Episode).where(Episode.story_id == s.id).order_by(Episode.index))
        eps = eps_res.all()
        items = []
        for e in eps:
            ch_res = await session.exec(select(Choice).where(Choice.episode_id == e.id))
            chs = ch_res.all()
            items.append(
                EpisodeModel(
                    id=e.id,
                    index=e.index,
                    content=e.content,
                    choices=[ChoiceModel(id=c.id, text=c.text, next_episode_index=c.next_episode_index, xp_delta=c.xp_delta) for c in chs],
                ).model_dump()
            )
        detail = StoryDetailModel(id=s.id, title=s.title, description=s.description, episodes=items)
        return success(detail.model_dump())


# PUBLIC_INTERFACE
@router.get(
    "/stories/{story_id}/episodes/{ep_index}",
    summary="Get episode",
    description="Get specific episode (by index within story) with its choices.",
)
async def get_episode(story_id: int = Path(..., ge=1), ep_index: int = Path(..., ge=0)):
    async with get_session() as session:
        s = await session.get(Story, story_id)
        if not s:
            raise ApplicationError("Story not found", ErrorCode.RESOURCE_NOT_FOUND, status_code=404)
        ep_res = await session.exec(select(Episode).where(Episode.story_id == story_id, Episode.index == ep_index))
        e = ep_res.first()
        if not e:
            raise ApplicationError("Episode not found", ErrorCode.RESOURCE_NOT_FOUND, status_code=404)
        ch_res = await session.exec(select(Choice).where(Choice.episode_id == e.id))
        chs = ch_res.all()
        ep = EpisodeModel(
            id=e.id,
            index=e.index,
            content=e.content,
            choices=[ChoiceModel(id=c.id, text=c.text, next_episode_index=c.next_episode_index, xp_delta=c.xp_delta) for c in chs],
        )
        return success(ep.model_dump())


# PUBLIC_INTERFACE
@router.post(
    "/stories/{story_id}/choices",
    summary="Submit a choice and advance",
    description="Submits a choice for current episode, updates XP and progression, and returns next episode payload and XP.",
    response_model=dict,
)
async def submit_choice(payload: SubmitChoiceRequest, user: User = Depends(get_demo_user), story_id: int = Path(..., ge=1)):
    async with get_session() as session:
        # Ensure user and current story
        db_user = await session.get(User, user.id)
        if not db_user:
            raise ApplicationError("User not found", ErrorCode.AUTHENTICATION_ERROR, status_code=401)
        if db_user.current_story_id != story_id:
            # Reset to this story at start if different
            db_user.current_story_id = story_id
            db_user.current_episode_index = 0
            await session.commit()

        # Validate choice belongs to current episode
        ep_res = await session.exec(select(Episode).where(Episode.story_id == story_id, Episode.index == db_user.current_episode_index))
        current_ep = ep_res.first()
        if not current_ep:
            raise ApplicationError("Current episode not found", ErrorCode.RESOURCE_NOT_FOUND, status_code=404)
        ch_res = await session.exec(select(Choice).where(Choice.id == payload.choice_id, Choice.episode_id == current_ep.id))
        choice = ch_res.first()
        if not choice:
            raise ApplicationError("Choice not valid for current episode", ErrorCode.VALIDATION_ERROR, status_code=400)

        # Update XP and progression
        db_user.xp += choice.xp_delta or 0
        next_index = choice.next_episode_index
        reached_end = next_index is None
        if reached_end:
            db_user.current_episode_index = None
        else:
            db_user.current_episode_index = next_index
        await session.commit()

        next_episode_payload = None
        if not reached_end:
            next_ep_res = await session.exec(select(Episode).where(Episode.story_id == story_id, Episode.index == next_index))
            next_ep = next_ep_res.first()
            ch2_res = await session.exec(select(Choice).where(Choice.episode_id == next_ep.id))
            chs2 = ch2_res.all()
            next_episode_payload = EpisodeModel(
                id=next_ep.id,
                index=next_ep.index,
                content=next_ep.content,
                choices=[ChoiceModel(id=c.id, text=c.text, next_episode_index=c.next_episode_index, xp_delta=c.xp_delta) for c in chs2],
            ).model_dump()

        resp = SubmitChoiceResponse(
            story_id=story_id,
            next_episode_index=next_index,
            current_xp=db_user.xp,
            reached_end=reached_end,
            next_episode=next_episode_payload,
        ).model_dump()
        return success(resp)
