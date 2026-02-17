from fastapi import APIRouter, Response

from src.routers.schemas.auth import Authentication

router = APIRouter()


@router.post("/register")
async def register(data: Authentication, response: Response, service):
    ...


@router.post("/login")
async def login(data: Authentication, response: Response, service):
    ...