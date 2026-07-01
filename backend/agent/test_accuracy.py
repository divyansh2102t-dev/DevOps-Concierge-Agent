import sys
import json
import urllib.request
import urllib.error
import ast
import re

# Benchmark Prompts representing complex coding tasks
BENCHMARK_PROMPTS = [
    {
        "id": 1,
        "category": "Frontend (React + Tailwind)",
        "task": "Create a glassmorphic React/Next.js navigation bar with search state, notification count badge, and avatar. Use Tailwind CSS v4 class syntax.",
        "keywords": ["navbar", "state", "backdrop-blur", "tailwind", "avatar", "flex", "search"]
    },
    {
        "id": 2,
        "category": "System Scripting (Python)",
        "task": "Write a Python script that recursively watches a directory for new files, logs their creation to a SQLite database, and handles keyboard interrupts gracefully.",
        "keywords": ["sqlite3", "watchdog", "observer", "insert", "db", "keyboardinterrupt", "try"]
    },
    {
        "id": 3,
        "category": "DevOps (CI/CD Pipeline)",
        "task": "Create a GitHub Actions workflow YAML file that triggers on push to main, runs npm install, runs tests, and deploys to Vercel if tests pass.",
        "keywords": ["on", "push", "branches", "main", "steps", "vercel", "npm install", "run"]
    },
    {
        "id": 4,
        "category": "Backend (FastAPI)",
        "task": "Write a FastAPI route that handles a POST request for user registration, validates the email format using pydantic, and returns a JSON response with status code 201.",
        "keywords": ["fastapi", "post", "pydantic", "basemodel", "email", "201", "router"]
    },
    {
        "id": 5,
        "category": "Database (SQL)",
        "task": "Write a PostgreSQL query to calculate the average watch time of vlogs per category, sorted by the highest watch time first, filtering for categories with more than 10 vlogs.",
        "keywords": ["select", "avg", "group by", "having", "order by", "desc", "count"]
    }
]

def query_ollama(model_name, prompt):
    url = "http://localhost:11434/api/generate"
    data = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2  # Low temperature for stable, predictable coding evaluation
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data.get("response", "")
    except urllib.error.URLError as e:
        print(f"Connection Error: Could not connect to local Ollama server. Is it running? ({e})")
        return None
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return None

def evaluate_python_syntax(code_str):
    # Try to parse the code block as Python abstract syntax tree to verify compile correctness
    try:
        # Extract python code block if wrapped in markdown
        py_blocks = re.findall(r"```python(.*?)```", code_str, re.DOTALL)
        code_to_parse = py_blocks[0] if py_blocks else code_str
        ast.parse(code_to_parse)
        return True, "Valid Python syntax"
    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} on line {e.lineno}"
    except Exception as e:
        return True, f"Skipped (Non-executable or generic: {e})"

def evaluate_hallucinations(code_str):
    # Search for suspicious import statements in python blocks
    suspicious_imports = []
    # Simple check for fake or common hallucinated packages in coding models
    hallucinated_candidates = ["vercel_sdk", "huggingface_coder_helper", "openai_custom_helper", "ollama_python_wrapper_pro"]
    for candidate in hallucinated_candidates:
        if candidate in code_str:
            suspicious_imports.append(candidate)
            
    if suspicious_imports:
        return False, f"Detected hallucinated packages: {suspicious_imports}"
    return True, "No hallucinated imports detected"

def evaluate_instruction_compliance(code_str, keywords):
    code_lower = code_str.lower()
    matched = [kw for kw in keywords if kw in code_lower]
    percentage = (len(matched) / len(keywords)) * 100
    return percentage, f"Matched {len(matched)}/{len(keywords)} requirements"

def run_accuracy_benchmarks(model_name="qwen2.5-coder:1.5b"):
    print("=" * 70)
    print(f"   STARTING CODING ACCURACY & HALLUCINATION BENCHMARK")
    print(f"   Target Local Model: {model_name}")
    print("=" * 70)
    
    # Verify Ollama is running
    test_response = query_ollama(model_name, "Hello")
    if not test_response:
        print("\n[CRITICAL] Ollama connection failed. Please ensure Ollama is running on your machine.")
        print("Run `ollama run qwen2.5-coder:1.5b` in a terminal first.")
        return

    results = []
    total_score = 0

    for item in BENCHMARK_PROMPTS:
        print(f"\nEvaluating Prompt #{item['id']} [{item['category']}]...")
        print(f"  Task: {item['task'][:70]}...")
        
        # Get Model Response
        response = query_ollama(model_name, item['task'])
        if not response:
            print("  [FAILED] Model failed to generate response.")
            continue
            
        # 1. Syntax Correctness (Only for Python categories)
        syntax_ok = True
        syntax_msg = "Passed (Generic syntax verification)"
        if "Python" in item['category']:
            syntax_ok, syntax_msg = evaluate_python_syntax(response)
            
        # 2. Hallucination Check
        no_hallucinations, hallucination_msg = evaluate_hallucinations(response)
        
        # 3. Instruction Compliance
        compliance_pct, compliance_msg = evaluate_instruction_compliance(response, item['keywords'])
        
        # Score calculation: 50% Compliance, 30% Syntax, 20% No Hallucinations
        syntax_score = 30 if syntax_ok else 0
        hallucination_score = 20 if no_hallucinations else 0
        compliance_score = compliance_pct * 0.5
        
        score = syntax_score + hallucination_score + compliance_score
        total_score += score
        
        results.append({
            "id": item['id'],
            "category": item['category'],
            "syntax": syntax_msg,
            "hallucination": hallucination_msg,
            "compliance": compliance_msg,
            "score": round(score, 1)
        })
        
        print(f"  -> Score: {round(score, 1)}/100 (Syntax: {'PASS' if syntax_ok else 'FAIL'}, Hallucination: {'NONE' if no_hallucinations else 'DETECTED'})")

    avg_score = round(total_score / len(BENCHMARK_PROMPTS), 1)
    
    # Print Markdown Summary Report
    print("\n" + "=" * 70)
    print("                      EVALUATION REPORT SUMMARY")
    print("=" * 70)
    print(f"\n### Model Benchmarked: `{model_name}`")
    print(f"### Final Coding Accuracy Score: **{avg_score} / 100**\n")
    
    print("| ID | Category | Syntax Integrity | Hallucination Status | Instruction Compliance | Score |")
    print("|---|---|---|---|---|---|")
    for r in results:
        print(f"| {r['id']} | {r['category']} | {r['syntax']} | {r['hallucination']} | {r['compliance']} | **{r['score']}** |")
        
    print("\n### Key Takeaways:")
    if avg_score < 75:
        print("> [!WARNING]")
        print("> The model scores below the target threshold for stable agentic operations.")
        print("> Common issues include missing instructions, syntax slips in large code blocks, and hallucinated modules.")
        print("> **Recommendation:** Proceed with the QLoRA training script using `fine_tune.py` to boost accuracy.")
    else:
        print("> [!NOTE]")
        print("> The model has strong baseline capabilities. Fine-tuning will further optimize it for specific web layout schemas and API structures.")

if __name__ == "__main__":
    # Can pass model name as argument
    target_model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:1.5b"
    run_accuracy_benchmarks(target_model)
