import requests
B = "http://localhost:8000"

# Test 1: Demo login
r = requests.post(B + "/auth/demo")
print("DEMO STATUS:", r.status_code)
d = r.json()
t = d["access_token"]

# Test 2: auth/me with demo token
r2 = requests.get(B + "/auth/me", headers={"Authorization": "Bearer " + t})
print("AUTH_ME STATUS:", r2.status_code)
print("AUTH_ME BODY:", r2.json())

# Test 3: Check JWT payload
import base64, json
payload = json.loads(base64.b64decode(t.split(".")[1] + "=="))
print("JWT PAYLOAD:", payload)

# Test 4: Check JARVIS_SECRET consistency
# The server that issued the token must decode it with same secret
# If server restarted with --reload, secret might have changed if ephemeral
print("TOKEN PREFIX:", t[:30])
