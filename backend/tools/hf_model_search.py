import os
import time
import uuid
import json
import httpx
import asyncio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, "generated_media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# Optimized candidate pools for each task type on Hugging Face to enable instant model failover
TASK_CANDIDATE_MODELS = {
    "text-to-image": [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
        "stabilityai/stable-diffusion-2-1",
        "runwayml/stable-diffusion-v1-5"
    ],
    "text-to-speech": [
        "facebook/mms-tts-eng",
        "espnet/kan-bayashi_ljspeech_vits",
        "suno/bark-small"
    ],
    "image-to-text": [
        "Salesforce/blip-image-captioning-large",
        "Salesforce/blip-image-captioning-base",
        "nlpconnect/vit-gpt2-image-captioning"
    ],
    "text-to-video": [
        "damo-vilab/text-to-video-ms-1.7b",
        "ByteDance/AnimateDiff"
    ],
}

async def search_best_model(task_type: str) -> str:
    """
    Dynamically queries the Hugging Face Hub API to find the most popular (highest downloads)
    model for a specific task. Falls back to the first candidate if Hub API is slow or offline.
    """
    url = f"https://huggingface.co/api/models?filter={task_type}&sort=downloads&direction=-1&limit=3"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=4.0)
            if resp.status_code == 200:
                models = resp.json()
                if models and len(models) > 0:
                    model_id = models[0].get("modelId")
                    if model_id:
                        return model_id
    except Exception as e:
        print(f"[HF Model Hub] Hub search failed/timed out, using optimized fallback: {e}")
    
    candidates = TASK_CANDIDATE_MODELS.get(task_type, [])
    return candidates[0] if candidates else "stabilityai/stable-diffusion-2-1"


async def execute_hf_inference(model_id: str, payload: dict, token: str) -> bytes:
    """
    Sends a request to the Hugging Face Serverless Inference API for the selected model.
    """
    url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        # Use an aggressive 10 second timeout for model inference connections
        resp = await client.post(url, headers=headers, json=payload, timeout=httpx.Timeout(15.0, connect=4.0))
        if resp.status_code == 503:
            # Model is loading, wait and retry once
            estimated_time = 10.0
            try:
                err_data = resp.json()
                estimated_time = err_data.get("estimated_time", 10.0)
            except Exception:
                pass
            print(f"[HF Inference] Model {model_id} is loading. Waiting {estimated_time:.1f}s...")
            await asyncio.sleep(min(estimated_time, 8.0))
            resp = await client.post(url, headers=headers, json=payload, timeout=httpx.Timeout(15.0, connect=4.0))

        if resp.status_code != 200:
            raise Exception(f"Inference failed with status {resp.status_code}: {resp.text}")
        
        return resp.content


async def run_media_automation(task_type: str, prompt: str, token: str) -> dict:
    """
    Automatically searches the Hugging Face hub for the best model, runs the inference,
    saves the generated media to your local PC, and returns the metadata and markdown link.
    If the selected model is overloaded, it immediately fails over to the next candidate model.
    """
    # 1. Discover the best model dynamically
    discovered_model = await search_best_model(task_type)
    
    # Build unique candidates list preserving priority order
    candidates = [discovered_model] + TASK_CANDIDATE_MODELS.get(task_type, [])
    seen = set()
    unique_candidates = []
    for c in candidates:
        if c and c not in seen:
            unique_candidates.append(c)
            seen.add(c)

    print(f"[HF Automation] Candidates for '{task_type}': {unique_candidates}")
    
    # 2. Build task payload
    payload = {"inputs": prompt}
    
    # 3. Execute inference with multi-model failover
    content_bytes = None
    successful_model = None
    last_err = None
    
    for model_id in unique_candidates:
        try:
            print(f"[HF Automation] Trying model: {model_id}...")
            content_bytes = await execute_hf_inference(model_id, payload, token)
            successful_model = model_id
            print(f"[HF Automation] Model {model_id} executed successfully!")
            break
        except Exception as e:
            print(f"[HF Automation] Model {model_id} failed: {e}. Moving to next candidate...")
            last_err = e
            
    if not content_bytes:
        raise Exception(f"All candidate models for '{task_type}' failed or were overloaded. Last error: {last_err}")
            
    # 4. Save file locally in user's workspace
    file_id = str(uuid.uuid4())[:8]
    ext = "png"
    if task_type == "text-to-speech":
        ext = "flac" 
    elif task_type == "text-to-video":
        ext = "mp4"
        
    filename = f"hf_{task_type.replace('-', '_')}_{file_id}.{ext}"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(content_bytes)
        
    relative_url = f"/api/media/{filename}"
    
    # 5. Build markdown tag for easy UI rendering
    if task_type == "text-to-image":
        markdown_tag = f"\n\n![Generated Image]({relative_url})\n"
    elif task_type == "text-to-speech":
        markdown_tag = f"\n\n🔊 **Generated Audio:** [Listen/Download Audio]({relative_url})\n"
    elif task_type == "text-to-video":
        markdown_tag = f"\n\n🎬 **Generated Video:** [Watch/Download Video]({relative_url})\n"
    else:
        markdown_tag = f"\n\n📁 **Generated Media File:** [Open File]({relative_url})\n"
        
    return {
        "success": True,
        "model_id": successful_model,
        "filepath": filepath,
        "url": relative_url,
        "markdown": markdown_tag
    }


async def search_dynamic_text_models(prompt: str) -> list:
    """
    Analyzes the user's prompt, classifies the specialized need (coding, databases, math, system design, etc.),
    and dynamically queries the Hugging Face Hub API to discover the top-performing, most popular models
    matching that specific skill.
    """
    prompt_lower = prompt.lower()
    search_query = "instruct"
    
    # Semantic classification based on prompt contents
    if any(x in prompt_lower for x in ["code", "python", "javascript", "c++", "java", "rust", "go", "script", "implement", "programming", "develop"]):
        search_query = "coder"
    elif any(x in prompt_lower for x in ["sql", "database", "postgres", "mysql", "query", "schema", "table"]):
        search_query = "sql"
    elif any(x in prompt_lower for x in ["math", "equation", "solve", "calculus", "algebra", "number"]):
        search_query = "math"
    elif any(x in prompt_lower for x in ["translate", "translation", "language", "multilingual"]):
        search_query = "translation"
    elif any(x in prompt_lower for x in ["architect", "system design", "structure", "uml", "design pattern"]):
        search_query = "instruct"
        
    url = f"https://huggingface.co/api/models?filter=text-generation&search={search_query}&sort=downloads&direction=-1&limit=5"
    discovered = []
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=4.0)
            if resp.status_code == 200:
                models = resp.json()
                for m in models:
                    model_id = m.get("modelId")
                    if model_id and "/" in model_id:
                        discovered.append(model_id)
    except Exception as e:
        print(f"[HF Dynamic Search] Failed to search Hub for '{search_query}': {e}")
        
    return discovered
