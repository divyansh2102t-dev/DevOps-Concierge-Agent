import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

def merge_and_save():
    base_model_id = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    adapter_dir = "backend/agent/fine_tuned_devops_qwen"
    output_dir = "backend/agent/merged_devops_qwen"
    
    print("=" * 60)
    print("      MERGING DEVOPS CODER BASE MODEL & LORA ADAPTER")
    print("=" * 60)
    
    if not os.path.exists(adapter_dir):
        print(f"Error: Adapter directory not found at {adapter_dir}!")
        return
        
    print(f"Loading base model: {base_model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        torch_dtype=torch.float16,
        device_map="cpu",  # Run on CPU to save GPU VRAM
        trust_remote_code=True
    )
    
    print(f"Loading LoRA adapter from: {adapter_dir}...")
    model = PeftModel.from_pretrained(base_model, adapter_dir)
    
    print("Merging weights (combining base model and adapter)...")
    merged_model = model.merge_and_unload()
    
    print(f"Saving merged model to: {output_dir}...")
    merged_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print("\n" + "=" * 60)
    print("SUCCESS: Model successfully merged and saved!")
    print(f"Location: {output_dir}")
    print("=" * 60)

if __name__ == "__main__":
    merge_and_save()
