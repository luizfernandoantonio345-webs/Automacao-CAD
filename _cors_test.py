import requests

# Simulate browser preflight (OPTIONS) for /login
print("=== OPTIONS /login (preflight) ===")
r = requests.options("http://localhost:8000/login", headers={
    "Origin": "http://localhost:3000",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type,authorization"
}, timeout=5)
print("Status:", r.status_code)
print("CORS headers:")
for k, v in r.headers.items():
    if "access-control" in k.lower() or "allow" in k.lower():
        print(f"  {k}: {v}")

# Simulate browser POST /login
print("\n=== POST /login (with Origin) ===")
r2 = requests.post("http://localhost:8000/login", json={
    "email": "luizfernandoantonio345@gmail.com",
    "senha": "Santos14!@"
}, headers={
    "Origin": "http://localhost:3000",
    "Content-Type": "application/json"
}, timeout=5)
print("Status:", r2.status_code)
print("CORS headers:")
for k, v in r2.headers.items():
    if "access-control" in k.lower() or "allow" in k.lower():
        print(f"  {k}: {v}")
print("Body:", r2.text[:200])

# Simulate browser POST /auth/demo
print("\n=== POST /auth/demo ===")
r3 = requests.post("http://localhost:8000/auth/demo", headers={
    "Origin": "http://localhost:3000"
}, timeout=5)
print("Status:", r3.status_code)
print("CORS headers:")
for k, v in r3.headers.items():
    if "access-control" in k.lower() or "allow" in k.lower():
        print(f"  {k}: {v}")
print("Body:", r3.text[:200])
