from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

# Configure basic logging to print all INFO level logs to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from contextlib import asynccontextmanager
from app.api.webhook import router as webhook_router
from app.api.console import router as console_router
from app.api.console_api import router as console_api_router
from app.api.auth import router as auth_router
from app.api.super_admin import router as admin_router
from app.core.config import settings
from app.services.scheduler_service import SchedulerService

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and start background reminder scheduler
    SchedulerService.start()
    yield
    # Shutdown: Stop background reminder scheduler
    SchedulerService.shutdown()

app = FastAPI(
    title="WhatsApp Webhook Backend Server",
    description="A FastAPI backend server configured for WhatsApp Business Webhook integration",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware to allow requests from any origin for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(os.path.dirname(BASE_DIR), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routes
app.include_router(console_router, tags=["console"])
app.include_router(console_api_router, prefix="/api/v1", tags=["console_api"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(webhook_router, prefix="/api/v1", tags=["webhook"])
app.include_router(webhook_router, tags=["webhook_compatibility"])  # Alias for /webhook direct routing
