from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ServiceCategory(BaseModel):
    __tablename__ = "service_categories"

    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(120), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon_url = Column(String(255), nullable=True)
    
    # Self-referencing foreign key for nested subcategories (Spec 9.9)
    parent_id = Column(Integer, ForeignKey("service_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    parent = relationship("ServiceCategory", remote_side="ServiceCategory.id", backref="subcategories")
    listings = relationship("ServiceListing", back_populates="category", cascade="all, delete-orphan")
