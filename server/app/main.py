import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import engine
from app.models import Base
from app.routers import auth, projects, endpoints, incidents, websocket
from app.core.websocket_manager import redis_pubsub_listener
from app.core.logging_config import setup_logging

# Initialize structured logging
setup_logging()
logger = logging.getLogger("app.main")

# Create database tables. In production we would use Alembic migrations,
# but for learning and quick development, we let SQLAlchemy generate them.
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic: Start the Redis Pub/Sub listener in the background
    pubsub_task = asyncio.create_task(redis_pubsub_listener())
    yield
    # Shutdown logic: Cancel the task
    pubsub_task.cancel()
    try:
        await pubsub_task
    except asyncio.CancelledError:
        pass

# 1. Create a FastAPI instance with lifespan event handlers
app = FastAPI(
    title="PulseGuard API",
    description="AI-Powered API Monitoring & Incident Analysis Platform",
    version="0.1.0",
    lifespan=lifespan
)

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database exception encountered: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred."}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server exception: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."}
    )


# CORS configurations - Allow local Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(endpoints.router)
app.include_router(incidents.router)
app.include_router(websocket.router)

# 2. Define a basic route (endpoint) using a path decorator.
# "@app.get('/')" tells FastAPI that this function handles GET requests to the root path.
@app.get("/")
def read_root():
    return {"message": "Welcome to PulseGuard API!"}
