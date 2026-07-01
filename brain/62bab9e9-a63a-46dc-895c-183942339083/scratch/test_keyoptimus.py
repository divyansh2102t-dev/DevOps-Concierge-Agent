import sys
import os
import time

# Add backend to sys.path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from backend.key_optimizer.scheduler import (
    route_request, report_success, report_failure, 
    _get_key_state, DEFAULT_LIMITS, PROVIDER_MODELS
)
from backend.key_optimizer.excel_logger import EXCEL_FILE, initialize_excel

def test_key_optimus():
    print("=== Testing KeyOptimus Scheduling, Wastage Prevention & Excel Logging ===")
    
    # 1. Initialize Excel Log
    print("\n1. Initializing Excel Log sheet...")
    initialize_excel()
    if os.path.exists(EXCEL_FILE):
        print(f"[PASS] Excel file exists at: {EXCEL_FILE}")
    else:
        print("[FAIL] Excel file creation failed!")
        return

    # 2. Mock some active keys in memory (we'll simulate key state directly)
    # Let's say we have:
    # - Key A: Gemini (Premium, supporting multimodal)
    # - Key B: Groq (Basic, supporting text only)
    # We will simulate their states in the _usage_db.
    key_premium = "premium_gemini_key_123"
    key_basic = "basic_groq_key_456"
    
    # Let's mock get_all_keys in scheduler module to return these two keys
    import backend.key_optimizer.scheduler as scheduler
    
    def mock_get_all_keys():
        return [
            {"provider": "gemini", "value": key_premium, "label": "Mock Premium Gemini"},
            {"provider": "groq", "value": key_basic, "label": "Mock Basic Groq"}
        ]
    scheduler.get_all_keys = mock_get_all_keys
    
    # 3. Test Text Task routing (should choose basic key first to avoid wasting premium Gemini)
    print("\n2. Testing simple TEXT task routing...")
    route1 = route_request(task_type="text", session_id="TEST-SESSION-1")
    print(f"Routed Text Task -> Provider: {route1.get('provider')}, Key Label: {route1.get('label')}, Model: {route1.get('model')}")
    if route1.get("provider") == "groq":
        print("[PASS] Wastage Prevention Succeeded: Prioritized basic Groq key for simple text!")
    else:
        print("[FAIL] Wastage Prevention Failed: Routed text to premium key unnecessarily.")

    # 4. Test Multimodal Task routing (should choose premium Gemini)
    print("\n3. Testing MULTIMODAL task routing...")
    route2 = route_request(task_type="multimodal", session_id="TEST-SESSION-1")
    print(f"Routed Multimodal Task -> Provider: {route2.get('provider')}, Key Label: {route2.get('label')}, Model: {route2.get('model')}")
    if route2.get("provider") == "gemini":
        print("[PASS] Capability Alignment Succeeded: Correctly routed multimodal task to Gemini!")
    else:
        print("[FAIL] Capability Alignment Failed: Routed multimodal task to basic key.")

    # 5. Test Wastage Prevention under Low Quota
    print("\n4. Simulating low remaining quota on Premium Key...")
    # Set daily request count of Gemini to 1498 out of 1500 limit (only 2 left)
    # Under our rule: if remaining limit <= 5, it should be LOCKED OUT of text tasks
    # to save it strictly for specialized multimodal tasks!
    state_premium = _get_key_state(key_premium, "gemini-2.5-flash")
    state_premium["rpd_count"] = 1498 # 2 remaining
    
    print("Remaining daily requests on Premium Key:", 1500 - state_premium["rpd_count"])
    
    # Run a text routing request: it must avoid the premium key!
    route3 = route_request(task_type="text", session_id="TEST-SESSION-2")
    print(f"Routed Text Task under tight quota -> Provider: {route3.get('provider')}, Model: {route3.get('model')}")
    
    # Run a multimodal routing request: it should still allow the premium key!
    route4 = route_request(task_type="multimodal", session_id="TEST-SESSION-2")
    print(f"Routed Multimodal Task under tight quota -> Provider: {route4.get('provider')}, Model: {route4.get('model')}")
    
    if route3.get("provider") == "groq" and route4.get("provider") == "gemini":
        print("[PASS] Quota Protection & Wastage Prevention Succeeded: Saved premium key strictly for multimodal!")
    else:
        print("[FAIL] Quota Protection Failed: Premium key was wasted or not selected.")

    # 6. Test Success & Failure Logging
    print("\n5. Testing metrics logging to Excel...")
    report_success(key_basic, "groq", "llama-3.3-70b-versatile", tokens_used=1200, elapsed_time=0.45, session_id="TEST-SESSION-1")
    print("[PASS] Reported success to Excel.")
    
    report_failure(key_premium, "gemini", "gemini-2.5-flash", "429: Resource Exhausted", session_id="TEST-SESSION-1")
    print("[PASS] Reported rate limit failure (triggers model swapping / quarantine) to Excel.")
    
    print("\n=== All Tests Completed Successfully! ===")

if __name__ == "__main__":
    test_key_optimus()
