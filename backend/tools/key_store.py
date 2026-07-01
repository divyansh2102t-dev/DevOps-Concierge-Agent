import os
import json
from cryptography.fernet import Fernet

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
KEY_FILE = os.path.join(BASE_DIR, ".keys.key")
STORE_FILE = os.path.join(BASE_DIR, ".keys.json")

VALID_KEY_NAMES = ["GEMINI_API_KEY", "HUGGINGFACE_API_KEY", "GITHUB_TOKEN", "VERCEL_TOKEN", "PROJECTS_DIR", "API_KEYS_QUEUE", "NEON_API_KEY", "RENDER_TOKEN", "DISABLED_KEYS"]


def _get_cipher():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    with open(KEY_FILE, "rb") as f:
        key = f.read()
    return Fernet(key)


def _load_store():
    if not os.path.exists(STORE_FILE):
        return {}
    cipher = _get_cipher()
    with open(STORE_FILE, "r") as f:
        data = json.load(f)
    result = {}
    for k, v in data.items():
        try:
            result[k] = cipher.decrypt(v.encode()).decode()
        except Exception:
            result[k] = ""
    return result


def _save_store(data):
    cipher = _get_cipher()
    encrypted = {}
    for k, v in data.items():
        encrypted[k] = cipher.encrypt(v.encode()).decode()
    with open(STORE_FILE, "w") as f:
        json.dump(encrypted, f, indent=2)


def set_key(name, value):
    if name not in VALID_KEY_NAMES:
        raise ValueError(f"Invalid key name. Must be one of: {VALID_KEY_NAMES}")
    store = _load_store()
    store[name] = value
    _save_store(store)


def get_key(name):
    store = _load_store()
    if name != "DISABLED_KEYS":
        disabled_val = store.get("DISABLED_KEYS") or "[]"
        try:
            import json
            disabled_list = json.loads(disabled_val)
            if name in disabled_list:
                return None
        except Exception:
            pass
    return store.get(name)


def delete_key(name):
    store = _load_store()
    if name in store:
        del store[name]
        _save_store(store)
        return True
    return False


def list_keys():
    store = _load_store()
    disabled_keys_val = store.get("DISABLED_KEYS") or "[]"
    try:
        disabled_keys = json.loads(disabled_keys_val)
    except Exception:
        disabled_keys = []
        
    result = {}
    for name in VALID_KEY_NAMES:
        if name == "DISABLED_KEYS":
            continue
        if name in store and store[name]:
            val = store[name]
            is_enabled = name not in disabled_keys
            if name == "PROJECTS_DIR":
                result[name] = {
                    "configured": True,
                    "preview": val,
                    "enabled": True
                }
            elif name == "API_KEYS_QUEUE":
                try:
                    queue = json.loads(val)
                    masked_queue = []
                    for item in queue:
                        k_val = item.get("value", "")
                        masked_val = k_val[:4] + "****" + k_val[-4:] if len(k_val) > 8 else "****"
                        masked_queue.append({
                            "id": item.get("id"),
                            "provider": item.get("provider"),
                            "label": item.get("label"),
                            "preview": masked_val,
                            "enabled": item.get("enabled", True)
                        })
                    result[name] = {
                        "configured": True,
                        "queue": masked_queue
                    }
                except Exception:
                    result[name] = {
                        "configured": True,
                        "queue": []
                    }
            else:
                result[name] = {
                    "configured": True,
                    "preview": val[:4] + "****" + val[-4:] if len(val) > 8 else "****",
                    "enabled": is_enabled
                }
        else:
            if name == "PROJECTS_DIR":
                result[name] = {
                    "configured": True,
                    "preview": os.path.join(os.path.expanduser("~"), "DevOps-Concierge-Projects"),
                    "enabled": True
                }
            elif name == "API_KEYS_QUEUE":
                result[name] = {
                    "configured": False,
                    "queue": []
                }
            else:
                result[name] = {"configured": False, "preview": None, "enabled": False}
    return result


def get_all_keys():
    return _load_store()
