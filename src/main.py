from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
from openai import AsyncOpenAI
import os
from typing import List, Dict
from dotenv import load_dotenv
import json
from fastapi.responses import FileResponse

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(title="AI Development Setup Assistant")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store checklist state
checklist_state = {
    "items": [
        {"id": 1, "description": "Install Python 3.12 or later", "is_completed": False},
        {"id": 2, "description": "Set up virtual environment", "is_completed": False},
        {"id": 3, "description": "Install PostgreSQL", "is_completed": False},
        {"id": 4, "description": "Install required Python packages", "is_completed": False},
        {"id": 5, "description": "Configure environment variables", "is_completed": False},
        {"id": 6, "description": "Set up database and run migrations", "is_completed": False},
        {"id": 7, "description": "Install development tools (git, IDE, etc.)", "is_completed": False},
        {"id": 8, "description": "Configure version control", "is_completed": False},
        {"id": 9, "description": "Set up linting and formatting", "is_completed": False},
        {"id": 10, "description": "Configure testing environment", "is_completed": False}
    ]
}

# Store conversation history
conversation_history = []

class Message(BaseModel):
    content: str

class ChecklistResponse(BaseModel):
    message: str
    updated_items: List[Dict]

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/checklist")
async def get_checklist():
    return checklist_state

@app.post("/api/chat")
async def chat(message: Message):
    try:
        # Create system message with current checklist state
        checklist_status = "\n".join([
            f"{item['id']}. {'[x]' if item['is_completed'] else '[ ]'} {item['description']}"
            for item in checklist_state["items"]
        ])
        
        system_message = f"""You are an AI assistant helping with development environment setup.
Current checklist status:
{checklist_status}

Your task is to:
1. Help users complete the checklist items
2. Ask verification questions for tasks users claim to have completed
3. Mark items as complete when users provide valid verification
4. Provide specific, actionable guidance
5. Keep track of progress and suggest next steps

VERIFICATION RULES:
1. When a user claims to have completed a task, ask for specific verification
2. When a user provides verification (like command output):
   - If the verification is valid, IMMEDIATELY use update_checklist to mark the item as complete
   - If the verification is invalid, explain why and what's needed
3. Examples of valid verification:
   - Python installation: Output shows Python 3.12 or later -> Mark item 1 complete
   - Virtual environment: Terminal shows (.venv) -> Mark item 2 complete
   - PostgreSQL: pg_isready shows server running -> Mark item 3 complete

IMPORTANT: 
- IMMEDIATELY mark items as complete when users provide valid verification output
- Use update_checklist function with completed_items array
- Don't ask for verification again if valid proof is provided
- For command outputs:
  - python --version showing 3.12+ -> Mark Python installation complete
  - Terminal showing (.venv) -> Mark virtual environment complete
  - pg_isready success -> Mark PostgreSQL complete
  - pip list in venv -> Mark virtual environment complete
  - git --version -> Mark development tools complete"""

        # Add user message to history
        conversation_history.append({"role": "user", "content": message.content})
        
        # Get AI response
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                *conversation_history[-4:]  # Include last 4 messages for context
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "update_checklist",
                    "description": "Update the completion status of checklist items",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "completed_items": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "IDs of items to mark as completed"
                            },
                            "message": {
                                "type": "string",
                                "description": "Response message to show to the user"
                            }
                        },
                        "required": ["message"]
                    }
                }
            }],
            tool_choice="auto"
        )

        # Process the response
        ai_message = response.choices[0].message
        logger.info(f"AI response: {ai_message}")

        if ai_message.tool_calls:
            # Update checklist based on AI's decision
            tool_call = ai_message.tool_calls[0]
            function_args = json.loads(tool_call.function.arguments)
            logger.info(f"Function args: {function_args}")

            newly_completed = []
            if "completed_items" in function_args:
                for item_id in function_args["completed_items"]:
                    logger.info(f"Marking item {item_id} as completed")
                    for item in checklist_state["items"]:
                        if item["id"] == item_id and not item["is_completed"]:
                            item["is_completed"] = True
                            newly_completed.append(item["description"])
                            logger.info(f"Marked item {item_id} ({item['description']}) as completed")
            
            # Add completion status to message if items were completed
            message = function_args["message"]
            if newly_completed:
                completion_status = "\n\n✅ Just completed:\n" + "\n".join(f"- {item}" for item in newly_completed)
                total_completed = sum(1 for item in checklist_state["items"] if item["is_completed"])
                completion_status += f"\n\nProgress: {total_completed}/{len(checklist_state['items'])} tasks completed"
                message += completion_status
            
            return {
                "message": message,
                "updated_items": checklist_state["items"]
            }
        else:
            # Add current progress to regular messages occasionally
            message = ai_message.content
            total_completed = sum(1 for item in checklist_state["items"] if item["is_completed"])
            if total_completed > 0 and ("progress" in message.lower() or "status" in message.lower()):
                progress = f"\n\nCurrent Progress: {total_completed}/{len(checklist_state['items'])} tasks completed"
                message += progress
            
            return {
                "message": message,
                "updated_items": checklist_state["items"]
            }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 