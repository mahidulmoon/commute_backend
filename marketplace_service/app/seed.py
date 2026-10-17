from sqlalchemy.orm import Session
from app.models.category import ServiceCategory
from app.logger import logger

INITIAL_CATEGORIES = [
    {
        "name": "Plumbing",
        "slug": "plumbing",
        "description": "Tap repair, leak repair, toilet installation, call-out, and emergency plumbing.",
        "display_order": 1,
    },
    {
        "name": "Electrical",
        "slug": "electrical",
        "description": "Lighting, socket installation, fault finding, and certified electrical work.",
        "display_order": 2,
    },
    {
        "name": "Cleaning",
        "slug": "cleaning",
        "description": "Domestic, deep clean, end-of-tenancy, commercial and carpet cleaning.",
        "display_order": 3,
    },
    {
        "name": "Heating and Cooling",
        "slug": "heating-and-cooling",
        "description": "Heating maintenance, boiler service, thermostat, and air conditioning.",
        "display_order": 4,
    },
    {
        "name": "Painting and Decorating",
        "slug": "painting-and-decorating",
        "description": "Interior and exterior painting, wallpapering, preparation, and materials.",
        "display_order": 5,
    },
    {
        "name": "Gardening and Landscaping",
        "slug": "gardening-and-landscaping",
        "description": "Lawn care, hedge trimming, clearance, patio work, and garden maintenance.",
        "display_order": 6,
    },
    {
        "name": "Moving and Removals",
        "slug": "moving-and-removals",
        "description": "House moves, packing, furniture transport, and single-item removals.",
        "display_order": 7,
    },
    {
        "name": "Handyman",
        "slug": "handyman",
        "description": "Furniture assembly, wall mounting, minor repairs, and odd jobs.",
        "display_order": 8,
    },
    {
        "name": "Car Services",
        "slug": "car-services",
        "description": "Mobile mechanic, vehicle diagnostics, detailing, and tyre replacement.",
        "display_order": 9,
    },
    {
        "name": "IT and Technology",
        "slug": "it-and-technology",
        "description": "Computer repair, home network setup, smart device configuration, and IT support.",
        "display_order": 10,
    },
    {
        "name": "Tutoring and Education",
        "slug": "tutoring-and-education",
        "description": "Academic subject tutoring, language lessons, music tutoring, and test preparation.",
        "display_order": 11,
    },
    {
        "name": "Photography and Events",
        "slug": "photography-and-events",
        "description": "Event photography, portraits, videography, and event planning services.",
        "display_order": 12,
    },
]


def seed_initial_categories(db: Session):
    """
    Seeds the 12 initial categories defined in Spec 9.2 if they do not exist.
    """
    seeded_count = 0
    for cat_data in INITIAL_CATEGORIES:
        existing = db.query(ServiceCategory).filter(ServiceCategory.slug == cat_data["slug"]).first()
        if not existing:
            cat = ServiceCategory(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=cat_data["description"],
                display_order=cat_data["display_order"],
                is_active=True,
            )
            db.add(cat)
            seeded_count += 1

    if seeded_count > 0:
        db.commit()
        logger.info(f"Successfully seeded {seeded_count} initial service categories.")
