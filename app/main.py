import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal
from app.routers import auth, admin, patients, lab


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(
    title="MedRecord API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded lab PDFs as static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router,     prefix="/auth",    tags=["auth"])
app.include_router(admin.router,    prefix="/admin",   tags=["admin"])
app.include_router(patients.router, prefix="/patients",tags=["patients"])
app.include_router(lab.router,      prefix="/lab",     tags=["lab"])


@app.get("/health")
async def health():
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unreachable"
    return {"status": "ok", "db": db_status, "version": "1.0.0"}
