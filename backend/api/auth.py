from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import asyncio
import uuid

router = APIRouter()

pending_actions: Dict[str, dict] = {}
action_results: Dict[str, asyncio.Event] = {}
action_decisions: Dict[str, bool] = {}


class AuthAction(BaseModel):
    action_id: str
    tool_name: str
    description: str
    details: Optional[dict] = None


async def request_authorization(tool_name, description, details=None, action_id=None):
    if not action_id:
        action_id = str(uuid.uuid4())
    pending_actions[action_id] = {
        "action_id": action_id,
        "tool_name": tool_name,
        "description": description,
        "details": details,
        "status": "pending"
    }
    action_results[action_id] = asyncio.Event()

    try:
        await asyncio.wait_for(action_results[action_id].wait(), timeout=300)
        approved = action_decisions.get(action_id, False)
    except asyncio.TimeoutError:
        approved = False
    finally:
        pending_actions.pop(action_id, None)
        action_results.pop(action_id, None)
        action_decisions.pop(action_id, None)

    return approved


@router.get("/pending")
async def get_pending():
    return list(pending_actions.values())


@router.post("/approve/{action_id}")
async def approve_action(action_id: str):
    if action_id not in pending_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    action_decisions[action_id] = True
    pending_actions[action_id]["status"] = "approved"
    action_results[action_id].set()
    return {"status": "approved"}


@router.post("/deny/{action_id}")
async def deny_action(action_id: str):
    if action_id not in pending_actions:
        raise HTTPException(status_code=404, detail="Action not found")
    action_decisions[action_id] = False
    pending_actions[action_id]["status"] = "denied"
    action_results[action_id].set()
    return {"status": "denied"}
