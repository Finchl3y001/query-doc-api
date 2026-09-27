from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .core.config import Settings, get_settings

settings = get_settings()

sync_engine = create_engine(settings.SYNC_URL, echo = True)
async_engine = create_async_engine(settings.ASYNC_URL, echo = True)

def sync_session():
    with Session(sync_engine) as session:
        yield session

async def async_session():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session

def create_db_and_tables():
    SQLModel.metadata.create_all(sync_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

