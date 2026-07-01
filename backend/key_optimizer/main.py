import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Ensure parent directories are in sys.path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.key_optimizer.scheduler import route_request, report_success, report_failure, get_scheduler_metrics
from backend.key_optimizer.excel_logger import excel_writer_worker, queue_log

app = FastAPI(
    title="KeyOptimus API Key Router",
    description="A highly efficient, deterministic scheduler microservice for load balancing and optimizing LLM provider API keys.",
    version="1.0.0"
)

# ── REQUEST/RESPONSE SCHEMAS ──
class RouteRequest(BaseModel):
    task_type: Optional[str] = "text"
    session_id: Optional[str] = "N/A"

class SuccessReport(BaseModel):
    key_value: str
    provider: str
    model: str
    tokens_used: Optional[int] = 0
    elapsed_time: Optional[float] = 0.0
    session_id: Optional[str] = "N/A"

class FailureReport(BaseModel):
    key_value: str
    provider: str
    model: str
    error_message: str
    session_id: Optional[str] = "N/A"

# ── STARTUP & SHUTDOWN EVENTS ──
background_tasks = []

@app.on_event("startup")
async def startup_event():
    """Initializes the background Excel logger task on startup."""
    print("[KeyOptimus] Initializing KeyOptimus microservice...")
    # Start the async Excel writer background worker
    worker_task = asyncio.create_task(excel_writer_worker())
    background_tasks.append(worker_task)
    
    # Log startup event
    queue_log(
        session_id="SYSTEM",
        action="STARTUP",
        provider="SYSTEM",
        key_label="SYSTEM",
        model="SYSTEM",
        task_type="system",
        status="SUCCESS",
        error_msg="KeyOptimus microservice successfully initialized and running on port 8005"
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleans up background tasks on shutdown."""
    print("[KeyOptimus] Shutting down KeyOptimus microservice...")
    for task in background_tasks:
        task.cancel()
    
    # Wait briefly for tasks to cancel
    await asyncio.sleep(0.5)

# ── ENDPOINTS ──

@app.post("/route", summary="Request the optimal API key and model for a task.")
async def api_route_request(req: RouteRequest):
    """
    Evaluates the request task type and returns the optimal key, model, and provider
    using deterministic load balancing, capability alignment, and wastage prevention.
    """
    result = route_request(task_type=req.task_type, session_id=req.session_id)
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error"))
    return result

@app.post("/report_success", summary="Report successful request execution to update rate-limit counters.")
async def api_report_success(report: SuccessReport):
    """
    Registers a successful API request, updates tokens/RPM/RPD states,
    and logs the execution metadata to the persistent Excel sheet.
    """
    report_success(
        key_val=report.key_value,
        provider=report.provider,
        model=report.model,
        tokens_used=report.tokens_used,
        elapsed_time=report.elapsed_time,
        session_id=report.session_id
    )
    return {"status": "success", "message": "Metrics updated successfully."}

@app.post("/report_failure", summary="Report API failure to trigger model-swapping or key quarantine.")
async def api_report_failure(report: FailureReport):
    """
    Registers an API failure, decides whether to swap model on same key or quarantine key,
    and updates metrics / Excel logs accordingly.
    """
    decision = report_failure(
        key_val=report.key_value,
        provider=report.provider,
        model=report.model,
        error_message=report.error_message,
        session_id=report.session_id
    )
    return {
        "status": "success",
        "decision": decision
    }

@app.get("/metrics", summary="Retrieve real-time metrics and quotas for all configured keys.")
async def api_get_metrics():
    """
    Returns a structured status list of all keys, their active RPM/RPD/TPM usage,
    and quarantine statuses for front-end dashboards.
    """
    return get_scheduler_metrics()

import asyncio

if __name__ == "__main__":
    # Start the service locally on port 8005
    uvicorn.run("main:app", host="127.0.0.1", port=8005, reload=True)
