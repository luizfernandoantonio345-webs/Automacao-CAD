import requests
try:
    r = requests.get("http://localhost:8000/health", timeout=5)
    print("HEALTH:", r.status_code, r.text[:200])
except Exception as e:
    print("ERROR:", e)

try:
    r2 = requests.post("http://localhost:8000/login", json={"email":"test@test.com","password":"x"}, timeout=5)
    print("LOGIN:", r2.status_code, r2.text[:200])
except Exception as e:
    print("LOGIN ERROR:", e)
