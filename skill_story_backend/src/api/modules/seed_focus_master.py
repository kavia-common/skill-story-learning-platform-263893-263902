"""Seed utilities for 'The Focus Master' story.

This module defines the story structure as JSON-like Python data and exposes
a single public function to insert/update it idempotently into the database.

Usage:
- Imported by the DB seeding pipeline to ensure the story exists.
- Can be run via a small helper script to insert once in authoring environments.
"""
from typing import Any, Dict
import logging
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .db import Story, Episode, Choice

logger = logging.getLogger("skill_story_backend.seed_focus_master")


# PUBLIC_INTERFACE
async def seed_focus_master(session: AsyncSession) -> Dict[str, Any]:
    """Insert or update the 'The Focus Master' story idempotently.

    Returns a dict with the story_id and counts for episodes/choices seeded.
    """
    story_payload = _focus_master_payload()

    # Ensure story exists by title
    res = await session.exec(select(Story).where(Story.title == story_payload["title"]))
    story = res.first()
    if not story:
        story = Story(title=story_payload["title"], description=story_payload["description"])
        session.add(story)
        await session.commit()
        await session.refresh(story)
        logger.info("Seeded story 'The Focus Master'", extra={"story_id": story.id})
    else:
        # Update description if changed
        if story.description != story_payload["description"]:
            story.description = story_payload["description"]
            await session.commit()
            logger.info("Updated story description for 'The Focus Master'", extra={"story_id": story.id})

    # Upsert episodes and choices by index and choice text respectively
    ep_count = 0
    ch_count = 0
    for idx, ep in enumerate(story_payload["episodes"]):
        ep_res = await session.exec(select(Episode).where(Episode.story_id == story.id, Episode.index == idx))
        db_ep = ep_res.first()
        if not db_ep:
            db_ep = Episode(story_id=story.id, index=idx, content=ep["content"])
            session.add(db_ep)
            await session.commit()
            await session.refresh(db_ep)
            logger.info("Seeded FM episode", extra={"story_id": story.id, "ep_index": idx, "ep_id": db_ep.id})
        else:
            if db_ep.content != ep["content"]:
                db_ep.content = ep["content"]
                await session.commit()
                logger.info("Updated FM episode content", extra={"story_id": story.id, "ep_index": idx})
        ep_count += 1

        # choices
        for ch in ep.get("choices", []):
            ch_res = await session.exec(select(Choice).where(Choice.episode_id == db_ep.id, Choice.text == ch["text"]))
            db_ch = ch_res.first()
            if not db_ch:
                db_ch = Choice(
                    episode_id=db_ep.id,
                    text=ch["text"],
                    next_episode_index=ch["next"],
                    xp_delta=ch.get("xp", 0),
                )
                session.add(db_ch)
                ch_count += 1
                logger.info(
                    "Seeded FM choice",
                    extra={"episode_id": db_ep.id, "text": ch["text"], "next": ch["next"], "xp": ch.get("xp", 0)},
                )
            else:
                updated = False
                if db_ch.next_episode_index != ch["next"]:
                    db_ch.next_episode_index = ch["next"]
                    updated = True
                if db_ch.xp_delta != ch.get("xp", 0):
                    db_ch.xp_delta = ch.get("xp", 0)
                    updated = True
                if updated:
                    session.add(db_ch)
                    logger.info(
                        "Updated FM choice",
                        extra={
                            "choice_id": db_ch.id,
                            "episode_id": db_ep.id,
                            "text": ch["text"],
                            "next": ch["next"],
                            "xp": ch.get("xp", 0),
                        },
                    )
        await session.commit()

    return {"story_id": story.id, "episodes": ep_count, "choices": ch_count}


def _focus_master_payload() -> Dict[str, Any]:
    """Return the static payload for 'The Focus Master' story.

    Notes:
    - Terminal episodes have no choices (next: None).
    - Episode indices must align with next references.
    """
    return {
        "title": "The Focus Master",
        "description": "Sharpen your prioritization and deep-work habits through branching scenarios. Tags: productivity, focus",
        "episodes": [
            {
                "content": "It's 9:00 AM. Your day is packed. How do you start?",
                "choices": [
                    {"text": "Clarify the top 1-2 outcomes for today", "next": 1, "xp": 10},
                    {"text": "Open inbox and start replying", "next": 2, "xp": 4},
                ],
            },
            {
                "content": "You defined clear outcomes. Which focus block do you schedule first?",
                "choices": [
                    {"text": "90-minute deep work block on the most impactful task", "next": 3, "xp": 12},
                    {"text": "30-minute short block to 'warm up'", "next": 3, "xp": 6},
                ],
            },
            {
                "content": "Email pulls you into context-switching. You feel scattered.",
                "choices": [
                    {"text": "Close email, set a timer, and refocus on the priority", "next": 3, "xp": 10},
                    {"text": "Keep going in the inbox to 'clear the deck'", "next": 4, "xp": 2},
                ],
            },
            {
                "content": "You begin your focus block. A chat ping arrives. What do you do?",
                "choices": [
                    {"text": "Mute notifications and continue; check later", "next": 5, "xp": 12},
                    {"text": "Answer quickly—it's just a minute", "next": 4, "xp": 3},
                ],
            },
            {
                "content": "Interruptions accumulate and the block fragments. Progress is minimal.",
                "choices": [
                    {"text": "Restart a shorter 25-minute Pomodoro, single-tasking", "next": 5, "xp": 9},
                    {"text": "Multitask to catch up everywhere", "next": None, "xp": 1},
                ],
            },
            {
                "content": "You protect the time and complete a meaningful chunk. Reflect on what helped.",
                "choices": [
                    {"text": "Write a brief reflection to reinforce the habit", "next": None, "xp": 12},
                    {"text": "Move on immediately to the next meeting", "next": None, "xp": 5},
                ],
            },
        ],
    }
