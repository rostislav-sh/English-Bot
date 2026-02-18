from fastapi import APIRouter, HTTPException, Response
from fastapi.params import Depends

from src.database.unitofwork import UserUnitOfWork
from src.exceptions import UserAlreadyExistsError
from src.interfaces.unitofwork import IUserUnitOfWork
from src.routers.schemas.auth import Authentication, UserOut
from src.service.auth import AuthService

router = APIRouter()


async def get_uow() -> IUserUnitOfWork:
    return UserUnitOfWork()


async def get_user_service(uow: IUserUnitOfWork = Depends(get_uow)) -> AuthService:
    return AuthService(uow=uow)


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
        data: Authentication,
        service: AuthService = Depends(get_user_service)
):
    try:
        user = await service.register(email=data.email, password=data.password)
        return UserOut.model_validate(user, from_attributes=True)
    except UserAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Пользователь уже существует")


@router.post("/login")
async def login(data: Authentication, response: Response, service):
    ...