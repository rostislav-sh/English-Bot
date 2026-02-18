from pydantic import BaseModel, EmailStr


class Authentication(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr