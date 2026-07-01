import os
import sys
import time
import shutil
import subprocess

def run_automation():
    print("=" * 70)
    print("     AUTOMATED DEVOPS CODER GGUF CONVERSION & OLLAMA REGISTRATION")
    print("=" * 70)
    
    merged_dir = os.path.abspath("backend/agent/merged_devops_qwen")
    gguf_path = os.path.join(merged_dir, "devops-coder.gguf")
    modelfile_path = os.path.abspath("Modelfile")
    
    # Use a unique timestamp suffix to prevent folder clashes and handle Windows file locks
    timestamp = int(time.time())
    temp_clone_dir = f"llama_cpp_temp_{timestamp}"
    
    # 1. Install GGUF and SentencePiece dependencies
    print("\n1. Installing/Verifying 'gguf' and 'sentencepiece' packages via pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "gguf", "sentencepiece"])
        print("-> 'gguf' and 'sentencepiece' are ready.")
    except Exception as e:
        print(f"-> Warning/Error installing dependencies: {e}")
        
    # 2. Clone llama.cpp with depth=1
    print(f"\n2. Cloning lightweight llama.cpp repository into '{temp_clone_dir}'...")
    try:
        subprocess.check_call(["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp", temp_clone_dir])
        print("-> llama.cpp scripts cloned successfully.")
    except Exception as e:
        print(f"-> Error cloning llama.cpp scripts: {e}")
        return
        
    # 3. Run GGUF Conversion
    print("\n3. Converting merged model to GGUF format (this will take a minute)...")
    try:
        python_exe = sys.executable
        converter_script = os.path.abspath(os.path.join(temp_clone_dir, "convert_hf_to_gguf.py"))
        
        cmd = [
            python_exe,
            converter_script,
            merged_dir,
            "--outfile",
            gguf_path
        ]
        print(f"Running command: {' '.join(cmd)}")
        # Run it with the temp clone directory as working directory to resolve relative imports
        subprocess.check_call(cmd, cwd=os.path.abspath(temp_clone_dir))
        print(f"-> GGUF model successfully created at: {gguf_path}")
    except Exception as e:
        print(f"-> Error during GGUF conversion: {e}")
        # Clean up clone on failure
        cleanup_temp(temp_clone_dir)
        return
        
    # 4. Clean up temporary clone directory
    cleanup_temp(temp_clone_dir)
        
    # 5. Write Modelfile pointing directly to the GGUF file
    print("\n4. Creating Modelfile for Ollama...")
    # Normalize paths for Windows
    gguf_path_norm = gguf_path.replace("\\", "/")
    modelfile_content = f"FROM {gguf_path_norm}\n"
    
    try:
        with open(modelfile_path, "w", encoding="utf-8") as f:
            f.write(modelfile_content)
        print(f"-> Modelfile created at: {modelfile_path}")
    except Exception as e:
        print(f"-> Error writing Modelfile: {e}")
        return
        
    # 6. Register model in Ollama
    print("\n5. Registering model in local Ollama service...")
    try:
        # First stop any running instance of devops-concierge-coder
        subprocess.run(["ollama", "stop", "devops-concierge-coder"], capture_output=True)
        
        # Now create the new model
        cmd_create = ["ollama", "create", "devops-concierge-coder", "-f", modelfile_path]
        print(f"Running command: {' '.join(cmd_create)}")
        subprocess.check_call(cmd_create)
        print("\n" + "=" * 70)
        print("SUCCESS: devops-concierge-coder is registered and integrated!")
        print("It will now automatically appear in your frontend Model Selector!")
        print("=" * 70)
    except Exception as e:
        print(f"-> Error registering model in Ollama: {e}")
        print("Make sure your local Ollama background service is running.")

def cleanup_temp(path):
    print("\nCleaning up temporary files...")
    # Try to delete temporary clone directory.
    # If it fails due to Windows file locks, it will catch it and exit gracefully.
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        print("-> Temporary files cleaned up.")
    except Exception as e:
        print(f"-> Note: Temporary directory '{path}' could not be fully deleted due to active IDE indexing locks. It is safe to ignore this.")

if __name__ == "__main__":
    run_automation()
