import requests
B = "http://localhost:8000"

tests = [
    ("GET", "/insights", None),
    ("GET", "/history", None),
    ("GET", "/logs", None),
    ("POST", "/generate", {"tipo": "piping", "norma": "N-58"}),
    ("POST", "/excel", None),
    ("GET", "/project-draft", None),
    ("GET", "/project-draft-from-text", None),
    ("POST", "/project-draft-feedback", {"prompt":"t","feedback":"ok"}),
    ("POST", "/jobs/stress/porticos-50", None),
    ("POST", "/telemetry/test", None),
    ("GET", "/api/autocad/connect", None),
    ("POST", "/api/autocad/connect", None),
]

for method, path, body in tests:
    try:
        if method == "POST":
            r = requests.post(B + path, json=body, timeout=5)
        else:
            r = requests.get(B + path, timeout=5)
        print(f"{method:4s} {path:40s} -> {r.status_code}")
    except Exception as e:
        print(f"{method:4s} {path:40s} -> ERROR: {type(e).__name__}")
