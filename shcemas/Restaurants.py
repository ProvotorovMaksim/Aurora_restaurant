from sqlalchemy import Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from shcemas.Base import Base

class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
