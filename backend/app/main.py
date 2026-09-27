"""FastAPI application entry point."""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as api_router
from app.api.websocket import router as ws_router
from app.config import settings
from app.database import init_db
from app.logging import configure_logging, get_request_id, set_request_id
from app.schemas import HealthResponse
from app.services.predictor import predictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    predictor.load()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Real-time fraud detection with ML monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure structured logging
configure_logging()

# Middleware to set request ID for each request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    response = await call_next(request)
    return response

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger = logging.getLogger(__name__)
    logger.error(
        f"HTTP exception: {exc.detail}",
        extra={"request_id": get_request_id()},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger(__name__)
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"request_id": get_request_id()},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(ws_router)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy" if predictor.is_loaded else "degraded",
        model_loaded=predictor.is_loaded,
        model_version=predictor.version if predictor.is_loaded else None,
        database_connected=True,
    )


@app.get("/")
def root():
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": settings.api_prefix,
    }