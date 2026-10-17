import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db_global
from app.models.category import ServiceCategory
from app.schema.category_schema import CategoryCreate, CategoryUpdate, CategoryResponse
from app.utils.auth_validation import get_admin_user
from app.utils.response import success_response, error_response
from app.logger import logger

router = APIRouter(prefix="/categories", tags=["Categories"])


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.get("")
@router.get("/")
def list_categories(
    active_only: bool = Query(default=True, description="Filter only active categories"),
    parent_only: bool = Query(default=False, description="Filter only root categories"),
    db: Session = Depends(get_db_global),
):
    try:
        query = db.query(ServiceCategory)
        if active_only:
            query = query.filter(ServiceCategory.is_active.is_(True))
        if parent_only:
            query = query.filter(ServiceCategory.parent_id.is_(None))

        categories = query.order_by(ServiceCategory.display_order.asc(), ServiceCategory.name.asc()).all()

        result = []
        for cat in categories:
            cat_dict = {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description,
                "icon_url": cat.icon_url,
                "parent_id": cat.parent_id,
                "display_order": cat.display_order,
                "is_active": cat.is_active,
                "created_at": cat.created_at.isoformat() if cat.created_at else None,
                "subcategories": [
                    {
                        "id": sub.id,
                        "name": sub.name,
                        "slug": sub.slug,
                        "description": sub.description,
                        "icon_url": sub.icon_url,
                        "parent_id": sub.parent_id,
                        "display_order": sub.display_order,
                        "is_active": sub.is_active,
                        "created_at": sub.created_at.isoformat() if sub.created_at else None,
                    }
                    for sub in cat.subcategories if (not active_only or sub.is_active)
                ] if cat.parent_id is None else None
            }
            result.append(cat_dict)

        return success_response("Categories fetched successfully.", {"items": result, "total": len(result)}, 200)

    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return error_response(str(e), None, 500)


@router.get("/{category_id_or_slug}")
def get_category(
    category_id_or_slug: str,
    db: Session = Depends(get_db_global),
):
    try:
        if category_id_or_slug.isdigit():
            cat = db.query(ServiceCategory).filter(ServiceCategory.id == int(category_id_or_slug)).first()
        else:
            cat = db.query(ServiceCategory).filter(ServiceCategory.slug == category_id_or_slug).first()

        if not cat:
            return error_response("Category not found.", None, 404)

        data = {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon_url": cat.icon_url,
            "parent_id": cat.parent_id,
            "display_order": cat.display_order,
            "is_active": cat.is_active,
            "created_at": cat.created_at.isoformat() if cat.created_at else None,
        }
        return success_response("Category fetched successfully.", data, 200)

    except Exception as e:
        logger.error(f"Error fetching category {category_id_or_slug}: {str(e)}")
        return error_response(str(e), None, 500)


@router.post("")
@router.post("/")
def create_category(
    data: CategoryCreate,
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """Admin-only: Create a new service category."""
    try:
        slug = data.slug or slugify(data.name)
        existing = db.query(ServiceCategory).filter(
            (ServiceCategory.name == data.name) | (ServiceCategory.slug == slug)
        ).first()
        if existing:
            return error_response("A category with this name or slug already exists.", None, 400)

        cat = ServiceCategory(
            name=data.name,
            slug=slug,
            description=data.description,
            icon_url=data.icon_url,
            parent_id=data.parent_id,
            display_order=data.display_order or 0,
            is_active=data.is_active if data.is_active is not None else True,
        )
        db.add(cat)
        db.commit()
        db.refresh(cat)

        logger.info(f"Category created: {cat.name} (id={cat.id}) by admin {admin_user.get('id')}")
        return success_response(
            "Category created successfully.",
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "parent_id": cat.parent_id,
            },
            201
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating category: {str(e)}")
        return error_response(str(e), None, 500)


@router.put("/{category_id}")
def update_category(
    category_id: int,
    data: CategoryUpdate,
    admin_user=Depends(get_admin_user),
    db: Session = Depends(get_db_global),
):
    """Admin-only: Update, nest, reorder, or deactivate a category."""
    try:
        cat = db.query(ServiceCategory).filter(ServiceCategory.id == category_id).first()
        if not cat:
            return error_response("Category not found.", None, 404)

        if data.name is not None:
            cat.name = data.name
        if data.slug is not None:
            cat.slug = data.slug
        if data.description is not None:
            cat.description = data.description
        if data.icon_url is not None:
            cat.icon_url = data.icon_url
        if data.parent_id is not None:
            if data.parent_id == cat.id:
                return error_response("A category cannot be its own parent.", None, 400)
            cat.parent_id = data.parent_id
        if data.display_order is not None:
            cat.display_order = data.display_order
        if data.is_active is not None:
            cat.is_active = data.is_active

        db.commit()
        db.refresh(cat)
        logger.info(f"Category updated: {cat.name} (id={cat.id}) by admin {admin_user.get('id')}")
        return success_response("Category updated successfully.", {"id": cat.id, "name": cat.name}, 200)

    except Exception as e:
        db.rollback()
        logger.error(f"Error updating category {category_id}: {str(e)}")
        return error_response(str(e), None, 500)
