from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
import models, schemas, auth


# ── Users ─────────────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email.lower().strip()).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        email=user.email.lower().strip(),
        hashed_password=auth.hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ── Notes ─────────────────────────────────────────────────────────────────────

def get_notes_for_user(db: Session, user_id: str, page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    # owned notes
    owned = db.query(models.Note).filter(models.Note.owner_id == user_id)
    # shared notes
    shared_ids = (
        db.query(models.NoteShare.note_id)
        .filter(models.NoteShare.shared_user_id == user_id)
        .subquery()
    )
    shared = db.query(models.Note).filter(models.Note.id.in_(shared_ids))
    # union: pinned first, then by updated_at desc
    all_notes = owned.union(shared).order_by(
        models.Note.is_pinned.desc(), models.Note.updated_at.desc()
    )
    return all_notes.offset(offset).limit(page_size).all()


def get_note_by_id(db: Session, note_id: str):
    return db.query(models.Note).filter(models.Note.id == note_id).first()


def user_can_access_note(db: Session, user_id: str, note_id: str) -> bool:
    note = get_note_by_id(db, note_id)
    if not note:
        return False
    if note.owner_id == user_id:
        return True
    share = (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_user_id == user_id,
        )
        .first()
    )
    return share is not None


def create_note(db: Session, note: schemas.NoteCreate, owner_id: str):
    db_note = models.Note(
        title=note.title.strip(),
        content=note.content or "",
        owner_id=owner_id,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


def update_note(db: Session, note_id: str, note: schemas.NoteCreate):
    db_note = get_note_by_id(db, note_id)
    if note.title is not None:
        db_note.title = note.title.strip()
    if note.content is not None:
        db_note.content = note.content
    db_note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_note)
    return db_note


def delete_note(db: Session, note_id: str):
    db_note = get_note_by_id(db, note_id)
    db.delete(db_note)
    db.commit()


# ── Sharing ───────────────────────────────────────────────────────────────────

def is_note_already_shared(db: Session, note_id: str, user_id: str) -> bool:
    return (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_user_id == user_id,
        )
        .first()
        is not None
    )


def share_note(db: Session, note_id: str, shared_user_id: str):
    share = models.NoteShare(note_id=note_id, shared_user_id=shared_user_id)
    db.add(share)
    db.commit()


# ── Pin ───────────────────────────────────────────────────────────────────────

def set_pin(db: Session, note_id: str, pinned: bool):
    note = get_note_by_id(db, note_id)
    note.is_pinned = pinned
    db.commit()
    db.refresh(note)
    return note


# ── Search ────────────────────────────────────────────────────────────────────

def search_notes(db: Session, user_id: str, query: str):
    q = f"%{query}%"
    shared_ids = (
        db.query(models.NoteShare.note_id)
        .filter(models.NoteShare.shared_user_id == user_id)
        .subquery()
    )
    return (
        db.query(models.Note)
        .filter(
            or_(models.Note.owner_id == user_id, models.Note.id.in_(shared_ids)),
            or_(models.Note.title.ilike(q), models.Note.content.ilike(q)),
        )
        .order_by(models.Note.is_pinned.desc(), models.Note.updated_at.desc())
        .all()
    )
