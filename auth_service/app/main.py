from fastapi import FastAPI
from .routers import test
from .routers.auth import auth
from .routers.profile import profile
from .database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from app.producer_push.rabbitmq import producer
from app.logger import logger

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "super-secret-key"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    # Connect to RabbitMQ on startup
    producer.connect()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")
    producer.close()

app.include_router(test.router, prefix="/api")
app.include_router(auth.router, prefix="/api/auth",tags = ['auth'])
app.include_router(profile.router, prefix="/api/profile",tags = ['profile'])