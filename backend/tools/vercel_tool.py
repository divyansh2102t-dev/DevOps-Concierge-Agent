import httpx
from backend.tools.key_store import get_key

VERCEL_API = "https://api.vercel.com"


def _headers():
    token = get_key("VERCEL_TOKEN")
    if not token:
        return None
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _create_neon_database(project_name):
    neon_key = get_key("NEON_API_KEY")
    if not neon_key:
        return None
        
    headers = {
        "Authorization": f"Bearer {neon_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    body = {
        "project": {
            "name": f"{project_name}-db",
            "pg_version": 15
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://console.neon.tech/api/v2/projects",
                json=body,
                headers=headers,
                timeout=20.0
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                
                # Check for direct connection URIs
                connection_uris = data.get("connection_uris", [])
                if connection_uris:
                    return connection_uris[0].get("connection_uri")
                
                # Reconstruct fallback connection string if connection_uris not present
                project_data = data.get("project", {})
                roles = data.get("roles", [])
                databases = data.get("databases", [])
                endpoints = data.get("endpoints", [])
                
                host = endpoints[0].get("host") if endpoints else None
                user = roles[0].get("name") if roles else "neondb_owner"
                password = roles[0].get("password") if roles else ""
                dbname = databases[0].get("name") if databases else "neondb"
                
                if host and password:
                    return f"postgresql://{user}:{password}@{host}/{dbname}?sslmode=require"
                
                # Alternate check under "project" payload
                if project_data:
                    proj_endpoints = project_data.get("endpoints", [])
                    proj_host = proj_endpoints[0].get("host") if proj_endpoints else None
                    if proj_host:
                        return f"postgresql://{user}:{password}@{proj_host}/{dbname}?sslmode=require"
        except Exception as e:
            print(f"Neon API Error: {e}")
            return None
    return None


async def create_project(project_name, github_repo, framework="nextjs", root_directory=None):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Vercel token not configured. Add it in Settings."}

    # Automatically create a Neon serverless PostgreSQL database if Neon API Key is configured
    db_url = None
    neon_key = get_key("NEON_API_KEY")
    if neon_key:
        db_url = await _create_neon_database(project_name)

    payload = {
        "name": project_name,
        "gitRepository": {
            "type": "github",
            "repo": github_repo
        },
        "framework": framework
    }
    if root_directory:
        payload["rootDirectory"] = root_directory

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VERCEL_API}/v9/projects",
            json=payload,
            headers=headers
        )

    if resp.status_code in (200, 201):
        data = resp.json()
        project_id = data.get("id")
        
        # If we successfully created a Neon database, inject it as DATABASE_URL on Vercel!
        neon_status = None
        if db_url:
            env_resp = await set_env_vars(project_id, {"DATABASE_URL": db_url})
            if env_resp.get("success"):
                neon_status = "Serverless PostgreSQL database created on Neon and linked to Vercel as DATABASE_URL!"
            else:
                neon_status = f"Database created on Neon, but failed to inject env var: {env_resp.get('error')}"
                
        return {
            "success": True,
            "project_id": project_id,
            "name": data.get("name"),
            "neon_database": "Created & Linked" if db_url else "Not configured",
            "neon_status": neon_status,
            "database_url": db_url[:28] + "..." if db_url else None
        }
    return {"success": False, "error": resp.text, "status": resp.status_code}


async def set_env_vars(project_id, env_vars):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Vercel token not configured"}

    env_list = []
    for key, value in env_vars.items():
        env_list.append({
            "key": key,
            "value": value,
            "target": ["production", "preview", "development"],
            "type": "encrypted"
        })

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VERCEL_API}/v10/projects/{project_id}/env",
            json=env_list,
            headers=headers
        )

    return {
        "success": resp.status_code in (200, 201),
        "status": resp.status_code
    }


async def trigger_deployment(project_name, github_repo, ref="main"):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Vercel token not configured"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{VERCEL_API}/v13/deployments",
            json={
                "name": project_name,
                "gitSource": {
                    "type": "github",
                    "repo": github_repo,
                    "ref": ref
                }
            },
            headers=headers
        )

    if resp.status_code in (200, 201):
        data = resp.json()
        return {
            "success": True,
            "deployment_id": data.get("id"),
            "url": f"https://{data.get('url', '')}",
            "status": data.get("readyState", "BUILDING")
        }
    return {"success": False, "error": resp.text}


async def get_deployment_status(deployment_id):
    headers = _headers()
    if not headers:
        return {"success": False, "error": "Vercel token not configured"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{VERCEL_API}/v13/deployments/{deployment_id}",
            headers=headers
        )

    if resp.status_code == 200:
        data = resp.json()
        return {
            "success": True,
            "status": data.get("readyState"),
            "url": f"https://{data.get('url', '')}"
        }
    return {"success": False, "error": resp.text}
