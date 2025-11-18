from typing import Optional, List, Dict, Any
import asyncio
import logging

from sqlmodel import SQLModel, Field, Relationship, select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker

from .config import settings

# Structured logger for DB module
logger = logging.getLogger("skill_story_backend.db")

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
    description: str  # include simple tags inline in description (e.g., [communication])

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


async def _connect_with_retries() -> None:
    """Create engine and test connection with retries and backoff."""
    global engine, AsyncSessionLocal
    url = settings.db_url()
    if engine is None:
        logger.info(
            "Creating async engine",
            extra={"db_url_driver": url.split("://", 1)[0], "retries": settings.DB_CONNECT_MAX_RETRIES},
        )
        # pool_pre_ping=True to validate connections from the pool
        engine = create_async_engine(url, echo=False, future=True, pool_pre_ping=True)
        AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    attempts = 0
    last_err: Optional[Exception] = None
    while attempts < settings.DB_CONNECT_MAX_RETRIES:
        attempts += 1
        try:
            async with engine.begin() as conn:
                # simple connect test; no-op
                await conn.run_sync(lambda conn: None)
            logger.info("Database connection established", extra={"attempt": attempts})
            return
        except Exception as e:
            last_err = e
            backoff = settings.DB_CONNECT_BACKOFF_SECONDS * attempts
            logger.warning(
                "Database connection attempt failed; retrying",
                extra={"attempt": attempts, "backoff_seconds": backoff, "error": str(e)},
            )
            await asyncio.sleep(backoff)
    # Retries exhausted
    logger.error(
        "Failed to connect to database after retries",
        extra={"retries": settings.DB_CONNECT_MAX_RETRIES, "error": str(last_err) if last_err else "unknown"},
    )
    # Do not raise to avoid crashing startup; subsequent DB usage will still error until DB becomes available.


async def _create_schema_safe() -> None:
    """Create tables if not exist, with error handling and logs."""
    if engine is None:
        return
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database schema ensured (create_all successful)")
    except Exception as e:
        logger.error("Schema creation failed", extra={"error": str(e)})
        # Avoid raising to not crash startup


async def _run_seed_safe() -> None:
    """Run seeding steps with idempotency and logging, safe to call multiple times."""
    try:
        async with get_session() as session:
            demo_username = "demo_user"

            # Ensure demo user exists
            res = await session.exec(select(User).where(User.username == demo_username))
            user = res.first()
            if not user:
                user = User(username=demo_username, display_name="Demo User", xp=0)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info("Seeded demo user", extra={"username": demo_username, "user_id": user.id})
            else:
                logger.info("Demo user exists", extra={"username": demo_username, "user_id": user.id})

            # Seed the bundled stories
            await _seed_stories(session)

            # Ensure demo_user has initial progress (only if not already set)
            res = await session.exec(select(User).where(User.username == demo_username))
            demo_user = res.first()
            if demo_user and demo_user.current_story_id is None:
                res_s = await session.exec(select(Story).where(Story.title == "Leadership Basics"))
                story_obj = res_s.first()
                if story_obj:
                    demo_user.current_story_id = story_obj.id
                    demo_user.current_episode_index = 0
                    await session.commit()
                    logger.info("Initialized demo user progress", extra={"story_id": story_obj.id})

            # Optionally seed a couple of journal entries for the demo user if none exist
            await _seed_demo_journals(session, user_id=user.id)
            logger.info("Seeding completed")
    except Exception as e:
        logger.error("Seeding failed", extra={"error": str(e)})
        # Swallow to avoid startup crash; can be retried later.


# PUBLIC_INTERFACE
async def init_db():
    """Initialize database engine, create tables, and seed demo data.

    Resiliency improvements:
    - Retries with backoff for initial DB connectivity
    - Safe schema creation and seeding (non-fatal on failure)
    - Optional seed deferral to avoid blocking service readiness
    """
    await _connect_with_retries()
    await _create_schema_safe()

    if settings.DB_SEED_DEFER:
        # Defer heavy seeding to background so readiness isn't blocked
        logger.info("Deferring DB seeding to background task", extra={"defer": True})
        try:
            asyncio.create_task(_run_seed_safe())
        except Exception as e:
            logger.error("Failed to schedule background seeding", extra={"error": str(e)})
    else:
        await _run_seed_safe()


# PUBLIC_INTERFACE
async def close_db():
    """Close engine reference (async engines close with GC; placeholder)."""
    # Nothing explicit needed; present for symmetry/future
    return


class SessionContext:
    """Async context manager for DB sessions."""

    def __init__(self):
        self.session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        if AsyncSessionLocal is None:
            # Ensure we at least attempted to connect if get_session is used before init_db
            await _connect_with_retries()
        self.session = AsyncSessionLocal()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if exc:
                await self.session.rollback()
        finally:
            await self.session.close()


# PUBLIC_INTERFACE
def get_session():
    """Helper to get an async session context manager."""
    return SessionContext()


async def _seed_stories(session: AsyncSession):
    """Create multiple sample stories with episodes and choices, idempotently.

    We keep tags simple by embedding them in descriptions (e.g., Tags: communication).
    Each episode has 2-3 choices affecting XP and progression.
    """

    # Define stories data model for seeding
    stories_payload: List[Dict[str, Any]] = [
        {
            "title": "Leadership Basics",
            "description": "A short scenario to practice leadership decision-making. Tags: leadership",
            "episodes": [
                {
                    "content": "You are leading a new project kickoff. How do you start?",
                    "choices": [
                        {"text": "Listen to the team's input", "next": 1, "xp": 10},
                        {"text": "Present a detailed plan immediately", "next": 2, "xp": 5},
                    ],
                },
                {
                    "content": "You choose to listen first. The team shares concerns.",
                    "choices": [
                        {"text": "Acknowledge concerns and co-create next steps", "next": None, "xp": 15}
                    ],
                },
                {
                    "content": "You choose to assert a plan. The team seems hesitant.",
                    "choices": [
                        {"text": "Invite feedback to adjust the plan", "next": None, "xp": 10}
                    ],
                },
            ],
        },
        {
            "title": "Effective Communication",
            "description": "Navigate a tough stakeholder update meeting. Tags: communication",
            "episodes": [
                {
                    "content": "The product launch is delayed. How do you open the stakeholder meeting?",
                    "choices": [
                        {"text": "Start with transparency about risks and status", "next": 1, "xp": 10},
                        {"text": "Highlight positives and defer the delay conversation", "next": 2, "xp": 5},
                        {"text": "Ask stakeholders for their priorities before sharing status", "next": 1, "xp": 8},
                    ],
                },
                {
                    "content": "Stakeholders appreciate the clarity. They ask for impact and next steps.",
                    "choices": [
                        {"text": "Share a concise impact summary and a mitigation plan", "next": 3, "xp": 15},
                        {"text": "Promise to follow up later via email", "next": 3, "xp": 5},
                    ],
                },
                {
                    "content": "Stakeholders look surprised when the delay surfaces later.",
                    "choices": [
                        {"text": "Apologize for the approach and reset with clear facts", "next": 3, "xp": 10},
                        {"text": "Continue focusing on positives only", "next": None, "xp": 2},
                    ],
                },
                {
                    "content": "Meeting wrap-up: stakeholders want a weekly update cadence.",
                    "choices": [
                        {"text": "Confirm a brief weekly status format", "next": None, "xp": 12},
                        {"text": "Suggest ad-hoc updates only", "next": None, "xp": 3},
                    ],
                },
            ],
        },
        {
            "title": "Emotional Intelligence at Work",
            "description": "Handle a teammate's frustration during a sprint. Tags: emotional-intelligence",
            "episodes": [
                {
                    "content": "A teammate is visibly frustrated after feedback on their code. What do you do first?",
                    "choices": [
                        {"text": "Privately ask how they are feeling and listen", "next": 1, "xp": 12},
                        {"text": "Remind them to be professional and move on", "next": 2, "xp": 3},
                    ],
                },
                {
                    "content": "They share they're overwhelmed. They fear missing expectations.",
                    "choices": [
                        {"text": "Validate feelings and ask what support would help", "next": 3, "xp": 15},
                        {"text": "Offer to pair-program on a problem area", "next": 3, "xp": 10},
                    ],
                },
                {
                    "content": "They quiet down, but the tension remains.",
                    "choices": [
                        {"text": "Revisit the conversation later with empathy", "next": 3, "xp": 8},
                        {"text": "Ignore it and focus on sprint tasks", "next": None, "xp": 1},
                    ],
                },
                {
                    "content": "You agree on a plan to adjust workload and checkpoints.",
                    "choices": [
                        {"text": "Summarize the plan and schedule a follow-up", "next": None, "xp": 12},
                        {"text": "Leave it informal with no clear next step", "next": None, "xp": 4},
                    ],
                },
            ],
        },
        {
            "title": "Team Decision-Making",
            "description": "Facilitate alignment on a technical approach. Tags: leadership, communication",
            "episodes": [
                {
                    "content": "Two engineers disagree on architecture. How do you begin?",
                    "choices": [
                        {"text": "Set a clear decision-making framework", "next": 1, "xp": 12},
                        {"text": "Let them debate freely and hope it resolves", "next": 2, "xp": 4},
                    ],
                },
                {
                    "content": "You outline criteria: scalability, complexity, and timeline.",
                    "choices": [
                        {"text": "Ask each to present trade-offs concisely", "next": 3, "xp": 12},
                        {"text": "Pick one quickly to save time", "next": None, "xp": 2},
                    ],
                },
                {
                    "content": "Debate is heated and unfocused.",
                    "choices": [
                        {"text": "Refocus on criteria and timebox discussion", "next": 3, "xp": 10},
                        {"text": "End the meeting without a decision", "next": None, "xp": 1},
                    ],
                },
                {
                    "content": "Team converges on a pragmatic option with a revisit checkpoint.",
                    "choices": [
                        {"text": "Document the decision and owners", "next": None, "xp": 12},
                        {"text": "Move on without documenting rationale", "next": None, "xp": 3},
                    ],
                },
            ],
        },
    ]

    # Seed each story by title, then episodes by index, then choices by text per episode
    for s in stories_payload:
        # Check for story existence by title
        existing_story_res = await session.exec(select(Story).where(Story.title == s["title"]))
        existing_story = existing_story_res.first()
        if not existing_story:
            story = Story(title=s["title"], description=s["description"])
            session.add(story)
            await session.commit()
            await session.refresh(story)
            logger.info("Seeded story", extra={"title": s["title"], "story_id": story.id})
        else:
            story = existing_story
            logger.info("Story exists", extra={"title": s["title"], "story_id": story.id})

        # Seed episodes
        for idx, ep in enumerate(s["episodes"]):
            ep_res = await session.exec(
                select(Episode).where(Episode.story_id == story.id, Episode.index == idx)
            )
            existing_ep = ep_res.first()
            if not existing_ep:
                new_ep = Episode(story_id=story.id, index=idx, content=ep["content"])
                session.add(new_ep)
                await session.commit()
                await session.refresh(new_ep)
                logger.info("Seeded episode", extra={"story_id": story.id, "ep_index": idx, "ep_id": new_ep.id})
            else:
                # Optionally update content if changed
                new_ep = existing_ep
                if existing_ep.content != ep["content"]:
                    existing_ep.content = ep["content"]
                    await session.commit()
                    logger.info("Updated episode content", extra={"story_id": story.id, "ep_index": idx})

            # Seed choices per episode
            for ch in ep.get("choices", []):
                # Idempotency heuristic: identify a choice by (episode_id, text)
                ch_res = await session.exec(
                    select(Choice).where(Choice.episode_id == new_ep.id, Choice.text == ch["text"])
                )
                existing_choice = ch_res.first()
                if not existing_choice:
                    choice = Choice(
                        episode_id=new_ep.id,
                        text=ch["text"],
                        next_episode_index=ch["next"],
                        xp_delta=ch["xp"],
                    )
                    session.add(choice)
                    logger.info(
                        "Seeded choice",
                        extra={"episode_id": new_ep.id, "text": ch["text"], "next": ch["next"], "xp": ch["xp"]},
                    )
                else:
                    # Update attributes if needed to match seed spec
                    updated = False
                    if existing_choice.next_episode_index != ch["next"]:
                        existing_choice.next_episode_index = ch["next"]
                        updated = True
                    if existing_choice.xp_delta != ch["xp"]:
                        existing_choice.xp_delta = ch["xp"]
                        updated = True
                    if updated:
                        session.add(existing_choice)
                        logger.info(
                            "Updated choice",
                            extra={
                                "choice_id": existing_choice.id,
                                "episode_id": new_ep.id,
                                "text": ch["text"],
                                "next": ch["next"],
                                "xp": ch["xp"],
                            },
                        )
            await session.commit()


async def _seed_demo_journals(session: AsyncSession, user_id: int):
    """Seed a couple of journal entries for the demo user if they don't exist."""
    # Check if user has any journals
    res = await session.exec(select(JournalEntry).where(JournalEntry.user_id == user_id))
    existing = res.first()
    if existing:
        logger.info("Demo journals already exist", extra={"user_id": user_id})
        return  # already has entries; do not duplicate

    entries = [
        JournalEntry(
            user_id=user_id,
            content="Reflecting on leadership choices: listening first helped uncover hidden risks.",
        ),
        JournalEntry(
            user_id=user_id,
            content="Communication lesson: transparency early builds trust and reduces surprises.",
        ),
    ]
    session.add_all(entries)
    await session.commit()
    logger.info("Seeded demo journals", extra={"user_id": user_id, "count": len(entries)})
