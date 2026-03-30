"""Baseline test — AFTER P0 fixes (http.client for Python 3.14 compat)"""
import json
import http.client

HOST = "localhost"
PORT = 8000

tests = [
    ("POST", "/login", {"email": "tony@engenharia-cad.com", "senha": "123"}),
    ("POST", "/generate", {"tipo": "piping", "norma": "N-58"}),
    ("POST", "/api/cad/inject", {"refinery_id": "REGAP", "pressure_class": "#150", "norms": ["N-58"], "drawing_type": "piping"}),
    ("POST", "/api/autocad/draw-pipe", {"points": [[0,0,0],[100,0,0]], "diameter": 6, "layer": "PIPE-6"}),
    ("POST", "/api/autocad/finalize", None),
    ("POST", "/api/autocad/commit", None),
    ("POST", "/api/autocad/config/bridge", {"path": "..\\..\\Windows\\System32"}),
    ("POST", "/api/autocad/config/bridge", {"path": "/etc/passwd"}),
    ("POST", "/api/autocad/config/bridge", {"path": "C:\\CAD\\Bridge"}),
    ("GET", "/insights", None),
    ("GET", "/health", None),
    ("GET", "/system", None),
]

def do_request(method, path, payload=None):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode("utf-8") if payload else (b"{}" if method == "POST" else None)
    conn.request(method, path, body=body, headers=headers if method == "POST" else {})
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    try:
        return resp.status, json.loads(data)
    except Exception:
        return resp.status, {"raw": data[:200]}

print("=" * 70)
print("AFTER P0 FIXES — BASELINE TEST")
print("=" * 70)
for method, ep, payload in tests:
    try:
        code, body = do_request(method, ep, payload)
        extra = ""
        if code == 503:
            reason = (body or {}).get("detail", "")[:60]
            extra = f" [WATCHDOG BLOCKED: {reason}]"
        elif code == 422:
            detail = (body or {}).get("detail", "")
            if isinstance(detail, list):
                msg = detail[0].get("msg", "")[:60] if detail else ""
            else:
                msg = str(detail)[:60]
            extra = f" [VALIDATION REJECTED: {msg}]"
        elif code == 200 and "config/bridge" in ep:
            extra = f" [ACCEPTED: success={body.get('success') if body else '?'}]"
        print(f"  {method:4s} {ep:45s} -> {code}{extra}")
    except Exception as e:
        print(f"  {method:4s} {ep:45s} -> ERROR: {e}")

# Check current RAM
code, sys_data = do_request("GET", "/system")
if sys_data:
    print(f"\n  System: CPU={sys_data.get('cpu')}% RAM={sys_data.get('ram')}% Disk={sys_data.get('disk')}%")
print("=" * 70)
