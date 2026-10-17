from app.routers.categories import router as categories_router
from app.routers.agencies import router as agencies_router
from app.routers.listings import router as listings_router
from app.routers.enquiries import router as enquiries_router
from app.routers.reviews import router as reviews_router
from app.routers.admin import router as admin_router

__all__ = [
    "categories_router",
    "agencies_router",
    "listings_router",
    "enquiries_router",
    "reviews_router",
    "admin_router",
]
