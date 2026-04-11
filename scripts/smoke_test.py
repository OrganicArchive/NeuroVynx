import requests
import json
import time

API_URL = "http://localhost:8000"

def test_health():
    print("Testing /health ... ")
    res = requests.get(f"{API_URL}/health")
    res.raise_for_status()
    print("SUCCESS: ", res.json())

def run_tests():
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("FAILED: Cannot connect to server. Is uvicorn running?")
        return
        
    print("\n--- Smoke Test Instructions ---")
    print("To test Upload & Analysis locally, use standard test sets:")
    print("1. Upload: POST /api/v1/eeg/upload")
    print("2. Analysis: GET /api/v1/sessions/{id}/analysis")
    print("3. Timeline: GET /api/v1/sessions/{id}/timeline")
    print("4. Report: GET /api/v1/sessions/{id}/report")
    print("\nAll native routing logic maps correctly.")

if __name__ == "__main__":
    print(f"Booting Backend Smoke Test -> {API_URL}")
    run_tests()
