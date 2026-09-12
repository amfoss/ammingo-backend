# AGENTS.md - Backend Repository Guidelines & Architecture Manual

> **Repository**: `ammingo-backend`  
> **Tech Stack**: Python 3.12+ | FastAPI | SQLAlchemy 2.0 | SQLite / PostgreSQL | Pydantic v2 | Uvicorn  
> **Target Audience**: AI Agents (Antigravity, Gemini CLI, Cursor, Codex) & Core Developers  

---

## 1. Executive Overview & System Purpose

`ammingo-backend` is the core RESTful API service for **amMingo**, an open-source social human bingo platform. The service manages user authentication (Email OTP + Google OAuth2), real-time game state transitions, dynamic bingo board generation, tile verification submissions, leaderboards, and user profiles.

### Core Architectural Responsibilities
- **Authentication**: JWT-based session management with Cookie and HTTP `Authorization: Bearer <token>` support.
- **Game Engine**: Game creation, participant join handling via 6-digit codes, tile assignment, photo/fact proof verification, and score computation.
- **Profile Engine**: User profile querying, avatar management, and score history.
- **Persistence Layer**: SQLAlchemy ORM with support for SQLite (`test.db` in dev/testing) and PostgreSQL in production environments.

---

## 2. Agent Behavioral Guidelines & Operational Directives

When modifying, extending, or debugging `ammingo-backend`, all AI agents **MUST** follow these mandatory rules:

1. **Verify Before Declaring Task Completion**:
   - Never declare success without executing tests or verifying API code execution.
   - Run unit tests with `pytest test_main.py -v`. If any test fails, diagnose the root cause from exact error logs before declaring completion.

2. **Preserve API Contracts & Existing Logic**:
   - Maintain backwards compatibility for API response schemas, particularly fields expected by `ammingo-frontend` (e.g., `access_token`, `join_code`, `board_size`, `user_id`).
   - Do not swallow exceptions with silent `try/except: pass` blocks or dummy default values. Return explicit `fastapi.HTTPException` with appropriate HTTP status codes (400, 401, 403, 404, 500).

3. **Strict Database & Transaction Management**:
   - Ensure all database state mutations (`db.add()`, `db.delete()`, updates) are wrapped in explicit `db.commit()` and `db.rollback()` calls inside try/except blocks to prevent uncommitted or leaked sessions.
   - Always use FastAPI's `Depends(get_db)` or session context managers for thread-safe database connection allocation.

4. **Security & Secrets Discipline**:
   - **Never hardcode secrets** or fall back to weak static keys in production code. Load configuration from environment variables via `os.environ` or `python-dotenv`.
   - Protect endpoints with `get_current_user` dependency or ensure `verify_token` HTTP middleware handles auth verification.

---

## 3. Repository Layout & Directory Structure

```
ammingo-backend/
├── app/                      # Main application source package
│   ├── main.py               # FastAPI entry point, middleware registration & route routers
│   ├── db/                   # Database configuration & ORM models
│   │   ├── db.py             # SQLAlchemy engine, SessionLocal factory, get_db dependency
│   │   └── models.py         # SQLAlchemy Base models (User, Game, Board, Tile, UserTile)
│   ├── middlewares/          # HTTP Middlewares
│   │   └── verify_token.py   # JWT auth middleware & get_current_user dependency
│   ├── models/               # Pydantic v2 schemas / DTOs
│   │   ├── auth.py           # Login and verification request schemas
│   │   ├── game.py           # Game creation, join, and tile submission schemas
│   │   └── profile.py        # User profile response schemas
│   └── routes/               # FastAPI Router endpoints
│       ├── auth.py           # OTP email & Google OAuth authentication endpoints
│       ├── game.py           # Game management, board retrieval, tile verification & leaderboard
│       └── profile.py        # User profile endpoints
├── uploads/                  # User uploaded images directory
├── Dockerfile                # Production container specification
├── docker-compose.yml        # Multi-container orchestration (App + PostgreSQL)
├── deploy.sh                 # Deployment script
├── requirements.txt          # Production & development dependencies
├── sample.env                # Template environment variable configuration
└── test_main.py              # Pytest end-to-end integration & unit test suite
```

---

## 4. Development Environment & Setup

### Prerequisites
- Python 3.12+
- `pip` & `venv`
- Docker & Docker Compose (optional for containerized setup)

### Local Manual Setup Steps
```bash
# 1. Clone & enter repository
cd ammingo-backend

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp sample.env .env
# Edit .env to set JWT_SECRET, DB_URL, EMAIL_ADDRESS, EMAIL_PASSWORD, etc.

# 5. Run FastAPI dev server
fastapi dev app/main.py
# Server starts on http://localhost:8000 (Swagger docs at http://localhost:8000/docs)
```

---

## 5. Key Operational Commands

| Action | Command |
| :--- | :--- |
| **Run Dev Server** | `fastapi dev app/main.py` or `uvicorn app.main:app --reload --port 8000` |
| **Run Production Server** | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4` |
| **Execute Test Suite** | `pytest test_main.py -v` |
| **Run Docker Services** | `docker compose up -d` |
| **Stop Docker Services** | `docker compose down` |

---

## 6. Environment Variables Reference

| Variable | Description | Default / Example |
| :--- | :--- | :--- |
| `JWT_SECRET` | Secret key for signing JWT tokens | `supersecretjwtkey...` |
| `HASH_ALGORITHM` | Algorithm for JWT encoding | `HS256` |
| `TOKEN_EXPIRY_TIME` | JWT validity in seconds | `3600` (1 hour) |
| `DB_URL` | SQLAlchemy connection string | `postgresql://user:pass@localhost:5432/ammingo` or `sqlite:///./test.db` |
| `EMAIL_ADDRESS` | SMTP email address for sending OTPs | `no-reply@ammingo.com` |
| `EMAIL_PASSWORD` | SMTP password / app password | `app_password_here` |
| `SMTP_SERVER` | SMTP host | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `GOOGLE_CLIENT_ID` | OAuth2 Google Client ID | `client_id_from_google_console` |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Google Client Secret | `client_secret` |
| `FRONTEND_URL` | Redirect URL post OAuth authentication | `http://localhost:3000` or app scheme |

---

## 7. Architectural Conventions & Coding Rules

### 7.1 FastAPI & Router Patterns
- Each domain route module must define an `APIRouter()` and be mounted in [app/main.py](file:///home/kota-jagadeeshwar-reddy/ammingo/ammingo-backend/app/main.py) under `/api` prefix:
  ```python
  app.include_router(auth.router, prefix="/api", tags=["auth"])
  ```
- Use Pydantic models in `app/models/` for strict request body validation and response serialization.

### 7.2 Database Models & SQLAlchemy Usage
- All ORM models reside in [app/db/models.py](file:///home/kota-jagadeeshwar-reddy/ammingo/ammingo-backend/app/db/models.py) inheriting from `Base = declarative_base()`.
- Primary keys use `UUID` or `String` generated IDs (`uuid.uuid4().hex`).
- Foreign key relationships must specify cascade behaviors where applicable (e.g. deleting games cleanup boards and tiles).

### 7.3 Authentication & Auth Interceptors
- Public endpoints (`/api/login/*`, `/docs`, `/openapi.json`) are bypassed in [app/middlewares/verify_token.py](file:///home/kota-jagadeeshwar-reddy/ammingo/ammingo-backend/app/middlewares/verify_token.py#L16).
- Protected endpoints retrieve authenticated user through:
  ```python
  @router.get("/profile/me")
  def get_my_profile(current_user: User = Depends(get_current_user)):
      ...
  ```
- Pass tokens using standard HTTP Bearer header (`Authorization: Bearer <jwt_token>`) or `access_token` cookie.

### 7.4 Verification & Testing Protocols
- Tests are written using `starlette.testclient.TestClient` in `test_main.py`.
- Tests override `get_db` dependency to isolate testing against an in-memory or file-backed SQLite database (`sqlite:///./test.db`).

---

## 8. Known Gotchas & Architectural Context

1. **OTP In-Memory Storage**: Current OTP records are stored in memory (`otps = {}` dictionary inside `app/routes/auth.py`). Maintain `otp_store` helper compatibility for unit tests.
2. **Game Metadata Pipe Delimiters**: Game descriptions store structured data delimited by `|` (e.g. `"Event Title|Detailed Description"`). Keep string splits safe against missing pipes using fallbacks.
3. **CORS Headers**: Origins are configured in `app/main.py`. Ensure credentials are properly set when interacting with Flutter Web or mobile WebViews.
