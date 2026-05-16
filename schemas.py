from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str


class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = ""


class NoteOut(BaseModel):
    id: str
    title: str
    content: str
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShareNote(BaseModel):
    share_with_email: EmailStr
