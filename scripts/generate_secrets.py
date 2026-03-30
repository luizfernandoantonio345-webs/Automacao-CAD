#!/usr/bin/env python3
"""
Script to generate secure secrets for .env file
"""
import secrets
import string

def generate_secret(length=32):
    """Generate a cryptographically secure random string"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    print("# Generated secure secrets - copy to your .env file")
    print(f"ENG_AUTH_SECRET={generate_secret(32)}")
    print(f"JARVIS_SECRET={generate_secret(32)}")
    print(f"LICENSE_SECRET={generate_secret(32)}")
    print("\n# Copy these values to your .env file and keep them secure!")