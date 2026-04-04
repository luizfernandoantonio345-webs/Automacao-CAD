import json
import urllib.request
import urllib.error

base = "https://automacao-cadbackend.vercel.app"
passed = []
failed = []


def req(path, method="GET", data=None, headers=None, expect=200):
    headers = headers or {}
    payload = None
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", "ignore")
            status = response.status
            ok = status == expect
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}] {method} {path} -> {status}")
            if not ok:
                failed.append(f"{method} {path} expected {expect} got {status}")
            else:
                passed.append(f"{method} {path}")
            return status, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        ok = exc.code == expect
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {method} {path} -> {exc.code}  {body[:200]}")
        if ok:
            passed.append(f"{method} {path}")
        else:
            failed.append(f"{method} {path} expected {expect} got {exc.code}: {body[:120]}")
        return exc.code, body
    except Exception as exc:
        print(f"  [FAIL] {method} {path} -> ERROR: {exc}")
        failed.append(f"{method} {path} ERROR: {exc}")
        return None, str(exc)


print("=== PUBLIC ENDPOINTS ===")
req("/")
req("/health")
req("/docs")
req("/openapi.json")
req("/redoc")

print("\n=== AUTH FLOWS ===")
# Register a real test user
reg_email = "testuser_probe@engcad.test"
_, reg_body = req("/auth/register", "POST", {"email": reg_email, "senha": "TestPass123!", "empresa": "Probe Corp"}, expect=200)
if "already" in reg_body.lower() or "registrado" in reg_body.lower():
    print(f"  [INFO] /auth/register: user already exists, will login instead")
    _, login_body = req("/login", "POST", {"email": reg_email, "senha": "TestPass123!"}, expect=200)
    reg_token = json.loads(login_body).get("access_token") if login_body.startswith("{") else None
else:
    reg_token = json.loads(reg_body).get("access_token") if reg_body.startswith("{") else None

_, demo_body = req("/auth/demo", "POST", {})
demo_token = json.loads(demo_body).get("access_token") if demo_body.startswith("{") else None

print("\n=== LOGIN ===")
_, lo = req("/login", "POST", {"email": "tony@engenharia-cad.com", "senha": "qualquer"}, expect=401)

print("\n=== AUTHENTICATED ENDPOINTS (demo token) ===")
if demo_token:
    h = {"Authorization": f"Bearer {demo_token}"}
    req("/auth/me", headers=h)
    req("/system", headers=h)
    req("/projects", headers=h)
    req("/insights", headers=h)
    req("/history", headers=h)
    req("/project-stats", headers=h)
    req("/logs", headers=h)
    req("/api/refineries", headers=h)
    req("/api/refineries/REGAP", headers=h)
    req("/ai/health", headers=h)
    req("/generate", "POST", {"diameter": 6, "length": 1000, "company": "X", "part_name": "Y", "code": "T-1"}, headers=h, expect=403)

print("\n=== AUTHENTICATED ENDPOINTS (real user token) ===")
if reg_token:
    h2 = {"Authorization": f"Bearer {reg_token}"}
    req("/auth/me", headers=h2)
    req("/generate", "POST", {"diameter": 6, "length": 1000, "company": "TestCo", "part_name": "PIPE-01", "code": "T-001", "executar": False}, headers=h2)
    req("/projects", headers=h2)

print("\n=== SECURITY: BLOCKED WITHOUT TOKEN ===")
req("/projects", expect=401)
req("/system", expect=401)
req("/auth/me", expect=401)

print("\n=== SUMMARY ===")
print(f"  Passed: {len(passed)}")
print(f"  Failed: {len(failed)}")
for f in failed:
    print(f"  !! {f}")
