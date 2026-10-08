from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, create_engine

from .core.config import get_settings

settings = get_settings()

sync_engine = create_engine(str(settings.SYNC_URL), echo = True)
async_engine = create_async_engine(str(settings.ASYNC_URL), echo = True)

def sync_session():
    with Session(sync_engine) as session:
        yield session

async def async_session():
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session

#commented out since alembic now handles creation of tables, updating columns, tracking version history
#def create_db_and_tables():
#    SQLModel.metadata.create_all(sync_engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application is booting up...")
    yield
    print("Application is shutting down...")

