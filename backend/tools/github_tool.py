import httpx
import subprocess
import os
from backend.tools.key_store import get_key


async def create_repository(repo_name, description="", private=True):
    token = get_key("GITHUB_TOKEN")
    if not token:
        return {"success": False, "error": "GitHub token not configured. Add it in Settings."}

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.github.com/user/repos",
            json={
                "name": repo_name,
                "description": description,
                "private": True,
                "auto_init": False
            },
            headers=headers
        )

    if resp.status_code == 201:
        data = resp.json()
        return {
            "success": True,
            "repo_url": data["html_url"],
            "clone_url": data["clone_url"],
            "full_name": data["full_name"]
        }

    return {"success": False, "error": resp.text, "status": resp.status_code}


def push_to_github(project_dir, repo_url):
    try:
        token = get_key("GITHUB_TOKEN")
        if not token:
            return {"success": False, "error": "GitHub Personal Access Token not configured. Please configure it in Settings."}

        # Inject GITHUB_TOKEN into repo_url if it's an HTTPS URL to allow authentication in subprocess
        authenticated_url = repo_url
        if repo_url.startswith("https://"):
            authenticated_url = repo_url.replace("https://", f"https://{token}@")

        # 1. Initialize git if needed
        subprocess.run(["git", "init"], cwd=project_dir, capture_output=True, text=True)
        
        # 2. Check if remote origin already exists
        check_remote = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_dir, capture_output=True, text=True
        )
        
        cmds = [
            ["git", "add", "."],
            ["git", "commit", "-m", "Initial commit by DevOps Concierge Agent"],
            ["git", "branch", "-M", "main"],
        ]
        
        if check_remote.returncode == 0:
            # Remote origin exists, update it to authenticated_url
            cmds.append(["git", "remote", "set-url", "origin", authenticated_url])
        else:
            # Remote origin does not exist, add it
            cmds.append(["git", "remote", "add", "origin", authenticated_url])
            
        cmds.append(["git", "push", "-u", "origin", "main"])

        for cmd in cmds:
            result = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                err = result.stderr.lower()
                # Ignore harmless warnings/messages
                if "nothing to commit" in err or "up-to-date" in err or "no changes added" in err:
                    continue
                # Mask token in error message if present to prevent leaks
                err_msg = result.stderr
                if token in err_msg:
                    err_msg = err_msg.replace(token, "******")
                return {"success": False, "error": err_msg, "command": " ".join(cmd).replace(token, "******")}

        return {"success": True, "message": f"Code pushed to {repo_url}"}
    except Exception as e:
        # Mask token in exception message as well
        err_msg = str(e)
        token = get_key("GITHUB_TOKEN")
        if token and token in err_msg:
            err_msg = err_msg.replace(token, "******")
        return {"success": False, "error": err_msg}


async def get_user_info():
    token = get_key("GITHUB_TOKEN")
    if not token:
        return None
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.github.com/user", headers=headers)
    if resp.status_code == 200:
        return resp.json()
    return None
