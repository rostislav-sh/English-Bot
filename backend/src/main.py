from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routers import auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("start")
    yield
    print("end")


app = FastAPI(lifespan=lifespan)

app.include_router(
    auth_router,
    tags=["Авторизация"],
)
