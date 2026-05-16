import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    shared_notes = relationship("NoteShare", back_populates="shared_user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=new_uuid)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="notes")
    shares = relationship("NoteShare", back_populates="note", cascade="all, delete-orphan")


class NoteShare(Base):
    __tablename__ = "note_shares"

    id = Column(String, primary_key=True, default=new_uuid)
    note_id = Column(String, ForeignKey("notes.id"), nullable=False)
    shared_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    shared_at = Column(DateTime, default=datetime.utcnow)

    note = relationship("Note", back_populates="shares")
    shared_user = relationship("User", back_populates="shared_notes")
