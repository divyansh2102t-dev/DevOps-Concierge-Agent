TOOL_DEFINITIONS = [
    {
        "name": "parse_url",
        "description": "Unified resource reader. Use this to read and extract text from local files (DOCX, PPTX, PDF, Images, TXT) or URLs (including private/authenticated pages like ChatGPT chats or GitHub issues by automatically leveraging your local Chrome/Edge browser sessions).",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The absolute local file path (e.g. C:\\project\\report.docx) or the Web URL to read."
                }
            },
            "required": ["url"]
        },
        "requires_auth": False
    },
    {
        "name": "scaffold_project",
        "description": "Generate a complete Next.js project structure with all necessary config files.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "Name for the project"},
                "output_dir": {"type": "string", "description": "Optional output directory path"}
            },
            "required": ["project_name"]
        },
        "requires_auth": False
    },
    {
        "name": "select_database",
        "description": "Analyze project requirements and recommend the best database. Returns scored recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "requirements_text": {"type": "string", "description": "Text describing the project requirements"}
            },
            "required": ["requirements_text"]
        },
        "requires_auth": False
    },
    {
        "name": "generate_db_config",
        "description": "Generate database connection boilerplate files for the selected database type.",
        "parameters": {
            "type": "object",
            "properties": {
                "db_type": {"type": "string", "enum": ["postgresql", "mongodb", "sqlite", "supabase"]},
                "project_dir": {"type": "string", "description": "Path to the project directory"}
            },
            "required": ["db_type", "project_dir"]
        },
        "requires_auth": False
    },
    {
        "name": "extract_credentials",
        "description": "Extract API keys and environment variables from user-provided text.",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text containing potential API keys or env vars"}
            },
            "required": ["text"]
        },
        "requires_auth": False
    },
    {
        "name": "generate_env_file",
        "description": "Create a secure .env file and .env.example in the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "env_vars": {"type": "object", "description": "Key-value pairs of environment variables"},
                "project_dir": {"type": "string", "description": "Path to the project directory"}
            },
            "required": ["env_vars", "project_dir"]
        },
        "requires_auth": False
    },
    {
        "name": "create_github_repo",
        "description": "Create a new GitHub repository. Requires user authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "repo_name": {"type": "string", "description": "Repository name"},
                "description": {"type": "string", "description": "Repository description"},
                "private": {"type": "boolean", "description": "Whether the repo should be private"}
            },
            "required": ["repo_name"]
        },
        "requires_auth": True
    },
    {
        "name": "push_to_github",
        "description": "Initialize git and push project code to a GitHub repository. Requires user authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_dir": {"type": "string", "description": "Path to the local project"},
                "repo_url": {"type": "string", "description": "GitHub repository clone URL"}
            },
            "required": ["project_dir", "repo_url"]
        },
        "requires_auth": True
    },
    {
        "name": "deploy_to_vercel",
        "description": "Create a Vercel project linked to a GitHub repo and trigger deployment. Requires authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "Vercel project name"},
                "github_repo": {"type": "string", "description": "GitHub repo in 'owner/name' format"},
                "framework": {"type": "string", "description": "Framework type", "default": "nextjs"},
                "root_directory": {"type": "string", "description": "Optional subdirectory that contains the frontend code (e.g. 'frontend')"}
            },
            "required": ["project_name", "github_repo"]
        },
        "requires_auth": True
    },
    {
        "name": "deploy_to_render",
        "description": "Deploy a Python/FastAPI backend service to Render. Requires user authorization.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "A unique name for your Render service"},
                "github_repo": {"type": "string", "description": "GitHub repository HTML URL (e.g. https://github.com/owner/name)"},
                "env_vars": {"type": "object", "description": "Optional environment variables key-value pairs to inject"}
            },
            "required": ["service_name", "github_repo"]
        },
        "requires_auth": True
    },
    {
        "name": "get_render_status",
        "description": "Retrieve the deployment and hosting status of a Render service.",
        "parameters": {
            "type": "object",
            "properties": {
                "service_id": {"type": "string", "description": "The unique ID of the Render service"}
            },
            "required": ["service_id"]
        },
        "requires_auth": False
    },
    {
        "name": "set_vercel_env",
        "description": "Inject environment variables into a Vercel project.",
        "parameters": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Vercel project ID"},
                "env_vars": {"type": "object", "description": "Key-value pairs of env vars"}
            },
            "required": ["project_id", "env_vars"]
        },
        "requires_auth": True
    },
    {
        "name": "generate_docs",
        "description": "Generate business handover documentation: PPTX presentation, DOCX report, and Mermaid diagrams.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content_data": {
                    "type": "object",
                    "description": "Structured content with 'slides', 'sections', and 'diagram' keys"
                },
                "output_dir": {"type": "string", "description": "Directory to save generated files"}
            },
            "required": ["title", "content_data", "output_dir"]
        },
        "requires_auth": False
    },
    {
        "name": "connect_mcp_server",
        "description": "Connect to a Model Context Protocol server for extended capabilities like filesystem access, database queries, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "server_url": {"type": "string", "description": "MCP server URL or command"},
                "server_type": {"type": "string", "enum": ["stdio", "sse", "http"], "description": "Connection type"}
            },
            "required": ["server_url", "server_type"]
        },
        "requires_auth": False
    },
    {
        "name": "generate_devops_config",
        "description": "Generate industry-standard, production-ready DevOps configurations for Docker, AWS, Kafka, Kubernetes, and CI/CD pipelines in the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "config_type": {
                    "type": "string",
                    "enum": ["docker", "kubernetes", "aws", "cicd"],
                    "description": "Type of DevOps configuration to generate"
                },
                "project_dir": {
                    "type": "string",
                    "description": "Path to the local project directory"
                },
                "params": {
                    "type": "object",
                    "description": "Optional parameters: app_name, port, db_type, aws_region, ecr_registry, kafka_topic"
                }
            },
            "required": ["config_type", "project_dir"]
        },
        "requires_auth": False
    },
    {
        "name": "run_terminal_command",
        "description": "Run a terminal command inside your project directory. For persistent dev servers (like npm run dev, next dev, or start http://localhost:3000), set run_in_background to true so the tool returns immediately.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to run"},
                "working_dir": {"type": "string", "description": "The path to the project directory where the command should run"},
                "run_in_background": {"type": "boolean", "description": "Set to true for starting persistent local servers or opening browser urls so the tool returns immediately."}
            },
            "required": ["command", "working_dir"]
        },
        "requires_auth": True
    },
    {
        "name": "read_project_file",
        "description": "Read the contents of a file within the project directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "The relative or absolute path of the file to read"}
            },
            "required": ["file_path"]
        },
        "requires_auth": False
    },
    {
        "name": "write_project_file",
        "description": "Write or overwrite a file within the project directory. Requires user approval.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "The relative or absolute path of the file to write"},
                "content": {"type": "string", "description": "The text content to write to the file"}
            },
            "required": ["file_path", "content"]
        },
        "requires_auth": True
    },
    {
        "name": "web_search",
        "description": "Search the web (Google/DuckDuckGo) in real-time to answer questions, find information, verify facts, or retrieve up-to-date details. Returns organic search results containing titles, links, and snippets. Use this to prevent hallucinations or when you need online details.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up (e.g. 'Divyansh Tiwari portfolio' or 'latest nextjs features')"
                }
            },
            "required": ["query"]
        },
        "requires_auth": False
    },
    {
        "name": "check_credentials",
        "description": "Query the status of local credentials and API keys (such as GITHUB_TOKEN, VERCEL_TOKEN, RENDER_TOKEN, and NEON_API_KEY). Returns a summary of which keys are configured and which are missing, without exposing their actual secret values.",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "requires_auth": False
    }
]


import os
import subprocess
import asyncio

def _get_user_projects_dir():
    from backend.tools.key_store import get_key
    configured_dir = get_key("PROJECTS_DIR")
    if configured_dir:
        return os.path.normpath(configured_dir)
    return os.path.join(os.path.expanduser("~"), "DevOps-Concierge-Projects")

def _sanitize_path(path):
    if not path:
        return _get_user_projects_dir()
    
    # Normalize the path
    norm_path = os.path.normpath(path)
    
    # If it is absolute, check if it is inside the DevOps-Concierge-Agent repository.
    # If it is inside the repo, we redirect it to be relative to the projects directory.
    if os.path.isabs(norm_path):
        repo_dir = "DevOps-Concierge-Agent"
        if repo_dir in norm_path:
            parts = norm_path.split(repo_dir)
            rel_part = parts[-1].lstrip("\\/")
            if not rel_part:
                return _get_user_projects_dir()
            return os.path.join(_get_user_projects_dir(), rel_part)
        return norm_path
    
    # For relative paths, append them directly to the user projects directory to preserve sub-folder structures!
    return os.path.join(_get_user_projects_dir(), norm_path)

async def _run_terminal_command(command, working_dir, run_in_background=False):
    sanitized_dir = _sanitize_path(working_dir)
    os.makedirs(sanitized_dir, exist_ok=True)
    
    # --- Auto-Package Manager Optimization ---
    import shutil
    has_pnpm = shutil.which("pnpm") is not None
    has_bun = shutil.which("bun") is not None
    
    if not has_pnpm and not has_bun and "npm" in command:
        try:
            # Auto-install pnpm globally once to unlock 10x speeds!
            install_proc = await asyncio.create_subprocess_shell(
                "npm install -g pnpm",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(install_proc.communicate(), timeout=20.0)
            if shutil.which("pnpm") or install_proc.returncode == 0:
                has_pnpm = True
        except Exception:
            pass
            
    # Translate command to the fastest manager
    if has_bun:
        if command.startswith("npm install") or command.startswith("npm ci"):
            command = command.replace("npm install", "bun install").replace("npm ci", "bun install")
        elif command.startswith("npm run "):
            command = command.replace("npm run ", "bun run ")
        elif command.startswith("npx "):
            command = command.replace("npx ", "bunx ")
    elif has_pnpm:
        if command.startswith("npm install") or command.startswith("npm ci"):
            command = command.replace("npm install", "pnpm install").replace("npm ci", "pnpm install")
        elif command.startswith("npm run "):
            command = command.replace("npm run ", "pnpm ")
        elif command.startswith("npx "):
            command = command.replace("npx ", "pnpm dlx ")
    # ------------------------------------------

    # Start terminal session in tracker
    from backend.agent.terminal_manager import manager
    cmd_id = manager.start_session(command, sanitized_dir)
    
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=sanitized_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        manager.update_session(cmd_id, pid=process.pid)
        manager.set_process(cmd_id, process)  # Store handle for on-demand kill
        
        if run_in_background:
            # Consume streams in background so it updates live
            async def consume_bg():
                async def read_out():
                    while True:
                        line = await process.stdout.readline()
                        if not line:
                            break
                        manager.update_session(cmd_id, stdout_chunk=line.decode(errors="ignore"))
                async def read_err():
                    while True:
                        line = await process.stderr.readline()
                        if not line:
                            break
                        manager.update_session(cmd_id, stderr_chunk=line.decode(errors="ignore"))
                await asyncio.gather(read_out(), read_err())
                exit_code = await process.wait()
                manager.complete_session(cmd_id, exit_code)
                
            asyncio.create_task(consume_bg())
            
            return {
                "success": True,
                "status": "running_in_background",
                "message": f"Command started successfully in the background (PID: {process.pid}).",
                "stdout": "Process is running in the background...",
                "stderr": "",
                "command_id": cmd_id
            }
            
        # Synchronous execution: stream line-by-line
        stdout_chunks = []
        stderr_chunks = []
        
        async def read_stdout():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore")
                stdout_chunks.append(decoded)
                manager.update_session(cmd_id, stdout_chunk=decoded)
                
        async def read_stderr():
            while True:
                line = await process.stderr.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore")
                stderr_chunks.append(decoded)
                manager.update_session(cmd_id, stderr_chunk=decoded)

        await asyncio.gather(read_stdout(), read_stderr())
        exit_code = await process.wait()
        
        manager.complete_session(cmd_id, exit_code)
        
        return {
            "success": True,
            "status": "completed",
            "exit_code": exit_code,
            "stdout": "".join(stdout_chunks),
            "stderr": "".join(stderr_chunks),
            "command_id": cmd_id
        }
    except Exception as e:
        manager.complete_session(cmd_id, -1, error=str(e))
        return {"success": False, "error": str(e), "command_id": cmd_id}

def _read_project_file(file_path):
    full_path = _sanitize_path(file_path)
    if not os.path.exists(full_path):
        return {"success": False, "error": f"File not found: {file_path}"}
    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _write_project_file(file_path, content):
    full_path = _sanitize_path(file_path)
    try:
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Successfully wrote file: {os.path.basename(full_path)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def _check_credentials():
    from backend.tools.key_store import list_keys
    try:
        keys = list_keys()
        summary = {k: v.get("configured", False) for k, v in keys.items()}
        return {"success": True, "credentials": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}

TOOL_MAP = {}


def register_tools():
    from backend.tools.url_parser import parse_url
    from backend.tools.scaffolder import scaffold_nextjs, add_file_to_project
    from backend.tools.db_selector import select_database, generate_db_files
    from backend.tools.credential_manager import extract_env_vars, generate_env_file
    from backend.tools.github_tool import create_repository, push_to_github
    from backend.tools.vercel_tool import create_project, set_env_vars, trigger_deployment
    from backend.tools.render_tool import create_render_service, get_render_deployment_status
    from backend.tools.doc_generator import generate_all_docs
    from backend.agent.mcp_client import connect_mcp
    from backend.tools.devops_tool import generate_devops_config
    from backend.tools.web_search import web_search

    TOOL_MAP["parse_url"] = lambda **kw: parse_url(kw["url"])
    TOOL_MAP["scaffold_project"] = lambda **kw: scaffold_nextjs(kw["project_name"], _sanitize_path(kw.get("output_dir")))
    TOOL_MAP["select_database"] = lambda **kw: select_database(kw["requirements_text"])
    TOOL_MAP["generate_db_config"] = lambda **kw: generate_db_files(kw["db_type"], _sanitize_path(kw["project_dir"]))
    TOOL_MAP["extract_credentials"] = lambda **kw: extract_env_vars(kw["text"])
    TOOL_MAP["generate_env_file"] = lambda **kw: generate_env_file(kw["env_vars"], _sanitize_path(kw["project_dir"]))
    TOOL_MAP["create_github_repo"] = lambda **kw: create_repository(kw["repo_name"], kw.get("description", ""), kw.get("private", False))
    TOOL_MAP["push_to_github"] = lambda **kw: push_to_github(_sanitize_path(kw["project_dir"]), kw["repo_url"])
    TOOL_MAP["deploy_to_vercel"] = lambda **kw: create_project(kw["project_name"], kw["github_repo"], kw.get("framework", "nextjs"), kw.get("root_directory"))
    TOOL_MAP["deploy_to_render"] = lambda **kw: create_render_service(kw["service_name"], kw["github_repo"], kw.get("env_vars"))
    TOOL_MAP["get_render_status"] = lambda **kw: get_render_deployment_status(kw["service_id"])
    TOOL_MAP["set_vercel_env"] = lambda **kw: set_env_vars(kw["project_id"], kw["env_vars"])
    TOOL_MAP["generate_docs"] = lambda **kw: generate_all_docs(kw["title"], kw["content_data"], _sanitize_path(kw.get("output_dir")))
    TOOL_MAP["connect_mcp_server"] = lambda **kw: connect_mcp(kw["server_url"], kw["server_type"])
    TOOL_MAP["generate_devops_config"] = lambda **kw: generate_devops_config(kw["config_type"], _sanitize_path(kw["project_dir"]), kw.get("params"))
    TOOL_MAP["run_terminal_command"] = lambda **kw: _run_terminal_command(kw["command"], kw["working_dir"], kw.get("run_in_background", False))
    TOOL_MAP["read_project_file"] = lambda **kw: _read_project_file(kw["file_path"])
    TOOL_MAP["write_project_file"] = lambda **kw: _write_project_file(kw["file_path"], kw["content"])
    TOOL_MAP["web_search"] = lambda **kw: web_search(kw["query"])
    TOOL_MAP["check_credentials"] = lambda **kw: _check_credentials()


def get_tool(name):
    if not TOOL_MAP:
        register_tools()
    return TOOL_MAP.get(name)


def get_tool_def(name):
    for t in TOOL_DEFINITIONS:
        if t["name"] == name:
            return t
    return None


def requires_authorization(name):
    t = get_tool_def(name)
    return t.get("requires_auth", False) if t else False
