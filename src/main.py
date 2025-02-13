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
from fastapi.responses import FileResponse, StreamingResponse
import httpx

from database.connection import get_db
from database.models import ChecklistCategory, ChecklistSection, ChecklistItem
from agents.checklist_agent import ChecklistAgent

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client with custom httpx client to avoid proxies issue
http_client = httpx.AsyncClient(
    timeout=60.0,
    follow_redirects=True
)
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=http_client
)

# Initialize the checklist agent
checklist_agent = ChecklistAgent(os.getenv("OPENAI_API_KEY"))

# Add this near other environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Default voice

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

@app.post("/api/chat")
async def chat(message: Message, db: Session = Depends(get_db)):
    try:
        # Get current checklist state for context
        categories = db.query(ChecklistCategory).all()
        checklist_status = []
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
                        item_map[item.description.lower()] = {
                            "id": item.id,
                            "category": category.name,
                            "section": section.name,
                            "is_completed": item.is_completed
                        }
                checklist_status.append(cat_status)

        # Process message using the agent
        result = await checklist_agent.process_message(
            message.content,
            message.session_id or "default",
            "".join(checklist_status),
            item_map
        )

        # Handle item updates if any
        status_message = []
        completed_updates = []
        uncompleted_updates = []

        if "completed_items" in result:
            for item_id in result["completed_items"]:
                try:
                    item = db.query(ChecklistItem).filter(ChecklistItem.id == item_id).first()
                    if item and not item.is_completed:
                        item.is_completed = True
                        item.last_checked = datetime.utcnow()
                        completed_updates.append(f"{item.description} (in {item_map[item.description.lower()]['section']})")
                        logger.info(f"Marked item {item_id} ({item.description}) as completed")
                except Exception as e:
                    logger.error(f"Error updating item {item_id}: {str(e)}")

        if "uncompleted_items" in result:
            for item_id in result["uncompleted_items"]:
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

        # Only add progress if there were updates
        if completed_updates or uncompleted_updates:
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

        # Return response with consistent message structure
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": result.get("message", ""),
                    "type": "message",
                    "timestamp": datetime.utcnow().isoformat()
                },
                # Add image message if present
                *([] if not result.get("image_url") else [{
                    "role": "assistant",
                    "content": result["image_url"],
                    "type": "image",
                    "timestamp": datetime.utcnow().isoformat()
                }]),
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
        logger.error(f"Error in chat endpoint: {str(e)}")
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Error: {str(e)}",
                    "type": "error",
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

@app.post("/api/elevenlabs-tts")
async def elevenlabs_tts(message: Message):
    """Stream audio from ElevenLabs TTS API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
                headers={
                    "Accept": "audio/mpeg",
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "text": message.content,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                return StreamingResponse(
                    response.iter_bytes(),
                    media_type="audio/mpeg",
                    headers={
                        "Content-Disposition": "attachment; filename=speech.mp3"
                    }
                )
            else:
                raise HTTPException(status_code=response.status_code, detail=str(response.text))
                
    except Exception as e:
        logger.error(f"Error in elevenlabs-tts endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 