from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from src.exceptions import AppError
from src.routers import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("start")
    yield
    print("end")


app = FastAPI(lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc)},
    )


app.include_router(
    auth_router,
    tags=["Авторизация"],
)