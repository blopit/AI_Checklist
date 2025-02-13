from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from openai import AsyncOpenAI
import httpx
from crewai import Agent, Task, Crew
from langchain.tools import BaseTool, StructuredTool
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_models import ChatOpenAI
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chat_openai(api_key):
    # Create ChatOpenAI instance with minimal configuration
    return ChatOpenAI(
        model_name="gpt-4",
        openai_api_key=api_key,
        temperature=0.0
    )

# Define tool functions
def format_checklist(items: List[Dict[str, Any]]) -> str:
    """Format checklist items in a structured way"""
    return json.dumps(items, indent=2)

def validate_checklist(checklist: Dict[str, Any]) -> bool:
    """Validate checklist structure and required fields"""
    return all(
        required in checklist for required in ["title", "description", "items"]
    )

def analyze_complexity(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze the complexity of checklist items"""
    return {
        "simple": [i for i in items if len(i.get("steps", [])) <= 3],
        "complex": [i for i in items if len(i.get("steps", [])) > 3]
    }

def suggest_improvements(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Suggest improvements for checklist items"""
    return [
        {
            "item": item,
            "suggestions": ["Make more specific", "Add time estimates", "Break down into subtasks"]
        }
        for item in items
    ]

class ConversationMemory:
    def __init__(self, max_history_age: int = 24):
        self.conversation_history = {}  # session_id -> list of messages
        self.current_items = {}  # session_id -> dict of current items being discussed
        self.verification_state = {}  # session_id -> dict of items needing verification
        self.max_history_age = max_history_age  # hours
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        
        # Clean up old messages
        self._cleanup_old_messages(session_id)
    
    def get_messages(self, session_id: str) -> List[Dict]:
        """Get all messages for a session."""
        return self.conversation_history.get(session_id, [])
    
    def get_recent_context(self, session_id: str, max_messages: int = 10) -> List[Dict]:
        """Get the most recent messages for context, formatted for the OpenAI API."""
        messages = self.get_messages(session_id)
        # Return only the most recent messages, limited by max_messages
        recent_messages = messages[-max_messages:] if messages else []
        # Convert to format expected by OpenAI API
        return [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in recent_messages
        ]
    
    def set_current_items(self, session_id: str, items: Dict):
        """Set the current items being discussed."""
        self.current_items[session_id] = items
    
    def get_current_items(self, session_id: str) -> Dict:
        """Get the current items being discussed."""
        return self.current_items.get(session_id, {})
    
    def set_verification_state(self, session_id: str, state: Dict):
        """Set the verification state for items."""
        self.verification_state[session_id] = state
    
    def get_verification_state(self, session_id: str) -> Dict:
        """Get the verification state for items."""
        return self.verification_state.get(session_id, {})
    
    def _cleanup_old_messages(self, session_id: str):
        """Remove messages older than max_history_age hours."""
        if session_id in self.conversation_history:
            cutoff_time = datetime.now() - timedelta(hours=self.max_history_age)
            self.conversation_history[session_id] = [
                msg for msg in self.conversation_history[session_id]
                if msg["timestamp"] > cutoff_time
            ]
    
    def clear(self):
        """Clear all conversation history."""
        self.conversation_history.clear()
        self.current_items.clear()
        self.verification_state.clear()

class ChecklistAgent:
    def __init__(self, api_key: str):
        # Initialize HTTP client
        http_client = httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True
        )
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=http_client
        )
        
        # Initialize conversation memory
        self.memory = ConversationMemory()
        
        # Configure LLM
        llm = create_chat_openai(api_key)
        
        # Initialize tools
        checklist_tools = [
            StructuredTool.from_function(
                func=format_checklist,
                name="format_checklist",
                description="Format checklist items in a structured way"
            ),
            StructuredTool.from_function(
                func=validate_checklist,
                name="validate_checklist",
                description="Validate checklist structure and required fields"
            )
        ]
        
        analysis_tools = [
            StructuredTool.from_function(
                func=analyze_complexity,
                name="analyze_complexity",
                description="Analyze the complexity of checklist items"
            ),
            StructuredTool.from_function(
                func=suggest_improvements,
                name="suggest_improvements",
                description="Suggest improvements for checklist items"
            )
        ]
        
        # Initialize the main checklist agent
        self.checklist_manager = Agent(
            role="Checklist Manager",
            goal="Manage and maintain checklists effectively",
            backstory="""You are an expert checklist manager who helps users create, 
            update, and maintain their checklists. You understand the importance of 
            organization and can help break down complex tasks into manageable steps.""",
            tools=checklist_tools,
            llm=llm,
            verbose=True
        )
        
        # Initialize the task analyzer agent
        self.task_analyzer = Agent(
            role="Task Analyzer",
            goal="Analyze and optimize checklist items",
            backstory="""You are an expert at analyzing tasks and suggesting 
            improvements. You help ensure checklist items are clear, actionable, 
            and properly organized.""",
            tools=analysis_tools,
            llm=llm,
            verbose=True
        )
        
        # Create the crew
        self.crew = Crew(
            agents=[self.checklist_manager, self.task_analyzer],
            tasks=[],
            verbose=True
        )

    async def create_checklist(self, title: str, description: str, items: List[Dict]) -> Dict:
        """Create a new checklist with the given title, description, and items."""
        task = Task(
            description=f"""Create a new checklist with the following details:
            Title: {title}
            Description: {description}
            Items: {json.dumps(items, indent=2)}
            
            Ensure all items are properly formatted and organized.""",
            agent=self.checklist_manager,
            context=[{
                "title": title,
                "description": "Create a new checklist with the provided details",
                "items": items,
                "expected_output": "A formatted and validated checklist"
            }],
            expected_output="A formatted and validated checklist"
        )
        
        analyze_task = Task(
            description=f"""Analyze the checklist items and suggest any improvements:
            Items: {json.dumps(items, indent=2)}""",
            agent=self.task_analyzer,
            context=[{
                "items": items,
                "description": "Analyze checklist items for potential improvements",
                "expected_output": "Analysis and suggestions for improvement"
            }],
            expected_output="Analysis and suggestions for improvement"
        )
        
        self.crew.tasks = [analyze_task, task]
        result = await self.crew.kickoff()
        
        return {
            "title": title,
            "description": description,
            "items": items,
            "analysis": result
        }

    async def update_checklist(self, checklist_id: str, updates: Dict) -> Dict:
        """Update an existing checklist with the given updates."""
        task = Task(
            description=f"""Update the checklist with ID {checklist_id} with the following changes:
            {json.dumps(updates, indent=2)}
            
            Ensure all updates are properly applied and maintain checklist integrity.""",
            agent=self.checklist_manager,
            context=[{
                "checklist_id": checklist_id,
                "updates": updates,
                "description": "Update an existing checklist with the provided changes",
                "expected_output": "Updated checklist with applied changes"
            }],
            expected_output="Updated checklist with applied changes"
        )
        
        self.crew.tasks = [task]
        result = await self.crew.kickoff()
        
        return {
            "checklist_id": checklist_id,
            "updates": updates,
            "result": result
        }

    async def get_checklist_suggestions(self, context: str) -> List[Dict]:
        """Get suggestions for checklist items based on the given context."""
        task = Task(
            description=f"""Analyze the following context and suggest relevant checklist items:
            Context: {context}
            
            Provide detailed and actionable checklist items that would be helpful in this context.""",
            agent=self.task_analyzer,
            context=[{
                "input_context": context,
                "description": "Generate checklist suggestions based on the provided context",
                "expected_output": "List of suggested checklist items"
            }],
            expected_output="List of suggested checklist items"
        )
        
        self.crew.tasks = [task]
        result = await self.crew.kickoff()
        
        return result

    def get_conversation_history(self) -> Dict[str, List[Dict]]:
        """Retrieve the conversation history from memory."""
        return self.memory.conversation_history

    async def clear_memory(self):
        """Clear the agent's conversation memory."""
        self.memory.clear()

    async def process_message(
        self,
        message: str,
        session_id: str,
        checklist_status: str,
        item_map: Dict
    ) -> Dict:
        """Process a user message and return the response with any updates"""
        
        # Store the current items for context
        self.memory.set_current_items(session_id, item_map)
        
        # Add user message to history
        self.memory.add_message(session_id, "user", message)
        
        # Get conversation context
        conversation_context = self.memory.get_recent_context(session_id)
        
        # Prepare the system message with current context
        system_message = f"""You are an AI assistant specializing in compliance checklists for RED Hospitality and Leisure.
Your main responsibilities are:
1. Help users complete checklist items
2. Ask verification questions for tasks users claim to have completed
3. Mark items as complete when users provide valid verification
4. Provide specific, actionable guidance
5. Keep track of progress and suggest next steps

Current checklist status:
{checklist_status}

VERIFICATION RULES:
1. When a user claims to have completed tasks, ask for specific verification
2. When a user provides verification:
   - If the verification is valid, mark ONLY the items being discussed as complete
   - If the verification is invalid, explain why and what's needed
   - When a user verifies multiple items at once, update ONLY those items
3. Examples of valid verification:
   - Documentation: User confirms they have the physical document
   - Inspections: User describes the inspection results
   - Equipment: User confirms functionality or presence
   - Training: User provides certification details

IMPORTANT RULES:
1. NEVER uncheck items unless explicitly requested by the user
2. NEVER make assumptions about item status - ask the user if unclear
3. Only update items that are specifically mentioned in the user's message
4. If there's any ambiguity, ask for clarification
5. Consider the context and meaning of the user's message
6. Include ONLY verified items in your response
7. NEVER update items that weren't part of the current conversation
8. Maintain conversation context - if discussing a specific item, stay focused on it

When using the update_checklist_items function:
1. Include items in completed_items[] ONLY when:
   - The item was specifically mentioned in the current conversation
   - The user has explicitly verified it
   - You have asked for and received confirmation
2. Include items in uncompleted_items[] ONLY when the user has explicitly asked to uncheck them
3. Include clear reasoning in your message about what was verified and why
4. When multiple items are verified at once, list all of them in your response"""

        try:
            # Get AI response
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_message},
                    *conversation_context,
                    {"role": "user", "content": message}
                ],
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "update_checklist_items",
                        "description": "Update the completion status of checklist items",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "completed_items": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "IDs of items to mark as completed"
                                },
                                "uncompleted_items": {
                                    "type": "array",
                                    "items": {"type": "integer"},
                                    "description": "IDs of items to mark as uncompleted"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "Response message explaining what was verified and updated"
                                }
                            }
                        }
                    }
                }],
                tool_choice="auto"
            )

            # Process the response
            ai_message = response.choices[0].message
            logger.info(f"AI response: {ai_message}")

            # Store AI message in history
            self.memory.add_message(
                session_id,
                "assistant",
                ai_message.content if ai_message.content else "(function call)"
            )

            # Process tool calls if any
            if ai_message.tool_calls:
                tool_call = ai_message.tool_calls[0]
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in function arguments")
                    function_args = {
                        "message": "I apologize, but I encountered an error processing the updates."
                    }
                
                logger.info(f"Function args: {function_args}")
                return function_args

            # Return regular message if no tool calls
            return {"message": ai_message.content}

        except Exception as e:
            logger.error(f"Error in process_message: {str(e)}")
            return {
                "message": "I apologize, but I encountered an error processing your request. Please try again."
            }

    def get_memory_context(self, session_id: str) -> Dict:
        return {
            "recent_messages": self.memory.get_recent_context(session_id),
            "current_items": self.memory.get_current_items(session_id),
            "verification_states": self.memory.get_verification_state(session_id)
        }

    def clear_session(self, session_id: str):
        if session_id in self.memory.conversation_history:
            del self.memory.conversation_history[session_id]
        if session_id in self.memory.current_items:
            del self.memory.current_items[session_id]
        if session_id in self.memory.verification_state:
            del self.memory.verification_state[session_id] 