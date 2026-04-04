import json, urllib.request, urllib.error, sys

base = "https://automacao-cadbackend.vercel.app"
passed = 0
failed = 0

def call(path, method="GET", data=None, headers=None):
    global passed, failed
    headers = headers or {}
    payload = None
    if data is not None:
        payload = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            body = r.read().decode("utf-8","ignore")
            print(f"  PASS  {method} {path} -> {r.status}  {body[:120]}")
            passed += 1
            return r.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8","ignore")
        print(f"  FAIL  {method} {path} -> HTTP {e.code}  {body[:300]}")
        failed += 1
        return e.code, body

# Public endpoints
call("/")
call("/health")
call("/openapi.json")

# Auth
_, db = call("/auth/demo", "POST", {})
token = json.loads(db)["access_token"]
H = {"Authorization": f"Bearer {token}"}

_, rb = call("/auth/register", "POST", {"email":"test_deploy@test.com","senha":"TestPass123","empresa":"Test"})
# May already exist — that's OK

call("/login", "POST", {"email":"test_deploy@test.com","senha":"TestPass123"})

# Authenticated read
call("/auth/me", headers=H)
call("/system", headers=H)
call("/projects", headers=H)
call("/insights", headers=H)
call("/history", headers=H)
call("/project-stats", headers=H)

# CAD routes
call("/api/refineries", headers=H)
call("/api/refineries/REGAP", headers=H)

# Generate — needs real user (demo is blocked)
_, lb = call("/login", "POST", {"email":"test_deploy@test.com","senha":"TestPass123"})
real_token = None
try:
    real_token = json.loads(lb).get("access_token")
except:
    pass

if real_token:
    RH = {"Authorization": f"Bearer {real_token}"}
    call("/generate", "POST", {
        "diameter": 6, "length": 1000, "company": "TEST", "part_name": "PIPE",
        "code": "T-001", "executar": False
    }, RH)
    call("/projects", headers=RH)
else:
    print("  SKIP  POST /generate (no real user token)")

# AI / watchdog
call("/ai/health", headers=H)
call("/logs", headers=H)

print(f"\n{'='*50}")
print(f"Total: {passed+failed}  PASSED: {passed}  FAILED: {failed}")
sys.exit(1 if failed else 0)
