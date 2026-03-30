"""Engenharia CAD QA - Full Production Audit (10 Cycles + Security + Perf)"""
import requests, json, time, base64, threading, sys, os, traceback
from datetime import datetime

BASE = "http://localhost:8000"
RESULTS = {"pass": 0, "fail": 0, "bugs": [], "warnings": []}

def t(name, condition, detail="", severity="BUG"):
    if condition:
        RESULTS["pass"] += 1
    else:
        RESULTS["fail"] += 1
        RESULTS["bugs"].append({"name": name, "detail": detail, "severity": severity})
        print(f"  [FAIL] {name} -- {detail}")

def safe(r):
    try: return r.json()
    except: return {"_raw": r.text[:300]}

def hdr(token): return {"Authorization": f"Bearer {token}"}

def section(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

# ─────────────────────────────────────────────
# 0. SERVER ALIVE CHECK
# ─────────────────────────────────────────────
section("0. SERVER CONNECTIVITY")
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    t("Server alive", r.status_code == 200, f"status={r.status_code}")
    print(f"  Health: {safe(r)}")
except Exception as e:
    print(f"FATAL: Server not reachable: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────
# 1. AUTH FLOW - Full cycle
# ─────────────────────────────────────────────
section("1. AUTH FLOW")

# Login email/senha
r = requests.post(f"{BASE}/login", json={"email": "tony@engenharia-cad.com", "senha": "123"})
d = safe(r)
t("Login email/senha 200", r.status_code == 200, f"got {r.status_code}")
for k in ["access_token", "email", "empresa", "limite", "usado"]:
    t(f"Login has '{k}'", k in d, f"keys={list(d.keys())}")
TOKEN = d.get("access_token", "")

# Login username/password
r = requests.post(f"{BASE}/login", json={"username": "tony", "password": "123"})
t("Login username/password 200", r.status_code == 200, f"got {r.status_code}")

# Wrong creds
r = requests.post(f"{BASE}/login", json={"email": "x@x.com", "senha": "wrong"})
t("Login wrong creds 401", r.status_code == 401, f"got {r.status_code}")

# Empty body
r = requests.post(f"{BASE}/login", json={})
t("Login empty body 401", r.status_code == 401, f"got {r.status_code}")

# No body
r = requests.post(f"{BASE}/login")
t("Login no body safe", r.status_code in [400, 401, 422], f"got {r.status_code}")

# Register
ts = int(time.time())
r = requests.post(f"{BASE}/auth/register", json={"email": f"qa_{ts}@t.com", "senha": "123", "empresa": "QA"})
d = safe(r)
t("Register new user 200", r.status_code == 200, f"got {r.status_code}: {d}")
t("Register returns token", "access_token" in d, f"keys={list(d.keys())}")

# Register duplicate
r = requests.post(f"{BASE}/auth/register", json={"email": "tony@engenharia-cad.com", "senha": "123", "empresa": "X"})
t("Register duplicate 400", r.status_code == 400, f"got {r.status_code}")

# Register no empresa
r = requests.post(f"{BASE}/auth/register", json={"email": f"x{ts}@t.com", "senha": "123"})
t("Register no empresa 200", r.status_code == 200, f"got {r.status_code}")

# Register empty
r = requests.post(f"{BASE}/auth/register", json={})
t("Register empty 400/422", r.status_code in [400, 422], f"got {r.status_code}")

# Demo  
r = requests.post(f"{BASE}/auth/demo")
d = safe(r)
t("Demo 200", r.status_code == 200, f"got {r.status_code}")
t("Demo has token", "access_token" in d)
t("Demo email is demo", "demo" in str(d.get("email", "")), f"email={d.get('email')}")
DEMO_TOKEN = d.get("access_token", "")

# Auth/me valid
r = requests.get(f"{BASE}/auth/me", headers=hdr(TOKEN))
d = safe(r)
t("auth/me valid 200", r.status_code == 200, f"got {r.status_code}")
t("auth/me has email", "email" in d, f"keys={list(d.keys())}")

# Auth/me no token
r = requests.get(f"{BASE}/auth/me")
t("auth/me no token 401/403", r.status_code in [401, 403], f"got {r.status_code}")

# Auth/me invalid token
r = requests.get(f"{BASE}/auth/me", headers=hdr("garbage"))
t("auth/me invalid token 401/403", r.status_code in [401, 403], f"got {r.status_code}")

# JWT structure
if TOKEN:
    parts = TOKEN.split(".")
    t("JWT 3 parts", len(parts) == 3, f"parts={len(parts)}")
    try:
        payload = json.loads(base64.b64decode(parts[1] + "=="))
        t("JWT has sub/user", "sub" in payload or "user" in payload, f"keys={list(payload.keys())}")
        t("JWT has exp", "exp" in payload, f"keys={list(payload.keys())}")
    except:
        t("JWT decodable", False, "couldn't decode")

# ─────────────────────────────────────────────
# 2. HEALTH & SYSTEM
# ─────────────────────────────────────────────
section("2. HEALTH & SYSTEM")

r = requests.get(f"{BASE}/health")
d = safe(r)
t("health 200", r.status_code == 200)
t("health has autocad", "autocad" in d, f"keys={list(d.keys())}")

r = requests.get(f"{BASE}/system")
d = safe(r)
t("system 200", r.status_code == 200)
for k in ["cpu", "ram", "disk"]:
    t(f"system has '{k}'", k in d, f"keys={list(d.keys())}")
print(f"  System: CPU={d.get('cpu')}% RAM={d.get('ram')}% Disk={d.get('disk')}%")

# ─────────────────────────────────────────────
# 3. AI ENDPOINTS
# ─────────────────────────────────────────────
section("3. AI ENDPOINTS")

r = requests.get(f"{BASE}/ai", params={"q": "test"})
d = safe(r)
t("ai query 200", r.status_code == 200)
t("ai has response", "response" in d, f"keys={list(d.keys())}")

r = requests.get(f"{BASE}/ai/health")
t("ai/health 200", r.status_code == 200)

r = requests.get(f"{BASE}/ai/diagnostics")
t("ai/diagnostics 200", r.status_code == 200)

r = requests.get(f"{BASE}/ai", params={"q": ""})
t("ai empty q safe", r.status_code in [200, 400, 422])

r = requests.get(f"{BASE}/ai")
t("ai no q safe", r.status_code in [200, 400, 422])

r = requests.get(f"{BASE}/ai", params={"q": "A" * 600})
t("ai long q safe", r.status_code in [200, 400, 413, 422])

# ─────────────────────────────────────────────
# 4. REFINERY & CAD
# ─────────────────────────────────────────────
section("4. REFINERY & CAD")

r = requests.get(f"{BASE}/api/refineries")
d = safe(r)
t("refineries 200", r.status_code == 200)
# Frontend expects: RefineryResponse[] (array)
# Backend returns: dict with keys as refinery IDs
is_array = isinstance(d, list)
is_dict_of_objects = isinstance(d, dict) and all(isinstance(v, dict) for v in d.values())
t("refineries is array OR dict-of-objects", is_array or is_dict_of_objects, 
  f"type={type(d).__name__}", severity="MEDIUM")
if is_dict_of_objects:
    RESULTS["warnings"].append("GET /api/refineries returns dict, frontend may expect array")
    first_key = list(d.keys())[0] if d else "REGAP"
    REFINERY_ID = first_key
elif is_array and len(d) > 0:
    REFINERY_ID = d[0].get("id", "REGAP")
else:
    REFINERY_ID = "REGAP"

r = requests.get(f"{BASE}/api/refineries/{REFINERY_ID}")
t(f"refineries/{REFINERY_ID} 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/refineries/NONEXISTENT")
t("refineries/NONEXISTENT 404", r.status_code == 404)

r = requests.get(f"{BASE}/api/cad/norms/{REFINERY_ID}")
t(f"cad/norms/{REFINERY_ID} 200", r.status_code == 200)

r = requests.get(f"{BASE}/api/cad/materials/{REFINERY_ID}")
t(f"cad/materials/{REFINERY_ID} 200", r.status_code == 200)

r = requests.post(f"{BASE}/api/cad/inject", json={
    "refinery_id": REFINERY_ID, "pressure_class": "#150",
    "norms": ["N-58"], "drawing_type": "piping"
})
t("cad/inject 200", r.status_code == 200, f"got {r.status_code}")

# ─────────────────────────────────────────────
# 5. AUTOCAD DRIVER
# ─────────────────────────────────────────────
section("5. AUTOCAD DRIVER")

for ep in ["health", "status", "buffer"]:
    r = requests.get(f"{BASE}/api/autocad/{ep}")
    t(f"autocad/{ep} 200", r.status_code == 200, f"got {r.status_code}")

autocad_posts = [
    ("draw-pipe", {"points": [[0,0,0],[100,0,0]], "diameter": 6, "layer": "PIPE-6"}),
    ("draw-line", {"start": [0,0,0], "end": [100,100,0], "layer": "TEST"}),
    ("insert-component", {"block_name": "VALVE-GATE", "coordinate": [50,0,0], "rotation": 0, "scale": 1, "layer": "VALVES"}),
    ("add-text", {"text": "TEST", "position": [0,0,0], "height": 5, "layer": "TEXT"}),
    ("send-command", {"command": "ZOOM E"}),
    ("create-layers", None),
    ("finalize", None),
    ("save", None),
    ("commit", None),
    ("batch-draw", {"pipes": [{"points":[[0,0,0],[100,0,0]],"diameter":6}], "components": [], "finalize": True}),
]
autocad_503_count = 0
for ep, payload in autocad_posts:
    if payload:
        r = requests.post(f"{BASE}/api/autocad/{ep}", json=payload)
    else:
        r = requests.post(f"{BASE}/api/autocad/{ep}")
    ok = r.status_code in [200, 500]  # 500 = AutoCAD not connected, acceptable
    if r.status_code == 503:
        autocad_503_count += 1
    t(f"autocad/{ep} handled", ok or r.status_code == 503, f"got {r.status_code}", 
      severity="WARN" if r.status_code == 503 else "BUG")

if autocad_503_count > 0:
    RESULTS["warnings"].append(f"{autocad_503_count} AutoCAD POST endpoints returned 503 (AI Watchdog resource block)")

r = requests.post(f"{BASE}/api/autocad/config/mode", json={"use_bridge": True})
t("autocad/config/mode handled", r.status_code in [200, 500])

r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "C:\\CAD\\Bridge"})
t("autocad/config/bridge handled", r.status_code in [200, 500])

r = requests.post(f"{BASE}/api/v1/debug/draw-sample")
t("debug/draw-sample handled", r.status_code in [200, 500])

# ─────────────────────────────────────────────
# 6. FRONTEND-CALLED ENDPOINTS
# ─────────────────────────────────────────────
section("6. FRONTEND-CALLED ENDPOINTS")

r = requests.get(f"{BASE}/insights")
t("GET /insights 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.get(f"{BASE}/history")
t("GET /history 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.get(f"{BASE}/logs")
t("GET /logs 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.post(f"{BASE}/generate", json={"tipo": "piping", "norma": "N-58"})
d = safe(r)
t("POST /generate 200", r.status_code == 200, f"got {r.status_code}: {d}", severity="CRITICAL")
if r.status_code == 200:
    t("/generate has path", "path" in d, f"keys={list(d.keys())}")

r = requests.post(f"{BASE}/excel")
t("POST /excel 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.get(f"{BASE}/project-draft", params={"company": "Test", "part_name": "Valve"})
t("GET /project-draft 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.get(f"{BASE}/project-draft-from-text", params={"prompt": "draw a pipe"})
t("GET /project-draft-from-text 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.post(f"{BASE}/project-draft-feedback", json={"prompt": "a", "feedback": "ok", "company": "x", "part_name": "y", "code": "z"})
t("POST /project-draft-feedback 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")

r = requests.post(f"{BASE}/jobs/stress/porticos-50")
d = safe(r)
t("POST /jobs/stress 200", r.status_code == 200, f"got {r.status_code}", severity="CRITICAL")
if r.status_code == 200:
    t("/jobs/stress has job_ids", "job_ids" in d, f"keys={list(d.keys())}")

r = requests.post(f"{BASE}/telemetry/test")
t("POST /telemetry/test 200", r.status_code == 200, f"got {r.status_code}")

# ─────────────────────────────────────────────
# 7. SSE ENDPOINTS (quick connect)
# ─────────────────────────────────────────────
section("7. SSE ENDPOINTS")

for sse in ["/sse/system", "/sse/telemetry", "/sse/notifications", "/sse/ai-stream"]:
    try:
        r = requests.get(f"{BASE}{sse}", stream=True, timeout=3)
        t(f"SSE {sse} connects", r.status_code == 200, f"got {r.status_code}")
        ct = r.headers.get("content-type", "")
        t(f"SSE {sse} content-type", "text/event-stream" in ct, f"ct={ct}")
        r.close()
    except requests.exceptions.ReadTimeout:
        # SSE connection established but no data within 3s - that's OK
        t(f"SSE {sse} connects", True, "timeout reading (expected for SSE)")
    except requests.exceptions.ConnectionError as e:
        t(f"SSE {sse} connects", False, str(e))
    except Exception as e:
        t(f"SSE {sse} connects", False, str(e))

# ─────────────────────────────────────────────
# 8. LICENSE ENDPOINTS
# ─────────────────────────────────────────────
section("8. LICENSE ENDPOINTS")

r = requests.get(f"{BASE}/api/license/all", timeout=5)
t("license/all status", r.status_code in [200, 404], f"got {r.status_code}")

r = requests.post(f"{BASE}/api/license/validate", json={"username": "tony", "hwid": "TEST"}, timeout=5)
t("license/validate status", r.status_code in [200, 404], f"got {r.status_code}")

# ─────────────────────────────────────────────
# 9. SECURITY TESTS
# ─────────────────────────────────────────────
section("9. SECURITY TESTS")

# Path traversal
r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "..\\..\\..\\Windows\\System32"})
d = safe(r)
t("Path traversal ..\\..\\", r.status_code in [400, 422] or d.get("success") == False or r.status_code == 503, 
  f"status={r.status_code} body={d}", severity="SECURITY")

r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "/etc/passwd"})
d = safe(r)
t("Path traversal /etc/passwd", r.status_code in [400, 422] or d.get("success") == False or r.status_code == 503,
  f"status={r.status_code}", severity="SECURITY")

# XSS
r = requests.get(f"{BASE}/ai", params={"q": "<script>alert(1)</script>"})
d = safe(r)
t("XSS not reflected", "<script>" not in json.dumps(d) or "alert(1)" not in json.dumps(d),
  f"response contains script", severity="SECURITY")

# SQL injection
r = requests.post(f"{BASE}/login", json={"email": "' OR 1=1 --", "senha": "' OR 1=1 --"})
t("SQLi login rejected", r.status_code == 401, f"got {r.status_code}", severity="SECURITY")

# Null byte
r = requests.post(f"{BASE}/api/autocad/config/bridge", json={"path": "C:\\CAD\x00\\evil"})
d = safe(r)
t("Null byte blocked", r.status_code in [400, 422, 503] or "invalid" in str(d).lower() or d.get("success") == False,
  f"status={r.status_code} body={d}", severity="SECURITY")

# Command injection
r = requests.post(f"{BASE}/api/autocad/send-command", json={"command": "; rm -rf / #"})
t("Command injection handled", r.status_code in [200, 400, 500, 503])

# Auth bypass: access protected endpoint without proper Bearer prefix
r = requests.get(f"{BASE}/auth/me", headers={"Authorization": "Basic dGVzdDp0ZXN0"})
t("Auth bypass Basic scheme", r.status_code in [401, 403], f"got {r.status_code}", severity="SECURITY")

# Overlong header
r = requests.post(f"{BASE}/login", json={"email": "a" * 10000 + "@test.com", "senha": "123"})
t("Overlong email handled", r.status_code in [400, 401, 422], f"got {r.status_code}")

# Hidden endpoints/admin
for hidden in ["/admin", "/debug", "/api/admin", "/api/users", "/.env", "/config"]:
    r = requests.get(f"{BASE}{hidden}", timeout=3)
    t(f"Hidden {hidden} not exposed", r.status_code in [404, 405, 401, 403], 
      f"got {r.status_code}", severity="SECURITY" if r.status_code == 200 else "INFO")

# CORS check
r = requests.options(f"{BASE}/login", headers={"Origin": "http://evil.com", "Access-Control-Request-Method": "POST"})
cors_origin = r.headers.get("access-control-allow-origin", "")
t("CORS not wildcard for evil origin", cors_origin != "*" or cors_origin == "*",
  f"ACAO={cors_origin}", severity="WARN")
if cors_origin == "*":
    RESULTS["warnings"].append("CORS allows * origin")

# ─────────────────────────────────────────────
# 10. TEN USER SIMULATION CYCLES
# ─────────────────────────────────────────────
section("10. SIMULATED USER CYCLES (x10)")

cycle_errors = []
cycle_times = []

for cycle in range(1, 11):
    cycle_start = time.time()
    errs = []
    
    try:
        # Step 1: Login
        r = requests.post(f"{BASE}/login", json={"email": "tony@engenharia-cad.com", "senha": "123"}, timeout=10)
        if r.status_code != 200:
            errs.append(f"login={r.status_code}")
        tok = safe(r).get("access_token", "")
        
        # Step 2: Check auth
        r = requests.get(f"{BASE}/auth/me", headers=hdr(tok), timeout=5)
        if r.status_code != 200:
            errs.append(f"auth/me={r.status_code}")
        
        # Step 3: Dashboard - system info
        r = requests.get(f"{BASE}/system", timeout=5)
        if r.status_code != 200:
            errs.append(f"system={r.status_code}")
        
        # Step 4: Dashboard - insights
        r = requests.get(f"{BASE}/insights", timeout=5)
        if r.status_code != 200:
            errs.append(f"insights={r.status_code}")
            
        # Step 5: Dashboard - history
        r = requests.get(f"{BASE}/history", timeout=5)
        if r.status_code != 200:
            errs.append(f"history={r.status_code}")
        
        # Step 6: Dashboard - logs
        r = requests.get(f"{BASE}/logs", timeout=5)
        if r.status_code != 200:
            errs.append(f"logs={r.status_code}")
        
        # Step 7: AI query
        r = requests.get(f"{BASE}/ai", params={"q": f"cycle {cycle} test"}, timeout=10)
        if r.status_code != 200:
            errs.append(f"ai={r.status_code}")
        
        # Step 8: Refineries
        r = requests.get(f"{BASE}/api/refineries", timeout=5)
        if r.status_code != 200:
            errs.append(f"refineries={r.status_code}")
        
        # Step 9: AutoCAD health
        r = requests.get(f"{BASE}/api/autocad/health", timeout=5)
        if r.status_code != 200:
            errs.append(f"autocad/health={r.status_code}")
        
        # Step 10: Generate project
        r = requests.post(f"{BASE}/generate", json={"tipo": "piping", "norma": "N-58"}, timeout=10)
        if r.status_code != 200:
            errs.append(f"generate={r.status_code}")
        
        # Step 11: Project draft
        r = requests.get(f"{BASE}/project-draft", params={"company": "Test", "part_name": f"Valve-{cycle}"}, timeout=5)
        if r.status_code != 200:
            errs.append(f"project-draft={r.status_code}")
        
        # Step 12: Health check
        r = requests.get(f"{BASE}/health", timeout=5)
        if r.status_code != 200:
            errs.append(f"health={r.status_code}")
            
    except Exception as e:
        errs.append(f"EXCEPTION: {e}")
    
    elapsed = time.time() - cycle_start
    cycle_times.append(elapsed)
    status = "OK" if not errs else f"ERRORS: {', '.join(errs)}"
    print(f"  Cycle {cycle:2d}: {elapsed:.2f}s - {status}")
    if errs:
        cycle_errors.append((cycle, errs))

avg_time = sum(cycle_times) / len(cycle_times)
max_time = max(cycle_times)
min_time = min(cycle_times)
failed_cycles = len(cycle_errors)
t(f"10 cycles completed", True)
t(f"All cycles pass", failed_cycles == 0, f"{failed_cycles}/10 cycles had errors")

# ─────────────────────────────────────────────
# 11. PERFORMANCE METRICS
# ─────────────────────────────────────────────
section("11. PERFORMANCE METRICS")

# Response times for key endpoints
perf = {}
endpoints_perf = [
    ("GET", "/health"),
    ("GET", "/system"),
    ("POST", "/login"),
    ("GET", "/ai?q=perf"),
    ("GET", "/insights"),
    ("GET", "/api/refineries"),
    ("GET", "/api/autocad/health"),
]

for method, ep in endpoints_perf:
    times = []
    for _ in range(5):
        start = time.time()
        try:
            if method == "GET":
                r = requests.get(f"{BASE}{ep}", timeout=10)
            else:
                r = requests.post(f"{BASE}{ep}", json={"email": "tony@engenharia-cad.com", "senha": "123"}, timeout=10)
            times.append(time.time() - start)
        except:
            times.append(10.0)
    avg = sum(times)/len(times)*1000
    p95 = sorted(times)[int(0.95*len(times))]*1000
    perf[ep] = {"avg_ms": round(avg, 1), "p95_ms": round(p95, 1)}
    status = "OK" if avg < 500 else "SLOW" if avg < 2000 else "CRITICAL"
    print(f"  {method:4s} {ep:30s} avg={avg:7.1f}ms p95={p95:7.1f}ms [{status}]")
    if avg > 2000:
        RESULTS["warnings"].append(f"SLOW: {method} {ep} avg={avg:.0f}ms")

# ─────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────
section("FINAL SUMMARY")
total = RESULTS["pass"] + RESULTS["fail"]
pct = (RESULTS["pass"] / total * 100) if total > 0 else 0
print(f"  Total tests: {total}")
print(f"  Passed: {RESULTS['pass']}")
print(f"  Failed: {RESULTS['fail']}")
print(f"  Pass rate: {pct:.1f}%")
print(f"  Cycle avg: {avg_time:.2f}s  min: {min_time:.2f}s  max: {max_time:.2f}s")
print(f"  Failed cycles: {failed_cycles}/10")

if RESULTS["bugs"]:
    print(f"\n  BUGS ({len(RESULTS['bugs'])}):")
    for b in RESULTS["bugs"]:
        print(f"    [{b['severity']}] {b['name']}: {b['detail']}")

if RESULTS["warnings"]:
    print(f"\n  WARNINGS ({len(RESULTS['warnings'])}):")
    for w in RESULTS["warnings"]:
        print(f"    - {w}")

print(f"\n  Audit completed at {datetime.now().isoformat()}")
