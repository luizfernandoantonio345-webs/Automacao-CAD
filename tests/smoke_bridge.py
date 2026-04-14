"""Quick bridge chain smoke test — run once and delete."""
import httpx
import json

BASE = "http://localhost:8000"

print("--- STEP 1: Enqueue ---")
r = httpx.post(f"{BASE}/api/bridge/send", json={"lisp_code": '(command "_LINE" "0,0" "100,100" "")', "operation": "test"}, timeout=5)
print(f"  HTTP {r.status_code}: {r.json()}")
cmd_id = r.json().get("id")

print("--- STEP 2: Pending ---")
r2 = httpx.get(f"{BASE}/api/bridge/pending", timeout=5)
data = r2.json()
print(f"  Count: {data['count']}")

print(f"--- STEP 3: ACK {cmd_id} ---")
r3 = httpx.post(f"{BASE}/api/bridge/ack/{cmd_id}", timeout=5)
print(f"  HTTP {r3.status_code}: {r3.json()}")

print("--- STEP 4: Verify empty ---")
r4 = httpx.get(f"{BASE}/api/bridge/pending", timeout=5)
print(f"  Pending after ACK: {r4.json()['count']}")

print("--- STEP 5: draw-pipe ---")
r5 = httpx.post(f"{BASE}/api/bridge/draw-pipe", json={"points": [[0,0,0],[500,0,0]], "diameter": 6}, timeout=5)
print(f"  HTTP {r5.status_code}: {r5.json()}")

print("--- STEP 6: Bridge status ---")
r6 = httpx.get(f"{BASE}/api/bridge/status", timeout=5)
print(json.dumps(r6.json(), indent=2))

print("\n=== BRIDGE CHAIN: ALL OK ===")
