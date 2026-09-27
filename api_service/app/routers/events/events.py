from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import Optional

from app.utils.auth_validation import get_current_user
from app.utils.response import success_response, error_response
from app.database import get_db_global
from app.schema.eventschema import (
    EventCreate,
    EventUpdate,
    EventResponse,
    MyEventsResponse,
)
from app.models.events import EventModel
from app.logger import logger

router = APIRouter()


@router.post("/create_event")
def create_event(
    event_data: EventCreate,
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        event = EventModel(
            user_id=user_data.get("id"),
            title=event_data.title,
            description=event_data.description,
            location=event_data.location,
            event_date=event_data.event_date,
            group_id=event_data.group_id,
        )

        db.add(event)
        db.commit()
        db.refresh(event)
        logger.info(f"Event created successfully with id {event.id} by user {user_data.get('id')}.")
        return success_response("Event creation successful.", jsonable_encoder(event), 201)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating event for user {user_data.get('id')}: {str(e)}")
        return error_response(str(e), None, 400)


@router.get("/get_my_events", response_model=MyEventsResponse)
def get_my_events(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        events = (
            db.query(EventModel)
            .filter(
                EventModel.user_id == user_data.get("id"),
                EventModel.is_deleted.is_(False),
            )
            .order_by(
                EventModel.created_at.desc(),
                EventModel.id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        total_count = (
            db.query(EventModel)
            .filter(
                EventModel.user_id == user_data.get("id"),
                EventModel.is_deleted.is_(False),
            )
            .count()
        )

        event_response = {
            "items": jsonable_encoder(events),
            "total": total_count,
        }
        return success_response("Events fetched successfully.", event_response, 200)
    except Exception as e:
        logger.error(f"Error fetching events for user {user_data.get('id')}: {str(e)}")
        return error_response(str(e), None, 400)


@router.get("/get_my_events_by_group", response_model=MyEventsResponse)
def get_my_events_by_group(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        if not user_data.get("group_id"):
            logger.warning("Group is not assigned for this user yet.")
            return error_response("Group is not assigned for this user yet.", None, 400)

        events = (
            db.query(EventModel)
            .filter(
                EventModel.group_id == user_data.get("group_id"),
                EventModel.is_deleted.is_(False),
            )
            .order_by(
                EventModel.created_at.desc(),
                EventModel.id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        total_count = (
            db.query(EventModel)
            .filter(
                EventModel.group_id == user_data.get("group_id"),
                EventModel.is_deleted.is_(False),
            )
            .count()
        )

        event_response = {
            "items": jsonable_encoder(events),
            "total": total_count,
        }
        return success_response("Events fetched successfully.", event_response, 200)
    except Exception as e:
        logger.error(f"Error fetching events for group {user_data.get('group_id')}: {str(e)}")
        return error_response(str(e), None, 400)


@router.get("/get_all_events", response_model=MyEventsResponse)
def get_all_events(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    group_id: Optional[int] = Query(default=None, description="Filter by group id"),
    db: Session = Depends(get_db_global),
):
    try:
        query = db.query(EventModel).filter(EventModel.is_deleted.is_(False))
        if group_id is not None:
            query = query.filter(EventModel.group_id == group_id)

        events = (
            query.order_by(
                EventModel.created_at.desc(),
                EventModel.id.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

        total_count = query.count()

        event_response = {
            "items": jsonable_encoder(events),
            "total": total_count,
        }
        return success_response("Events fetched successfully.", event_response, 200)
    except Exception as e:
        logger.error(f"Error fetching all events: {str(e)}")
        return error_response(str(e), None, 400)


@router.get("/search", response_model=MyEventsResponse)
def search_events(
    q: Optional[str] = Query(default=None, description="Search term for event title, description or location"),
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=10, ge=1, le=100, description="Max number of records to return"),
    db: Session = Depends(get_db_global),
):
    try:
        stmt = (
            select(EventModel)
            .filter(EventModel.is_deleted.is_(False))
            .order_by(EventModel.created_at.desc())
        )

        filters = []
        if q:
            search_filter = or_(
                EventModel.title.ilike(f"%{q}%"),
                EventModel.description.ilike(f"%{q}%"),
                EventModel.location.ilike(f"%{q}%"),
            )
            filters.append(search_filter)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.offset(skip).limit(limit)
        results = db.scalars(stmt).all()

        total_count = len(results)

        event_response = {
            "items": jsonable_encoder(results),
            "total": total_count,
        }
        return success_response("Events fetched successfully.", event_response, 200)
    except Exception as e:
        logger.error(f"Error searching events with query '{q}': {str(e)}")
        return error_response(str(e), None, 400)


@router.get("/get_event/{event_id}")
def get_event_by_id(
    event_id: int,
    db: Session = Depends(get_db_global),
):
    try:
        event = (
            db.query(EventModel)
            .filter(
                EventModel.id == event_id,
                EventModel.is_deleted.is_(False),
            )
            .first()
        )

        if not event:
            return error_response("Event not found.", None, 404)

        return success_response("Event fetched successfully.", jsonable_encoder(event), 200)
    except Exception as e:
        logger.error(f"Error fetching event {event_id}: {str(e)}")
        return error_response(str(e), None, 400)


@router.put("/update_event/{event_id}")
def update_event(
    event_id: int,
    event_data: EventUpdate,
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        event = (
            db.query(EventModel)
            .filter(
                EventModel.id == event_id,
                EventModel.is_deleted.is_(False),
            )
            .first()
        )

        if not event:
            return error_response("Event not found.", None, 404)

        if event.user_id != user_data.get("id"):
            return error_response("You are not authorized to update this event.", None, 403)

        if event_data.title is not None:
            event.title = event_data.title
        if event_data.description is not None:
            event.description = event_data.description
        if event_data.location is not None:
            event.location = event_data.location
        if event_data.event_date is not None:
            event.event_date = event_data.event_date
        if event_data.group_id is not None:
            event.group_id = event_data.group_id

        db.commit()
        db.refresh(event)
        logger.info(f"Event {event_id} updated successfully by user {user_data.get('id')}.")
        return success_response("Event updated successfully.", jsonable_encoder(event), 200)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating event {event_id}: {str(e)}")
        return error_response(str(e), None, 400)


@router.delete("/delete_event/{event_id}")
def delete_event(
    event_id: int,
    user_data=Depends(get_current_user),
    db: Session = Depends(get_db_global),
):
    try:
        event = (
            db.query(EventModel)
            .filter(
                EventModel.id == event_id,
                EventModel.is_deleted.is_(False),
            )
            .first()
        )

        if not event:
            return error_response("Event not found.", None, 404)

        if event.user_id != user_data.get("id"):
            return error_response("You are not authorized to delete this event.", None, 403)

        event.is_deleted = True
        db.commit()
        logger.info(f"Event {event_id} deleted successfully by user {user_data.get('id')}.")
        return success_response("Event deleted successfully.", None, 200)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting event {event_id}: {str(e)}")
        return error_response(str(e), None, 400)
