import os
import uuid
import base64
import re
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import json
import asyncio
from backend.database import (
    create_conversation, list_conversations, get_conversation,
    update_conversation, delete_conversation, add_message,
    get_messages, search_conversations
)
from backend.agent.orchestrator import run_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = "gemini-2.5-flash"
    user_memory: Optional[str] = None
    images: Optional[List[str]] = None  # List of base64 data URLs or strings


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    model: Optional[str] = None


def save_b64_image(base64_str: str) -> str:
    if "," in base64_str:
        header, base64_str = base64_str.split(",", 1)
        match = re.search(r"data:([^;]+);base64", header)
        mime_type = match.group(1) if match else "image/png"
    else:
        mime_type = "image/png"
        
    ext = "png"
    if "jpeg" in mime_type or "jpg" in mime_type:
        ext = "jpg"
    elif "gif" in mime_type:
        ext = "gif"
    elif "webp" in mime_type:
        ext = "webp"
        
    img_data = base64.b64decode(base64_str)
    filename = f"{uuid.uuid4()}.{ext}"
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(backend_dir, "..", "generated_media")
    os.makedirs(media_dir, exist_ok=True)
    
    local_path = os.path.join(media_dir, filename)
    with open(local_path, "wb") as f:
        f.write(img_data)
        
    return f"/api/media/{filename}"


def save_training_turn(user_msg: str, assistant_msg: str, user_memory: str = None):
    try:
        import json
        from backend.agent.system_prompt import SYSTEM_PROMPT
        
        sys_prompt = SYSTEM_PROMPT
        if user_memory:
            sys_prompt += f"\n\nUSER PERSONALIZATION & MEMORY:\n{user_memory}\nUse this memory to adapt your tone, style, and recall past decisions to talk to the user naturally."
            
        turn = {
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ]
        }
        
        file_path = "agent_training_data.jsonl"
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(turn, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Error saving training turn: {e}")


@router.post("")
async def send_message(req: ChatRequest):
    conv_id = req.conversation_id
    if not conv_id:
        conv_id = await create_conversation(req.model)

    tool_data = None
    if req.images:
        image_urls = []
        for img_b64 in req.images:
            try:
                url = save_b64_image(img_b64)
                image_urls.append(url)
            except Exception as e:
                print(f"Error saving base64 image: {e}")
        if image_urls:
            tool_data = {"images": image_urls}

    user_msg = req.message
    if not user_msg.strip() and req.images:
        user_msg = "Please analyze the attached image and solve/explain the problem shown in it."

    await add_message(conv_id, "user", user_msg, tool_data=tool_data)

    async def event_stream():
        from backend.agent.terminal_manager import manager
        # Initialize active agent status
        manager.set_active_agents([{"name": "DevOps Concierge", "status": "active"}])
        
        full_response = ""
        try:
            async for event in run_agent(conv_id, user_msg, req.model, user_memory=req.user_memory):
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"
                if event.get("type") == "text":
                    full_response += event.get("content", "")
                elif event.get("type") == "done":
                    if full_response:
                        # Clean out any XML-based tool call tags from the saved message
                        clean_response = re.sub(r"<call:\w+>[\s\S]*?</call:\w+>", "", full_response).strip()
                        await add_message(conv_id, "assistant", clean_response)
                        save_training_turn(user_msg, clean_response, req.user_memory)
                    if event.get("title"):
                        await update_conversation(conv_id, title=event["title"])
        except Exception as e:
            error_event = json.dumps({"type": "error", "content": str(e)})
            yield f"data: {error_event}\n\n"
        finally:
            # Guarantee agent status is cleared on stream close/abort/error
            manager.set_active_agents([])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Conversation-Id": conv_id,
        }
    )


@router.get("/sessions")
async def get_sessions(q: Optional[str] = None):
    if q:
        return await search_conversations(q)
    return await list_conversations()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    conv = await get_conversation(session_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    messages = await get_messages(session_id)
    return messages


@router.put("/sessions/{session_id}")
async def update_session(session_id: str, update: ConversationUpdate):
    await update_conversation(session_id, title=update.title, model=update.model)
    return {"status": "updated"}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    from backend.agent.orchestrator import set_agent_state
    from backend.agent.terminal_manager import manager
    set_agent_state(session_id, "stopped")
    manager.kill_all_active_sessions()
    await delete_conversation(session_id)
    return {"status": "deleted"}


@router.get("/terminals")
async def get_terminals():
    from backend.agent.terminal_manager import manager
    return {
        "terminals": manager.get_all_sessions(),
        "active_agents": manager.get_active_agents()
    }


@router.post("/terminals/clear")
async def clear_terminals():
    from backend.agent.terminal_manager import manager
    manager.clear_history()
    return {"status": "cleared"}


@router.post("/terminals/{cmd_id}/kill")
async def kill_terminal(cmd_id: str):
    from backend.agent.terminal_manager import manager
    killed = manager.kill_session(cmd_id)
    if killed:
        return {"status": "killed", "command_id": cmd_id}
    return {"status": "not_running", "command_id": cmd_id}


@router.post("/agent/{conversation_id}/pause")
async def pause_agent(conversation_id: str):
    from backend.agent.orchestrator import set_agent_state
    set_agent_state(conversation_id, "paused")
    return {"status": "paused", "conversation_id": conversation_id}


@router.post("/agent/{conversation_id}/resume")
async def resume_agent(conversation_id: str):
    from backend.agent.orchestrator import set_agent_state
    set_agent_state(conversation_id, "running")
    return {"status": "running", "conversation_id": conversation_id}


@router.post("/agent/{conversation_id}/stop")
async def stop_agent(conversation_id: str):
    from backend.agent.orchestrator import set_agent_state
    from backend.agent.terminal_manager import manager
    set_agent_state(conversation_id, "stopped")
    manager.kill_all_active_sessions()
    return {"status": "stopped", "conversation_id": conversation_id}

