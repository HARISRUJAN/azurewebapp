from sqlalchemy.orm import Session
from app.models.database import get_db

# Dependency for getting database session
def get_database() -> Session:
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

