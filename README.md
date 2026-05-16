# Notes App — Backend API

A multi-user notes service with JWT auth, CRUD, note sharing, pinning, search, and pagination.

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Framework | FastAPI (Python) |
| Database | SQLite (local) / PostgreSQL (production) |
| Auth | JWT via `python-jose` |
| Passwords | bcrypt via `passlib` |
| ORM | SQLAlchemy 2.0 |
| Deploy | Render.com (free tier) |

---

## Local Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd notes-app

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) set env vars — defaults work for local SQLite
export SECRET_KEY="some-random-secret"

# 5. Run
uvicorn main:app --reload
```

Server runs at **http://localhost:8000**
Interactive docs at **http://localhost:8000/docs**

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing secret | hardcoded dev value |
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./notes.db` |

---

## API Endpoints

### Auth
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | No | Register new user |
| POST | `/login` | No | Login, returns JWT |

### Notes
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notes` | ✓ | List all notes (paginated) |
| GET | `/notes/{id}` | ✓ | Get single note |
| POST | `/notes` | ✓ | Create note |
| PUT | `/notes/{id}` | ✓ | Update note |
| DELETE | `/notes/{id}` | ✓ | Delete note |
| POST | `/notes/{id}/share` | ✓ | Share note with user |
| POST | `/notes/{id}/pin` | ✓ | Pin note to top |
| POST | `/notes/{id}/unpin` | ✓ | Unpin note |

### Search & Meta
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/search?q=keyword` | ✓ | Full-text search |
| GET | `/openapi.json` | No | OpenAPI spec |
| GET | `/about` | No | Author info |

### Pagination
`GET /notes?page=1&page_size=20`

---

## Deploy to Render.com (Free)

1. Push this project to a GitHub repo.
2. Go to [render.com](https://render.com) → **New → Blueprint**.
3. Connect your GitHub repo — Render reads `render.yaml` automatically.
4. Click **Apply**. It will provision a free PostgreSQL DB + web service.
5. Your URL will be `https://notes-app-xxxx.onrender.com`.

> **Important:** On the free tier, the service sleeps after 15 minutes of inactivity and takes ~30s to wake. Upgrade to the $7/month plan if the tests time out.

---

## Custom Features

### 1. Note Pinning (`POST /notes/{id}/pin`)
Pin important notes so they always surface at the top of `GET /notes`. This mirrors how Google Keep and Apple Notes work — it's the #1 power-user feature in any notes app.

### 2. Full-text Search (`GET /search?q=keyword`)
Searches both `title` and `content` across owned and shared notes. Makes the app genuinely useful at scale.

### 3. Pagination (`GET /notes?page=1&page_size=20`)
Prevents unbounded result sets. Keeps the API production-safe and fast.

---

## Edge Cases Handled

- Duplicate email on register → 409
- Wrong password on login → 401
- Accessing another user's note → 403
- Updating/deleting a shared note (only owner allowed) → 403
- Sharing with yourself → 400
- Sharing with non-existent user → 404
- Empty title on create → 400
- Invalid pagination params → 400
- Invalid/expired JWT → 401
- Note not found → 404
