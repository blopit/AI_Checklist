"""
Test configuration and fixtures
"""
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends

from ..database.models import Base, ChecklistCategory, ChecklistSection, ChecklistItem
from ..database.connection import get_db
from ..main import app

# Set test environment
os.environ["ENV"] = "test"

# Load test environment variables
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(test_env_path)

# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )
    
    # Set asyncio_mode to "auto" to handle async tests
    config.option.asyncio_mode = "auto"
    
    # Configure the event loop scope for async fixtures
    config.option.asyncio_fixture_scope = "function"

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create a fresh test database for each test"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Get a test database session
    db = TestingSessionLocal()
    
    try:
        # Clear any existing data
        db.query(ChecklistItem).delete()
        db.query(ChecklistSection).delete()
        db.query(ChecklistCategory).delete()
        db.commit()
        
        # Override the database dependency
        app.dependency_overrides[get_db] = lambda: db
        
        yield db
    finally:
        db.rollback()
        db.close()
        # Drop all tables after the test
        Base.metadata.drop_all(bind=engine)
        # Clean up the override
        app.dependency_overrides.pop(get_db, None)

# Override the database dependency
async def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Override the database dependency for tests
app.dependency_overrides[get_db] = override_get_db 