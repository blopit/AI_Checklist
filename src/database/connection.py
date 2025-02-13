import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get environment
ENV = os.getenv("ENV", "development")
logger.info(f"Running in {ENV} environment")

# SQLite database URL with absolute path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# In production (cPanel), we need to use a path relative to the home directory
if ENV == "production":
    # Get user's home directory (usually something like /home/username in cPanel)
    HOME_DIR = os.path.expanduser("~")
    DATABASE_PATH = os.path.join(HOME_DIR, "checklist.db")
else:
    # In development, use the project directory
    DATABASE_PATH = os.path.join(BASE_DIR, "checklist.db")

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
logger.info(f"Using database at: {DATABASE_PATH}")

# Create SQLAlchemy engine with SQLite
try:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Needed for SQLite
    )
    
    # Test the connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        logger.info("Successfully connected to the database")
except Exception as e:
    logger.error(f"Error connecting to database: {str(e)}")
    raise

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 