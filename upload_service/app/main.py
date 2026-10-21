import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, engine
from app.logger import logger
from app.models import UploadFileModel  # noqa: F401 — ensure table is registered
from app.routers import upload_router

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
SECRET_KEY = os.getenv("SECRET_KEY", "d2bcbac0d9e7f5ffaf6b0fd44d8042f7fd438d7b24ec5e2f31e3c74a6233bcf9")
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables on startup
    Base.metadata.create_all(bind=engine)
    logger.info("upload_service started — DB tables ensured.")

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Upload directory ready: {UPLOAD_DIR}")

    yield

    logger.info("upload_service shutting down.")


app = FastAPI(
    title="Upload Service",
    description="Centralised file/media upload microservice",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL] if FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving ─────────────────────────────────────────────────────
# Serves uploaded files at  GET /uploads/<category>/<date>/<filename>
app.mount(
    "/uploads",
    StaticFiles(directory=UPLOAD_DIR),
    name="uploads",
)

# ── Routers ─────────────────────────────────────────────────────────────────
app.include_router(upload_router, prefix="/api/upload", tags=["Upload"])


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "upload_service"}
