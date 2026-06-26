from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./judiciary.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)          # UUID
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    cases = relationship("Case", back_populates="user")


class Case(Base):
    __tablename__ = "cases"
    id = Column(String, primary_key=True)          # UUID
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="cases")
    documents = relationship("Document", back_populates="case")


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)          # UUID
    case_id = Column(String, ForeignKey("cases.id"))
    user_id = Column(String)
    filename = Column(String)
    doc_type = Column(String)                      # judgment, petition, FIR, statute
    raw_text = Column(Text)
    analysis = Column(JSON)                        # full NLP + LLM output stored here
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="documents")


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session