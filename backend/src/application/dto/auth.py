"""DTO слоя application — пересекают границу api↔application."""

from pydantic import BaseModel, ConfigDict


class TokenPair(BaseModel):
    model_config = ConfigDict(frozen=True)
    access_token: str
    token_type: str
    token_type: str = "bearer"


class GoogleUserData(BaseModel):
    model_config = ConfigDict(frozen=True)
    google_id: str
    email: str
    email_verified: bool
    username: str | None = None
    picture: str | None = None


class GoogleAuthorizationURL(BaseModel):
    model_config = ConfigDict(frozen=True)
    url: str
    state: str


class RegisterCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str
    password: str
    username: str


class LoginCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    email: str
    password: str

