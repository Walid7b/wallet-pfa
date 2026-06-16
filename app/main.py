from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

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

# Expose /metrics au format Prometheus (Phase 4 — monitoring)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "service": "wallet-pfa"}
