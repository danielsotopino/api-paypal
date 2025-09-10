from sqlalchemy.orm import declarative_base
from sqlalchemy import JSON as SQJSON

Base = declarative_base()

# Fix for SQLAlchemy JSON compatibility
JSON = SQJSON