from fastapi import FastAPI
from app.core.database import engine
from app.models import Base
from app.routers import auth, projects, endpoints

# Create database tables. In production we would use Alembic migrations,
# but for learning and quick development, we let SQLAlchemy generate them.
Base.metadata.create_all(bind=engine)

# 1. Create a FastAPI instance. This acts as the main hub of our application.
app = FastAPI(
    title="PulseGuard API",
    description="AI-Powered API Monitoring & Incident Analysis Platform",
    version="0.1.0"
)

# Register Routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(endpoints.router)

# 2. Define a basic route (endpoint) using a path decorator.
# "@app.get('/')" tells FastAPI that this function handles GET requests to the root path.
@app.get("/")
def read_root():
    return {"message": "Welcome to PulseGuard API!"}
