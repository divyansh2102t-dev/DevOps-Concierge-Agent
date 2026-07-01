import os
import sys
import json
import threading
import subprocess
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from backend.tools.key_store import get_key
from backend.agent.dataset_loader import download_coding_dataset
from backend.agent.test_accuracy import run_accuracy_benchmarks

router = APIRouter()

# Global state to track background training progress and logs
training_state = {
    "status": "idle",  # idle, loading_dataset, training, evaluating, done, error
    "logs": "",
    "progress": 0,
    "error_message": ""
}

class FineTuneRequest(BaseModel):
    model_id: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    dataset_limit: int = 500

class HFUploadRequest(BaseModel):
    repo_id: str
    file_path: str = "backend/agent/coding_train_dataset.jsonl"

class ModelfileRequest(BaseModel):
    model_name: str = "devops-concierge-custom"
    base_model: str = "qwen2.5-coder:1.5b"
    system_prompt: str = ""

def run_training_in_background(model_id: str, limit: int):
    global training_state
    try:
        # Step 1: Download & curate dataset
        training_state["status"] = "loading_dataset"
        training_state["logs"] += ">>> Starting dataset generation from Hugging Face...\n"
        training_state["progress"] = 10
        
        success = download_coding_dataset(limit=limit)
        if not success:
            training_state["logs"] += ">>> Warning: Streaming failed, loaded high-quality fallback dataset.\n"
        else:
            training_state["logs"] += ">>> Dataset successfully created!\n"
        
        training_state["progress"] = 30

        # Step 2: Start QLoRA fine-tuning script
        training_state["status"] = "training"
        training_state["logs"] += ">>> Launching QLoRA training loop (3 epochs)...\n"
        training_state["logs"] += ">>> Loading base model weights. Please wait...\n"
        
        # We run the fine-tuning script in a subprocess to capture stdout logs in real-time
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent", "fine_tune.py")
        process = subprocess.Popen(
            [sys.executable, script_path, model_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        # Read logs in real-time
        for line in process.stdout:
            training_state["logs"] += line
            # Basic parsing of training progress for the progress bar
            if "Epoch" in line or "loss" in line:
                training_state["progress"] = min(90, training_state["progress"] + 5)

        process.wait()
        
        if process.returncode != 0:
            raise Exception(f"Fine-tuning process exited with non-zero code: {process.returncode}")
            
        training_state["progress"] = 95
        training_state["status"] = "done"
        training_state["logs"] += ">>> FINE-TUNING COMPLETED SUCCESSFULLY!\n"
        training_state["logs"] += f">>> LoRA adapters saved to: backend/agent/fine_tuned_devops_qwen/\n"
        
    except Exception as e:
        training_state["status"] = "error"
        training_state["error_message"] = str(e)
        training_state["logs"] += f"\n>>> [CRITICAL ERROR] Training failed: {e}\n"

@router.get("/status")
async def get_training_status():
    return training_state

@router.post("/run")
async def start_fine_tuning(req: FineTuneRequest, background_tasks: BackgroundTasks):
    global training_state
    if training_state["status"] in ["loading_dataset", "training"]:
        raise HTTPException(status_code=400, detail="A training session is already in progress.")
        
    # Reset state
    training_state["status"] = "loading_dataset"
    training_state["logs"] = "Initializing training pipeline...\n"
    training_state["progress"] = 0
    training_state["error_message"] = ""
    
    background_tasks.add_task(run_training_in_background, req.model_id, req.dataset_limit)
    return {"status": "started", "message": "Training pipeline started in the background."}

@router.post("/evaluate")
async def evaluate_model(model_name: str = "qwen2.5-coder:1.5b"):
    try:
        # Run accuracy evaluation suite and capture output
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agent", "test_accuracy.py")
        result = subprocess.run(
            [sys.executable, script_path, model_name],
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "status": "success",
            "model": model_name,
            "report": result.stdout
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e.stderr or e.stdout}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-to-hf")
async def upload_dataset_to_hf(req: HFUploadRequest):
    hf_token = get_key("HUGGINGFACE_API_KEY")
    if not hf_token:
        raise HTTPException(
            status_code=400, 
            detail="Hugging Face Write Token is missing. Please configure it in the Settings panel."
        )
        
    if not os.path.exists(req.file_path):
        raise HTTPException(status_code=404, detail=f"File not found at: {req.file_path}")

    try:
        from huggingface_hub import HfApi
        api = HfApi(token=hf_token)
        
        filename = os.path.basename(req.file_path)
        print(f"Uploading {filename} to HF repo {req.repo_id}...")
        
        # Upload file to HF datasets hub
        api.upload_file(
            path_or_fileobj=req.file_path,
            path_in_repo=filename,
            repo_id=req.repo_id,
            repo_type="dataset"
        )
        
        return {
            "status": "success",
            "message": f"Successfully uploaded {filename} to Hugging Face dataset repo {req.repo_id}!",
            "url": f"https://huggingface.co/datasets/{req.repo_id}"
        }
    except ImportError:
        raise HTTPException(status_code=500, detail="huggingface_hub package is not installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-ollama-model")
async def register_ollama_model(req: ModelfileRequest):
    try:
        # 1. Create the Modelfile content
        modelfile_content = f"FROM {req.base_model}\n"
        if req.system_prompt:
            modelfile_content += f'SYSTEM """{req.system_prompt}"""\n'
        
        modelfile_path = "Modelfile-temp"
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)
            
        # 2. Run 'ollama create'
        process = subprocess.run(
            ["ollama", "create", req.model_name, "-f", modelfile_path],
            capture_output=True,
            text=True
        )
        
        # Clean up temp modelfile
        if os.path.exists(modelfile_path):
            os.remove(modelfile_path)
            
        if process.returncode != 0:
            raise Exception(f"Ollama creation failed: {process.stderr}")
            
        return {
            "status": "success",
            "message": f"Successfully created and registered model '{req.model_name}' in local Ollama instance!",
            "output": process.stdout
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
