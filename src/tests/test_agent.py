"""
Tests for ChecklistAgent
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from ..agents.checklist_agent import ChecklistAgent, ConversationMemory
import os
from datetime import datetime, timedelta

@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response"""
    return MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content="Test response",
                    tool_calls=None
                )
            )
        ]
    )

@pytest.fixture
def mock_openai_client(mock_openai_response):
    """Create a mock OpenAI client"""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
    return mock_client

@pytest.fixture
def agent(mock_openai_client):
    """Create a test agent with mocked OpenAI client"""
    with patch('openai.AsyncOpenAI', return_value=mock_openai_client):
        agent = ChecklistAgent(os.getenv("OPENAI_API_KEY"))
        agent.client = mock_openai_client
        return agent

@pytest.fixture
def memory():
    """Create a test memory instance"""
    return ConversationMemory(max_history_age=24)

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test agent initialization"""
    assert agent is not None
    assert agent.memory is not None
    assert agent.client is not None

@pytest.mark.asyncio
async def test_process_message(agent):
    """Test processing a basic message"""
    result = await agent.process_message(
        "Hello",
        "test_session",
        "No items in checklist",
        {}
    )
    assert isinstance(result, dict)
    assert "message" in result
    assert result["message"] == "Test response"

@pytest.mark.asyncio
async def test_process_message_with_items(agent, mock_openai_response):
    """Test processing a message with checklist items"""
    # Set up mock response for a tool call
    mock_openai_response.choices[0].message.tool_calls = [
        MagicMock(
            function=MagicMock(
                arguments='{"completed_items": [1], "message": "Verified VHF radio check"}'
            )
        )
    ]
    
    checklist_status = """
    ## Safety
    ### Equipment
    □ VHF Radio Check (ID: 1)
    □ Safety Equipment Inspection (ID: 2)
    """
    item_map = {
        "vhf radio check": {
            "id": 1,
            "category": "Safety",
            "section": "Equipment",
            "is_completed": False
        },
        "safety equipment inspection": {
            "id": 2,
            "category": "Safety",
            "section": "Equipment",
            "is_completed": False
        }
    }
    
    result = await agent.process_message(
        "I've completed the VHF radio check",
        "test_session",
        checklist_status,
        item_map
    )
    assert isinstance(result, dict)
    assert "completed_items" in result
    assert result["completed_items"] == [1]

def test_memory_management(memory):
    """Test conversation memory management"""
    # Add some messages
    memory.add_message("test_session", "user", "Hello")
    memory.add_message("test_session", "assistant", "Hi there")
    
    # Check recent context
    context = memory.get_recent_context("test_session")
    assert len(context) == 2
    assert context[0]["role"] == "user"
    assert context[1]["role"] == "assistant"

def test_memory_cleanup(memory):
    """Test old conversation cleanup"""
    # Add an old message
    old_time = datetime.utcnow() - timedelta(hours=25)
    memory.conversation_history["old_session"] = [{
        "role": "user",
        "content": "Old message",
        "timestamp": old_time
    }]
    
    # Add a new message to trigger cleanup
    memory.add_message("new_session", "user", "New message")
    
    # Old session should be removed
    assert "old_session" not in memory.conversation_history
    assert "new_session" in memory.conversation_history

def test_verification_state(memory):
    """Test verification state management"""
    items = {"item1": "pending"}
    memory.set_verification_state("test_session", items)
    
    state = memory.get_verification_state("test_session")
    assert state == items

def test_current_items(memory):
    """Test current items management"""
    items = {"item1": {"status": "pending"}}
    memory.set_current_items("test_session", items)
    
    current = memory.get_current_items("test_session")
    assert current == items 