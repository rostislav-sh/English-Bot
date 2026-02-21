import datetime
from datetime import timezone
from typing import Annotated

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import DateTime, String, ForeignKey, Boolean, func, text

from .config_db import Base


int_pk = Annotated[int, mapped_column(primary_key=True)]

created_at = Annotated[
    datetime.datetime, 
    mapped_column(DateTime(timezone=True), server_default=func.now())
]

updated_at = Annotated[
    datetime.datetime, 
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.datetime.now(timezone.utc),
    )
]


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int_pk]
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", 
        cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id: Mapped[int_pk]
    
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete="CASCADE"), index=True)

    token_hash: Mapped[str] = mapped_column(String(128), unique=True)

    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")