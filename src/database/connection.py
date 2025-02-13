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
def get_database_url():
    if ENV == "test":
        return "sqlite:///:memory:", {"check_same_thread": False}
    
    # Get database URL from environment variable
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Construct URL from individual components if DATABASE_URL is not provided
        db_user = os.getenv("POSTGRES_USER", "postgres")
        db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB", "auto_checklist")
        
        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Handle special case where DATABASE_URL starts with postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url, {}

try:
    # Get database URL and connect args
    DATABASE_URL, connect_args = get_database_url()
    
    # Create SQLAlchemy engine
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    
    # Test the connection only in development mode
    if ENV == "development":
        with engine.connect() as conn:
            logger.info("Successfully connected to the database")
except Exception as e:
    logger.error(f"Error connecting to database: {str(e)}")
    if ENV != "development":
        # In production, don't fail immediately - let the application handle reconnection
        logger.warning("Continuing despite database connection error in non-development environment")
    else:
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