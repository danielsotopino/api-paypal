from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from paypal_api.config import settings
from paypal_api.models.base import Base

engine = None
SessionLocal = None

def init_db(database_url=None):
    """Initialize database connection"""
    global engine, SessionLocal
    
    if database_url is None:
        database_url = settings.DATABASE_URL
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create all tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    return engine

def get_db():
    """Get a database session"""
    if SessionLocal is None:
        init_db()
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()