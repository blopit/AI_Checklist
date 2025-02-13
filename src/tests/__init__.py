"""
Test suite for AI Development Setup Assistant
"""

import pytest
import httpx
from ..main import app
from fastapi import FastAPI

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

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_read_root(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_get_checklists_empty(client):
    response = await client.get("/api/checklists")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_chat_endpoint(client):
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
async def test_chat_endpoint_error_handling(client):
    response = await client.post(
        "/api/chat",
        json={"wrong_field": "Hello"}
    )
    assert response.status_code == 422  # FastAPI validation error

@pytest.mark.asyncio
async def test_chat_endpoint_with_empty_message(client):
    response = await client.post(
        "/api/chat",
        json={"content": "", "session_id": "test_session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["messages"]) == 2

@pytest.mark.asyncio
async def test_chat_endpoint_with_special_characters(client):
    response = await client.post(
        "/api/chat",
        json={"content": "Hello! @#$%^&*()", "session_id": "test_session"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_speech_to_text_endpoint(client):
    # This is a mock test since we can't easily test actual audio file processing
    with open("tests/test_audio.txt", "w") as f:
        f.write("test audio content")
    
    with open("tests/test_audio.txt", "rb") as f:
        files = {"audio": ("test_audio.wav", f, "audio/wav")}
        response = await client.post(
            "/api/speech-to-text",
            files=files
        )
    
    # Since we're not actually sending audio, we expect an error
    assert response.status_code == 500
    
    # Cleanup
    import os
    os.remove("tests/test_audio.txt")

@pytest.mark.asyncio
async def test_text_to_speech_endpoint(client):
    response = await client.post(
        "/api/text-to-speech",
        json={"content": "Hello, this is a test message"}
    )
    # Since we're using the real OpenAI API, we expect a successful response
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"

@pytest.mark.asyncio
async def test_checklist_item_update(client):
    response = await client.post(
        "/api/checklist/item",
        json={
            "id": 1,
            "is_completed": True,
            "notes": "Test note",
            "checked_by": "Tester"
        }
    )
    assert response.status_code in [200, 404]  # 404 is acceptable as it's a demo with empty DB 