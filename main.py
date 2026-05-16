from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn

from database import engine, get_db
import models, schemas, auth, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Notes App API",
    description="A multi-user notes service with sharing functionality",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if not user.email or not user.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=409, detail="Email already registered")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    crud.create_user(db, user)
    return {"message": "User registered successfully"}


@app.post("/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user or not auth.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token}


# ── Notes CRUD ────────────────────────────────────────────────────────────────

@app.get("/notes", response_model=List[schemas.NoteOut])
def get_notes(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")
    notes = crud.get_notes_for_user(db, current_user.id, page, page_size)
    return notes


@app.get("/notes/{note_id}", response_model=schemas.NoteOut)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    note = crud.get_note_by_id(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not crud.user_can_access_note(db, current_user.id, note_id):
        raise HTTPException(status_code=403, detail="Access denied")
    return note


@app.post("/notes", response_model=schemas.NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    note: schemas.NoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if not note.title or not note.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    return crud.create_note(db, note, current_user.id)


@app.put("/notes/{note_id}", response_model=schemas.NoteOut)
def update_note(
    note_id: str,
    note: schemas.NoteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    db_note = crud.get_note_by_id(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if db_note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can update this note")
    return crud.update_note(db, note_id, note)


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    db_note = crud.get_note_by_id(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if db_note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can delete this note")
    crud.delete_note(db, note_id)


# ── Share ─────────────────────────────────────────────────────────────────────

@app.post("/notes/{note_id}/share")
def share_note(
    note_id: str,
    payload: schemas.ShareNote,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    db_note = crud.get_note_by_id(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if db_note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can share this note")
    target = crud.get_user_by_email(db, payload.share_with_email)
    if not target:
        raise HTTPException(status_code=404, detail="User with that email not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share a note with yourself")
    if crud.is_note_already_shared(db, note_id, target.id):
        return {"message": "Note already shared with this user"}
    crud.share_note(db, note_id, target.id)
    return {"message": f"Note shared with {payload.share_with_email}"}


# ── Search (stretch goal) ─────────────────────────────────────────────────────

@app.get("/search", response_model=List[schemas.NoteOut])
def search_notes(
    q: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    return crud.search_notes(db, current_user.id, q.strip())


# ── Meta ──────────────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/about")
def about():
    return {
        "name": "Candidate Name",
        "email": "candidate@email.com",
        "my features": {
            "Note Pinning": (
                "Users can pin important notes so they always appear at the top of GET /notes. "
                "Chosen because it's the #1 power-user request in any notes app — "
                "quick access to high-priority items without manual searching."
            ),
            "Full-text Search": (
                "GET /search?q=keyword searches both title and content of all notes "
                "the user owns or has access to. Chosen because it makes the app "
                "genuinely useful at scale when users have dozens of notes."
            ),
            "Pagination": (
                "GET /notes supports ?page and ?page_size query params. "
                "Prevents unbounded result sets and keeps the API production-safe."
            ),
        },
    }


# ── Pin feature (custom) ──────────────────────────────────────────────────────

@app.post("/notes/{note_id}/pin")
def pin_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    db_note = crud.get_note_by_id(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not crud.user_can_access_note(db, current_user.id, note_id):
        raise HTTPException(status_code=403, detail="Access denied")
    crud.set_pin(db, note_id, True)
    return {"message": "Note pinned"}


@app.post("/notes/{note_id}/unpin")
def unpin_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(auth.get_current_user),
):
    db_note = crud.get_note_by_id(db, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if not crud.user_can_access_note(db, current_user.id, note_id):
        raise HTTPException(status_code=403, detail="Access denied")
    crud.set_pin(db, note_id, False)
    return {"message": "Note unpinned"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
