import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app, checklist_state

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_get_checklist():
    response = client.get("/api/checklist")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert all(isinstance(item, dict) for item in data["items"])
    assert all("id" in item and "description" in item and "is_completed" in item 
              for item in data["items"])

def test_chat_endpoint():
    # Test basic chat functionality
    response = client.post(
        "/api/chat",
        json={"content": "Hello, I need help setting up my environment"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "updated_items" in data
    assert isinstance(data["message"], str)
    assert isinstance(data["updated_items"], list)

def test_chat_completion_verification():
    # Test checklist item completion verification
    response = client.post(
        "/api/chat",
        json={"content": "I've installed Python 3.12"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data["message"].lower() or "verify" in data["message"].lower()

def test_invalid_chat_message():
    response = client.post(
        "/api/chat",
        json={"content": ""}
    )
    assert response.status_code == 200  # Should still return 200 with a helpful message

def test_checklist_state_integrity():
    # Test that checklist items maintain correct structure
    response = client.get("/api/checklist")
    initial_state = response.json()
    
    # Send a chat message that might update state
    client.post("/api/chat", json={"content": "I've completed everything"})
    
    # Check state again
    response = client.get("/api/checklist")
    new_state = response.json()
    
    # Verify structure remains intact
    assert len(initial_state["items"]) == len(new_state["items"])
    assert all(isinstance(item["is_completed"], bool) for item in new_state["items"]) 