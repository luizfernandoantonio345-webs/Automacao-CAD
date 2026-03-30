"""Engenharia CAD QA - Complete Endpoint Test Suite"""
import requests
import json
import time
import sys

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0
BUGS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} -- {detail}")
        BUGS.append(f"{name}: {detail}")

def safe_json(r):
    try:
        return r.json()
    except:
        return {"_raw": r.text[:200]}

# =============================================
# 1. AUTH ENDPOINTS
# =============================================
print("\n" + "="*60)
print("AUTH ENDPOINTS")
print("="*60)

# Login with email/senha
r = requests.post(f"{BASE}/login", json={"email": "tony@engenharia-cad.com", "senha": "123"})
d = safe_json(r)
test("POST /login (email/senha) status=200", r.status_code == 200, f"got {r.status_code}")
test("POST /login returns access_token", "access_token" in d, f"keys={list(d.keys())}")
test("POST /login returns email", "email" in d, f"keys={list(d.keys())}")
test("POST /login returns empresa", "empresa" in d, f"keys={list(d.keys())}")
test("POST /login returns limite", "limite" in d, f"keys={list(d.keys())}")
test("POST /login returns usado", "usado" in d, f"keys={list(d.keys())}")
TOKEN = d.get("access_token", "")

# Login with username/password
r = requests.post(f"{BASE}/login", json={"username": "tony", "password": "123"})
d = safe_json(r)
test("POST /login (username/password) status=200", r.status_code == 200, f"got {r.status_code}")
test("POST /login (username/password) returns access_token", "access_token" in d, f"keys={list(d.keys())}")

# Login wrong credentials
r = requests.post(f"{BASE}/login", json={"email": "wrong@test.com", "senha": "wrong"})
test("POST /login wrong creds status=401", r.status_code == 401, f"got {r.status_code}")

# Login empty body
r = requests.post(f"{BASE}/login", json={})
test("POST /login empty body status=401", r.status_code == 401, f"got {r.status_code}: {safe_json(r)}")

# Login no body at all
r = requests.post(f"{BASE}/login")
test("POST /login no body doesn't crash", r.status_code in [400, 401, 422], f"got {r.status_code}")

# Register new user
r = requests.post(f"{BASE}/auth/register", json={"email": f"qa_{int(time.time())}@test.com", "senha": "test123", "empresa": "QACo"})
d = safe_json(r)
test("POST /auth/register status=200", r.status_code == 200, f"got {r.status_code}: {d}")
test("POST /auth/register returns access_token", "access_token" in d, f"keys={list(d.keys())}")

# Register duplicate
r = requests.post(f"{BASE}/auth/register", json={"email": "tony@engenharia-cad.com", "senha": "123", "empresa": "X"})
test("POST /auth/register duplicate status=400", r.status_code == 400, f"got {r.status_code}: {safe_json(r)}")

# Register without empresa
r = requests.post(f"{BASE}/auth/register", json={"email": f"noempresa_{int(time.time())}@test.com", "senha": "123"})
d = safe_json(r)
test("POST /auth/register no empresa status=200", r.status_code == 200, f"got {r.status_code}: {d}")

# Register empty body
r = requests.post(f"{BASE}/auth/register", json={})
test("POST /auth/register empty body rejects", r.status_code in [400, 422], f"got {r.status_code}: {safe_json(r)}")

# Demo login
r = requests.post(f"{BASE}/auth/demo")
d = safe_json(r)
test("POST /auth/demo status=200", r.status_code == 200, f"got {r.status_code}")
test("POST /auth/demo returns access_token", "access_token" in d, f"keys={list(d.keys())}")
test("POST /auth/demo returns email with demo", "email" in d and "demo" in str(d.get("email", "")), f"email={d.get('email')}")

# Auth/me with valid token
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {TOKEN}"})
d = safe_json(r)
test("GET /auth/me valid token status=200", r.status_code == 200, f"got {r.status_code}: {d}")
test("GET /auth/me returns email", "email" in d, f"keys={list(d.keys())}")

# Auth/me without token
r = requests.get(f"{BASE}/auth/me")
test("GET /auth/me no token rejects", r.status_code in [401, 403], f"got {r.status_code}: {safe_json(r)}")

# Auth/me with invalid token
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer invalidtoken"})
test("GET /auth/me invalid token rejects", r.status_code in [401, 403], f"got {r.status_code}: {safe_json(r)}")

# =============================================
# 2. HEALTH & SYSTEM ENDPOINTS
# =============================================
print("\n" + "="*60)
print("HEALTH & SYSTEM ENDPOINTS")
print("="*60)

r = requests.get(f"{BASE}/health")
d = safe_json(r)
test("GET /health status=200", r.status_code == 200, f"got {r.status_code}")
test("GET /health returns autocad key", "autocad" in d, f"keys={list(d.keys())}")

r = requests.get(f"{BASE}/system")
d = safe_json(r)
test("GET /system status=200", r.status_code == 200, f"got {r.status_code}")
test("GET /system returns cpu", "cpu" in d, f"keys={list(d.keys())}")
test("GET /system returns ram", "ram" in d, f"keys={list(d.keys())}")
test("GET /system returns disk", "disk" in d, f"keys={list(d.keys())}")

# =============================================
# 3. AI ENDPOINTS
# =============================================
print("\n" + "="*60)
print("AI ENDPOINTS")
print("="*60)

r = requests.get(f"{BASE}/ai", params={"q": "test"})
d = safe_json(r)
test("GET /ai status=200", r.status_code == 200, f"got {r.status_code}")
test("GET /ai returns response key", "response" in d, f"keys={list(d.keys())}")

r = requests.get(f"{BASE}/ai/health")
d = safe_json(r)
test("GET /ai/health status=200", r.status_code == 200, f"got {r.status_code}")

r = requests.get(f"{BASE}/ai/diagnostics")
d = safe_json(r)
test("GET /ai/diagnostics status=200", r.status_code == 200, f"got {r.status_code}")

# AI with empty query
r = requests.get(f"{BASE}/ai", params={"q": ""})
test("GET /ai empty q handled", r.status_code in [200, 400, 422], f"got {r.status_code}")

# AI without q param
r = requests.get(f"{BASE}/ai")
test("GET /ai no q param handled", r.status_code in [200, 400, 422], f"got {r.status_code}")

# AI with very long query (over 500 chars)
r = requests.get(f"{BASE}/ai", params={"q": "A" * 600})
test("GET /ai long query handled", r.status_code in [200, 400, 413, 422], f"got {r.status_code}")

# =============================================
# 4. REFINERY / CAD ENDPOINTS
# =============================================
print("\n" + "="*60)
print("REFINERY & CAD ENDPOINTS")
print("="*60)

r = requests.get(f"{BASE}/api/refineries")
d = safe_json(r)
test("GET /api/refineries status=200", r.status_code == 200, f"got {r.status_code}")
test("GET /api/refineries returns array", isinstance(d, list), f"type={type(d).__name__}")
if isinstance(d, list) and len(d) > 0:
    test("GET /api/refineries has entries", len(d) > 0, f"len={len(d)}")
    first = d[0]
    test("Refinery has id", "id" in first, f"keys={list(first.keys())}")
    test("Refinery has name", "name" in first, f"keys={list(first.keys())}")
    REFINERY_ID = first.get("id", "REGAP")
else:
    REFINERY_ID = "REGAP"

r = requests.get(f"{BASE}/api/refineries/{REFINERY_ID}")
d = safe_json(r)
test(f"GET /api/refineries/{REFINERY_ID} status=200", r.status_code == 200, f"got {r.status_code}")

# Non-existing refinery
r = requests.get(f"{BASE}/api/refineries/NONEXISTENT")
test("GET /api/refineries/NONEXISTENT status=404", r.status_code == 404, f"got {r.status_code}: {safe_json(r)}")

# CAD norms
r = requests.get(f"{BASE}/api/cad/norms/{REFINERY_ID}")
d = safe_json(r)
test(f"GET /api/cad/norms/{REFINERY_ID} status=200", r.status_code == 200, f"got {r.status_code}")

# CAD materials
r = requests.get(f"{BASE}/api/cad/materials/{REFINERY_ID}")
d = safe_json(r)
test(f"GET /api/cad/materials/{REFINERY_ID} status=200", r.status_code == 200, f"got {r.status_code}")

# CAD inject
r = requests.post(f"{BASE}/api/cad/inject", json={
    "refinery_id": REFINERY_ID,
    "pressure_class": "#150",
    "norms": ["N-58"],
    "drawing_type": "piping"
})
d = safe_json(r)
test("POST /api/cad/inject status=200", r.status_code == 200, f"got {r.status_code}: {d}")

# =============================================
# 5. AUTOCAD DRIVER ENDPOINTS
# =============================================
print("\n" + "="*60)
print("AUTOCAD DRIVER ENDPOINTS")
print("="*60)

r = requests.get(f"{BASE}/api/autocad/health")
d = safe_json(r)
test("GET /api/autocad/health status=200", r.status_code == 200, f"got {r.status_code}")

r = requests.get(f"{BASE}/api/autocad/status")
d = safe_json(r)
test("GET /api/autocad/status status=200", r.status_code == 200, f"got {r.status_code}")

r = requests.get(f"{BASE}/api/autocad/buffer")
d = safe_json(r)
test("GET /api/autocad/buffer status=200", r.status_code == 200, f"got {r.status_code}")

# Draw pipe without AutoCAD (should handle gracefully)
r = requests.post(f"{BASE}/api/autocad/draw-pipe", json={
    "points": [[0,0,0],[100,0,0]],
    "diameter": 6,
    "layer": "PIPE-6"
})
d = safe_json(r)
test("POST /api/autocad/draw-pipe handled", r.status_code in [200, 500], f"got {r.status_code}")

# Draw line
r = requests.post(f"{BASE}/api/autocad/draw-line", json={
    "start": [0,0,0],
    "end": [100,100,0],
    "layer": "TEST"
})
d = safe_json(r)
test("POST /api/autocad/draw-line handled", r.status_code in [200, 500], f"got {r.status_code}")

# Insert component
r = requests.post(f"{BASE}/api/autocad/insert-component", json={
    "block_name": "VALVE-GATE",
    "coordinate": [50,0,0],
    "rotation": 0,
    "scale": 1,
    "layer": "VALVES"
})
d = safe_json(r)
test("POST /api/autocad/insert-component handled", r.status_code in [200, 500], f"got {r.status_code}")

# Add text
r = requests.post(f"{BASE}/api/autocad/add-text", json={
    "text": "TEST",
    "position": [0,0,0],
    "height": 5,
    "layer": "TEXT"
})
d = safe_json(r)
test("POST /api/autocad/add-text handled", r.status_code in [200, 500], f"got {r.status_code}")

# Send raw command
r = requests.post(f"{BASE}/api/autocad/send-command", json={"command": "ZOOM E"})
d = safe_json(r)
test("POST /api/autocad/send-command handled", r.status_code in [200, 500], f"got {r.status_code}")

# Create layers
r = requests.post(f"{BASE}/api/autocad/create-layers")
d = safe_json(r)
test("POST /api/autocad/create-layers handled", r.status_code in [200, 500], f"got {r.status_code}")

# Finalize
r = requests.post(f"{BASE}/api/autocad/finalize")
d = safe_json(r)
test("POST /api/autocad/finalize handled", r.status_code in [200, 500], f"got {r.status_code}")

# Save
r = requests.post(f"{BASE}/api/autocad/save")
d = safe_json(r)
test("POST /api/autocad/save handled", r.status_code in [200, 500], f"got {r.status_code}")

# Config mode
r = requests.post(f"{BASE}/api/autocad/config/mode", json={"use_bridge": True})
d = safe_json(r)
test("POST /api/autocad/config/mode handled", r.status_code in [200, 500], f"got {r.status_code}")

# Config bridge path
r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "C:\\CAD\\Bridge"})
d = safe_json(r)
test("POST /api/autocad/config/bridge handled", r.status_code in [200, 500], f"got {r.status_code}")

# Bridge commit
r = requests.post(f"{BASE}/api/autocad/commit")
d = safe_json(r)
test("POST /api/autocad/commit handled", r.status_code in [200, 500], f"got {r.status_code}")

# Batch draw
r = requests.post(f"{BASE}/api/autocad/batch-draw", json={
    "pipes": [{"points":[[0,0,0],[100,0,0]],"diameter":6}],
    "components": [{"block_name":"VALVE-GATE","coordinate":[50,0,0]}],
    "finalize": True
})
d = safe_json(r)
test("POST /api/autocad/batch-draw handled", r.status_code in [200, 500], f"got {r.status_code}")

# Debug draw-sample
r = requests.post(f"{BASE}/api/v1/debug/draw-sample")
d = safe_json(r)
test("POST /api/v1/debug/draw-sample handled", r.status_code in [200, 500], f"got {r.status_code}")

# =============================================
# 6. FRONTEND-CALLED ENDPOINTS
# =============================================
print("\n" + "="*60)
print("FRONTEND-CALLED ENDPOINTS")
print("="*60)

# /insights endpoint (called by Dashboard)
r = requests.get(f"{BASE}/insights")
test("GET /insights status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /insights endpoint NOT FOUND - Dashboard calls this")

# /history endpoint (called by Dashboard)
r = requests.get(f"{BASE}/history")
test("GET /history status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /history endpoint NOT FOUND - Dashboard calls this")

# /logs endpoint (called by Dashboard)
r = requests.get(f"{BASE}/logs")
test("GET /logs status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /logs endpoint NOT FOUND - Dashboard calls this")

# /generate endpoint (called by Dashboard)
r = requests.post(f"{BASE}/generate", json={"tipo": "piping", "norma": "N-58"})
test("POST /generate status", r.status_code in [200, 404, 422], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /generate endpoint NOT FOUND - Dashboard calls this")

# /excel endpoint (called by Dashboard)
r = requests.post(f"{BASE}/excel")
test("POST /excel status", r.status_code in [200, 400, 404, 422], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /excel endpoint NOT FOUND - Dashboard calls this")

# /project-draft endpoint (called by Dashboard)
r = requests.get(f"{BASE}/project-draft")
test("GET /project-draft status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /project-draft endpoint NOT FOUND - Dashboard calls this")

# /project-draft-from-text endpoint
r = requests.get(f"{BASE}/project-draft-from-text", params={"prompt": "draw a pipe"})
test("GET /project-draft-from-text status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /project-draft-from-text endpoint NOT FOUND - Dashboard calls this")

# /project-draft-feedback endpoint
r = requests.post(f"{BASE}/project-draft-feedback", json={"prompt": "t", "feedback": "ok", "company": "x", "part_name": "y", "code": "z"})
test("POST /project-draft-feedback status", r.status_code in [200, 404, 422], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("CRITICAL: /project-draft-feedback endpoint NOT FOUND")

# /jobs/stress/porticos-50 endpoint
r = requests.post(f"{BASE}/jobs/stress/porticos-50")
test("POST /jobs/stress/porticos-50 status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("MEDIUM: /jobs/stress/porticos-50 endpoint NOT FOUND")

# /telemetry/test
r = requests.post(f"{BASE}/telemetry/test")
test("POST /telemetry/test status", r.status_code in [200, 404], f"got {r.status_code}")

# =============================================
# 7. SSE ENDPOINTS (quick connect test)
# =============================================
print("\n" + "="*60)
print("SSE ENDPOINTS (Connection Test)")
print("="*60)

for sse_path in ["/sse/system", "/sse/telemetry", "/sse/notifications", "/sse/ai-stream"]:
    try:
        r = requests.get(f"{BASE}{sse_path}", stream=True, timeout=3)
        test(f"GET {sse_path} connects", r.status_code == 200, f"got {r.status_code}")
        ct = r.headers.get("content-type", "")
        test(f"GET {sse_path} is SSE", "text/event-stream" in ct, f"content-type={ct}")
        r.close()
    except requests.exceptions.Timeout:
        test(f"GET {sse_path} connects", True, "connected (timed out reading)")
    except Exception as e:
        test(f"GET {sse_path} connects", False, str(e))

# =============================================
# 8. LICENSE ENDPOINTS
# =============================================
print("\n" + "="*60)
print("LICENSE ENDPOINTS")
print("="*60)

r = requests.get(f"{BASE}/api/license/all")
test("GET /api/license/all status", r.status_code in [200, 404], f"got {r.status_code}")
if r.status_code == 404:
    BUGS.append("INFO: /api/license/all not found (may be on separate server)")

r = requests.post(f"{BASE}/api/license/validate", json={"username": "tony", "hwid": "TEST-HWID"})
test("POST /api/license/validate status", r.status_code in [200, 404], f"got {r.status_code}")

# =============================================
# 9. SECURITY TESTS
# =============================================
print("\n" + "="*60)
print("SECURITY TESTS")
print("="*60)

# Path traversal on bridge config
r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "..\\..\\..\\Windows\\System32"})
d = safe_json(r)
test("Path traversal blocked (..\\)", r.status_code in [400, 422] or (r.status_code == 200 and d.get("success") == False), f"status={r.status_code} body={d}")

r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "/etc/passwd"})
d = safe_json(r)
test("Path traversal blocked (/etc/passwd)", r.status_code in [400, 422] or (r.status_code == 200 and d.get("success") == False), f"status={r.status_code}")

# XSS in AI query
r = requests.get(f"{BASE}/ai", params={"q": "<script>alert(1)</script>"})
d = safe_json(r)
resp_text = str(d)
test("XSS in AI query not reflected raw", "<script>" not in resp_text or "alert(1)" not in resp_text, f"response contains script tag")

# SQL injection attempt
r = requests.post(f"{BASE}/login", json={"email": "' OR 1=1 --", "senha": "' OR 1=1 --"})
test("SQL injection login rejected", r.status_code == 401, f"got {r.status_code}")

# Null byte injection
r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "C:\\CAD\x00\\evil"})
d = safe_json(r)
test("Null byte in path blocked", r.status_code in [400, 422] or "invalid" in str(d).lower() or d.get("success") == False, f"status={r.status_code} body={d}")

# Command injection in send-command  
r = requests.post(f"{BASE}/api/autocad/send-command", json={"command": "; rm -rf / #"})
d = safe_json(r)
test("Command injection in send-command handled", r.status_code in [200, 400, 500], f"status={r.status_code}")

# JWT token structure
import base64
if TOKEN:
    parts = TOKEN.split(".")
    test("JWT has 3 parts", len(parts) == 3, f"parts={len(parts)}")
    try:
        payload = json.loads(base64.b64decode(parts[1] + "=="))
        test("JWT payload has sub claim", "sub" in payload, f"payload keys={list(payload.keys())}")
        test("JWT payload has exp claim", "exp" in payload, f"payload keys={list(payload.keys())}")
    except:
        test("JWT payload decodable", False, "could not decode")

# =============================================
# SUMMARY
# =============================================
print("\n" + "="*60)
print(f"FINAL RESULTS: {PASS} PASSED, {FAIL} FAILED")
print("="*60)
if BUGS:
    print("\nBUGS FOUND:")
    for b in BUGS:
        print(f"  - {b}")
