"""
Tests for main application functionality
"""
import pytest
import httpx
from ..main import app

@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_app_startup(client):
    """Test application startup and basic configuration"""
    assert app.title == "RED Hospitality Compliance Assistant"
    
    # Test CORS configuration
    response = await client.options("/")
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"

@pytest.mark.asyncio
async def test_static_files(client):
    """Test static files are served correctly"""
    response = await client.get("/static/index.html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_read_root(client):
    """Test root endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_get_checklist(client):
    """Test getting checklist"""
    response = await client.get("/api/checklists")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_chat_endpoint(client):
    """Test chat endpoint with valid message"""
    response = await client.post(
        "/api/chat",
        json={
            "content": "Hello",
            "session_id": "test_session"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "success" in data
    assert data["success"] is True

@pytest.mark.asyncio
async def test_chat_completion_verification(client):
    """Test chat completion with verification"""
    response = await client.post(
        "/api/chat",
        json={
            "content": "I've completed the safety check",
            "session_id": "test_session"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "messages" in data
    assert "success" in data
    assert data["success"] is True

@pytest.mark.asyncio
async def test_invalid_chat_message(client):
    """Test chat endpoint with invalid message"""
    response = await client.post(
        "/api/chat",
        json={"wrong_field": "Hello"}
    )
    assert response.status_code == 422  # Validation error

@pytest.mark.asyncio
async def test_checklist_state_integrity(client):
    """Test checklist state integrity"""
    # Get initial state
    response = await client.get("/api/checklists")
    assert response.status_code == 200
    initial_state = response.json()
    
    # Make a chat request
    response = await client.post(
        "/api/chat",
        json={
            "content": "Show me the checklist",
            "session_id": "test_session"
        }
    )
    assert response.status_code == 200
    
    # Verify state hasn't changed unexpectedly
    response = await client.get("/api/checklists")
    assert response.status_code == 200
    current_state = response.json()
    assert current_state == initial_state 