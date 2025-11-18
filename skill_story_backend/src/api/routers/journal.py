from typing import Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlmodel import select

from ..modules.db import get_session, JournalEntry, User
from ..modules.errors import ApplicationError, ErrorCode, success

router = APIRouter(tags=["journal"])


class JournalEntryModel(BaseModel):
    id: int
    content: str


class JournalCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


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
@router.get("/journal", summary="List journal entries", description="Lists journal entries for the demo user")
async def list_journal(user: User = Depends(get_demo_user)):
    async with get_session() as session:
        res = await session.exec(select(JournalEntry).where(JournalEntry.user_id == user.id))
        items = res.all()
        payload = [JournalEntryModel(id=i.id, content=i.content).model_dump() for i in items]
        return success(payload)


# PUBLIC_INTERFACE
@router.post("/journal", summary="Create journal entry", description="Creates a new journal entry for the demo user")
async def create_journal(payload: JournalCreateRequest, user: User = Depends(get_demo_user)):
    async with get_session() as session:
        entry = JournalEntry(user_id=user.id, content=payload.content)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return success(JournalEntryModel(id=entry.id, content=entry.content).model_dump())
