from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.tools.key_store import set_key, get_key, delete_key, list_keys, VALID_KEY_NAMES

router = APIRouter()

AVAILABLE_MODELS = [
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "tier": "free", "default": True},
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "tier": "free", "default": False},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "tier": "pro", "default": False},
]


class KeyInput(BaseModel):
    name: str
    value: str


@router.get("/keys")
async def get_keys():
    return list_keys()


@router.post("/keys")
async def add_key(key_input: KeyInput):
    try:
        set_key(key_input.name, key_input.value)
        return {"status": "saved", "name": key_input.name}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/keys/{key_name}")
async def remove_key(key_name: str):
    if delete_key(key_name):
        return {"status": "deleted", "name": key_name}
    raise HTTPException(status_code=404, detail="Key not found")


class QueueKeyInput(BaseModel):
    provider: str
    label: str
    value: str


@router.post("/keys/queue")
async def add_queue_key(key_input: QueueKeyInput):
    import uuid
    import json
    
    current_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(current_val)
    except Exception:
        queue = []
        
    new_key = {
        "id": str(uuid.uuid4()),
        "provider": key_input.provider,
        "label": key_input.label,
        "value": key_input.value
    }
    queue.append(new_key)
    set_key("API_KEYS_QUEUE", json.dumps(queue))
    return {"status": "added", "key": {
        "id": new_key["id"],
        "provider": new_key["provider"],
        "label": new_key["label"]
    }}


@router.delete("/keys/queue/{key_id}")
async def remove_queue_key(key_id: str):
    import json
    
    current_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(current_val)
    except Exception:
        queue = []
        
    initial_len = len(queue)
    queue = [item for item in queue if item.get("id") != key_id]
    
    if len(queue) == initial_len:
        raise HTTPException(status_code=404, detail="Key not found in queue")
        
    set_key("API_KEYS_QUEUE", json.dumps(queue))
    return {"status": "deleted", "id": key_id}


@router.post("/keys/{key_name}/toggle")
async def toggle_core_key(key_name: str):
    import json
    if key_name not in VALID_KEY_NAMES:
        raise HTTPException(status_code=400, detail="Invalid key name")
        
    disabled_keys_val = get_key("DISABLED_KEYS") or "[]"
    try:
        disabled_keys = json.loads(disabled_keys_val)
    except Exception:
        disabled_keys = []
        
    if key_name in disabled_keys:
        disabled_keys.remove(key_name)
        status = "enabled"
    else:
        disabled_keys.append(key_name)
        status = "disabled"
        
    set_key("DISABLED_KEYS", json.dumps(disabled_keys))
    return {"status": status, "name": key_name}


@router.post("/keys/queue/{key_id}/toggle")
async def toggle_queue_key(key_id: str):
    import json
    current_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(current_val)
    except Exception:
        queue = []
        
    found = False
    status = "enabled"
    for item in queue:
        if item.get("id") == key_id:
            found = True
            is_enabled = item.get("enabled", True)
            item["enabled"] = not is_enabled
            status = "disabled" if is_enabled else "enabled"
            break
            
    if not found:
        raise HTTPException(status_code=404, detail="Key not found in queue")
        
    set_key("API_KEYS_QUEUE", json.dumps(queue))
    return {"status": status, "id": key_id}


@router.get("/models")
async def get_models():
    gemini_key = get_key("GEMINI_API_KEY")
    models = []
    
    # 1. Add Cloud Gemini Models
    for m in AVAILABLE_MODELS:
        model = dict(m)
        if m["tier"] == "pro":
            model["available"] = bool(gemini_key)
            model["note"] = "Requires Google AI Pro subscription" if not gemini_key else None
        else:
            model["available"] = True
        models.append(model)
        
    # 2. Add Local Ollama Models dynamically
    RECOMMENDED_LOCAL_MODELS = [
        {"id": "qwen2.5-coder:1.5b", "name": "Qwen 2.5 Coder 1.5B", "badge": "Local LLM"},
        {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder 7B", "badge": "Local LLM"},
        {"id": "llava:latest", "name": "LLaVA 7B", "badge": "Local Vision"}
    ]
    
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if r.status_code == 200:
            data = r.json()
            local_list = data.get("models", [])
            installed_names = {item.get("name") for item in local_list}
            
            # Add already installed models
            for item in local_list:
                name = item.get("name")
                clean_name = name[:-7] if name.endswith(":latest") else name
                
                # Check if it is a vision model
                is_vision = any(x in clean_name.lower() for x in ["llava", "vision", "vl", "minicpm"])
                badge = "Local Vision" if is_vision else "Local LLM"
                
                models.append({
                    "id": name,
                    "name": f"💻 {clean_name} ({badge})",
                    "tier": "local",
                    "available": True,
                    "default": False
                })
                
            # Add recommended models that are not yet installed
            for rec in RECOMMENDED_LOCAL_MODELS:
                rec_id = rec["id"]
                rec_id_latest = rec_id if ":" in rec_id else f"{rec_id}:latest"
                
                # If neither the ID nor ID:latest is in the installed set, offer to install it
                if rec_id not in installed_names and rec_id_latest not in installed_names:
                    models.append({
                        "id": rec_id,
                        "name": f"📥 {rec['name']} (Click to Auto-Install)",
                        "tier": "local",
                        "available": True,
                        "default": False
                    })
    except Exception:
        pass
        
    return models


@router.get("/keys/status")
async def keys_status():
    keys = list_keys()
    all_configured = all(v["configured"] for v in keys.values())
    missing = [k for k, v in keys.items() if not v["configured"]]
    return {
        "all_configured": all_configured,
        "missing": missing,
        "keys": keys
    }


class BillingApproval(BaseModel):
    provider: str
    approved: bool


@router.get("/keys/discover")
async def discover_keys():
    raise HTTPException(
        status_code=400,
        detail="Credentials auto-discovery has been permanently disabled by administrator request."
    )


@router.post("/keys/approve-billing")
async def approve_billing(approval: BillingApproval):
    raise HTTPException(
        status_code=400,
        detail="Billing approval is disabled because auto-discovery is disabled."
    )


class SelectFolderResponse(BaseModel):
    success: bool
    path: Optional[str] = None
    error: Optional[str] = None


class DevOpsPushRequest(BaseModel):
    project_dir: str
    repo_name: Optional[str] = None
    private: Optional[bool] = True


class DevOpsDeployRequest(BaseModel):
    github_url: str
    project_name: Optional[str] = None


@router.post("/select-folder", response_model=SelectFolderResponse)
async def select_folder():
    import subprocess
    cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$f = New-Object System.Windows.Forms.OpenFileDialog; "
        "$f.ValidateNames = $false; "
        "$f.CheckFileExists = $false; "
        "$f.CheckPathExists = $true; "
        "$f.FileName = 'Folder Selection.'; "
        "$f.Title = 'Select your DevOps Project Folder'; "
        "if ($f.ShowDialog() -eq 'OK') { Split-Path $f.FileName }"
    )
    try:
        proc = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=60)
        selected_path = proc.stdout.strip()
        if not selected_path:
            return {"success": False, "error": "Folder selection cancelled."}
        return {"success": True, "path": selected_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/devops/push")
async def devops_push(req: DevOpsPushRequest):
    import os
    from backend.tools.github_tool import create_repository, push_to_github
    
    project_dir = os.path.normpath(req.project_dir)
    if not os.path.exists(project_dir) or not os.path.isdir(project_dir):
        return {"success": False, "error": f"Invalid project directory: {project_dir}"}
        
    repo_name = req.repo_name or os.path.basename(project_dir)
    if not repo_name:
        repo_name = "devops-concierge-project"
        
    # 1. Create Repository on GitHub
    repo_res = await create_repository(repo_name, description="Created by DevOps Concierge Agent", private=req.private)
    if not repo_res.get("success"):
        err_msg = str(repo_res.get("error", ""))
        if "already exists" in err_msg.lower() or repo_res.get("status") == 422:
            from backend.tools.github_tool import get_user_info
            user_info = await get_user_info()
            if user_info:
                username = user_info["login"]
                repo_res = {
                    "success": True,
                    "repo_url": f"https://github.com/{username}/{repo_name}",
                    "clone_url": f"https://github.com/{username}/{repo_name}.git"
                }
            else:
                return {"success": False, "error": f"Failed to create GitHub repository (already exists, but couldn't verify owner): {err_msg}"}
        else:
            return {"success": False, "error": f"Failed to create GitHub repository: {err_msg}"}
        
    repo_url = repo_res["clone_url"]
    html_url = repo_res["repo_url"]
    
    # 2. Push local directory to repository
    push_res = push_to_github(project_dir, repo_url)
    if not push_res.get("success"):
        return {
            "success": False, 
            "error": f"Failed to push to GitHub: {push_res.get('error')}",
            "html_url": html_url
        }
        
    return {
        "success": True,
        "message": f"Successfully created and pushed to GitHub!",
        "repo_url": html_url,
        "clone_url": repo_url
    }


@router.post("/devops/deploy/vercel")
async def devops_deploy_vercel(req: DevOpsDeployRequest):
    import re
    from backend.tools.vercel_tool import create_project, trigger_deployment
    
    github_url = req.github_url.strip()
    
    # Parse owner/repo from URL
    match = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?$", github_url)
    if match:
        github_repo = match.group(1)
    else:
        parts = [p for p in github_url.split("/") if p]
        if len(parts) >= 2:
            github_repo = f"{parts[-2]}/{parts[-1].replace('.git', '')}"
        else:
            github_repo = github_url
            
    repo_name = github_repo.split("/")[-1]
    project_name = req.project_name or repo_name
    
    # 1. Create Project on Vercel
    proj_res = await create_project(project_name, github_repo)
    if not proj_res.get("success"):
        return {"success": False, "error": f"Failed to create Vercel project: {proj_res.get('error')}"}
        
    # 2. Trigger Deployment on Vercel
    deploy_res = await trigger_deployment(project_name, github_repo)
    if not deploy_res.get("success"):
        return {
            "success": False,
            "error": f"Vercel project created, but deployment failed: {deploy_res.get('error')}",
            "project_id": proj_res.get("project_id")
        }
        
    return {
        "success": True,
        "message": "Successfully deployed to Vercel!",
        "project_id": proj_res.get("project_id"),
        "url": deploy_res.get("url"),
        "status": deploy_res.get("status")
    }


@router.post("/devops/deploy/render")
async def devops_deploy_render(req: DevOpsDeployRequest):
    from backend.tools.render_tool import create_render_service
    
    github_url = req.github_url.strip()
    parts = [p for p in github_url.split("/") if p]
    repo_name = parts[-1].replace(".git", "") if parts else "render-service"
    service_name = req.project_name or f"{repo_name}-service"
    
    # 1. Create Render Service
    render_res = await create_render_service(service_name, github_url)
    if not render_res.get("success"):
        return {"success": False, "error": f"Failed to create Render service: {render_res.get('error')}"}
        
    return {
        "success": True,
        "message": "Successfully deployed to Render!",
        "service_id": render_res.get("service_id"),
        "url": render_res.get("url"),
        "deploy_url": render_res.get("deploy_url"),
        "status": render_res.get("status")
    }


