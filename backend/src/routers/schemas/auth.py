from pydantic import BaseModel, EmailStr, Field


class Authentication(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Пароль от 8 до 128 символов")


class UserOut(BaseModel):
    id: int
    email: EmailStr