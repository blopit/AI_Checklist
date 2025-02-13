from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.background import BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import logging
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import json
from fastapi.responses import FileResponse

from database.connection import get_db
from database.models import ChecklistCategory, ChecklistSection, ChecklistItem

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Store conversation history in memory
# Key: session_id, Value: list of messages with timestamp
conversation_history = {}

# Maximum age for conversation history (in hours)
MAX_HISTORY_AGE = 24

app = FastAPI(title="RED Hospitality Compliance Assistant")

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

class Message(BaseModel):
    content: str
    session_id: Optional[str] = None

class ChecklistItemUpdate(BaseModel):
    id: int
    is_completed: bool
    notes: Optional[str] = None
    checked_by: Optional[str] = None

class ChecklistResponse(BaseModel):
    message: str
    categories: List[Dict]

def clean_old_conversations():
    """Remove conversation histories older than MAX_HISTORY_AGE hours"""
    current_time = datetime.utcnow()
    to_remove = []
    for session_id, history in conversation_history.items():
        if history:
            last_message_time = history[-1]["timestamp"]
            if current_time - last_message_time > timedelta(hours=MAX_HISTORY_AGE):
                to_remove.append(session_id)
    
    for session_id in to_remove:
        del conversation_history[session_id]

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/checklists")
async def get_checklists(db: Session = Depends(get_db)):
    try:
        categories = db.query(ChecklistCategory).all()
        result = []
        
        for category in categories:
            cat_dict = {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "sections": []
            }
            
            for section in sorted(category.sections, key=lambda s: s.order):
                section_dict = {
                    "id": section.id,
                    "name": section.name,
                    "description": section.description,
                    "items": []
                }
                
                for item in sorted(section.items, key=lambda i: i.order):
                    section_dict["items"].append({
                        "id": item.id,
                        "description": item.description,
                        "is_completed": item.is_completed,
                        "notes": item.notes,
                        "last_checked": item.last_checked.isoformat() if item.last_checked else None,
                        "checked_by": item.checked_by
                    })
                
                cat_dict["sections"].append(section_dict)
            
            result.append(cat_dict)
        
        return result
    except Exception as e:
        logger.error(f"Error fetching checklists: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/checklist/item")
async def update_checklist_item(item_update: ChecklistItemUpdate, db: Session = Depends(get_db)):
    try:
        item = db.query(ChecklistItem).filter(ChecklistItem.id == item_update.id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        item.is_completed = item_update.is_completed
        if item_update.notes:
            item.notes = item_update.notes
        if item_update.checked_by:
            item.checked_by = item_update.checked_by
        if item_update.is_completed:
            item.last_checked = datetime.utcnow()
        
        db.commit()
        return {"message": "Item updated successfully"}
    except Exception as e:
        logger.error(f"Error updating checklist item: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(message: Message, db: Session = Depends(get_db)):
    try:
        # Clean old conversations periodically
        clean_old_conversations()

        # Initialize or get conversation history
        session_id = message.session_id or "default"
        if session_id not in conversation_history:
            conversation_history[session_id] = []

        # Get current checklist state for context
        categories = db.query(ChecklistCategory).all()
        checklist_status = []
        
        # Create a mapping of descriptions to item IDs for verification
        item_map = {}
        
        # Handle empty database case
        if not categories:
            checklist_status = ["No checklist categories found in the database."]
        else:
            for category in categories:
                cat_status = f"\n## {category.name}\n"
                for section in sorted(category.sections, key=lambda s: s.order):
                    cat_status += f"\n### {section.name}\n"
                    for item in sorted(section.items, key=lambda i: i.order):
                        status = "✓" if item.is_completed else "□"
                        cat_status += f"{status} {item.description} (ID: {item.id})\n"
                        # Store the mapping of description to ID
                        item_map[item.description.lower()] = {
                            "id": item.id,
                            "category": category.name,
                            "section": section.name,
                            "is_completed": item.is_completed
                        }
                checklist_status.append(cat_status)

        # Build conversation context
        conversation_context = []
        if conversation_history[session_id]:
            # Get last 10 messages for context
            recent_history = conversation_history[session_id][-10:]
            conversation_context = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in recent_history
            ]
        
        system_message = f"""You are an AI assistant helping with compliance checklists for RED Hospitality and Leisure.
Current checklist status:
{''.join(checklist_status)}

Your task is to:
1. Help users complete the checklist items
2. Ask verification questions for tasks users claim to have completed
3. Mark items as complete when users provide valid verification
4. Provide specific, actionable guidance
5. Keep track of progress and suggest next steps

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
4. When multiple items are verified at once, list all of them in your response

RESPONSE FORMAT:
1. Your message should be clear and conversational
2. Status updates will be shown separately in the chat
3. DO NOT include checklist IDs in your response
4. DO NOT repeat the status updates in your message

CHECKLIST UPDATES:
- Only mark items complete when the user provides clear verification
- Only uncheck items when explicitly requested
- Always ask for clarification if the user's intent is unclear
- Keep responses focused on the current verification or request
- NEVER update unrelated items"""

        # Prepare messages for API call
        messages = [{"role": "system", "content": system_message}]
        messages.extend(conversation_context)
        messages.append({"role": "user", "content": message.content})

        # Get AI response
        try:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
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
                tool_choice="auto",
                timeout=30  # Add timeout for demo purposes
            )
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return {
                "messages": [
                    {
                        "role": "system",
                        "content": "I apologize, but I'm having trouble processing your request right now. Please try again.",
                        "type": "error",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "role": "system",
                        "content": "",
                        "type": "status_update",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "categories": categories,
                "success": False
            }

        # Process the response
        ai_message = response.choices[0].message
        logger.info(f"AI response: {ai_message}")

        try:
            # Store messages in conversation history
            conversation_history[session_id].append({
                "role": "user",
                "content": message.content,
                "timestamp": datetime.utcnow()
            })
            conversation_history[session_id].append({
                "role": "assistant",
                "content": ai_message.content if ai_message.content else "(function call)",
                "timestamp": datetime.utcnow()
            })

            # Initialize status message and updates lists
            status_message = []
            completed_updates = []
            uncompleted_updates = []

            if ai_message.tool_calls:
                # Update checklist based on AI's decision
                tool_call = ai_message.tool_calls[0]
                try:
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in function arguments")
                    function_args = {"message": "I apologize, but I encountered an error processing the updates."}

                logger.info(f"Function args: {function_args}")

                # Handle completed items if present
                if "completed_items" in function_args:
                    for item_id in function_args["completed_items"]:
                        try:
                            item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
                            if item and not item.is_completed:
                                item.is_completed = True
                                item.last_checked = datetime.utcnow()
                                completed_updates.append(f"{item.description} (in {item_map[item.description.lower()]['section']})")
                                logger.info(f"Marked item {item_id} ({item.description}) as completed")
                        except Exception as e:
                            logger.error(f"Error updating item {item_id}: {str(e)}")

                # Handle uncompleted items if present
                if "uncompleted_items" in function_args:
                    for item_id in function_args["uncompleted_items"]:
                        try:
                            item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
                            if item and item.is_completed:
                                item.is_completed = False
                                uncompleted_updates.append(f"{item.description} (in {item_map[item.description.lower()]['section']})")
                                logger.info(f"Marked item {item_id} ({item.description}) as uncompleted")
                        except Exception as e:
                            logger.error(f"Error updating item {item_id}: {str(e)}")

                try:
                    db.commit()
                except Exception as e:
                    logger.error(f"Error committing changes: {str(e)}")
                    db.rollback()
                    return {
                        "messages": [
                            {
                                "role": "assistant",
                                "content": "I apologize, but I couldn't save the changes to the database. Please try again.",
                                "type": "error",
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            {
                                "role": "system",
                                "content": "",
                                "type": "status_update",
                                "timestamp": datetime.utcnow().isoformat()
                            }
                        ],
                        "categories": categories,
                        "success": False
                    }

            # Get updated checklist state
            categories = await get_checklists(db)

            # Build status update message
            if completed_updates:
                status_message.append("✅ Just completed:\n" + "\n".join(f"- {item}" for item in completed_updates))
            if uncompleted_updates:
                status_message.append("❌ Just unchecked:\n" + "\n".join(f"- {item}" for item in uncompleted_updates))

            # Get total progress
            total_items = 0
            completed_items = 0
            for category in categories:
                for section in category["sections"]:
                    for item in section["items"]:
                        total_items += 1
                        if item["is_completed"]:
                            completed_items += 1

            if total_items > 0:
                status_message.append(f"\nProgress: {completed_items}/{total_items} items completed")

            # Store the status update as a separate system message in conversation history
            if status_message:
                conversation_history[session_id].append({
                    "role": "system",
                    "content": "\n".join(status_message),
                    "timestamp": datetime.utcnow(),
                    "type": "status_update"
                })

            # Return messages and updated categories with consistent message structure
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": function_args.get("message", ai_message.content) if ai_message.tool_calls else ai_message.content,
                        "type": "message",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "role": "system",
                        "content": "\n".join(status_message) if status_message else "",
                        "type": "status_update",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "categories": categories,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I apologize, but I encountered an error processing the response. Please try again later.",
                        "type": "error",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "role": "system",
                        "content": "",
                        "type": "status_update",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "categories": categories if 'categories' in locals() else [],
                "success": False
            }

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Error: {str(e)}",
                    "type": "error",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "role": "system",
                    "content": "",
                    "type": "status_update",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "categories": [],
            "success": False
        }

@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        # Save the audio file temporarily
        temp_file = f"temp_{audio.filename}"
        with open(temp_file, "wb") as buffer:
            content = await audio.read()
            buffer.write(content)
        
        # Transcribe using OpenAI's Whisper API
        with open(temp_file, "rb") as audio_file:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        
        # Clean up temp file
        os.remove(temp_file)
        
        return {"text": transcript.text}
        
    except Exception as e:
        logger.error(f"Error in speech-to-text endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/text-to-speech")
async def text_to_speech(message: Message, background_tasks: BackgroundTasks):
    try:
        # Generate speech using OpenAI's TTS API
        response = await client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=message.content
        )
        
        # Create a temporary file to store the audio
        temp_file = "temp_speech.mp3"
        response.stream_to_file(temp_file)
        
        # Schedule file cleanup after response is sent
        background_tasks.add_task(os.remove, temp_file)
        
        # Return the audio file
        return FileResponse(
            temp_file,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )
        
    except Exception as e:
        logger.error(f"Error in text-to-speech endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 