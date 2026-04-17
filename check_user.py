#!/usr/bin/env python
"""Check if enterprise user exists."""
import sys
sys.path.insert(0, '.')

from backend.database.db import get_db

with get_db() as conn:
    result = conn.execute("""
        SELECT email, tier, limite FROM users WHERE email = 'santossod345@gmail.com'
    """).fetchone()
    if result:
        email, tier, limite = result
        print(f"✅ Enterprise user found:")
        print(f"   Email: {email}")
        print(f"   Tier: {tier}")
        print(f"   Limite: {limite}")
        sys.exit(0)
    else:
        print("❌ Enterprise user not found locally")
        sys.exit(1)
