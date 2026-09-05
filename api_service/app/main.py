from fastapi import FastAPI
from app.routers import test
from app.database import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from app.routers.post import posts, job_post
from app.routers.comments import comments
from app.routers.reaction import reaction

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

app.include_router(test.router, prefix="/api")
app.include_router(posts.router, prefix="/api/post")
app.include_router(comments.router, prefix="/api")
app.include_router(reaction.router, prefix="/api")
app.include_router(job_post.router, prefix="/api")