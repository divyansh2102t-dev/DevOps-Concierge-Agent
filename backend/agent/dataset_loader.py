import os
import sys
import json
import subprocess

def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing missing dependency: {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure required libraries are installed
install_and_import("datasets")
install_and_import("pandas")

from datasets import load_dataset

def download_coding_dataset(limit=500, output_path="backend/agent/coding_train_dataset.jsonl"):
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        print(f"Dataset already exists at {output_path} ({os.path.getsize(output_path)} bytes). Skipping download.")
        return True
    print("Connecting to Hugging Face Hub...")
    print("Streaming 'TokenBender/code_instructions_122k_alpaca_style' dataset...")
    
    try:
        # Load the dataset in streaming mode to avoid downloading gigabytes of data
        dataset = load_dataset("TokenBender/code_instructions_122k_alpaca_style", split="train", streaming=True)
        
        filtered_samples = []
        count = 0
        
        # Keywords to prioritize web-development, Next.js, React, Tailwind, Python, and scripting
        keywords = ["react", "next.js", "nextjs", "tailwind", "css", "html", "javascript", "js", "python", "script", "api", "json", "database"]
        
        print("Filtering for high-quality web development and scripting instructions...")
        for item in dataset:
            instruction = item.get("instruction", "") or ""
            input_text = item.get("input", "") or ""
            output_text = item.get("output", "") or ""
            
            combined_text = (instruction + " " + input_text).lower()
            
            # Check if it matches our target keywords and has substantial output
            if any(kw in combined_text for kw in keywords) and len(output_text) > 100:
                # Format into a clean Alpaca structure
                sample = {
                    "instruction": instruction.strip(),
                    "input": input_text.strip(),
                    "output": output_text.strip()
                }
                filtered_samples.append(sample)
                count += 1
                
                if count % 50 == 0:
                    print(f"  Processed {count}/{limit} samples...")
                
                if count >= limit:
                    break
        
        # Ensure target directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as JSONL
        with open(output_path, "w", encoding="utf-8") as f:
            for sample in filtered_samples:
                f.write(json.dumps(sample) + "\n")
                
        print(f"\nSuccess! Successfully saved {len(filtered_samples)} curated coding instruction samples to:")
        print(f"  -> {os.path.abspath(output_path)}")
        return True
        
    except Exception as e:
        print(f"Error streaming dataset from Hugging Face: {e}")
        # Fallback: create a basic synthetic dataset if streaming fails
        print("Creating a high-quality fallback dataset locally...")
        create_fallback_dataset(output_path)
        return False

def create_fallback_dataset(output_path):
    fallback_data = [
        {
            "instruction": "Write a glassmorphic React navigation bar with a search input and profile avatar using Tailwind CSS.",
            "input": "",
            "output": "import React, { useState } from 'react';\n\nexport default function Navbar() {\n  const [search, setSearch] = useState('');\n  return (\n    <nav className=\"sticky top-0 z-50 backdrop-blur-md bg-zinc-950/70 border-b border-zinc-800/60 px-6 py-4 flex items-center justify-between\">\n      <span className=\"text-xl font-bold text-white\">DevOps<span className=\"text-violet-500\">Concierge</span></span>\n      <input\n        type=\"text\"\n        placeholder=\"Search...\"\n        value={search}\n        onChange={(e) => setSearch(e.target.value)}\n        className=\"bg-zinc-900 text-white px-4 py-2 rounded-full border border-zinc-800 focus:outline-none focus:border-violet-500\"\n      />\n    </nav>\n  );\n}"
        },
        {
            "instruction": "Create a Python script that monitors a directory for file changes and logs them to a file.",
            "input": "",
            "output": "import time\nfrom watchdog.observers import Observer\nfrom watchdog.events import FileSystemEventHandler\n\nclass LogHandler(FileSystemEventHandler):\n    def on_modified(self, event):\n        if not event.is_directory:\n            print(f'File modified: {event.src_path}')\n\nif __name__ == '__main__':\n    event_handler = LogHandler()\n    observer = Observer()\n    observer.schedule(event_handler, path='.', recursive=False)\n    observer.start()\n    try:\n        while True:\n            time.sleep(1)\n    except KeyboardInterrupt:\n        observer.stop()\n    observer.join()"
        }
    ]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for sample in fallback_data:
            f.write(json.dumps(sample) + "\n")
    print(f"Fallback dataset saved to {output_path}")

if __name__ == "__main__":
    download_coding_dataset()
