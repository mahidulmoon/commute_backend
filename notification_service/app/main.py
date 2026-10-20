import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, engine
from app.models import (
    notification,
    preference,
)
from app.routers.notifications import router as notifications_router
from app.routers.preferences import router as preferences_router
from app.routers.websocket import router as websocket_router
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Notification database tables initialized successfully.")
    except Exception as e:
        logger.warning(f"Database table initialization notice: {e}")
    yield


app = FastAPI(
    title="Notification Microservice",
    description="Notification Microservice supporting In-App, Realtime WebSockets, Preferences, and Cross-Service Dispatch",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "super-secret-key")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/notifications/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "notification_service"}


# Mount all notification routes under /api/notifications
app.include_router(notifications_router, prefix="/api/notifications")
app.include_router(preferences_router, prefix="/api/notifications")
app.include_router(websocket_router, prefix="/api/notifications")
