from app.routers.notifications import router as notifications_router
from app.routers.preferences import router as preferences_router
from app.routers.websocket import router as websocket_router

__all__ = [
    "notifications_router",
    "preferences_router",
    "websocket_router",
]
