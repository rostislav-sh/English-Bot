import datetime
from typing import Annotated

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text

from .config_db import Base

int_pk = Annotated[int, mapped_column(primary_key=True)]
created_at = Annotated[datetime.datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]
updated_at = Annotated[datetime.datetime, mapped_column(
    server_default=text("TIMEZONE('utc', now())"),
    onupdate=datetime.datetime.utcnow,
)]


class Users(Base):
    __tablename__ = 'users'

    id: Mapped[int_pk]
    username: Mapped[str]
    email: Mapped[str]
