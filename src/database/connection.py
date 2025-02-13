from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment
ENV = os.getenv("ENV", "development")

# Database connection settings
if ENV == "test":
    DATABASE_URL = "sqlite:///:memory:"
    connect_args = {"check_same_thread": False}
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/auto_checklist")
    connect_args = {}

try:
    # Create SQLAlchemy engine
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    # Test the connection
    with engine.connect() as conn:
        logger.info("Successfully connected to the database")
except Exception as e:
    logger.error(f"Error connecting to database: {str(e)}")
    raise

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 