import os
import sys
import torch
import subprocess

def check_training_dependencies():
    required = ["transformers", "peft", "trl", "accelerate", "bitsandbytes"]
    missing = []
    for req in required:
        try:
            __import__(req)
        except ImportError:
            missing.append(req)
            
    if missing:
        print(f"Missing machine learning packages: {missing}")
        print("Installing required training dependencies. This might take a minute...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Dependencies successfully installed!")
        except Exception as e:
            print(f"Warning: Automatic installation failed: {e}")
            print("Please run: pip install transformers peft trl accelerate bitsandbytes torch")

if __name__ == "__main__":
    check_training_dependencies()

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset

def run_fine_tuning(
    model_id="Qwen/Qwen2.5-Coder-1.5B-Instruct",
    dataset_path="backend/agent/coding_train_dataset.jsonl",
    output_dir="backend/agent/fine_tuned_devops_qwen"
):
    print("=" * 60)
    print("       STARTING DEVOPS CONCIERGE QLORA FINE-TUNING")
    print("=" * 60)
    
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}!")
        print("Please run backend/agent/dataset_loader.py first to acquire the dataset.")
        return
        
    # 1. Hardware Check
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Active Hardware Device: {device.upper()}")
    if device == "cpu":
        print("[WARNING] CUDA-compatible GPU not found. Training on CPU will be extremely slow.")
        print("It is highly recommended to run this on a machine with an NVIDIA GPU.")
    
    # 2. Load Dataset
    print(f"Loading local dataset from: {dataset_path}...")
    dataset = load_dataset("json", data_files=dataset_path, split="train")
    print(f"Loaded {len(dataset)} training samples successfully!")

    # 3. Configure Quantization (4-Bit)
    print("Configuring 4-bit quantization (NF4) for efficient memory usage...")
    bnb_config = None
    is_bf16_supported = False
    if device == "cuda":
        is_bf16_supported = torch.cuda.is_bf16_supported()
        print(f"CUDA BF16 Support: {is_bf16_supported}")
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if is_bf16_supported else torch.float16,
            bnb_4bit_use_secondary_quant=True if hasattr(BitsAndBytesConfig, 'bnb_4bit_use_secondary_quant') else False,
            bnb_4bit_use_double_quant=True
        )

    # 4. Load Base Model & Tokenizer
    print(f"Downloading/Loading base model: {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=bnb_config if device == "cuda" else None,
        device_map="auto" if device == "cuda" else None,
        torch_dtype=torch.bfloat16 if (device == "cuda" and is_bf16_supported) else torch.float16,
        trust_remote_code=True
    )

    if device == "cuda":
        model = prepare_model_for_kbit_training(model)

    # 5. Configure LoRA
    print("Setting up Low-Rank Adaptation (LoRA) adapters...")
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    # 6. Training Arguments
    print("Setting up training hyperparameters...")
    training_args = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=(device == "cuda" and not is_bf16_supported),
        bf16=(device == "cuda" and is_bf16_supported),
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="no",
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        report_to="none",
        max_length=512,
    )

    # Helper function to format prompts for Supervised Fine-Tuning
    def formatting_prompts_func(example):
        instruction = example.get('instruction', '') or ''
        input_val = example.get('input', '') or ''
        output = example.get('output', '') or ''
        
        # Formatting as Alpaca style prompt
        if input_val:
            return f"Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Input:\n{input_val}\n\n### Response:\n{output}"
        else:
            return f"Below is an instruction that describes a task. Write a response that appropriately completes the request.\n\n### Instruction:\n{instruction}\n\n### Response:\n{output}"

    # 7. Supervised Fine-Tuning (SFT) Trainer
    print("Initializing SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=lora_config,
        processing_class=tokenizer,
        formatting_func=formatting_prompts_func,
        args=training_args,
    )

    # 8. Run Training Loop
    print("\nTraining starting... This will run for 3 epochs.")
    print("Progress logs will display loss values every 10 steps.")
    trainer.train()
    
    # 9. Save Fine-Tuned Model
    print(f"\nTraining completed! Saving LoRA adapter to: {output_dir}...")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print("LoRA adapter successfully saved!")
    
    print("\nTo load this model in Ollama, you can merge the adapter and convert it to GGUF.")
    print("Next step: Run backend/agent/test_accuracy.py to evaluate the model!")

if __name__ == "__main__":
    run_fine_tuning()
