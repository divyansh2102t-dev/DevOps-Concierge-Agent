import httpx
from backend.tools.key_store import get_key

RENDER_API = "https://api.render.com/v1"


def _headers():
    token = get_key("RENDER_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


async def get_owner_id():
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Render API key not configured. Add it in Settings."}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{RENDER_API}/owners", headers=headers, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    # Return the first owner workspace ID
                    return {"success": True, "owner_id": data[0]["owner"]["id"]}
                return {"success": False, "error": "No owners/workspaces found in Render account."}
            return {"success": False, "error": f"Failed to get owner: {resp.text}", "status": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def create_render_service(service_name, github_repo, env_vars=None, project_dir=None):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Render API key not configured. Add it in Settings."}

    # 1. Retrieve Render Workspace Owner ID
    owner_res = await get_owner_id()
    if not owner_res.get("success"):
        return owner_res
    owner_id = owner_res["owner_id"]

    # 2. Format environment variables for Render API
    # Render expects: [{"key": "NAME", "value": "VAL"}]
    formatted_env_vars = []
    if env_vars:
        for k, v in env_vars.items():
            if v:
                formatted_env_vars.append({"key": k, "value": str(v)})

    # Detect the environment from the project directory
    import os
    env_type = "python"
    build_cmd = "pip install -r requirements.txt"
    start_cmd = "python main.py"

    if project_dir and os.path.exists(project_dir) and os.path.isdir(project_dir):
        # Check for Node (package.json)
        if os.path.exists(os.path.join(project_dir, "package.json")):
            env_type = "node"
            build_cmd = "npm install && npm run build"
            start_cmd = "npm start"
        # Check for sub-folder backend (like our own devops agent workspace)
        elif os.path.exists(os.path.join(project_dir, "backend", "requirements.txt")):
            env_type = "python"
            build_cmd = "pip install -r backend/requirements.txt"
            start_cmd = "python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
        # Check for generic Python (requirements.txt)
        elif os.path.exists(os.path.join(project_dir, "requirements.txt")) or os.path.exists(os.path.join(project_dir, "main.py")):
            env_type = "python"
            build_cmd = "pip install -r requirements.txt"
            start_cmd = "python main.py"

    # 3. Formulate Render Web Service creation payload
    payload = {
        "type": "web_service",
        "name": service_name,
        "ownerId": owner_id,
        "repo": github_repo,
        "branch": "main",
        "serviceDetails": {
            "env": env_type,
            "plan": "free",
            "envVars": formatted_env_vars,
            "envSpecificDetails": {
                "buildCommand": build_cmd,
                "startCommand": start_cmd
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            # Check if a service with the target name already exists, and if so, trigger a rebuild/redeploy
            try:
                list_resp = await client.get(f"{RENDER_API}/services", headers=headers, params={"limit": 100}, timeout=15.0)
                if list_resp.status_code == 200:
                    services = list_resp.json()
                    existing_service = None
                    for item in services:
                        srv = item.get("service") if isinstance(item, dict) else item
                        if srv and srv.get("name") == service_name:
                            existing_service = srv
                            break
                    
                    if existing_service:
                        service_id = existing_service["id"]
                        # Trigger deploy for the existing service
                        deploy_resp = await client.post(
                            f"{RENDER_API}/services/{service_id}/deploys",
                            headers=headers,
                            json={"clearCache": "clear"},
                            timeout=15.0
                        )
                        if deploy_resp.status_code in (200, 201, 202):
                            # Try to extract the URL safely
                            live_url = existing_service.get("url")
                            if not live_url:
                                live_url = existing_service.get("serviceDetails", {}).get("url", "")
                            if not live_url:
                                live_url = f"https://{service_name}.onrender.com"
                                
                            return {
                                "success": True,
                                "service_id": service_id,
                                "name": existing_service.get("name", service_name),
                                "url": live_url,
                                "status": "redeploying",
                                "deploy_url": f"https://dashboard.render.com/web/{service_id}"
                            }
            except Exception as check_err:
                print(f"Non-fatal error checking existing services: {check_err}")

            resp = await client.post(f"{RENDER_API}/services", json=payload, headers=headers, timeout=20.0)
            
            # If name is already in use, automatically append a random 4-character suffix and retry
            if resp.status_code == 422 and "already in use" in resp.text:
                import random
                import string
                suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
                payload["name"] = f"{service_name}-{suffix}"
                resp = await client.post(f"{RENDER_API}/services", json=payload, headers=headers, timeout=20.0)

            if resp.status_code in (200, 201, 202):
                data = resp.json()
                service_id = data.get("id")
                srv_details = data.get("serviceDetails", {})
                return {
                    "success": True,
                    "service_id": service_id,
                    "name": data.get("name"),
                    "url": data.get("url"),
                    "status": data.get("status", "created"),
                    "deploy_url": f"https://dashboard.render.com/web/{service_id}"
                }
            return {"success": False, "error": resp.text, "status": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}


async def get_render_deployment_status(service_id):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Render API key not configured."}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{RENDER_API}/services/{service_id}", headers=headers, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                # Check if there is an active deploy or check general status
                return {
                    "success": True,
                    "status": data.get("status"), # active, suspended, etc.
                    "url": data.get("url"),
                    "name": data.get("name"),
                    "updatedAt": data.get("updatedAt")
                }
            return {"success": False, "error": resp.text, "status": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
