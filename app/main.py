from contextlib import asynccontextmanager
from fastapi import FastAPI

from .database import engine, Base
from .routers import auth_router, wallet_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Wallet PFA",
    description="Application fintech cobaye — pipeline CI/CD DevSecOps",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router.router)
app.include_router(wallet_router.router)


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "service": "wallet-pfa"}
