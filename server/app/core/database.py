from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# 1. Create the database engine.
# The engine is the entry point to our database, managing connection pools.
engine = create_engine(settings.DATABASE_URL)

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
