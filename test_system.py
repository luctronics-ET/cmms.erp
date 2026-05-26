#!/usr/bin/env python3
"""System initialization and endpoint testing script."""
import subprocess
import time
import requests
import sys
import os
import signal
import json

# Ensure we're in the repo directory
repo_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(repo_dir)

# Configuration
BASE_URL = "http://127.0.0.1:8010"
ENDPOINTS = [
    "/",
    "/index.html",
    "/docs",
    "/api/modulos",
]

print("=" * 70)
print("CMASM ERP SYSTEM INITIALIZATION & TESTING")
print("=" * 70)

# 1. Check Python
print("\n[1] PYTHON & DEPENDENCIES CHECK")
try:
    result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True, timeout=5)
    py_version = result.stdout.strip() or result.stderr.strip()
    print(f"✓ Python: {py_version}")
except Exception as e:
    print(f"✗ Python check failed: {e}")
    sys.exit(1)

# 2. Install dependencies
print("\n[2] INSTALLING DEPENDENCIES")
try:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode == 0:
        print("✓ Dependencies installed successfully")
    else:
        print(f"✗ Dependency installation failed:\n{result.stderr}")
        sys.exit(1)
except Exception as e:
    print(f"✗ Dependency install error: {e}")
    sys.exit(1)

# 3. Start FastAPI server in background
print("\n[3] STARTING FASTAPI SERVER")
try:
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8010"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    print(f"✓ Server process started (PID: {server_process.pid})")
    time.sleep(3)  # Wait for server to start
except Exception as e:
    print(f"✗ Failed to start server: {e}")
    sys.exit(1)

# 4. Test endpoints
print("\n[4] TESTING ENDPOINTS")
test_results = []
for endpoint in ENDPOINTS:
    url = BASE_URL + endpoint
    try:
        response = requests.get(url, timeout=5)
        content_preview = response.text[:100].replace("\n", " ") if response.text else ""
        print(f"  {endpoint:20} → {response.status_code:3} | {content_preview[:60]}")
        test_results.append((endpoint, response.status_code, "OK"))
    except requests.exceptions.ConnectionError:
        print(f"  {endpoint:20} → ERR | Connection refused")
        test_results.append((endpoint, "ERR", "Connection failed"))
    except Exception as e:
        print(f"  {endpoint:20} → ERR | {str(e)[:50]}")
        test_results.append((endpoint, "ERR", str(e)))

# 5. Try to open browser
print("\n[5] OPENING BROWSER")
try:
    import webbrowser
    result = webbrowser.open(BASE_URL)
    if result:
        print(f"✓ Browser opened to {BASE_URL}")
    else:
        print(f"⚠ Browser open returned False (may have opened in background)")
except Exception as e:
    print(f"⚠ Could not open browser: {e}")

# 6. Run pytest
print("\n[6] RUNNING PYTEST TESTS")
try:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        timeout=60
    )
    # Print pytest output
    if result.stdout:
        print(result.stdout)
    if result.returncode != 0 and result.stderr:
        print("STDERR:", result.stderr)
    pytest_status = "PASSED" if result.returncode == 0 else "FAILED"
    print(f"✓ Pytest result: {pytest_status}")
except Exception as e:
    print(f"✗ Pytest error: {e}")

# 7. Cleanup
print("\n[7] CLEANUP")
try:
    os.kill(server_process.pid, signal.SIGTERM)
    server_process.wait(timeout=5)
    print(f"✓ Server process stopped (PID: {server_process.pid})")
except ProcessLookupError:
    print("✓ Server process already terminated")
except Exception as e:
    print(f"⚠ Error stopping server: {e}")

# Summary
print("\n" + "=" * 70)
print("ENDPOINT TEST SUMMARY")
print("=" * 70)
for endpoint, status, msg in test_results:
    symbol = "✓" if status == "OK" else "✗"
    print(f"{symbol} {endpoint:20} → {status}")

print("\n" + "=" * 70)
print("END OF REPORT")
print("=" * 70)
