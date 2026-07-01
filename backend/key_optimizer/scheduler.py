import os
import sys
import json
import time
import asyncio
from backend.tools.key_store import get_key
from backend.key_optimizer.excel_logger import queue_log

# ── PROVIDER CAPABILITY & MODEL MAPS ──
PROVIDER_CAPABILITIES = {
    "gemini": ["text", "multimodal", "image_gen", "audio"],
    "openai": ["text", "multimodal"],
    "anthropic": ["text", "multimodal"],
    "groq": ["text"],
    "huggingface": ["text"],
    "ollama": ["text"]
}

# Supported models per provider (in priority order for intra-key swapping)
PROVIDER_MODELS = {
    "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
    "openai": ["gpt-4o-mini", "gpt-4o"],
    "anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
    "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
    "huggingface": ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-7B-Instruct"],
    "ollama": ["devops-concierge-coder:latest", "qwen2.5-coder:1.5b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]
}

# Dynamic model priority based on task complexity and reasoning requirements
TASK_MODEL_PRIORITIES = {
    "complex_reasoning": {
        "gemini": ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-1.5-flash"],
        "openai": ["gpt-4o", "gpt-4o-mini"],
        "anthropic": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "huggingface": ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-7B-Instruct"],
        "ollama": ["devops-concierge-coder:latest", "qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5-coder:1.5b"]
    },
    "text": {
        "gemini": ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro", "gemini-1.5-pro"],
        "openai": ["gpt-4o-mini", "gpt-4o"],
        "anthropic": ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest"],
        "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768"],
        "huggingface": ["Qwen/Qwen2.5-7B-Instruct", "Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"],
        "ollama": ["devops-concierge-coder:latest", "qwen2.5-coder:7b", "qwen2.5-coder:1.5b", "qwen2.5-coder:14b"]
    },
    "multimodal": {
        "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
        "openai": ["gpt-4o-mini", "gpt-4o"],
        "anthropic": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
        "groq": ["llama-3.3-70b-versatile"],
        "huggingface": ["Qwen/Qwen2.5-72B-Instruct"]
    }
}

# ── FREE TIER / LIMITS DATABASE ──
# Default rate limits (RPM: Requests per Min, RPD: Requests per Day, TPM: Tokens per Min)
DEFAULT_LIMITS = {
    "gemini": {
        "gemini-2.5-flash": {"rpm": 15, "rpd": 1500, "tpm": 1000000},
        "gemini-2.5-pro": {"rpm": 2, "rpd": 50, "tpm": 32000},
        "gemini-1.5-flash": {"rpm": 15, "rpd": 1500, "tpm": 1000000},
        "gemini-1.5-pro": {"rpm": 2, "rpd": 50, "tpm": 32000}
    },
    "openai": {
        "gpt-4o-mini": {"rpm": 3, "rpd": 200, "tpm": 40000},
        "gpt-4o": {"rpm": 3, "rpd": 200, "tpm": 40000}
    },
    "anthropic": {
        "claude-3-5-haiku-latest": {"rpm": 5, "rpd": 50, "tpm": 20000},
        "claude-3-5-sonnet-latest": {"rpm": 5, "rpd": 50, "tpm": 20000}
    },
    "groq": {
        "llama-3.3-70b-versatile": {"rpm": 30, "rpd": 14400, "tpm": 79000},
        "mixtral-8x7b-32768": {"rpm": 30, "rpd": 14400, "tpm": 79000},
        "gemma2-9b-it": {"rpm": 30, "rpd": 14400, "tpm": 15000}
    },
    "huggingface": {
        "Qwen/Qwen2.5-72B-Instruct": {"rpm": 10, "rpd": 1000, "tpm": 50000},
        "meta-llama/Llama-3.3-70B-Instruct": {"rpm": 10, "rpd": 1000, "tpm": 50000},
        "Qwen/Qwen2.5-7B-Instruct": {"rpm": 20, "rpd": 2000, "tpm": 100000}
    },
    "ollama": {
        "devops-concierge-coder:latest": {"rpm": 9999, "rpd": 99999, "tpm": 99999999},
        "qwen2.5-coder:1.5b": {"rpm": 9999, "rpd": 99999, "tpm": 99999999},
        "qwen2.5-coder:7b": {"rpm": 9999, "rpd": 99999, "tpm": 99999999},
        "qwen2.5-coder:14b": {"rpm": 9999, "rpd": 99999, "tpm": 99999999}
    }
}

# ── IN-MEMORY QUANTUM STATE TRACKERS ──
# Structure: { key_value: { model_name: { "rpm_timestamps": [...], "rpd_count": int, "tpm_sum": int } } }
_usage_db = {}
# Structure: { key_value: expiration_timestamp }
_quarantine_db = {}
# Global load balancing index
_rotation_index = 0
_lock = asyncio.Lock()

def _get_key_state(key_val, model):
    """Initializes and returns the state tracker dictionary for a given key/model pair."""
    if key_val not in _usage_db:
        _usage_db[key_val] = {}
    if model not in _usage_db[key_val]:
        _usage_db[key_val][model] = {
            "rpm_timestamps": [],
            "rpd_count": 0,
            "tpm_sum": 0,
            "last_reset_day": time.strftime("%Y-%m-%d")
        }
    
    state = _usage_db[key_val][model]
    
    # Daily quota reset check
    current_day = time.strftime("%Y-%m-%d")
    if state["last_reset_day"] != current_day:
        state["rpd_count"] = 0
        state["tpm_sum"] = 0
        state["last_reset_day"] = current_day
        
    # Clean up RPM timestamps older than 60 seconds
    now = time.time()
    state["rpm_timestamps"] = [t for t in state["rpm_timestamps"] if now - t < 60]
    
    return state

def is_ollama_running():
    """High-speed synchronous TCP connection check to detect local Ollama instance."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.05):
            return True
    except Exception:
        return False

def get_installed_ollama_models():
    """Queries local Ollama tags endpoint to fetch downloaded models."""
    import urllib.request
    import json
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=0.2) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []

def is_ollama_model_installed(model_name, installed_list):
    """Verifies if the specified model is present in Ollama's local tags database."""
    model_lower = model_name.lower()
    for inst in installed_list:
        inst_lower = inst.lower()
        if model_lower == inst_lower:
            return True
        if model_lower in inst_lower or inst_lower in model_lower:
            return True
    return False

def get_all_keys():
    """Fetches all keys configured in key_store (primary + queue) and local engines."""
    keys = []
    
    # 1. Fetch Primary Gemini Key
    primary = get_key("GEMINI_API_KEY")
    if primary:
        keys.append({
            "provider": "gemini",
            "value": primary,
            "label": "Primary Gemini Key"
        })
        
    # 2. Fetch Keys Queue
    queue_val = get_key("API_KEYS_QUEUE") or "[]"
    try:
        queue = json.loads(queue_val)
    except Exception:
        queue = []
        
    for item in queue:
        if item.get("enabled") is False:
            continue
        keys.append({
            "provider": item.get("provider", "gemini"),
            "value": item.get("value"),
            "label": item.get("label", "Backup Key")
        })

    # 3. Auto-Inject Local Ollama Engine if running
    if is_ollama_running():
        keys.append({
            "provider": "ollama",
            "value": "http://localhost:11434",
            "label": "Local Ollama Engine"
        })
        
    return keys

def get_remaining_capacity(key_val, provider, model):
    """Calculates how many requests are remaining for a model on a given key based on free-tier limits."""
    state = _get_key_state(key_val, model)
    limits = DEFAULT_LIMITS.get(provider, {}).get(model, {"rpm": 5, "rpd": 100, "tpm": 20000})
    
    rpm_used = len(state["rpm_timestamps"])
    rpd_used = state["rpd_count"]
    
    rpm_rem = max(0, limits["rpm"] - rpm_used)
    rpd_rem = max(0, limits["rpd"] - rpd_used)
    
    return min(rpm_rem, rpd_rem), rpd_rem

def is_quarantined(key_val):
    """Checks if a key is currently quarantined."""
    expiry = _quarantine_db.get(key_val, 0)
    if time.time() < expiry:
        return True
    if key_val in _quarantine_db:
        del _quarantine_db[key_val]
    return False

def route_request(task_type="text", session_id="N/A"):
    """
    Core Deterministic Selection & Optimization Algorithm.
    Selects the best key and model based on:
    - Task type and capabilities.
    - Rate limit state and token consumption.
    - Wastage prevention logic (preserving premium features when limits are tight).
    - Active installation verification for local Ollama models.
    """
    global _rotation_index
    
    all_keys = get_all_keys()
    if not all_keys:
        return {"success": False, "error": "No API keys configured."}
        
    # Filter out quarantined keys
    active_keys = [k for k in all_keys if not is_quarantined(k["value"])]
    if not active_keys:
        # Fallback to quarantined keys if everything is locked out
        active_keys = all_keys
        
    # Fetch installed Ollama models to prevent routing to missing models
    installed_ollama = []
    if any(k["provider"] == "ollama" for k in active_keys):
        installed_ollama = get_installed_ollama_models()

    # ── CATEGORIZE KEYS BY CAPABILITY ──
    basic_keys = []
    premium_keys = []
    
    for k in active_keys:
        provider = k["provider"]
        caps = PROVIDER_CAPABILITIES.get(provider, ["text"])
        
        # A premium key has advanced capabilities (like image_gen or audio)
        if "image_gen" in caps or "audio" in caps:
            premium_keys.append(k)
        else:
            basic_keys.append(k)
            
    selected_key = None
    selected_model = None
    selected_provider = None
    selected_label = None
    
    # ── STEP 1: ROUTING WITH WASTAGE PREVENTION ──
    if task_type in ("text", "complex_reasoning"):
        # Get dynamic model priorities for this task type
        priority_map = TASK_MODEL_PRIORITIES.get(task_type, TASK_MODEL_PRIORITIES["text"])
        
        # If the task is simple text or complex reasoning, try to use basic keys first!
        for k in basic_keys:
            provider = k["provider"]
            models = priority_map.get(provider, PROVIDER_MODELS.get(provider, []))
            if provider == "ollama":
                models = [m for m in models if is_ollama_model_installed(m, installed_ollama)]
            for model in models:
                cap_rem, rpd_rem = get_remaining_capacity(k["value"], provider, model)
                if cap_rem > 0:
                    selected_key = k["value"]
                    selected_model = model
                    selected_provider = provider
                    selected_label = k["label"]
                    break
            if selected_key:
                break
                
        # If no basic key is available, evaluate premium keys
        if not selected_key:
            for k in premium_keys:
                provider = k["provider"]
                models = priority_map.get(provider, PROVIDER_MODELS.get(provider, []))
                if provider == "ollama":
                    models = [m for m in models if is_ollama_model_installed(m, installed_ollama)]
                for model in models:
                    cap_rem, rpd_rem = get_remaining_capacity(k["value"], provider, model)
                    
                    # Wastage Prevention Threshold:
                    # If this premium key is running low on daily requests (e.g. less than 5 remaining),
                    # do NOT waste it on a simple text prompt. Save it for image/video/audio generation!
                    if rpd_rem <= 5 and len(basic_keys) > 0 and task_type == "text":
                        # Skip this key for simple text tasks; preserve it!
                        continue
                        
                    if cap_rem > 0:
                        selected_key = k["value"]
                        selected_model = model
                        selected_provider = provider
                        selected_label = k["label"]
                        break
                if selected_key:
                    break
                    
    else: # Task is a specialized task like "image_gen", "multimodal", or "audio"
        # Prioritize premium keys that actually support this task!
        for k in premium_keys:
            provider = k["provider"]
            caps = PROVIDER_CAPABILITIES.get(provider, [])
            if task_type in caps:
                models = PROVIDER_MODELS.get(provider, [])
                if provider == "ollama":
                    models = [m for m in models if is_ollama_model_installed(m, installed_ollama)]
                for model in models:
                    cap_rem, rpd_rem = get_remaining_capacity(k["value"], provider, model)
                    if cap_rem > 0:
                        selected_key = k["value"]
                        selected_model = model
                        selected_provider = provider
                        selected_label = k["label"]
                        break
            if selected_key:
                break
                
        # Fallback to standard keys if no specialized key is available (e.g. sending vision task to openai)
        if not selected_key:
            for k in basic_keys:
                provider = k["provider"]
                caps = PROVIDER_CAPABILITIES.get(provider, [])
                if task_type in caps:
                    models = PROVIDER_MODELS.get(provider, [])
                    if provider == "ollama":
                        models = [m for m in models if is_ollama_model_installed(m, installed_ollama)]
                    for model in models:
                        cap_rem, rpd_rem = get_remaining_capacity(k["value"], provider, model)
                        if cap_rem > 0:
                            selected_key = k["value"]
                            selected_model = model
                            selected_provider = provider
                            selected_label = k["label"]
                            break
                if selected_key:
                    break

    # ── STEP 2: DYNAMIC LOAD BALANCING ROTATION ──
    # If multiple keys are equally capable and available, rotate them using the global pointer
    if not selected_key and active_keys:
        priority_map = TASK_MODEL_PRIORITIES.get(task_type, TASK_MODEL_PRIORITIES["text"])
        # Fallback to rotation of the active keys to find *any* key that has quota
        _rotation_index = (_rotation_index + 1) % len(active_keys)
        rotated_keys = active_keys[_rotation_index:] + active_keys[:_rotation_index]
        
        for k in rotated_keys:
            provider = k["provider"]
            models = priority_map.get(provider, PROVIDER_MODELS.get(provider, []))
            if provider == "ollama":
                models = [m for m in models if is_ollama_model_installed(m, installed_ollama)]
            for model in models:
                cap_rem, rpd_rem = get_remaining_capacity(k["value"], provider, model)
                if cap_rem > 0 or (rpd_rem > 0 and len(rotated_keys) == 1):
                    selected_key = k["value"]
                    selected_model = model
                    selected_provider = provider
                    selected_label = k["label"]
                    break
            if selected_key:
                break

    if selected_key:
        # Record routing decision to Excel
        queue_log(
            session_id=session_id,
            action="ROUTE",
            provider=selected_provider,
            key_label=selected_label,
            model=selected_model,
            task_type=task_type,
            status="SUCCESS",
            error_msg="Routed optimally by KeyOptimus"
        )
        return {
            "success": True,
            "provider": selected_provider,
            "key": selected_key,
            "model": selected_model,
            "label": selected_label
        }
        
    return {"success": False, "error": "All API keys have exceeded their active rate limits/quotas."}

def report_success(key_val, provider, model, tokens_used=0, elapsed_time=0.0, session_id="N/A"):
    """Increments request and token counts upon successful API completion."""
    state = _get_key_state(key_val, model)
    state["rpm_timestamps"].append(time.time())
    state["rpd_count"] += 1
    state["tpm_sum"] += tokens_used
    
    # Retrieve key label for logging
    label = "Unknown Key"
    for k in get_all_keys():
        if k["value"] == key_val:
            label = k["label"]
            break
            
    queue_log(
        session_id=session_id,
        action="EXECUTE",
        provider=provider,
        key_label=label,
        model=model,
        task_type="text",
        status="SUCCESS",
        tokens_used=tokens_used,
        latency=elapsed_time,
        error_msg="Successful request execution"
    )

def report_failure(key_val, provider, model, error_message, session_id="N/A"):
    """
    Handles API failure reporting. Decides between:
    - Intra-key model swapping (swapping to alternative models on same key).
    - Key-level quarantine (blocking key for 5 minutes).
    """
    label = "Unknown Key"
    for k in get_all_keys():
        if k["value"] == key_val:
            label = k["label"]
            break
            
    error_msg_lower = error_message.lower()
    
    # Determine if it is a model-level or key-level error
    # Model-level errors are typically 429 rate limits on a specific model, or model-not-found
    is_model_specific = any(x in error_msg_lower for x in ["429", "resource_exhausted", "rate limit", "not_supported", "not found", "model_not_supported"])
    
    # If it is model-specific and we have alternative models, swap model!
    alternative_model = None
    if is_model_specific:
        models = PROVIDER_MODELS.get(provider, [])
        if model in models:
            idx = models.index(model)
            # Find the next model that still has quota
            for alt in models[idx+1:]:
                cap_rem, _ = get_remaining_capacity(key_val, provider, alt)
                if cap_rem > 0:
                    alternative_model = alt
                    break
                    
    if alternative_model:
        # Log model swap event
        queue_log(
            session_id=session_id,
            action="SWAP_MODEL",
            provider=provider,
            key_label=label,
            model=f"{model} -> {alternative_model}",
            task_type="error",
            status="SWAPPED",
            error_msg=f"Model rate-limited. Swapped to {alternative_model} on same key. Error: {error_message}"
        )
        return {
            "action": "retry_with_model",
            "model": alternative_model
        }
    else:
        # Key-level failure or rate-limited on all models: Quarantine the key for 5 minutes (300 seconds)
        quarantine_duration = 300
        _quarantine_db[key_val] = time.time() + quarantine_duration
        
        queue_log(
            session_id=session_id,
            action="QUARANTINE",
            provider=provider,
            key_label=label,
            model=model,
            task_type="error",
            status="QUARANTINED",
            error_msg=f"Key quarantined for 5m. Error: {error_message}"
        )
        return {
            "action": "rotate_key",
            "quarantined_until": time.strftime("%H:%M:%S", time.localtime(time.time() + quarantine_duration))
        }

def get_scheduler_metrics():
    """Returns all key capacities, active rates, and quarantine metrics for monitoring dashboards."""
    keys = get_all_keys()
    metrics = []
    
    for k in keys:
        provider = k["provider"]
        val = k["value"]
        models = PROVIDER_MODELS.get(provider, [])
        
        model_status = {}
        for m in models:
            state = _get_key_state(val, m)
            limits = DEFAULT_LIMITS.get(provider, {}).get(m, {"rpm": 0, "rpd": 0, "tpm": 0})
            
            rpm_used = len(state["rpm_timestamps"])
            rpd_used = state["rpd_count"]
            
            model_status[m] = {
                "rpm_limit": limits["rpm"],
                "rpm_used": rpm_used,
                "rpd_limit": limits["rpd"],
                "rpd_used": rpd_used,
                "tpm_used": state["tpm_sum"]
            }
            
        quarantined = is_quarantined(val)
        expiry = _quarantine_db.get(val, 0)
        rem_quarantine = max(0, int(expiry - time.time())) if quarantined else 0
        
        metrics.append({
            "label": k["label"],
            "provider": provider,
            "quarantined": quarantined,
            "quarantine_remaining_seconds": rem_quarantine,
            "models": model_status
        })
        
    return metrics
