"""DTO слоя application — пересекают границу api↔application."""

from pydantic import BaseModel, ConfigDict


class FrozenDTO(BaseModel):
    """База для всех application DTO."""
    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenPair(FrozenDTO):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class GoogleUserData(FrozenDTO):
    google_id: str
    email: str
    email_verified: bool
    username: str | None = None
    picture: str | None = None


class GoogleAuthorizationURL(FrozenDTO):
    url: str
    state: str


class RegisterCommand(FrozenDTO):
    email: str
    password: str
    username: str


class LoginCommand(FrozenDTO):
    email: str
    password: str

