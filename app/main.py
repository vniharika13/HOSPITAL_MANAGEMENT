from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.models import appointment, doctor, patient  # noqa: F401
from app.routers.appointments import router as appointments_router
from app.routers.doctors import router as doctors_router
from app.routers.patients import router as patients_router


@asynccontextmanager
async def lifespan(app):
    # Startup: create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(
    patients_router,
    prefix="/patients",
)

app.include_router(
    doctors_router,
    prefix="/doctors",
)

app.include_router(
    appointments_router,
    prefix="/appointments",
)

@app.get("/")
async def root():
    return {"message": "Hospital API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
