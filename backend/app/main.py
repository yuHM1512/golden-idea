from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import mimetypes
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from pathlib import Path
from app.config import settings
from app.database import Base, engine
from app.seed import (
    seed_units,
    seed_admin_user,
    seed_score_criteria,
    migrate_user_role_column,
    migrate_users_unit_nullable,
    migrate_idea_participants_column,
    migrate_idea_bo_phan_column,
    normalize_employee_codes,
    migrate_idea_category_column,
    migrate_score_k2_type_column,
    migrate_score_criteria_tables,
    migrate_payment_slip_reward_columns,
    migrate_reward_batch_special_coefficients_column,
    normalize_sample_idea_categories,
)

# Create tables on startup
def init_db():
    import app.models
    Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    migrate_user_role_column()
    migrate_users_unit_nullable()
    migrate_idea_participants_column()
    migrate_idea_bo_phan_column()
    normalize_employee_codes()
    migrate_idea_category_column()
    migrate_score_k2_type_column()
    migrate_score_criteria_tables()
    migrate_payment_slip_reward_columns()
    migrate_reward_batch_special_coefficients_column()
    normalize_sample_idea_categories()
    inserted = seed_units()
    if inserted:
        print(f"OK: Seeded units ({inserted})")
    seeded_criteria = seed_score_criteria()
    if seeded_criteria:
        print(f"OK: Seeded score criteria ({seeded_criteria})")
    if seed_admin_user():
        print("OK: Seeded admin user (employee_code=admin)")
    print("OK: Database tables initialized")
    yield
    # Shutdown
    print("OK: Shutting down...")

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Include routers FIRST (before static files)
from app.routers import ideas, units, users, dashboard, library, reviews, scores, payments, reward_batches
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
app.include_router(units.router, prefix="/api", tags=["units"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(library.router, prefix="/api", tags=["library"])
app.include_router(reviews.router, prefix="/api", tags=["reviews"])
app.include_router(scores.router, prefix="/api", tags=["scores"])
app.include_router(reward_batches.router, prefix="/api", tags=["reward-batches"])
app.include_router(payments.router, prefix="/api", tags=["payments"])

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "database": "connected"}

# Serve frontend static files — catch-all GET (must be LAST)
FRONTEND = Path(__file__).parent.parent.parent / "frontend"

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    def _file_response(path: Path) -> FileResponse:
        # Ensure UTF-8 for text assets so Vietnamese renders correctly even if the client
        # ignores/doesn't find the <meta charset> early enough.
        media_type, _ = mimetypes.guess_type(str(path))
        if media_type in {"text/html", "text/css", "application/javascript", "text/javascript"}:
            media_type = f"{media_type}; charset=utf-8"
        return FileResponse(str(path), media_type=media_type)

    if not full_path:
        return _file_response(FRONTEND / "index.html")

    file = FRONTEND / full_path

    # Direct file hit (e.g. /js/api.js, /pages/login.html)
    if file.is_file():
        return _file_response(file)

    # Directory hit (e.g. /pages/)
    if file.is_dir():
        index = file / "index.html"
        if index.is_file():
            return _file_response(index)

    # Extensionless HTML routes (e.g. /pages/login -> /pages/login.html)
    if file.suffix == "":
        html_file = FRONTEND / f"{full_path}.html"
        if html_file.is_file():
            return _file_response(html_file)

    # fallback to index.html
    return _file_response(FRONTEND / "index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
