
import requests
import json

BASE_URL = "http://localhost:5000"

def test_health():
    print("Testing /health...")
    res = requests.get(f"{BASE_URL}/health")
    print(res.json())

def test_sync_obs():
    print("\nTesting /sync-observation...")
    payload = {
        "sheet_name": "Rapport_Veille_Auto",
        "row_idx": 2,
        "text": "TEST OBSERVATION - " + str(requests.utils.quote(str(requests.utils.time.time())))
    }
    res = requests.post(f"{BASE_URL}/sync-observation", json=payload)
    print(res.json())

if __name__ == "__main__":
    try:
        test_health()
        test_sync_obs()
    except Exception as e:
        print(f"Error: {e}")
