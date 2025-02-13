import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.agents.checklist_agent import ChecklistAgent, ConversationMemory
from crewai import Task, Process

@pytest.fixture
def api_key():
    return "test-api-key"

@pytest.fixture
def mock_openai():
    with patch('src.agents.checklist_agent.OpenAI') as mock:
        yield mock

@pytest.fixture
def mock_async_openai():
    with patch('src.agents.checklist_agent.AsyncOpenAI') as mock:
        yield mock

@pytest.fixture
def mock_httpx_client():
    with patch('src.agents.checklist_agent.httpx.AsyncClient') as mock:
        yield mock

@pytest.fixture
def mock_crew():
    with patch('src.agents.checklist_agent.Crew') as mock:
        instance = mock.return_value
        # Set up the mock to return an async function
        instance.kickoff = AsyncMock(return_value="Analysis complete")
        yield instance

@pytest.fixture
def checklist_agent(api_key, mock_openai, mock_async_openai, mock_httpx_client, mock_crew):
    agent = ChecklistAgent(api_key)
    # Replace the real crew with our mock
    agent.crew = mock_crew
    return agent

@pytest.mark.asyncio
async def test_create_checklist(checklist_agent):
    # Test data
    title = "Test Checklist"
    description = "A test checklist"
    items = [
        {"id": 1, "name": "Item 1", "description": "First item"},
        {"id": 2, "name": "Item 2", "description": "Second item"}
    ]
    
    # Call the method
    result = await checklist_agent.create_checklist(title, description, items)
    
    # Verify the result
    assert result["title"] == title
    assert result["description"] == description
    assert result["items"] == items
    assert result["analysis"] == "Analysis complete"
    
    # Verify crew kickoff was called
    checklist_agent.crew.kickoff.assert_called_once()

@pytest.mark.asyncio
async def test_update_checklist(checklist_agent):
    # Test data
    checklist_id = "test-123"
    updates = {
        "title": "Updated Checklist",
        "items": [{"id": 1, "name": "Updated Item"}]
    }
    
    # Set up mock response
    checklist_agent.crew.kickoff = AsyncMock(return_value="Update complete")
    
    # Call the method
    result = await checklist_agent.update_checklist(checklist_id, updates)
    
    # Verify the result
    assert result["checklist_id"] == checklist_id
    assert result["updates"] == updates
    assert result["result"] == "Update complete"
    
    # Verify crew kickoff was called
    checklist_agent.crew.kickoff.assert_called_once()

@pytest.mark.asyncio
async def test_get_checklist_suggestions(checklist_agent):
    # Test data
    context = "Need a checklist for project planning"
    
    # Set up mock response
    expected_suggestions = [
        {"name": "Define project scope", "description": "Outline project objectives and deliverables"},
        {"name": "Create timeline", "description": "Set project milestones and deadlines"}
    ]
    checklist_agent.crew.kickoff = AsyncMock(return_value=expected_suggestions)
    
    # Call the method
    result = await checklist_agent.get_checklist_suggestions(context)
    
    # Verify the result
    assert result == expected_suggestions
    
    # Verify crew kickoff was called
    checklist_agent.crew.kickoff.assert_called_once()

def test_conversation_memory():
    memory = ConversationMemory(max_history_age=24)
    
    # Test adding and retrieving messages
    session_id = "test-session"
    memory.add_message(session_id, "user", "Hello")
    memory.add_message(session_id, "assistant", "Hi there")
    
    messages = memory.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hi there"
    
    # Test current items
    items = {"1": {"name": "Test Item"}}
    memory.set_current_items(session_id, items)
    retrieved_items = memory.get_current_items(session_id)
    assert retrieved_items == items
    
    # Test clearing memory
    memory.clear()
    assert len(memory.get_messages(session_id)) == 0
    assert memory.get_current_items(session_id) == {} 