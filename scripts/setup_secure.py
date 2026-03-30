#!/usr/bin/env python3
"""
Setup script to initialize the secure Engenharia Automacao CAD system
"""
import os
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent

def run_command(cmd, description):
    """Run a command and return success"""
    print(f"Running: {description}")
    try:
        # Use shell=True for Windows compatibility
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, cwd=project_root)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup process"""
    print("🚀 Setting up Engenharia Automacao CAD (Secure Version)\n")

    project_root = Path(__file__).parent

    # 1. Check if .env exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please copy .env.example to .env and fill with secure values")
        print("Or run: python generate_secrets.py > .env")
        return 1

    print("✅ .env file found")

    # 2. Install dependencies
    if not run_command("pip install passlib[bcrypt]", "Install bcrypt for password hashing"):
        return 1

    # 3. Run password migration
    if not run_command("python migrate_passwords.py", "Migrate user passwords to bcrypt"):
        return 1

    # 4. Run license migration
    if not run_command("python migrate_licenses.py", "Add HMAC signatures to licenses"):
        return 1

    # 5. Run security tests directly (not via subprocess to avoid issues)
    print("Running: Run security validation tests")
    try:
        # Import and run tests directly
        import test_security
        result = test_security.main()
        if result == 0:
            print("✅ Run security validation tests completed")
        else:
            print("❌ Run security validation tests failed")
            return 1
    except Exception as e:
        print(f"❌ Run security validation tests failed: {e}")
        return 1

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the licensing server: python licensing_server/app.py")
    print("2. Start the main API server: python integration/python_api/app.py")
    print("3. Start the frontend: cd frontend && npm start")
    print("\n⚠️  Remember to keep your .env file secure and never commit it!")

    return 0

if __name__ == "__main__":
    sys.exit(main())