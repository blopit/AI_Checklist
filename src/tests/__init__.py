"""
Test suite for AI Development Setup Assistant
""" 

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from ..main import app
from ..database.connection import get_db
from ..database.models import Base

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create test database tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200

def test_get_checklists_empty():
    response = client.get("/api/checklists")
    assert response.status_code == 200
    assert response.json() == []

def test_chat_endpoint():
    response = client.post(
        "/api/chat",
        json={"content": "Hello", "session_id": "test_session"}
    )
    assert response.status_code == 200
    assert "messages" in response.json()
    assert "categories" in response.json()
    assert "success" in response.json()
    assert len(response.json()["messages"]) == 2  # AI response and status update

def test_chat_endpoint_error_handling():
    response = client.post(
        "/api/chat",
        json={"wrong_field": "Hello"}
    )
    assert response.status_code in [400, 422]  # FastAPI validation error

def test_checklist_item_update():
    response = client.post(
        "/api/checklist/item",
        json={
            "id": 1,
            "is_completed": True,
            "notes": "Test note",
            "checked_by": "Tester"
        }
    )
    assert response.status_code in [200, 404]  # 404 is acceptable as it's a demo with empty DB 