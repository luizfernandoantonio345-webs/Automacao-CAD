import requests, json, time, sys

B = "http://localhost:8000"
results = []

def log(msg):
    print(msg, flush=True)
    results.append(msg)

log("=== ENGENHARIA CAD QA AUDIT RESULTS ===")
log(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# ── NEW ENDPOINTS ──
log("\n--- NEW ENDPOINTS ---")
for ep in ["/insights", "/history", "/logs"]:
    r = requests.get(f"{B}{ep}", timeout=5)
    d = r.json() if r.status_code == 200 else {}
    log(f"GET {ep}: {r.status_code} type={type(d).__name__}")

r = requests.post(f"{B}/generate", json={"tipo": "piping", "norma": "N-58"}, timeout=10)
d = r.json() if r.status_code == 200 else {}
log(f"POST /generate: {r.status_code} keys={list(d.keys()) if isinstance(d, dict) else ''}")

r = requests.post(f"{B}/excel", timeout=5)
log(f"POST /excel: {r.status_code}")

r = requests.get(f"{B}/project-draft", params={"company": "Test", "part_name": "Valve"}, timeout=5)
log(f"GET /project-draft: {r.status_code}")

r = requests.get(f"{B}/project-draft-from-text", params={"prompt": "draw a pipe"}, timeout=5)
log(f"GET /project-draft-from-text: {r.status_code}")

r = requests.post(f"{B}/project-draft-feedback", json={"prompt": "a", "feedback": "ok", "company": "x", "part_name": "y", "code": "z"}, timeout=5)
log(f"POST /project-draft-feedback: {r.status_code}")

r = requests.post(f"{B}/jobs/stress/porticos-50", timeout=5)
d = r.json() if r.status_code == 200 else {}
jids = d.get("job_ids", [])
log(f"POST /jobs/stress: {r.status_code} job_ids_count={len(jids)}")

# ── AUTH FULL ──
log("\n--- AUTH TESTS ---")
r = requests.post(f"{B}/login", json={"email": "tony@engenharia-cad.com", "senha": "123"}, timeout=10)
log(f"Login email/senha: {r.status_code}")
tok = r.json().get("access_token", "") if r.status_code == 200 else ""

r = requests.post(f"{B}/login", json={"username": "tony", "password": "123"}, timeout=10)
log(f"Login username/pw: {r.status_code}")

r = requests.post(f"{B}/login", json={"email": "x@x", "senha": "wrong"}, timeout=5)
log(f"Login wrong creds: {r.status_code}")

r = requests.post(f"{B}/login", json={}, timeout=5)
log(f"Login empty: {r.status_code}")

r = requests.post(f"{B}/auth/register", json={"email": f"qa_{int(time.time())}@x.com", "senha": "123", "empresa": "QA"}, timeout=10)
log(f"Register new: {r.status_code}")

r = requests.post(f"{B}/auth/register", json={"email": "tony@engenharia-cad.com", "senha": "123", "empresa": "X"}, timeout=5)
log(f"Register dup: {r.status_code}")

r = requests.post(f"{B}/auth/demo", timeout=5)
log(f"Demo login: {r.status_code}")

r = requests.get(f"{B}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=5)
log(f"auth/me valid: {r.status_code}")

r = requests.get(f"{B}/auth/me", timeout=5)
log(f"auth/me no tok: {r.status_code}")

r = requests.get(f"{B}/auth/me", headers={"Authorization": "Bearer garbage"}, timeout=5)
log(f"auth/me bad tok: {r.status_code}")

# ── HEALTH/SYSTEM/AI ──
log("\n--- HEALTH/SYSTEM/AI ---")
r = requests.get(f"{B}/health", timeout=5)
log(f"health: {r.status_code}")

r = requests.get(f"{B}/system", timeout=5)
d = r.json() if r.status_code == 200 else {}
log(f"system: {r.status_code} cpu={d.get('cpu')} ram={d.get('ram')} disk={d.get('disk')}")

r = requests.get(f"{B}/ai", params={"q": "test"}, timeout=10)
log(f"ai query: {r.status_code}")

r = requests.get(f"{B}/ai/health", timeout=5)
log(f"ai/health: {r.status_code}")

r = requests.get(f"{B}/ai/diagnostics", timeout=5)
log(f"ai/diagnostics: {r.status_code}")

# ── REFINERIES ──
log("\n--- REFINERIES ---")
r = requests.get(f"{B}/api/refineries", timeout=5)
d = r.json()
log(f"refineries: {r.status_code} type={type(d).__name__} keys={list(d.keys()) if isinstance(d, dict) else 'array'}")

# ── AUTOCAD ──
log("\n--- AUTOCAD ---")
for ep in ["health", "status", "buffer"]:
    r = requests.get(f"{B}/api/autocad/{ep}", timeout=5)
    log(f"autocad/{ep}: {r.status_code}")

for ep, payload in [
    ("draw-pipe", {"points": [[0,0,0],[100,0,0]], "diameter": 6, "layer": "PIPE-6"}),
    ("draw-line", {"start": [0,0,0], "end": [100,100,0], "layer": "TEST"}),
    ("send-command", {"command": "ZOOM E"}),
    ("create-layers", None),
    ("save", None),
]:
    if payload:
        r = requests.post(f"{B}/api/autocad/{ep}", json=payload, timeout=10)
    else:
        r = requests.post(f"{B}/api/autocad/{ep}", timeout=10)
    log(f"autocad/{ep}: {r.status_code}")

# ── SSE ──
log("\n--- SSE ---")
for sse in ["/sse/system", "/sse/telemetry", "/sse/notifications", "/sse/ai-stream"]:
    try:
        r = requests.get(f"{B}{sse}", stream=True, timeout=3)
        ct = r.headers.get("content-type", "")
        log(f"SSE {sse}: {r.status_code} type={'event-stream' if 'event-stream' in ct else ct}")
        r.close()
    except requests.exceptions.ReadTimeout:
        log(f"SSE {sse}: connected (read timeout - normal for SSE)")
    except Exception as e:
        log(f"SSE {sse}: ERROR {e}")

# ── SECURITY ──
log("\n--- SECURITY ---")
r = requests.post(f"{B}/login", json={"email": "' OR 1=1 --", "senha": "' OR 1=1 --"}, timeout=5)
log(f"SQLi login: {r.status_code} (expect 401)")

r = requests.get(f"{B}/ai", params={"q": "<script>alert(1)</script>"}, timeout=5)
has_script = "<script>" in json.dumps(r.json())
log(f"XSS ai: reflected={has_script}")

r = requests.post(f"{B}/api/autocad/config/bridge", json={"path": "..\\..\\Windows\\System32"}, timeout=5)
log(f"Path traversal: {r.status_code}")

r = requests.get(f"{B}/auth/me", headers={"Authorization": "Basic dGVzdDp0ZXN0"}, timeout=5)
log(f"Auth bypass Basic: {r.status_code} (expect 401/403)")

for hidden in ["/admin", "/debug", "/.env", "/config"]:
    r = requests.get(f"{B}{hidden}", timeout=3)
    log(f"Hidden {hidden}: {r.status_code}")

# ── 10 CYCLES ──
log("\n--- 10 USER CYCLES ---")
cycle_times = []
cycle_errors = 0
for i in range(1, 11):
    t1 = time.time()
    ok = True
    try:
        r = requests.post(f"{B}/login", json={"email": "tony@engenharia-cad.com", "senha": "123"}, timeout=10)
        if r.status_code != 200: ok = False
        tok2 = r.json().get("access_token", "") if r.status_code == 200 else ""
        
        for ep in ["/auth/me", "/system", "/insights", "/history", "/logs", "/api/refineries", "/api/autocad/health", "/health"]:
            if ep == "/auth/me":
                r = requests.get(f"{B}{ep}", headers={"Authorization": f"Bearer {tok2}"}, timeout=5)
            else:
                r = requests.get(f"{B}{ep}", timeout=5)
            if r.status_code != 200: ok = False
        
        r = requests.get(f"{B}/ai", params={"q": f"cycle {i}"}, timeout=10)
        if r.status_code != 200: ok = False
    except:
        ok = False
    dt = time.time() - t1
    cycle_times.append(dt)
    if not ok: cycle_errors += 1
    log(f"  Cycle {i:2d}: {dt:.2f}s {'OK' if ok else 'FAIL'}")

log(f"  Passed: {10 - cycle_errors}/10")
log(f"  Avg: {sum(cycle_times)/len(cycle_times):.2f}s Min: {min(cycle_times):.2f}s Max: {max(cycle_times):.2f}s")

# ── PERF ──
log("\n--- PERFORMANCE (5 samples) ---")
for name, ep, payload in [
    ("health", "/health", None),
    ("system", "/system", None),
    ("login", "/login", {"email": "tony@engenharia-cad.com", "senha": "123"}),
    ("ai", "/ai?q=perf", None),
    ("insights", "/insights", None),
    ("refineries", "/api/refineries", None),
]:
    times = []
    for _ in range(5):
        t1 = time.time()
        try:
            if payload:
                r = requests.post(f"{B}{ep}", json=payload, timeout=10)
            else:
                r = requests.get(f"{B}{ep}", timeout=10)
            times.append(time.time() - t1)
        except:
            times.append(10.0)
    avg_ms = sum(times) / len(times) * 1000
    log(f"  {name:15s}: avg={avg_ms:7.1f}ms")

log("\n=== AUDIT COMPLETE ===")

# Write to file
with open("qa_results.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
