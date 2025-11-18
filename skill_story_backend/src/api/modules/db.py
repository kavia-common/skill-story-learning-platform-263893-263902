from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker

from .config import settings

# Define models

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    display_name: str
    xp: int = 0
    current_story_id: Optional[int] = Field(default=None, foreign_key="story.id")
    current_episode_index: Optional[int] = Field(default=None)

    journals: List["JournalEntry"] = Relationship(back_populates="user")


class Story(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str

    episodes: List["Episode"] = Relationship(back_populates="story")


class Episode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    story_id: int = Field(foreign_key="story.id", index=True)
    index: int = Field(index=True)  # episode order within a story (0-based)
    content: str

    story: Optional[Story] = Relationship(back_populates="episodes")
    choices: List["Choice"] = Relationship(back_populates="episode")


class Choice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    episode_id: int = Field(foreign_key="episode.id", index=True)
    text: str
    next_episode_index: Optional[int] = Field(default=None)  # None -> story end
    xp_delta: int = 0

    episode: Optional[Episode] = Relationship(back_populates="choices")


class JournalEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    content: str

    user: Optional[User] = Relationship(back_populates="journals")


engine: Optional[AsyncEngine] = None
AsyncSessionLocal = None


async def init_db():
    """Initialize database engine, create tables, and seed demo data."""
    global engine, AsyncSessionLocal
    if engine is None:
        engine = create_async_engine(settings.db_url(), echo=False, future=True)
        AsyncSessionLocal = sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    # Seed demo data idempotently
    async with get_session() as session:
        # Ensure demo user
        demo_username = "demo_user"
        res = await session.exec(select(User).where(User.username == demo_username))
        user = res.first()
        if not user:
            user = User(username=demo_username, display_name="Demo User", xp=0)
            session.add(user)
            await session.commit()
        # Seed story if not exists
        res = await session.exec(select(Story).where(Story.title == "Leadership Basics"))
        story = res.first()
        if not story:
            story = Story(
                title="Leadership Basics",
                description="A short scenario to practice leadership decision-making.",
            )
            session.add(story)
            await session.commit()
            await session.refresh(story)

            # Episodes
            ep0 = Episode(story_id=story.id, index=0, content="You are leading a new project kickoff. How do you start?")
            ep1 = Episode(story_id=story.id, index=1, content="You choose to listen first. The team shares concerns.")
            ep2 = Episode(story_id=story.id, index=2, content="You choose to assert a plan. The team seems hesitant.")
            session.add_all([ep0, ep1, ep2])
            await session.commit()
            await session.refresh(ep0)
            await session.refresh(ep1)
            await session.refresh(ep2)

            # Choices for ep0
            c0 = Choice(episode_id=ep0.id, text="Listen to the team's input", next_episode_index=1, xp_delta=10)
            c1 = Choice(episode_id=ep0.id, text="Present a detailed plan immediately", next_episode_index=2, xp_delta=5)
            session.add_all([c0, c1])

            # Choices for ep1 (end)
            c2 = Choice(episode_id=ep1.id, text="Acknowledge concerns and co-create next steps", next_episode_index=None, xp_delta=15)
            session.add(c2)

            # Choices for ep2 (end)
            c3 = Choice(episode_id=ep2.id, text="Invite feedback to adjust the plan", next_episode_index=None, xp_delta=10)
            session.add(c3)

            await session.commit()

        # Ensure demo_user has initial progress
        res = await session.exec(select(User).where(User.username == demo_username))
        demo_user = res.first()
        if demo_user and demo_user.current_story_id is None:
            # start at first episode of the story
            res_s = await session.exec(select(Story).where(Story.title == "Leadership Basics"))
            story_obj = res_s.first()
            demo_user.current_story_id = story_obj.id
            demo_user.current_episode_index = 0
            await session.commit()


async def close_db():
    """Close engine reference (async engines close with GC; placeholder)."""
    # Nothing explicit needed; present for symmetry/future
    return


class SessionContext:
    """Async context manager for DB sessions."""

    def __init__(self):
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        self.session = AsyncSessionLocal()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc:
                await self.session.rollback()
        finally:
            await self.session.close()


def get_session():
    """Helper to get an async session context manager."""
    return SessionContext()
