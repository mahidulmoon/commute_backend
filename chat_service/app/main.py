import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.database import Base, engine
from app.models import conversation, message  # ensure models are registered
from app.routers import conversation as conv_router, message as msg_router, websocket as ws_router

# Automatically create tables if they do not exist
try:
    Base.metadata.create_all(bind=engine)
except Exception as err:
    # In case the database container is starting up or migration handled externally
    import logging
    logging.getLogger("chat_service").warning(f"Database table initialization notice: {err}")

app = FastAPI(
    title="Chat Microservice",
    description="1-to-1 Realtime and REST Chat Service for fast_api_micro",
    version="1.0.0",
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


@app.get("/api/chat/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "chat_service"}


# Mount Chat Routers under /api/chat prefix
app.include_router(conv_router.router, prefix="/api/chat", tags=["Conversations"])
app.include_router(msg_router.router, prefix="/api/chat", tags=["Messages"])
app.include_router(ws_router.router, prefix="/api/chat", tags=["WebSocket"])
