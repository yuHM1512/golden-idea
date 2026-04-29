# Golden Idea Web App - Setup Guide

## Current Status ✓

Project structure, database schema, API endpoints, and Pydantic models are fully designed and ready for implementation.

## What's Been Created

### Configuration & Dependencies
- ✓ `.env.example` — Environment variables template
- ✓ `requirements.txt` — Python dependencies
- ✓ `app/config.py` — Settings management
- ✓ `app/database.py` — SQLAlchemy setup

### Database Models (SQLAlchemy)
- ✓ `app/models/user.py` — User with roles
- ✓ `app/models/unit.py` — Organization units
- ✓ `app/models/idea.py` — Idea submission (captures all form fields from Phiếu đăng ký)
- ✓ `app/models/score.py` — K1/K2/K3 scoring
- ✓ `app/models/review.py` — Multi-level review workflow
- ✓ `app/models/payment.py` — Payment slip management
- ✓ `app/models/attachment.py` — File attachments (images/videos)

### API Schemas (Pydantic)
- ✓ `app/schemas/user.py` — User request/response models
- ✓ `app/schemas/unit.py` — Unit models
- ✓ `app/schemas/idea.py` — Idea submission & list models
- ✓ `app/schemas/score.py` — Scoring models with K1/K2/K3 references
- ✓ `app/schemas/review.py` — Review workflow models
- ✓ `app/schemas/payment.py` — Payment slip models

### FastAPI Routers (Skeleton)
- ✓ `app/routers/auth.py` — Authentication endpoints
- ✓ `app/routers/ideas.py` — Idea submission & management
- ✓ `app/routers/reviews.py` — Multi-level approval workflow
- ✓ `app/routers/scores.py` — K1/K2/K3 scoring
- ✓ `app/routers/payments.py` — Payment slip generation & printing

### Documentation
- ✓ `README.md` — Project overview, setup, and architecture
- ✓ `API_SPEC.md` — Complete API specification with examples
- ✓ `SETUP.md` — This file

## Next Steps

### 1. Setup PostgreSQL Database

```bash
# Create database
createdb golden_idea

# Or via psql:
psql -U postgres -c "CREATE DATABASE golden_idea;"
```

### 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your PostgreSQL credentials
# Example:
# DATABASE_URL=postgresql://user:password@localhost:5432/golden_idea
# SECRET_KEY=generate-a-secure-key-here
```

### 3. Install Dependencies

```bash
cd backend
pip install -r ../requirements.txt
```

### 4. Run Server (test database connection)

```bash
python -m uvicorn app.main:app --reload
```

If successful:
- Tables will be auto-created in PostgreSQL
- Open `http://localhost:8000/docs` to see Swagger UI
- Test health endpoint: `http://localhost:8000/health`

### 5. Seed Database (Optional)

Create initial data (units, users, etc):
```bash
# To be created: app/scripts/seed_db.py
python app/scripts/seed_db.py
```

## Implementation Order (Recommended)

### Phase 1: User Management (Priority: HIGH)
- [ ] Implement simple JWT authentication in `routers/auth.py` (employee_code only, no password)
- [ ] Query user by employee_code from database
- [ ] Current user dependency for all protected routes
- [ ] Test login endpoint
- [ ] **TODO (Phase 2)**: Add password hashing (passlib/bcrypt) - currently commented out

### Phase 2: Idea Submission (Priority: HIGH)
- [ ] Implement idea creation in `routers/ideas.py`
- [ ] File upload handling (store in `./uploads`)
- [ ] List & filter ideas
- [ ] Get idea details

### Phase 3: Review Workflow (Priority: MEDIUM)
- [ ] State machine for idea status transitions
- [ ] Multi-level review in `routers/reviews.py`
- [ ] Role-based access control (RBAC) dependencies
- [ ] Auto-forward between levels

### Phase 4: Scoring System (Priority: MEDIUM)
- [ ] K1/K2/K3 scoring in `routers/scores.py`
- [ ] Auto-calculation of total score
- [ ] Validation of score ranges
- [ ] Score history tracking

### Phase 5: Payment Management (Priority: MEDIUM)
- [ ] Payment slip creation in `routers/payments.py`
- [ ] PDF rendering (WeasyPrint template)
- [ ] Print authorization (unit manager only)
- [ ] Signature tracking

### Phase 6: Frontend (Priority: MEDIUM)
- [ ] HTML form for idea submission
- [ ] Role-based dashboards
- [ ] Review interface
- [ ] Payment slip printing

## File Locations Quick Reference

```
backend/
├── app/
│   ├── main.py              ← FastAPI app
│   ├── config.py            ← Settings
│   ├── database.py          ← DB connection
│   ├── models/              ← SQLAlchemy ORM
│   ├── schemas/             ← Pydantic request/response
│   ├── routers/             ← API endpoints
│   ├── services/            ← Business logic (to create)
│   ├── dependencies.py      ← Auth guards (to create)
│   └── utils/               ← Helpers (to create)
└── alembic/                 ← Migrations (to setup)
```

## Key Implementation Notes

### 1. Anonymity
- `submitter_id` is always stored for backend tracking
- `is_anonymous` flag controls visibility in API responses
- Only LEADERSHIP & UNIT_MANAGER roles see employee names

### 2. Workflow State Machine
- Implement in `services/workflow.py`
- Validates allowed state transitions per role
- Auto-transitions on approval/rejection

### 3. File Uploads
- Store in `./uploads/{idea_id}/{filename}`
- Generate UUID-based filenames to prevent collisions
- Max 10MB, validate extensions

### 4. Scoring Logic
- K1: 2, 5, or 10 points (enum)
- K2: 2 or 3 points (enum)
- K3: 5-100 points (range based on measure type)
- Total = K1 + K2 + K3
- Store calculation history (track revisions)

### 5. PDF Generation
- Use WeasyPrint for server-side PDF rendering
- Template in `services/templates/payment_slip.html`
- Include 4 signature placeholders
- Print-friendly CSS styling

### 6. Multi-Level Review
- Each level has its own table row in `idea_reviews`
- Automatic status updates based on action
- Only one active review per level at a time

## Testing Checklist

- [ ] Server starts without errors
- [ ] Database tables created automatically
- [ ] Swagger UI loads at `/docs`
- [ ] Health endpoint responds
- [ ] CORS configured correctly
- [ ] File upload directory created
- [ ] JWT token generation works
- [ ] Protected routes reject unauthenticated requests

## Docker Setup (Optional)

```bash
# Create docker-compose.yml for PostgreSQL
docker-compose up -d

# Server runs in container:
# docker run -p 8000:8000 golden-idea-api
```

## Troubleshooting

**"psycopg2.OperationalError: could not connect to server"**
- Verify PostgreSQL is running
- Check DATABASE_URL in .env

**"ModuleNotFoundError: No module named 'sqlalchemy'"**
- Run `pip install -r requirements.txt`

**"FileNotFoundError: uploads directory"**
- Directory created automatically on first upload
- If not, run: `mkdir -p ./uploads`

## Support

See `README.md` and `API_SPEC.md` for more details.

---

Good luck! 🚀
