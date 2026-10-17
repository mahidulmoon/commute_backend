import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, engine, SessionLocal
from app.models import (
    category,
    agency,
    listing,
    enquiry,
    review,
    audit_log,
)
from app.seed import seed_initial_categories
from app.routers.categories import router as categories_router
from app.routers.agencies import router as agencies_router
from app.routers.listings import router as listings_router
from app.routers.enquiries import router as enquiries_router
from app.routers.reviews import router as reviews_router
from app.routers.admin import router as admin_router
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed initial categories
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
        db = SessionLocal()
        try:
            seed_initial_categories(db)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Database initialization or category seeding notice: {e}")
    yield


app = FastAPI(
    title="Services Marketplace Microservice",
    description="Services Marketplace API implementing Spec Section 9 (Agencies, Listings, Categories, Enquiries, Quotes, Reviews, Admin)",
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


@app.get("/api/marketplace/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "marketplace_service"}


# Mount all routers under /api/marketplace
app.include_router(categories_router, prefix="/api/marketplace")
app.include_router(agencies_router, prefix="/api/marketplace")
app.include_router(listings_router, prefix="/api/marketplace")
app.include_router(enquiries_router, prefix="/api/marketplace")
app.include_router(reviews_router, prefix="/api/marketplace")
app.include_router(admin_router, prefix="/api/marketplace")
