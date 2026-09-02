from sqlalchemy import (
    Column,
    BigInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    String
)
from sqlalchemy.sql import func


from app.database import Base


class ReactionModel(Base):
    __tablename__ = "post_reactions"

    id = Column(BigInteger, primary_key=True)

    post_id = Column(
        BigInteger,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
    )

    reaction_type = Column(
        String(20),
        nullable=False,
    )


    user_id = Column(
        BigInteger,
        # ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_user_reaction",
        ),
    )