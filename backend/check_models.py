import sqlite3
import os
import urllib.request
import json

# 1. Check active conversation model
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "concierge.db")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, model FROM conversations ORDER BY updated_at DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"Active Conversation ID: {row[0]}")
        print(f"Active Conversation Model: {row[1]}")
    conn.close()
else:
    print("Database not found!")

# 2. Check installed local Ollama models
print("\n--- INSTALLED OLLAMA MODELS ---")
try:
    with urllib.request.urlopen("http://localhost:11434/api/tags") as response:
        data = json.loads(response.read().decode())
        models = data.get("models", [])
        for m in models:
            print(f"- {m.get('name')} (Size: {m.get('size', 0) / (1024*1024):.1f} MB)")
except Exception as e:
    print(f"Failed to fetch local Ollama models: {e}")
