import json
import asyncio
import inspect
from google import genai
from google.genai import types
from backend.tools.key_store import get_key
from backend.agent.system_prompt import SYSTEM_PROMPT, TITLE_GENERATION_PROMPT, SIMPLE_SYSTEM_PROMPT
from backend.agent.tool_registry import (
    TOOL_DEFINITIONS, get_tool, requires_authorization, register_tools
)
from backend.api.auth import request_authorization
from backend.database import get_messages

# Global dictionary to track active agent states: "running", "paused", "stopped"
AGENT_STATES = {}

def get_agent_state(conversation_id: str) -> str:
    return AGENT_STATES.get(conversation_id, "running")

def set_agent_state(conversation_id: str, state: str):
    AGENT_STATES[conversation_id] = state


def _resolve_model(provider: str, model_name: str) -> str:
    if not model_name or model_name == "auto":
        if provider == "gemini": return "gemini-2.5-flash"
        elif provider == "openai": return "gpt-4o-mini"
        elif provider == "anthropic": return "claude-3-5-haiku-latest"
        elif provider == "groq": return "llama-3.3-70b-versatile"
        elif provider == "huggingface": return "Qwen/Qwen2.5-72B-Instruct"
    return model_name


def _build_gemini_tools():
    tools = []
    for t in TOOL_DEFINITIONS:
        tools.append(types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=t["parameters"]
            )
        ]))
    return tools


async def _generate_title(client, model, message):
    if not model or model == "auto":
        model = "gemini-2.5-flash"
    try:
        response = client.models.generate_content(
            model=model,
            contents=TITLE_GENERATION_PROMPT.format(message=message)
        )
        return response.text.strip()[:50]
    except Exception:
        return message[:30] + "..." if len(message) > 30 else message


def _detect_missing_credential(result, tool_name=""):
    err_str = ""
    if isinstance(result, dict):
        if not result.get("success", True) or "error" in result:
            err_str = str(result.get("error", ""))
        elif "output" in result and ("missing" in str(result["output"]).lower() or "error" in str(result["output"]).lower()):
            err_str = str(result["output"])
    elif isinstance(result, str):
        err_str = result

    err_str_lower = err_str.lower()
    
    if "github_token" in err_str_lower or "github token" in err_str_lower:
        return "GITHUB_TOKEN"
    elif "vercel_token" in err_str_lower or "vercel token" in err_str_lower:
        return "VERCEL_TOKEN"
    elif "gemini_api_key" in err_str_lower or "gemini api key" in err_str_lower or "gemini_key" in err_str_lower:
        return "GEMINI_API_KEY"
    elif "huggingface_api_key" in err_str_lower or "huggingface api key" in err_str_lower or "huggingface_token" in err_str_lower:
        return "HUGGINGFACE_API_KEY"
    elif "render_token" in err_str_lower or "render api key" in err_str_lower:
        return "RENDER_TOKEN"
    elif "neon_api_key" in err_str_lower or "neon key" in err_str_lower:
        return "NEON_API_KEY"
    elif "projects_dir" in err_str_lower or "projects directory" in err_str_lower:
        return "PROJECTS_DIR"
        
    return None


async def _execute_tool(tool_name, arguments):
    register_tools()
    func = get_tool(tool_name)
    if not func:
        return {"error": f"Unknown tool: {tool_name}"}

    try:
        result = func(**arguments)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, (dict, list, str)):
            result = str(result)
        return result
    except Exception as e:
        return {"error": str(e)}


def _collapse_messages(messages):
    """
    Collapses consecutive messages of the same role and ensures
    the last message is a 'user' message to satisfy LLM API constraints.
    """
    system_msgs = [m for m in messages if m.get("role") == "system"]
    chat_msgs = [m for m in messages if m.get("role") != "system"]
    
    collapsed = []
    for msg in chat_msgs:
        role = msg.get("role")
        content = msg.get("content")
        
        # Map any roles other than user to assistant (e.g. system/tool/etc if they slipped through)
        role = "user" if role == "user" else "assistant"
        
        # Skip empty assistant messages if they have no text
        if role == "assistant" and not content and "images" not in msg:
            continue
            
        if not collapsed:
            collapsed.append({"role": role, "content": content, **{k: v for k, v in msg.items() if k not in ["role", "content"]}})
            continue
            
        last = collapsed[-1]
        if last["role"] == role:
            # Merge content
            last_content = last.get("content")
            if isinstance(last_content, list) and isinstance(content, list):
                last["content"] = last_content + content
            elif isinstance(last_content, list):
                if content:
                    last["content"] = last_content + [{"type": "text", "text": str(content)}]
            elif isinstance(content, list):
                if last_content:
                    last["content"] = [{"type": "text", "text": str(last_content)}] + content
                else:
                    last["content"] = content
            else:
                text_last = str(last_content or "")
                text_msg = str(content or "")
                if text_last and text_msg:
                    last["content"] = text_last + "\n\n" + text_msg
                elif text_msg:
                    last["content"] = text_msg
            
            # Merge images
            if "images" in msg:
                if "images" not in last:
                    last["images"] = []
                for img in msg["images"]:
                    if img not in last["images"]:
                        last["images"].append(img)
        else:
            collapsed.append({"role": role, "content": content, **{k: v for k, v in msg.items() if k not in ["role", "content"]}})
            
    # Ensure the last message is a user message
    if collapsed and collapsed[-1]["role"] == "assistant":
        collapsed.append({"role": "user", "content": "Please continue and finalize your response."})
        
    return system_msgs + collapsed


async def _stream_openai(key, history_msgs, model="gpt-4o-mini", system_prompt=SYSTEM_PROMPT):
    import httpx
    import os
    import base64
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(backend_dir, "..", "generated_media")
    
    openai_msgs = []
    for msg in history_msgs:
        role = "user" if msg["role"] == "user" else "assistant"
        
        if msg.get("tool_data") and isinstance(msg["tool_data"], dict) and "images" in msg["tool_data"]:
            content_parts = [{"type": "text", "text": msg["content"]}]
            for img_url in msg["tool_data"]["images"]:
                filename = os.path.basename(img_url)
                local_path = os.path.join(media_dir, filename)
                if os.path.exists(local_path):
                    try:
                        with open(local_path, "rb") as f:
                            b64_data = base64.b64encode(f.read()).decode("utf-8")
                        mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{b64_data}"}
                        })
                    except Exception as img_err:
                        print(f"Error encoding image for OpenAI: {img_err}")
            openai_msgs.append({"role": role, "content": content_parts})
        else:
            openai_msgs.append({"role": role, "content": msg["content"]})
            
    # Collapse consecutive same-role messages
    openai_msgs = _collapse_messages(openai_msgs)
    openai_msgs.insert(0, {"role": "system", "content": system_prompt})
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": openai_msgs,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err_text = await r.aread()
                raise Exception(f"OpenAI Error ({r.status_code}): {err_text.decode()}")
                
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass


async def _stream_groq(key, history_msgs, model="llama-3.3-70b-versatile", system_prompt=SYSTEM_PROMPT):
    import httpx
    groq_msgs = []
    for msg in history_msgs:
        role = "user" if msg["role"] == "user" else "assistant"
        groq_msgs.append({"role": role, "content": msg["content"]})
    
    # Collapse consecutive same-role messages
    groq_msgs = _collapse_messages(groq_msgs)
    groq_msgs.insert(0, {"role": "system", "content": system_prompt})
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": groq_msgs,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err_text = await r.aread()
                raise Exception(f"Groq Error ({r.status_code}): {err_text.decode()}")
                
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass


async def _stream_anthropic(key, history_msgs, model="claude-3-5-haiku-latest", system_prompt=SYSTEM_PROMPT):
    import httpx
    import os
    import base64
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(backend_dir, "..", "generated_media")
    
    anthropic_msgs = []
    for msg in history_msgs:
        role = "user" if msg["role"] == "user" else "assistant"
        
        if msg.get("tool_data") and isinstance(msg["tool_data"], dict) and "images" in msg["tool_data"]:
            content_parts = [{"type": "text", "text": msg["content"]}]
            for img_url in msg["tool_data"]["images"]:
                filename = os.path.basename(img_url)
                local_path = os.path.join(media_dir, filename)
                if os.path.exists(local_path):
                    try:
                        with open(local_path, "rb") as f:
                            b64_data = base64.b64encode(f.read()).decode("utf-8")
                        mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
                        content_parts.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64_data
                            }
                        })
                    except Exception as img_err:
                        print(f"Error encoding image for Anthropic: {img_err}")
            anthropic_msgs.append({"role": role, "content": content_parts})
        else:
            anthropic_msgs.append({"role": role, "content": msg["content"]})
        
    anthropic_msgs = _collapse_messages(anthropic_msgs)
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "system": system_prompt,
        "messages": anthropic_msgs,
        "max_tokens": 4000,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err_text = await r.aread()
                raise Exception(f"Anthropic Error ({r.status_code}): {err_text.decode()}")
                
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("type") == "content_block_delta":
                            content = chunk["delta"].get("text", "")
                            if content:
                                yield content
                    except Exception:
                        pass


async def _stream_huggingface(key, history_msgs, model="Qwen/Qwen2.5-72B-Instruct", system_prompt=SYSTEM_PROMPT):
    import httpx
    hf_msgs = []
    for msg in history_msgs:
        role = "user" if msg["role"] == "user" else "assistant"
        hf_msgs.append({"role": role, "content": msg["content"]})
    
    # Collapse consecutive same-role messages
    hf_msgs = _collapse_messages(hf_msgs)
    hf_msgs.insert(0, {"role": "system", "content": system_prompt})
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": hf_msgs,
        "stream": True
    }
    
    url = "https://router.huggingface.co/v1/chat/completions"
    
    async with httpx.AsyncClient() as client:
        req = client.build_request("POST", url, headers=headers, json=body, timeout=httpx.Timeout(15.0, connect=3.0))
        r = await client.send(req, stream=True)
        
        if r.status_code == 503:
            await r.aclose()
            print(f"[HF Stream] Model {model} is loading. Waiting 5.0s for Hugging Face Hub...")
            import asyncio
            await asyncio.sleep(5.0)
            req = client.build_request("POST", url, headers=headers, json=body, timeout=httpx.Timeout(15.0, connect=3.0))
            r = await client.send(req, stream=True)
            
        if r.status_code != 200:
            err_text = await r.aread()
            await r.aclose()
            raise Exception(f"Hugging Face Error ({r.status_code}): {err_text.decode()}")
            
        try:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
        finally:
            await r.aclose()


async def _stream_ollama(history_msgs, model="qwen2.5-coder:7b", system_prompt=SYSTEM_PROMPT, base_url="http://localhost:11434"):
    import httpx
    import os
    import base64
    import json
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    media_dir = os.path.join(backend_dir, "..", "generated_media")
    
    # Check if the model is a local vision model. Only send images if the model supports them!
    model_lower = model.lower()
    is_vision_model = any(x in model_lower for x in ["llava", "vision", "vl", "minicpm"])
    
    ollama_msgs = []
    
    for msg in history_msgs:
        role = "user" if msg["role"] == "user" else "assistant"
        
        # Check if message has images (only for local vision models)
        images = []
        if is_vision_model and msg.get("tool_data") and isinstance(msg["tool_data"], dict) and "images" in msg["tool_data"]:
            for img_url in msg["tool_data"]["images"]:
                filename = os.path.basename(img_url)
                local_path = os.path.join(media_dir, filename)
                if os.path.exists(local_path):
                    try:
                        with open(local_path, "rb") as f:
                            img_bytes = f.read()
                        encoded = base64.b64encode(img_bytes).decode('utf-8')
                        # Ollama native API expects raw base64 string, without "data:image/...;base64," prefix
                        images.append(encoded)
                    except Exception as img_err:
                        print(f"Error loading image {filename} for Ollama: {img_err}")
        
        msg_obj = {"role": role, "content": msg["content"] or ""}
        if images:
            msg_obj["images"] = images
            
        ollama_msgs.append(msg_obj)
            
    # Collapse consecutive same-role messages
    ollama_msgs = _collapse_messages(ollama_msgs)
    ollama_msgs.insert(0, {"role": "system", "content": system_prompt})
            
    headers = {
        "Content-Type": "application/json"
    }
    body = {
        "model": model,
        "messages": ollama_msgs,
        "stream": True,
        "options": {
            "num_predict": -1,   # -1 enables infinite/unlimited token generation in Ollama
            "temperature": 0.2,  # Lower temperature for much higher precision in code and math
            "num_ctx": 8192      # Expand context window to fully support history and image payloads
        }
    }
    
    url = f"{base_url}/api/chat"
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", url, headers=headers, json=body, timeout=httpx.Timeout(60.0, connect=5.0)) as r:
            if r.status_code != 200:
                err_text = await r.aread()
                raise Exception(f"Ollama Error ({r.status_code}): {err_text.decode()}")
                
            async for line in r.aiter_lines():
                if line.strip():
                    try:
                        chunk = json.loads(line.strip())
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass


async def _pull_ollama_model_stream(model_name: str, base_url: str):
    import json
    import asyncio
    import urllib.request
    
    def run_pull():
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/api/pull",
            data=json.dumps({"name": model_name, "stream": True}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        return urllib.request.urlopen(req)

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, run_pull)
        
        last_pct = -10
        while True:
            line_bytes = await loop.run_in_executor(None, response.readline)
            if not line_bytes:
                break
            
            line = line_bytes.decode("utf-8").strip()
            if not line:
                continue
                
            try:
                data = json.loads(line)
                status = data.get("status", "")
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                
                if total > 0:
                    pct = int(completed / total * 100)
                    if pct >= last_pct + 10:
                        yield f"\n*(📥 Downloading model: {pct}%...)*"
                        last_pct = pct
                elif status:
                    if status == "success":
                        yield f"\n*(✅ Model successfully installed!)*\n\n"
            except Exception:
                pass
    except Exception as e:
        yield f"\n*(⚠️ Error pulling model: {e})*\n\n"


import time

# Global state for concurrent key rotation, load balancing, and self-healing (local fallback)
_key_rotation_counter = 0
_exhausted_keys = {}  # key_value -> expiration_timestamp
_key_lock = asyncio.Lock()

# Candidate pools for Hugging Face multi-model failovers. 
# If a model is overloaded (503/429/connection drop), the orchestrator immediately rotates to the next model using the SAME key.
HF_STAGE_MODELS = {
    "Architect": [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
    ],
    "Developer": [
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
    ],
    "QA Reviewer": [
        "Qwen/Qwen2.5-7B-Instruct",
        "meta-llama/Meta-Llama-3-8B-Instruct",
        "Qwen/Qwen2.5-72B-Instruct",
    ],
    "default": [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
    ]
}

def mark_key_exhausted(key_val, duration=300):
    """Marks an API key as rate-limited or exhausted globally for a set duration (default 5 mins)"""
    if key_val:
        _exhausted_keys[key_val] = time.time() + duration

def is_key_exhausted(key_val):
    """Checks if an API key is currently rate-limited/exhausted"""
    if not key_val:
        return True
    expiry = _exhausted_keys.get(key_val, 0)
    if time.time() < expiry:
        return True
    # Clean up expired key
    if key_val in _exhausted_keys:
        del _exhausted_keys[key_val]
    return False


# ── CUSTOM STREAMING HELPERS FOR MULTI-AGENT STAGES ──
async def _stream_openai_custom(key, messages, model):
    import httpx
    messages = _collapse_messages(messages)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages, "stream": True}
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err = await r.aread()
                raise Exception(f"OpenAI Error: {err.decode()}")
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content: yield content
                    except Exception: pass

async def _stream_huggingface_custom(key, messages, model):
    import httpx
    messages = _collapse_messages(messages)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages, "stream": True}
    url = "https://router.huggingface.co/v1/chat/completions"
    async with httpx.AsyncClient() as client:
        req = client.build_request("POST", url, headers=headers, json=body, timeout=httpx.Timeout(15.0, connect=3.0))
        r = await client.send(req, stream=True)
        
        if r.status_code == 503:
            await r.aclose()
            print(f"[HF Stream Custom] Model {model} is loading. Waiting 5.0s...")
            import asyncio
            await asyncio.sleep(5.0)
            req = client.build_request("POST", url, headers=headers, json=body, timeout=httpx.Timeout(15.0, connect=3.0))
            r = await client.send(req, stream=True)
            
        if r.status_code != 200:
            err = await r.aread()
            await r.aclose()
            raise Exception(f"Hugging Face Error: {err.decode()}")
            
        try:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content: yield content
                    except Exception: pass
        finally:
            await r.aclose()

async def _stream_groq_custom(key, messages, model):
    import httpx
    messages = _collapse_messages(messages)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages, "stream": True}
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err = await r.aread()
                raise Exception(f"Groq Error: {err.decode()}")
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]": break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content: yield content
                    except Exception: pass

async def _stream_anthropic_custom(key, messages, model, system_prompt):
    import httpx
    messages = _collapse_messages(messages)
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    body = {"model": model, "system": system_prompt, "messages": messages, "max_tokens": 4000, "stream": True}
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", "https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=httpx.Timeout(10.0, connect=4.0)) as r:
            if r.status_code != 200:
                err = await r.aread()
                raise Exception(f"Anthropic Error: {err.decode()}")
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    try:
                        chunk = json.loads(data_str)
                        if chunk.get("type") == "content_block_delta":
                            content = chunk["delta"].get("text", "")
                            if content: yield content
                    except Exception: pass


async def _execute_stage(stage_name, task_type, system_instruction, user_prompt, conversation_id, history_msgs):
    """
    Executes a single stage of the multi-agent pipeline.
    Routes the request, handles failovers, and streams the results.
    """
    global _key_rotation_counter
    success = False
    last_error = None
    full_response_parts = []
    
    # Allow up to 3 failover attempts per stage
    for attempt in range(3):
        route = await _get_optimal_route(task_type, conversation_id)
        if route and route.get("success"):
            provider = route["provider"]
            key = route["key"]
            cand_model = _resolve_model(provider, route["model"])
            label = route["label"]
        else:
            # Local fallback scheduling
            all_candidates = []
            hf_primary = get_key("HUGGINGFACE_API_KEY")
            if hf_primary:
                all_candidates.append({"provider": "huggingface", "key": hf_primary, "label": "Primary Hugging Face Key", "model": None})
            primary_key = get_key("GEMINI_API_KEY")
            if primary_key:
                all_candidates.append({"provider": "gemini", "key": primary_key, "label": "Primary Gemini Key", "model": None})
            queue_val = get_key("API_KEYS_QUEUE") or "[]"
            try:
                queue = json.loads(queue_val)
            except Exception:
                queue = []
            for item in queue:
                all_candidates.append({"provider": item.get("provider", "gemini"), "key": item.get("value"), "label": item.get("label", "Backup Key"), "model": None})
                
            active_candidates = [c for c in all_candidates if not is_key_exhausted(c["key"])]
            if not active_candidates:
                active_candidates = all_candidates
            if not active_candidates:
                raise Exception("No active keys available for this stage.")
                
            start_idx = _key_rotation_counter % len(active_candidates)
            _key_rotation_counter += 1
            cand = active_candidates[start_idx]
            provider = cand["provider"]
            key = cand["key"]
            label = cand["label"]
            cand_model = _resolve_model(provider, cand["model"])

        start_time = time.time()
        try:
            if provider == "gemini":
                client = genai.Client(api_key=key)
                contents = [types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)])]
                response = client.models.generate_content(
                    model=cand_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                    )
                )
                if response.candidates:
                    text = "".join([part.text for part in response.candidates[0].content.parts if part.text])
                    yield text
                    full_response_parts.append(text)
                
            elif provider == "openai":
                openai_msgs = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ]
                async with _key_lock:
                    async for chunk in _stream_openai_custom(key, openai_msgs, cand_model):
                        yield chunk
                        full_response_parts.append(chunk)
                    
            elif provider == "anthropic":
                anthropic_msgs = [{"role": "user", "content": user_prompt}]
                async with _key_lock:
                    async for chunk in _stream_anthropic_custom(key, anthropic_msgs, cand_model, system_instruction):
                        yield chunk
                        full_response_parts.append(chunk)
                    
            elif provider == "groq":
                groq_msgs = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ]
                async with _key_lock:
                    async for chunk in _stream_groq_custom(key, groq_msgs, cand_model):
                        yield chunk
                        full_response_parts.append(chunk)
                    
            elif provider == "huggingface":
                hf_msgs = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt}
                ]
                from backend.tools.hf_model_search import search_dynamic_text_models
                discovered_models = await search_dynamic_text_models(user_prompt)
                
                hf_models = HF_STAGE_MODELS.get(stage_name, HF_STAGE_MODELS["default"])
                combined = discovered_models + hf_models
                if cand_model in combined:
                    combined = [cand_model] + [m for m in combined if m != cand_model]
                else:
                    combined = [cand_model] + combined
                    
                seen = set()
                final_hf_models = []
                for m in combined:
                    if m not in seen:
                        final_hf_models.append(m)
                        seen.add(m)
                
                hf_success = False
                hf_last_err = None
                for model_id in final_hf_models:
                    try:
                        print(f"[HF Stage Failover] Stage '{stage_name}' trying model: {model_id}...")
                        async with _key_lock:
                            async for chunk in _stream_huggingface_custom(key, hf_msgs, model_id):
                                yield chunk
                                full_response_parts.append(chunk)
                        hf_success = True
                        cand_model = model_id
                        break
                    except Exception as inner_e:
                        err_str = str(inner_e).lower()
                        if "unauthorized" in err_str or "401" in err_str or "invalid token" in err_str:
                            raise inner_e
                        print(f"[HF Stage Failover] Model {model_id} failed: {inner_e}. Swapping to next capable model...")
                        hf_last_err = inner_e
                        
                if not hf_success:
                    raise hf_last_err or Exception(f"All Hugging Face models failed for stage {stage_name}")
            
            success = True
            elapsed = time.time() - start_time
            await _report_success_to_optimizer(key, provider, cand_model, 500, elapsed, conversation_id)
            break
            
        except Exception as e:
            import httpx
            import socket
            is_network_err = isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, socket.gaierror))
            if not is_network_err:
                err_str = str(e).lower()
                is_network_err = any(x in err_str for x in ["getaddrinfo", "resolv", "connection refused", "network is unreachable", "connecterror"])
            if is_network_err:
                raise Exception(
                    "Network Connection Error: The agent cannot reach the API servers. "
                    "Please check your internet connection or disconnect any VPN/Proxy."
                )
            last_error = e
            elapsed = time.time() - start_time
            mark_key_exhausted(key, duration=300)
            await _report_failure_to_optimizer(key, provider, cand_model, str(e), conversation_id)
            continue
            
    if not success:
        raise last_error or Exception(f"Stage {stage_name} failed.")

async def _get_optimal_route(task_type="text", session_id="N/A"):
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://127.0.0.1:8005/route",
                json={"task_type": task_type, "session_id": session_id},
                timeout=5.0
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[Orchestrator] KeyOptimus microservice offline, using local fallback: {e}")
    return None

async def _report_success_to_optimizer(key, provider, model, tokens_used, elapsed_time, session_id):
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                "http://127.0.0.1:8005/report_success",
                json={
                    "key_value": key,
                    "provider": provider,
                    "model": model,
                    "tokens_used": tokens_used,
                    "elapsed_time": elapsed_time,
                    "session_id": session_id
                },
                timeout=3.0
            )
        except Exception:
            pass

async def _report_failure_to_optimizer(key, provider, model, error_message, session_id):
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "http://127.0.0.1:8005/report_failure",
                json={
                    "key_value": key,
                    "provider": provider,
                    "model": model,
                    "error_message": error_message,
                    "session_id": session_id
                },
                timeout=3.0
            )
            if resp.status_code == 200:
                return resp.json().get("decision")
        except Exception:
            pass
    return None


async def run_agent(conversation_id, message, model="gemini-2.5-flash", user_memory=None):
    global _key_rotation_counter
    
    # Reset control state to running for the new execution turn
    set_agent_state(conversation_id, "running")
    
    # Check for hardcoded responses first to handle greetings and general agent questions locally
    from backend.agent.hardcoded_responses import get_hardcoded_response
    hardcoded_res = get_hardcoded_response(message)
    if hardcoded_res:
        yield {"type": "text", "content": hardcoded_res}
        title = message[:30] + "..." if len(message) > 30 else message
        yield {"type": "done", "conversation_id": conversation_id, "title": title}
        return
    
    # 1. Fetch conversation history first to detect any images in history
    history = await get_messages(conversation_id)
    
    # Check if the current message has images
    current_has_images = False
    if history:
        last_msg = history[-1]
        if last_msg.get("role") == "user" and last_msg.get("tool_data") and isinstance(last_msg["tool_data"], dict) and "images" in last_msg["tool_data"]:
            current_has_images = True

    # Check if any message in history has images
    has_images = False
    for msg in history:
        if msg.get("tool_data") and isinstance(msg["tool_data"], dict) and "images" in msg["tool_data"]:
            has_images = True
            break

    # Check if any multimodal keys are configured
    has_multimodal_key = False
    if get_key("GEMINI_API_KEY"):
        has_multimodal_key = True
    else:
        queue_val = get_key("API_KEYS_QUEUE") or "[]"
        try:
            queue = json.loads(queue_val)
            for item in queue:
                if item.get("provider", "gemini") in ["gemini", "openai", "anthropic"]:
                    has_multimodal_key = True
                    break
        except Exception:
            pass

    # Check if any local vision model is installed in Ollama
    has_local_vision = False
    try:
        from backend.key_optimizer.scheduler import is_ollama_running, get_installed_ollama_models
        if is_ollama_running():
            installed = get_installed_ollama_models()
            has_local_vision = any(any(k in inst.lower() for k in ["llava", "vision", "vl", "minicpm"]) for inst in installed)
    except Exception:
        pass

    has_multimodal_capability = has_multimodal_key or has_local_vision

    # 2. Determine task type dynamically based on prompt contents and complexity
    msg_lower = message.lower()

    # Check if the user is asking the agent to host/deploy itself (CRITICAL SELF-HOSTING TRIGGER)
    is_self_hosting_request = any(all(w in msg_lower for w in combo) for combo in [
        ["host", "yourself"], ["deploy", "yourself"], ["host", "agent"], ["deploy", "agent"], 
        ["self-host"], ["self", "host"], ["deploy", "me"], ["host", "me"]
    ])

    # Check if the history indicates an active DevOps/coding session
    has_devops_history = False
    if history:
        for msg in history[-4:]: # Check the last 4 messages for active DevOps context
            content_lower = (msg.get("content") or "").lower()
            if msg.get("tool_calls") or any(x in content_lower for x in [
                "scaffold", "implementation plan", "repository", "github", "deploy", "database", "pipeline", "ci/cd", "vercel", "portfolio", "nextjs"
            ]):
                has_devops_history = True
                break

    # Short follow-ups in a DevOps context should keep the complex reasoning mode active,
    # BUT only if they are actually related to proceeding, stack choices, or coding commands!
    # Conversational messages, corrections, or questions about the agent itself should fall back to general text mode.
    # Note: If it's a self-hosting request, it should NOT fall back to text mode!
    is_conversational_or_self_referential = any(x in msg_lower for x in [
        "yourself", "who are you", "who you are", "about you", "your name", "your creator", "your developer",
        "are you", "you are", "how are you", "hello", "hi", "hey", "dumb", "intelligent", "smart", "brain",
        "talking about you", "talk about you", "not any website", "not a website", "not the website"
    ]) and not is_self_hosting_request
    
    is_devops_action = any(x in msg_lower for x in [
        "do it", "go ahead", "yes", "proceed", "continue", "run", "scaffold", "create", "deploy", "build", "push",
        "approve", "confirm", "ok", "okay", "yep", "sure", "tailwind", "next", "react", "vite", "git", "github",
        "vercel", "postgres", "sqlite", "mongodb", "mysql", "database", "env", "key", "token", "stack"
    ])
    
    is_devops_followup = has_devops_history and is_devops_action and not is_conversational_or_self_referential

    if current_has_images or (has_images and has_multimodal_capability) or any(x in msg_lower for x in ["image", "photo", "picture", "diagram", "draw", "mermaid", "pptx", "docx", "chart"]):
        task_type = "multimodal"
    elif is_devops_followup or is_self_hosting_request or any(x in msg_lower for x in [
        "write", "code", "implement", "refactor", "debug", "fix", "error", "exception",
        "create a", "build a", "design a", "optimize", "class", "function", "database",
        "schema", "sql", "api", "script", "algorithm", "architecture", "develop"
    ]) or len(message.split()) > 40:
        task_type = "complex_reasoning"
    else:
        task_type = "text"

    if task_type == "complex_reasoning":
        yield {"type": "agent_state", "state": "running"}

    # 3. Build the dynamic system prompt including user memory personalization
    # Use SIMPLE_SYSTEM_PROMPT for multimodal or simple text tasks, and full SYSTEM_PROMPT for complex DevOps reasoning
    selected_prompt = SIMPLE_SYSTEM_PROMPT if task_type in ["multimodal", "text"] else SYSTEM_PROMPT
    dynamic_system_prompt = selected_prompt
    if user_memory:
        dynamic_system_prompt += f"\n\nUSER PERSONALIZATION & MEMORY:\n{user_memory}\nUse this memory to adapt your tone, style, and recall past decisions to talk to the user naturally."
        
    # Inject resumption/retry instructions if there is prior history in this session
    if history and len(history) > 1:
        dynamic_system_prompt += (
            "\n\n[System: Resuming task. Please review the previous conversation history, "
            "continue from where you left off, and adapt your approach to complete the user's objective. "
            "If any previous tool execution or terminal command failed, analyze the error and try a different, "
            "corrected approach. Proceed autonomously without repeating the same error.]"
        )
    
    # 2. Check for specialized media generation requests (text-to-image, text-to-speech, text-to-video)
    media_task = None
    if any(x in msg_lower for x in ["generate image", "create image", "text to image", "paint a", "draw a picture of"]):
        media_task = "text-to-image"
    elif any(x in msg_lower for x in ["generate speech", "text to speech", "tts", "read this", "convert to speech", "speak this"]):
        media_task = "text-to-speech"
    elif any(x in msg_lower for x in ["generate video", "create video", "text to video"]):
        media_task = "text-to-video"
        
    if media_task:
        # Find a Hugging Face token in our key pool
        hf_token = get_key("HUGGINGFACE_API_KEY")
        if not hf_token:
            queue_val = get_key("API_KEYS_QUEUE") or "[]"
            try:
                queue = json.loads(queue_val)
                for item in queue:
                    if item.get("provider") == "huggingface" and item.get("value"):
                        hf_token = item.get("value")
                        break
            except Exception:
                pass
            
        if hf_token:
            yield {
                "type": "text",
                "content": f"✨ **Dynamic Hugging Face Media Pipeline Activated!**\n\n"
            }
            yield {
                "type": "text",
                "content": f"🔍 **Searching HF Hub:** Locating the absolute best-fit open-source model for **{media_task}**...\n\n"
            }
            
            try:
                from backend.tools.hf_model_search import run_media_automation
                # Clean up prompt for media generation
                clean_prompt = message
                for phrase in ["generate image of", "create image of", "text to image of", "paint a of", "draw a picture of", "generate image", "create image", "text to image", "paint a", "draw a"]:
                    if phrase in clean_prompt.lower():
                        clean_prompt = clean_prompt.replace(phrase, "").strip()
                for phrase in ["generate speech of", "text to speech of", "convert to speech of", "speak this of", "read this of", "generate speech", "text to speech", "tts", "read this", "convert to speech", "speak this"]:
                    if phrase in clean_prompt.lower():
                        clean_prompt = clean_prompt.replace(phrase, "").strip()
                for phrase in ["generate video of", "create video of", "text to video of", "generate video", "create video", "text to video"]:
                    if phrase in clean_prompt.lower():
                        clean_prompt = clean_prompt.replace(phrase, "").strip()
                
                res = await run_media_automation(media_task, clean_prompt, hf_token)
                
                yield {
                    "type": "text",
                    "content": f"✨ **Model Selected:** `{res['model_id']}`\n\n"
                               f"🚀 **Execution:** Inference completed successfully!\n"
                               f"{res['markdown']}"
                }
                
                title = message[:30] + "..." if len(message) > 30 else message
                yield {"type": "done", "conversation_id": conversation_id, "title": title}
                return
            except Exception as e:
                yield {
                    "type": "text",
                    "content": f"\n\n*(⚠️ Media pipeline failed: {str(e)}. Falling back to text response...)*\n\n"
                }
        else:
            yield {
                "type": "text",
                "content": f"\n\n*(⚠️ Hugging Face Serverless API key is required for dynamic model execution. Please add a Hugging Face API key in Settings to generate images/audio.)*\n\n"
            }
    
    # Check if we should trigger the multi-agent team (supports single Hugging Face key or multiple keys of any provider)
    has_huggingface = False
    active_keys_count = 0
    if get_key("GEMINI_API_KEY"):
        active_keys_count += 1
    if get_key("HUGGINGFACE_API_KEY"):
        active_keys_count += 1
        has_huggingface = True
    
    queue_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(queue_val)
        for item in queue:
            if item.get("enabled") is False:
                continue
            active_keys_count += 1
            if item.get("provider") == "huggingface" and item.get("value"):
                has_huggingface = True
    except Exception:
        queue = []
        
    use_multi_agent = (task_type == "complex_reasoning" and (has_huggingface or active_keys_count >= 2))
    
    if use_multi_agent:
        from backend.agent.terminal_manager import manager
        yield {
            "type": "text",
            "content": "✨ **Multi-Agent Team Activated!** Coordinated locally on your PC, powered by Hugging Face & KeyOptimus.\n\n"
        }
        
        try:
            # Stage 1: Architect
            manager.set_active_agents([
                {"name": "Architect Agent", "status": "active"},
                {"name": "Developer Agent", "status": "waiting"},
                {"name": "QA Agent", "status": "waiting"}
            ])
            yield {
                "type": "text",
                "content": "### 🧠 Stage 1: System Architect (Llama 3.3 70B / Gemini Pro)\n*Analyzing request, designing the logical schemas, and creating an implementation plan...*\n\n"
            }
            architect_instruction = (
                "You are an expert System Architect. Analyze the user's request and write a highly detailed, "
                "step-by-step implementation plan. Outline the architecture, logic flow, file structure, "
                "and database schemas. Do not write the code blocks yet—focus purely on planning and architecture."
            )
            architect_prompt = f"User Request: {message}"
            
            architect_plan = ""
            async for chunk in _execute_stage("Architect", "complex_reasoning", architect_instruction, architect_prompt, conversation_id, history):
                yield {"type": "text", "content": chunk}
                architect_plan += chunk
                
            # Stage 2: Developer
            manager.set_active_agents([
                {"name": "Architect Agent", "status": "done"},
                {"name": "Developer Agent", "status": "active"},
                {"name": "QA Agent", "status": "waiting"}
            ])
            yield {
                "type": "text",
                "content": "\n\n---\n\n### 💻 Stage 2: Lead Developer (Qwen 2.5 Coder / Gemini Pro)\n*Implementing complete, clean, and production-grade code based on the Architect's plan...*\n\n"
            }
            developer_instruction = (
                "You are an expert Lead Software Engineer. Your task is to write clean, robust, well-commented, "
                "and complete code files based on the Architect's plan and the user's original request. "
                "Provide complete code blocks, not placeholders."
            )
            developer_prompt = f"User Request: {message}\n\nArchitect's Plan:\n{architect_plan}"
            
            developer_code = ""
            async for chunk in _execute_stage("Developer", "complex_reasoning", developer_instruction, developer_prompt, conversation_id, history):
                yield {"type": "text", "content": chunk}
                developer_code += chunk
                
            # Stage 3: QA Reviewer
            manager.set_active_agents([
                {"name": "Architect Agent", "status": "done"},
                {"name": "Developer Agent", "status": "done"},
                {"name": "QA Agent", "status": "active"}
            ])
            yield {
                "type": "text",
                "content": "\n\n---\n\n### 🔍 Stage 3: QA Reviewer (Qwen 7B / Gemini Flash)\n*Performing static code analysis, security auditing, and suggesting edge-case improvements...*\n\n"
            }
            qa_instruction = (
                "You are a Senior Quality Assurance Engineer. Review the code written by the Lead Developer. "
                "Identify any potential bugs, security concerns, edge cases, or performance optimizations, "
                "and provide a concise, constructive review summary."
            )
            qa_prompt = f"Developer's Code:\n{developer_code}"
            
            async for chunk in _execute_stage("QA Reviewer", "text", qa_instruction, qa_prompt, conversation_id, history):
                yield {"type": "text", "content": chunk}
                
            manager.set_active_agents([
                {"name": "Architect Agent", "status": "done"},
                {"name": "Developer Agent", "status": "done"},
                {"name": "QA Agent", "status": "done"}
            ])
                
            # Generate title if it is the first message
            title = message[:30] + "..." if len(message) > 30 else message
            yield {"type": "done", "conversation_id": conversation_id, "title": title}
            return
            
        except Exception as e:
            # If the multi-agent pipeline fails, yield a status notice and fallback to single-agent execution!
            yield {
                "type": "text",
                "content": f"\n\n*(⚠️ Multi-agent pipeline encountered an issue: {str(e)}. Automatically failing over to standard single-agent routing...)*\n\n"
            }
            # Let it fall through to the standard single-agent path!

    history_for_third_party = list(history)
    if len(history_for_third_party) == 0 or history_for_third_party[-1]["role"] != "user":
        history_for_third_party.append({"role": "user", "content": message})

    is_first_message = len(history) <= 1
    title = None
    success = False
    last_error = None

    # Try to execute the request using KeyOptimus routing. We allow up to 5 failover attempts.
    max_routing_attempts = 5
    last_attempted_key = None
    for attempt in range(max_routing_attempts):
        route = await _get_optimal_route(task_type, conversation_id)
        
        # If KeyOptimus is online, only accept its route for multimodal tasks if the provider supports images!
        if route and route.get("success") and (task_type != "multimodal" or route.get("provider") in ["gemini", "openai", "anthropic"]):
            provider = route["provider"]
            key = route["key"]
            cand_model = _resolve_model(provider, route["model"])
            label = route["label"]
        else:
            # Fallback to local scheduler if KeyOptimus is offline or routed incorrectly
            all_candidates = []
            
            # Check Ollama Local Engine
            from backend.key_optimizer.scheduler import is_ollama_running, get_installed_ollama_models
            if is_ollama_running():
                installed = get_installed_ollama_models()
                installed_lower = [inst.lower() for inst in installed]
                
                # If the user explicitly selected an installed Ollama model, make sure it is added as a candidate!
                is_explicit_ollama = ":" in model or "ollama" in model.lower() or any(x in model.lower() for x in ["qwen", "llama3.2-vision", "llava"])
                if is_explicit_ollama:
                    # Find matching installed name
                    matched_model = None
                    for inst in installed:
                        if model.lower() == inst.lower() or model.lower() in inst.lower() or inst.lower() in model.lower():
                            matched_model = inst
                            break
                    if matched_model:
                        # Only allow it for multimodal tasks if the model itself is a local vision model!
                        matched_lower = matched_model.lower()
                        is_vision = any(x in matched_lower for x in ["llava", "vision", "vl", "minicpm"])
                        if task_type != "multimodal" or is_vision:
                            all_candidates.append({
                                "provider": "ollama",
                                "key": "http://localhost:11434",
                                "label": f"Local Ollama: {matched_model}",
                                "model": matched_model
                            })
                
                # Also auto-discover local candidates based on task type
                if task_type == "multimodal":
                    # Look for installed vision models
                    vision_keywords = ["llava", "vision", "vl", "minicpm"]
                    for inst in installed:
                        if any(k in inst.lower() for k in vision_keywords):
                            # Avoid duplicate if already added via explicit selection
                            if not any(c["model"] == inst for c in all_candidates):
                                all_candidates.append({
                                    "provider": "ollama",
                                    "key": "http://localhost:11434",
                                    "label": f"Local Ollama Vision ({inst})",
                                    "model": inst
                                })
                else:
                    # Look for installed coding models
                    for model_name in ["qwen2.5-coder:1.5b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]:
                        if any(model_name in inst or inst in model_name for inst in installed_lower):
                            if not any(c["model"] == model_name for c in all_candidates):
                                all_candidates.append({
                                    "provider": "ollama",
                                    "key": "http://localhost:11434",
                                    "label": "Local Ollama Engine",
                                    "model": model_name
                                })

            # Check Hugging Face (only if NOT multimodal)
            if task_type != "multimodal":
                hf_primary = get_key("HUGGINGFACE_API_KEY")
                if hf_primary:
                    all_candidates.append({
                        "provider": "huggingface",
                        "key": hf_primary,
                        "label": "Primary Hugging Face Key",
                        "model": None
                    })
                    
            primary_key = get_key("GEMINI_API_KEY")
            if primary_key:
                all_candidates.append({
                    "provider": "gemini",
                    "key": primary_key,
                    "label": "Primary Gemini Key",
                    "model": model
                })
                
            queue_val = get_key("API_KEYS_QUEUE") or "[]"
            try:
                queue = json.loads(queue_val)
            except Exception:
                queue = []
            for item in queue:
                if item.get("enabled") is False:
                    continue
                prov = item.get("provider", "gemini")
                # If multimodal, only add multimodal providers from the queue
                if task_type == "multimodal" and prov not in ["gemini", "openai", "anthropic"]:
                    continue
                all_candidates.append({
                    "provider": prov,
                    "key": item.get("value"),
                    "label": item.get("label", "Backup Key"),
                    "model": None
                })
                
            active_candidates = [c for c in all_candidates if not is_key_exhausted(c["key"])]
            if not active_candidates:
                active_candidates = all_candidates
                
            # Sort candidates: cloud keys first, local Ollama last
            cloud_providers = ["gemini", "openai", "anthropic", "groq", "huggingface"]
            active_candidates.sort(key=lambda c: 0 if c["provider"] in cloud_providers else 1)
                
            # Prioritize the user's selected model provider if available
            requested_provider = "gemini" if "gemini" in model.lower() else ("openai" if "gpt" in model.lower() else ("anthropic" if "claude" in model.lower() else ("ollama" if "ollama" in model.lower() else None)))
            if requested_provider:
                preferred = [c for c in active_candidates if c["provider"] == requested_provider]
                others = [c for c in active_candidates if c["provider"] != requested_provider]
                active_candidates = preferred + others
            if not active_candidates:
                active_candidates = all_candidates
            # Intercept simple queries if there is no active AI engine
            is_simple = False
            simple_reply = ""
            if not active_candidates and message:
                cleaned = message.strip().lower().strip("?.!,")
                
                warning_suffix = (
                    "\n\n⚠️ **No Active AI Engine Available!**\n\n"
                    "To start chatting, please choose one of these options:\n\n"
                    "* **Option A (Cloud):** Get a free **[Gemini API Key here ↗](https://aistudio.google.com/app/apikey)**, then add it in the **Settings panel** (click the gear icon ⚙️ in the top-right corner of this page).\n"
                    "* **Option B (Offline):** Download the **[Ollama App here ↗](https://ollama.com/download)** and run it. Once running, open the **Settings panel** (gear icon ⚙️) and click **Install** on the **Qwen 2.5 Coder 1.5B** model to run completely offline and free!"
                )

                if cleaned in ["hello", "hi", "hey", "hola", "greetings", "yo"]:
                    is_simple = True
                    simple_reply = "Hello! I am the DevOps Concierge Agent, created by **Divyansh Tiwari**. How can I help you today?" + warning_suffix
                elif cleaned in ["who are you", "what is this", "what do you do"]:
                    is_simple = True
                    simple_reply = "I am the DevOps Concierge Agent — an advanced AI assistant created by **Divyansh Tiwari** to automate your software development lifecycle. You can scaffold projects, configure databases, manage credentials, push to GitHub, and deploy to Vercel/Render." + warning_suffix
                elif cleaned in ["how are you", "how's it going"]:
                    is_simple = True
                    simple_reply = "I'm doing great, ready to automate some DevOps tasks! What are we building today?" + warning_suffix
                elif cleaned in ["help", "info"]:
                    is_simple = True
                    simple_reply = "I can help you scaffold projects, configure databases, connect to GitHub, and deploy to Vercel/Render." + warning_suffix

            if is_simple:
                yield {
                    "type": "text",
                    "content": simple_reply
                }
                yield {"type": "done", "conversation_id": conversation_id}
                return

            if not active_candidates:
                if task_type == "multimodal":
                    content = (
                        "⚠️ **Vision Engine Required!**\n\n"
                        "You have uploaded an image, but there is no active Vision Engine available. To analyze images, please choose one of these options:\n\n"
                        "* **Option A (Cloud):** Get a free **[Gemini API Key here ↗](https://aistudio.google.com/app/apikey)**, then add it in the **Settings panel** (click the gear icon ⚙️ in the top-right corner of this page).\n"
                        "* **Option B (Offline):** Open the **Settings panel** (gear icon ⚙️) and click **Install** on either **Llava 7B** or **Llama 3.2 Vision 11B** in the local model section to run offline image analysis completely free!"
                    )
                    yield {
                        "type": "text",
                        "content": content
                    }
                    yield {"type": "done", "conversation_id": conversation_id}
                    return
                else:
                    # Execute free web search fallback
                    from backend.agent.hardcoded_responses import search_web_fallback
                    search_res = search_web_fallback(message)
                    
                    content = search_res
                    if "Offline Search Failed" not in search_res:
                        content += (
                            "\n\n---\n"
                            "💡 *Want to run code, scaffold apps, or deploy?* Connect a **Gemini API Key** or run a local **Ollama** model in Settings (⚙️) to enable full DevOps capabilities!"
                        )
                    yield {
                        "type": "text",
                        "content": content
                    }
                    yield {"type": "done", "conversation_id": conversation_id}
                    return
                
            async with _key_lock:
                start_idx = _key_rotation_counter % len(active_candidates)
                _key_rotation_counter += 1
            candidates = active_candidates[start_idx:] + active_candidates[:start_idx]
            
            cand = candidates[0]
            provider = cand["provider"]
            key = cand["key"]
            label = cand["label"]
            cand_model = _resolve_model(provider, cand["model"])

        if attempt > 0 and last_attempted_key and key != last_attempted_key:
            yield {
                "type": "text",
                "content": f"\n\n*(🔄 Rate limit or quota hit. Automatically failing over to backup key: **{label}** ({provider.upper()})...)*\n\n"
            }
        last_attempted_key = key
            
        start_time = time.time()
        try:
            if provider == "gemini":
                import os
                backend_dir = os.path.dirname(os.path.abspath(__file__))
                media_dir = os.path.join(backend_dir, "..", "generated_media")
                
                client = genai.Client(api_key=key)
                contents = []
                for msg in history:
                    if msg["role"] not in ["user", "assistant"]:
                        continue
                    role = "user" if msg["role"] == "user" else "model"
                    parts = [types.Part.from_text(text=msg["content"])]
                    
                    if msg.get("tool_data") and isinstance(msg["tool_data"], dict) and "images" in msg["tool_data"]:
                        for img_url in msg["tool_data"]["images"]:
                            filename = os.path.basename(img_url)
                            local_path = os.path.join(media_dir, filename)
                            if os.path.exists(local_path):
                                try:
                                    with open(local_path, "rb") as f:
                                        img_bytes = f.read()
                                    mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
                                    parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
                                except Exception as img_err:
                                    print(f"Error loading image {filename} for Gemini: {img_err}")
                                    
                    contents.append(types.Content(role=role, parts=parts))
                
                gemini_tools = _build_gemini_tools()
                max_iterations = 10
                
                for iteration in range(max_iterations):
                    # Check Pause/Stop state
                    if get_agent_state(conversation_id) == "stopped":
                        yield {"type": "agent_state", "state": "stopped"}
                        return
                    was_paused = False
                    while get_agent_state(conversation_id) == "paused":
                        if not was_paused:
                            yield {"type": "agent_state", "state": "paused"}
                            was_paused = True
                        await asyncio.sleep(0.5)
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                    if was_paused:
                        yield {"type": "agent_state", "state": "running"}

                    response = client.models.generate_content(
                        model=cand_model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=dynamic_system_prompt,
                            tools=gemini_tools,
                            temperature=0.7,
                        )
                    )
                    
                    if not response.candidates:
                        raise Exception("Gemini returned no candidates.")
                        
                    cand = response.candidates[0]
                    has_function_calls = False
                    text_parts = []
                    function_calls = []
                    
                    for part in cand.content.parts:
                        if part.text:
                            text_parts.append(part.text)
                        if part.function_call:
                            has_function_calls = True
                            function_calls.append(part.function_call)
                            
                    # Check for XML tool calls in text_parts as well (for 100% robust cross-provider support!)
                    full_text = "".join(text_parts)
                    import re
                    xml_matches = list(re.finditer(r"<call:(\w+)>([\s\S]*?)</call:\1>", full_text))
                    for match in xml_matches:
                        has_function_calls = True
                        t_name = match.group(1)
                        r_args = match.group(2).strip()
                        try:
                            t_args = json.loads(r_args) if r_args else {}
                        except Exception:
                            t_args = {}
                        if not any(fc.name == t_name for fc in function_calls):
                            class MockFunctionCall:
                                def __init__(self, name, args):
                                    self.name = name
                                    self.args = args
                            function_calls.append(MockFunctionCall(t_name, t_args))
                            
                    if text_parts:
                        yield {"type": "text", "content": "".join(text_parts)}
                        
                    if not has_function_calls:
                        break
                        
                    contents.append(cand.content)
                    function_response_parts = []
                    
                    import uuid
                    parallel_calls = []
                    sequential_calls = []
                    for fc in function_calls:
                        tool_name = fc.name
                        arguments = dict(fc.args) if fc.args else {}
                        call_id = str(uuid.uuid4())
                        if requires_authorization(tool_name):
                            sequential_calls.append((tool_name, arguments, call_id))
                        else:
                            parallel_calls.append((tool_name, arguments, call_id))
                            
                    # Check Pause/Stop state before starting parallel tools
                    if get_agent_state(conversation_id) == "stopped":
                        yield {"type": "agent_state", "state": "stopped"}
                        return
                    was_paused = False
                    while get_agent_state(conversation_id) == "paused":
                        if not was_paused:
                            yield {"type": "agent_state", "state": "paused"}
                            was_paused = True
                        await asyncio.sleep(0.5)
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                    if was_paused:
                        yield {"type": "agent_state", "state": "running"}

                    # 1. Yield all parallel tool starts
                    for tool_name, arguments, call_id in parallel_calls:
                        yield {
                            "type": "tool_start",
                            "tool": tool_name,
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                    # 2. Run parallel tools concurrently using asyncio.gather
                    async def _run_tool_task(name, args, cid):
                        try:
                            res = await _execute_tool(name, args)
                            return name, args, res, cid
                        except Exception as e:
                            return name, args, {"success": False, "error": str(e)}, cid
                            
                    if parallel_calls:
                        import asyncio
                        tasks = [_run_tool_task(name, args, cid) for name, args, cid in parallel_calls]
                        parallel_results = await asyncio.gather(*tasks)
                    else:
                        parallel_results = []
                        
                    # 3. Yield parallel tool results
                    for tool_name, arguments, result, call_id in parallel_results:
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result if isinstance(result, dict) else {"output": result},
                            "call_id": call_id
                        }
                        missing_cred = _detect_missing_credential(result, tool_name)
                        if missing_cred:
                            yield {
                                "type": "ui_event",
                                "action": "open_settings",
                                "highlight_field": missing_cred
                            }
                        
                        # Detect tool execution failure for self-healing
                        is_error = False
                        err_msg = ""
                        if isinstance(result, dict):
                            if "error" in result:
                                is_error = True
                                err_msg = str(result["error"])
                            elif result.get("success") is False:
                                is_error = True
                                err_msg = str(result.get("error") or "Unknown execution error")
                            elif result.get("exit_code") and result.get("exit_code") != 0:
                                is_error = True
                                err_msg = f"Terminal command exited with non-zero code {result.get('exit_code')}. Stderr: {result.get('stderr')}"
                                
                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response=result if isinstance(result, dict) else {"output": str(result)}
                            )
                        )
                        
                        if is_error:
                            guidance_text = f"\n\n[System: Tool '{tool_name}' failed! Error: {err_msg}. You must analyze this error, adapt your approach, and try a different method or correct your arguments. Do not repeat the same failing command!]"
                            function_response_parts.append(types.Part.from_text(text=guidance_text))
                        
                    # 4. Run sequential auth tools
                    for tool_name, arguments, call_id in sequential_calls:
                        # Check Pause/Stop state before each sequential tool
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                        was_paused = False
                        while get_agent_state(conversation_id) == "paused":
                            if not was_paused:
                                yield {"type": "agent_state", "state": "paused"}
                                was_paused = True
                            await asyncio.sleep(0.5)
                            if get_agent_state(conversation_id) == "stopped":
                                yield {"type": "agent_state", "state": "stopped"}
                                return
                        if was_paused:
                            yield {"type": "agent_state", "state": "running"}

                        yield {
                            "type": "tool_start",
                            "tool": tool_name,
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                        yield {
                            "type": "auth_request",
                            "action_id": call_id,
                            "tool": tool_name,
                            "description": f"The agent wants to execute: {tool_name}",
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                        approved = await request_authorization(
                            tool_name,
                            f"Execute {tool_name} with args: {json.dumps(arguments, default=str)}",
                            arguments,
                            action_id=call_id
                        )
                        
                        if not approved:
                            result = {"status": "denied", "message": "User denied this action"}
                            yield {"type": "tool_denied", "tool": tool_name, "call_id": call_id}
                        else:
                            yield {"type": "tool_approved", "tool": tool_name, "call_id": call_id}
                            try:
                                result = await _execute_tool(tool_name, arguments)
                            except Exception as e:
                                result = {"success": False, "error": str(e)}
                                
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result if isinstance(result, dict) else {"output": result},
                            "call_id": call_id
                        }
                        missing_cred = _detect_missing_credential(result, tool_name)
                        if missing_cred:
                            yield {
                                "type": "ui_event",
                                "action": "open_settings",
                                "highlight_field": missing_cred
                            }
                        
                        # Detect tool execution failure for self-healing
                        is_error = False
                        err_msg = ""
                        if isinstance(result, dict):
                            if "error" in result:
                                is_error = True
                                err_msg = str(result["error"])
                            elif result.get("success") is False:
                                is_error = True
                                err_msg = str(result.get("error") or "Unknown execution error")
                            elif result.get("exit_code") and result.get("exit_code") != 0:
                                is_error = True
                                err_msg = f"Terminal command exited with non-zero code {result.get('exit_code')}. Stderr: {result.get('stderr')}"
                                
                        function_response_parts.append(
                            types.Part.from_function_response(
                                name=tool_name,
                                response=result if isinstance(result, dict) else {"output": str(result)}
                            )
                        )
                        
                        if is_error:
                            guidance_text = f"\n\n[System: Tool '{tool_name}' failed! Error: {err_msg}. You must analyze this error, adapt your approach, and try a different method or correct your arguments. Do not repeat the same failing command!]"
                            function_response_parts.append(types.Part.from_text(text=guidance_text))
                        
                    contents.append(types.Content(
                        role="user",
                        parts=function_response_parts
                    ))
                
                if is_first_message:
                    title = await _generate_title(client, cand_model, message)
                
            elif provider in ["openai", "anthropic", "groq", "huggingface", "ollama"]:
                # Custom universal agentic loop for non-Gemini providers (enabling real tool execution!)
                max_tool_iterations = 10
                iteration = 0
                
                while iteration < max_tool_iterations:
                    # Check Pause/Stop state
                    if get_agent_state(conversation_id) == "stopped":
                        yield {"type": "agent_state", "state": "stopped"}
                        return
                    was_paused = False
                    while get_agent_state(conversation_id) == "paused":
                        if not was_paused:
                            yield {"type": "agent_state", "state": "paused"}
                            was_paused = True
                        await asyncio.sleep(0.5)
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                    if was_paused:
                        yield {"type": "agent_state", "state": "running"}

                    iteration += 1
                    
                    if provider == "openai":
                        stream = _stream_openai(key, history_for_third_party, cand_model, system_prompt=dynamic_system_prompt)
                    elif provider == "anthropic":
                        stream = _stream_anthropic(key, history_for_third_party, cand_model, system_prompt=dynamic_system_prompt)
                    elif provider == "groq":
                        stream = _stream_groq(key, history_for_third_party, cand_model, system_prompt=dynamic_system_prompt)
                    elif provider == "huggingface":
                        # Hugging Face specific multi-model failover streaming
                        from backend.tools.hf_model_search import search_dynamic_text_models
                        discovered_models = await search_dynamic_text_models(message)
                        hf_models = HF_STAGE_MODELS["default"]
                        combined = discovered_models + hf_models
                        if cand_model in combined:
                            combined = [cand_model] + [m for m in combined if m != cand_model]
                        else:
                            combined = [cand_model] + combined
                        
                        seen = set()
                        final_hf_models = []
                        for m in combined:
                            if m not in seen:
                                final_hf_models.append(m)
                                seen.add(m)
                        
                        hf_success = False
                        hf_last_err = None
                        for model_id in final_hf_models:
                            try:
                                print(f"[HF Chat Failover] Trying model: {model_id}...")
                                stream = _stream_huggingface(key, history_for_third_party, model_id, system_prompt=dynamic_system_prompt)
                                # Trigger actual evaluation of stream to verify success
                                chunks_buffered = []
                                async for chunk in stream:
                                    chunks_buffered.append(chunk)
                                hf_success = True
                                cand_model = model_id
                                
                                # Define a helper generator to yield buffered chunks
                                async def _buffered_gen():
                                    for c in chunks_buffered:
                                        yield c
                                stream = _buffered_gen()
                                break
                            except Exception as inner_e:
                                err_str = str(inner_e).lower()
                                if "unauthorized" in err_str or "401" in err_str or "invalid token" in err_str:
                                    raise inner_e
                                print(f"[HF Chat Failover] Model {model_id} failed: {inner_e}.")
                                hf_last_err = inner_e
                        
                        if not hf_success:
                            raise hf_last_err or Exception("All Hugging Face chat models failed.")
                            
                    elif provider == "ollama":
                        # Check if model is installed locally, and if not, pull it in the background
                        from backend.key_optimizer.scheduler import get_installed_ollama_models, is_ollama_model_installed
                        installed = get_installed_ollama_models()
                        if not is_ollama_model_installed(cand_model, installed):
                            yield {"type": "text", "content": f"\n\n*(📥 Model **{cand_model}** not found locally. Automatically downloading from Hugging Face... This first-time setup might take a few minutes...)*\n\n"}
                            async for progress in _pull_ollama_model_stream(cand_model, key):
                                yield {"type": "text", "content": progress}
                                
                        stream = _stream_ollama(history_for_third_party, cand_model, system_prompt=dynamic_system_prompt, base_url=key)
                    
                    full_text = ""
                    async for chunk in stream:
                        yield {"type": "text", "content": chunk}
                        full_text += chunk
                    
                    # Parse tool calls: <call:tool_name>JSON_ARGUMENTS</call:tool_name>
                    import re
                    tool_call_matches = list(re.finditer(r"<call:(\w+)>([\s\S]*?)</call:\1>", full_text))
                    
                    if not tool_call_matches:
                        break
                    
                    # Add assistant message containing the tool calls to history
                    history_for_third_party.append({"role": "assistant", "content": full_text})
                    
                    # Group parsed tool calls into parallel and sequential
                    parallel_calls = []
                    sequential_calls = []
                    for match in tool_call_matches:
                        tool_name = match.group(1)
                        raw_args = match.group(2).strip()
                        try:
                            arguments = json.loads(raw_args) if raw_args else {}
                        except Exception:
                            arguments = {}
                        
                        call_id = str(uuid.uuid4())
                        if requires_authorization(tool_name):
                            sequential_calls.append((tool_name, arguments, call_id))
                        else:
                            parallel_calls.append((tool_name, arguments, call_id))
                            
                    # Check Pause/Stop state before starting parallel tools
                    if get_agent_state(conversation_id) == "stopped":
                        yield {"type": "agent_state", "state": "stopped"}
                        return
                    was_paused = False
                    while get_agent_state(conversation_id) == "paused":
                        if not was_paused:
                            yield {"type": "agent_state", "state": "paused"}
                            was_paused = True
                        await asyncio.sleep(0.5)
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                    if was_paused:
                        yield {"type": "agent_state", "state": "running"}

                    # 1. Yield all parallel tool starts
                    for tool_name, arguments, call_id in parallel_calls:
                        yield {
                            "type": "tool_start",
                            "tool": tool_name,
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                    # 2. Run parallel tools concurrently using asyncio.gather
                    async def _run_tool_task_xml(name, args, cid):
                        try:
                            res = await _execute_tool(name, args)
                            return name, args, res, cid
                        except Exception as e:
                            return name, args, {"success": False, "error": str(e)}, cid
                            
                    if parallel_calls:
                        import asyncio
                        tasks = [_run_tool_task_xml(name, args, cid) for name, args, cid in parallel_calls]
                        parallel_results = await asyncio.gather(*tasks)
                    else:
                        parallel_results = []
                        
                    # 3. Yield parallel tool results
                    tool_results_summary = []
                    any_failed = False
                    for tool_name, arguments, result, call_id in parallel_results:
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result if isinstance(result, dict) else {"output": result},
                            "call_id": call_id
                        }
                        missing_cred = _detect_missing_credential(result, tool_name)
                        if missing_cred:
                            yield {
                                "type": "ui_event",
                                "action": "open_settings",
                                "highlight_field": missing_cred
                            }
                        
                        # Detect tool failure for self-healing
                        is_error = False
                        if isinstance(result, dict):
                            if "error" in result:
                                is_error = True
                            elif result.get("success") is False:
                                is_error = True
                            elif result.get("exit_code") and result.get("exit_code") != 0:
                                is_error = True
                        if is_error:
                            any_failed = True
                            
                        res_str = json.dumps(result, default=str)
                        tool_results_summary.append(f"Tool '{tool_name}' returned: {res_str}")
                        
                    # 4. Run sequential auth tools
                    for tool_name, arguments, call_id in sequential_calls:
                        # Check Pause/Stop state before each sequential tool
                        if get_agent_state(conversation_id) == "stopped":
                            yield {"type": "agent_state", "state": "stopped"}
                            return
                        was_paused = False
                        while get_agent_state(conversation_id) == "paused":
                            if not was_paused:
                                yield {"type": "agent_state", "state": "paused"}
                                was_paused = True
                            await asyncio.sleep(0.5)
                            if get_agent_state(conversation_id) == "stopped":
                                yield {"type": "agent_state", "state": "stopped"}
                                return
                        if was_paused:
                            yield {"type": "agent_state", "state": "running"}

                        yield {
                            "type": "tool_start",
                            "tool": tool_name,
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                        yield {
                            "type": "auth_request",
                            "action_id": call_id,
                            "tool": tool_name,
                            "description": f"The agent wants to execute: {tool_name}",
                            "arguments": arguments,
                            "call_id": call_id
                        }
                        
                        approved = await request_authorization(
                            tool_name,
                            f"Execute {tool_name} with args: {json.dumps(arguments, default=str)}",
                            arguments,
                            action_id=call_id
                        )
                        
                        if not approved:
                            result = {"status": "denied", "message": "User denied this action"}
                            yield {"type": "tool_denied", "tool": tool_name, "call_id": call_id}
                        else:
                            yield {"type": "tool_approved", "tool": tool_name, "call_id": call_id}
                            try:
                                result = await _execute_tool(tool_name, arguments)
                            except Exception as e:
                                result = {"success": False, "error": str(e)}
                                
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "result": result if isinstance(result, dict) else {"output": result},
                            "call_id": call_id
                        }
                        missing_cred = _detect_missing_credential(result, tool_name)
                        if missing_cred:
                            yield {
                                "type": "ui_event",
                                "action": "open_settings",
                                "highlight_field": missing_cred
                            }
                        
                        # Detect tool failure for self-healing
                        is_error = False
                        if isinstance(result, dict):
                            if "error" in result:
                                is_error = True
                            elif result.get("success") is False:
                                is_error = True
                            elif result.get("exit_code") and result.get("exit_code") != 0:
                                is_error = True
                        if is_error:
                            any_failed = True

                        res_str = json.dumps(result, default=str)
                        tool_results_summary.append(f"Tool '{tool_name}' returned: {res_str}")
                        
                    # Add results back as a system-user turn to let the model decide what to do next
                    feedback_message = "\n".join(tool_results_summary)
                    if any_failed:
                        feedback_message += (
                            "\n\n⚠️ **CRITICAL: Tool execution failed!**\n"
                            "[System: One or more tools failed during this iteration. Please analyze the error message above, "
                            "adapt your strategy, debug the code or command parameters, and try a different or corrected approach. "
                            "Do not repeat the exact same failing command without modification! Proceed autonomously to resolve this.]"
                        )
                    history_for_third_party.append({
                        "role": "user",
                        "content": f"[System: Tool execution completed. Results:\n{feedback_message}\n\nPlease proceed with the next steps or finalize your response.]"
                    })

            # On successful completion:
            success = True
            elapsed = time.time() - start_time
            # Report success to KeyOptimus (token usage estimated at 500 characters/tokens)
            await _report_success_to_optimizer(key, provider, cand_model, 500, elapsed, conversation_id)
            break
            
        except Exception as e:
            import httpx
            import socket
            is_network_err = isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout, socket.gaierror))
            if not is_network_err:
                err_str = str(e).lower()
                is_network_err = any(x in err_str for x in ["getaddrinfo", "resolv", "connection refused", "network is unreachable", "connecterror"])
            if is_network_err:
                yield {
                    "type": "text",
                    "content": (
                        "\n\n### ⚠️ 🌐 **Network Connection Error**\n\n"
                        "The agent cannot reach the API servers. This is usually a temporary internet/DNS issue.\n\n"
                        "**Try these steps to resolve it:**\n"
                        "1. **Check your connection** — Make sure you are online.\n"
                        "2. **Check your VPN/Proxy** — Disconnect if using one.\n"
                        "3. **Restart the backend** — Close and re-run `start.bat`.\n"
                    )
                }
                yield {"type": "done", "conversation_id": conversation_id}
                return
                
            last_error = e
            elapsed = time.time() - start_time
            
            # Local fallback quarantine
            mark_key_exhausted(key, duration=300)
            
            # Report failure to KeyOptimus microservice and get decision
            decision = await _report_failure_to_optimizer(key, provider, cand_model, str(e), conversation_id)
            
            # If the optimizer suggests retrying with a different model, we log it and proceed
            if decision and decision.get("action") == "retry_with_model":
                cand_model = decision["model"]
            
            continue
            
    if not success and last_error:
        error_msg = str(last_error).lower()
        error_str = str(last_error)
        
        if "getaddrinfo" in error_msg or "nodename nor servname" in error_msg or "name or service not known" in error_msg or "connectionerror" in error_msg or "networkerror" in error_msg or "urlopen error" in error_msg:
            friendly = (
                "🌐 **Network Connection Error**\n\n"
                "The agent cannot reach the API servers. This is usually a temporary internet/DNS issue.\n\n"
                "**Try these steps to resolve it:**\n\n"
                "1. **Check your connection** — Make sure you are online.\n"
                "2. **Check your VPN/Proxy** — Disconnect if using one.\n"
                "3. **Restart the backend** — Close and re-run `start.bat`."
            )
        elif "api_key_invalid" in error_msg or "api key not valid" in error_msg or "permission_denied" in error_msg or "401" in error_msg or "403" in error_msg:
            friendly = (
                "🔑 **Invalid or Expired API Key**\n\n"
                "One or more of your API keys was rejected by the provider.\n\n"
                "**Try these steps to resolve it:**\n\n"
                "1. **Verify your keys** — Make sure your keys are active and valid.\n"
                "2. **Update your keys** — Click the ⚙️ icon in Settings and update/add valid keys."
            )
        elif "429" in error_msg or "resource_exhausted" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
            friendly = (
                "⏳ **Rate Limit / Quota Exceeded on All Keys**\n\n"
                "All of your configured API keys have hit their usage limits.\n\n"
                "**Try these steps to resolve it:**\n\n"
                "1. **Wait 1-2 minutes** — Free-tier limits reset quickly.\n"
                "2. **Add more keys** — Add another backup key to your settings queue to keep going!"
            )
        elif "503" in error_msg or "unavailable" in error_msg or "overloaded" in error_msg or "high demand" in error_msg:
            friendly = (
                "🔄 **Service Temporarily Unavailable**\n\n"
                "The AI services are currently overloaded. Please wait 30 seconds and try again."
            )
        else:
            friendly = (
                f"⚠️ **Something went wrong**\n\n"
                f"An unexpected error occurred while processing your request.\n\n"
                f"**Error details:**\n```\n{error_str}\n```"
            )
            
        yield {"type": "error", "content": friendly}
        
    yield {"type": "done", "conversation_id": conversation_id, "title": title}

