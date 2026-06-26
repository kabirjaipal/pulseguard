from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

import os
import logging

logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
engine = None

def get_sqlite_engine():
    db_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../pulseguard.db"))
    logger.warning("No working PostgreSQL connection. Falling back to local SQLite database: %s", db_file_path)
    return create_engine(f"sqlite:///{db_file_path}", connect_args={"check_same_thread": False})

if db_url and db_url.startswith("postgresql"):
    try:
        # Create a test engine to check connectivity
        test_engine = create_engine(db_url)
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        logger.info("Successfully connected to PostgreSQL database.")
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL database: %s", str(e))
        engine = get_sqlite_engine()
else:
    engine = get_sqlite_engine()

# 2. Create SessionLocal class.
# Each instance of SessionLocal will represent a single database session/transaction.
# 'autocommit=False' means transactions won't be saved automatically; we must commit them.
# 'autoflush=False' prevents queries from pushing changes to the DB before committing.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Create the Base class.
# All our database models (like User, Project) will inherit from this Base class.
# SQLAlchemy uses it to detect and map models to database tables.
Base = declarative_base()

# 4. Dependency to get a DB session.
# This yields a DB session to a request, then closes the session when the request ends.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
