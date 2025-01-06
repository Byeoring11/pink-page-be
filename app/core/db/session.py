from contextvars import ContextVar, Token
from typing import Union

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_scoped_session, async_sessionmaker,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from core.config import settings

# 세션 컨텍스트 설정
session_context: ContextVar[str] = ContextVar("session_context")


def get_session_context() -> str:
    return session_context.get()


def set_session_context(session_id: str) -> Token:
    return session_context.set(session_id)


def reset_session_context(context: Token) -> None:
    session_context.reset(context)


# DB 설정
engines = create_async_engine(settings.DATABASE_URL, echo=True)


class SingleRoutingSession(Session):
    def get_bind(self, mapper=None, clause=None, **kw):
        return engines.sync_engine


async_session_factory = async_sessionmaker(
    class_=AsyncSession,
    sync_session_class=SingleRoutingSession,
    expire_on_commit=False,
)

# session 선언
session: Union[AsyncSession, async_scoped_session] = async_scoped_session(
    session_factory=async_session_factory,
    scopefunc=get_session_context,
)

# Base 선언
Base = declarative_base()