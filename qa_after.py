"""AFTER P0 fixes — baseline test (http.client for Python 3.14)"""
import json
import http.client

HOST = "localhost"
PORT = 8000


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


tests = [
    ("POST", "/login", {"email": "tony@engenharia-cad.com", "senha": "123"}),
    ("POST", "/generate", {"tipo": "piping", "norma": "N-58"}),
    ("POST", "/api/cad/inject", {
        "refinery_id": "REGAP", "pressure_class": "#150",
        "norms": ["N-58"], "drawing_type": "piping",
    }),
    ("POST", "/api/autocad/draw-pipe", {
        "points": [[0, 0, 0], [100, 0, 0]], "diameter": 6, "layer": "PIPE-6",
    }),
    ("POST", "/api/autocad/finalize", None),
    ("POST", "/api/autocad/commit", None),
    # Path traversal attacks — should be REJECTED (422) after P0-B fix
    ("POST", "/api/autocad/config/bridge", {"path": "..\\..\\Windows\\System32"}),
    ("POST", "/api/autocad/config/bridge", {"path": "/etc/passwd"}),
    # Valid path — should be ACCEPTED (200) after P0-A fix (not blocked by watchdog)
    ("POST", "/api/autocad/config/bridge", {"path": "C:\\CAD\\Bridge"}),
    ("GET", "/insights", None),
    ("GET", "/health", None),
    ("GET", "/system", None),
]

print("=" * 70)
print("AFTER P0 FIXES - BASELINE TEST")
print("=" * 70)
for method, ep, payload in tests:
    try:
        code, body = do_request(method, ep, payload)
        extra = ""
        if code == 503:
            reason = (body or {}).get("detail", "")
            extra = " [WATCHDOG BLOCKED: {}]".format(str(reason)[:60])
        elif code == 422:
            detail = (body or {}).get("detail", "")
            if isinstance(detail, list):
                msg = detail[0].get("msg", "")[:60] if detail else ""
            else:
                msg = str(detail)[:60]
            extra = " [VALIDATION REJECTED: {}]".format(msg)
        elif code == 200 and "config/bridge" in ep:
            s = body.get("success") if body else "?"
            extra = " [ACCEPTED: success={}]".format(s)
        print("  {:4s} {:45s} -> {}{}".format(method, ep, code, extra))
    except Exception as e:
        print("  {:4s} {:45s} -> ERROR: {}".format(method, ep, e))

code, sys_data = do_request("GET", "/system")
if sys_data and isinstance(sys_data, dict):
    print("")
    print("  System: CPU={}% RAM={}% Disk={}%".format(
        sys_data.get("cpu"), sys_data.get("ram"), sys_data.get("disk"),
    ))
print("=" * 70)
