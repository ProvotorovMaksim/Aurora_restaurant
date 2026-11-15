from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from shcemas.Base import Base

class Table(Base):
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hall_id: Mapped[int] = mapped_column(nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)
    capacity: Mapped[int] = mapped_column(nullable=False, default=2)