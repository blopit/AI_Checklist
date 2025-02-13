"""
Tests for API endpoints
"""
import pytest
import httpx
from httpx import AsyncClient
import os
from fastapi import Depends
from ..main import app
from ..database.models import Base, ChecklistCategory, ChecklistSection, ChecklistItem
from ..database.connection import get_db
from .conftest import test_db, TestingSessionLocal, override_get_db

@pytest.fixture
async def client():
    """Create a test client with the test database"""
    app.dependency_overrides[get_db] = override_get_db
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_read_root(client):
    """Test the root endpoint returns the HTML file"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_get_checklists_empty(test_db):
    """Test getting checklists when the database is empty"""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/checklists")
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.content}")
        assert response.status_code == 200
        assert response.json() == []

@pytest.mark.asyncio
async def test_chat_endpoint_basic(client):
    """Test basic chat functionality"""
    response = await client.post(
        "/api/chat",
        json={"content": "Hello", "session_id": "test_session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "categories" in data
    assert "success" in data
    assert len(data["messages"]) == 2  # AI response and status update
    assert data["success"] is True

@pytest.mark.asyncio
async def test_chat_endpoint_validation(client):
    """Test chat endpoint input validation"""
    response = await client.post(
        "/api/chat",
        json={"wrong_field": "Hello"}
    )
    assert response.status_code == 422  # FastAPI validation error

@pytest.mark.asyncio
async def test_chat_endpoint_empty_message(client):
    """Test chat endpoint with empty message"""
    response = await client.post(
        "/api/chat",
        json={"content": "", "session_id": "test_session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["messages"]) == 2

@pytest.mark.asyncio
async def test_chat_endpoint_special_chars(client):
    """Test chat endpoint with special characters"""
    response = await client.post(
        "/api/chat",
        json={"content": "Hello! @#$%^&*()", "session_id": "test_session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_speech_to_text(client):
    """Test speech-to-text endpoint with mock audio"""
    test_audio_dir = "tests/test_audio"
    os.makedirs(test_audio_dir, exist_ok=True)
    test_audio_file = os.path.join(test_audio_dir, "test_audio.txt")
    
    try:
        # Create mock audio file
        with open(test_audio_file, "w") as f:
            f.write("test audio content")
        
        # Test with mock audio
        with open(test_audio_file, "rb") as f:
            response = await client.post(
                "/api/speech-to-text",
                files={"audio": ("test_audio.wav", f, "audio/wav")}
            )
        
        # Since we're using mock audio, we expect an error
        assert response.status_code == 500
        
    finally:
        # Cleanup
        if os.path.exists(test_audio_file):
            os.remove(test_audio_file)

@pytest.mark.asyncio
async def test_text_to_speech(client):
    """Test text-to-speech endpoint"""
    response = await client.post(
        "/api/text-to-speech",
        json={"content": "Hello, this is a test message"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg" 