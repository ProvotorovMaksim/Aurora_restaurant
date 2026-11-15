from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from shcemas.Base import Base

class Hall(Base):
    __tablename__ = "halls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "restaurants.id",
            name="fk_halls_restaurant_id_restaurants",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
