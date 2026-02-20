#!/usr/bin/env python3
"""
FABB Launcher — starts the backend server and opens the UI in your browser.
Usage: python3 fabb.py
"""
import os
import sys
import time
import subprocess
import threading
import webbrowser
import urllib.request

BACKEND_PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support both flat layout (index.html next to fabb.py) and subfolder layout
_frontend_sub = os.path.join(BASE_DIR, "frontend", "index.html")
_frontend_flat = os.path.join(BASE_DIR, "index.html")
FRONTEND_PATH = _frontend_sub if os.path.exists(_frontend_sub) else _frontend_flat
BACKEND_PATH = os.path.join(BASE_DIR, "backend", "server.py")


def wait_for_backend(timeout=10):
    """Wait until the backend is responding."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def run_backend():
    """Run the backend server subprocess."""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    proc = subprocess.Popen(
        [sys.executable, BACKEND_PATH],
        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"),
        env=env,
    )
    return proc


def main():
    print("=" * 50)
    print("  FABB — Full-Auto Bug Buster")
    print("=" * 50)
    print()

    # Check frontend exists
    if not os.path.exists(FRONTEND_PATH):
        print(f"[ERROR] Frontend not found at: {FRONTEND_PATH}")
        sys.exit(1)

    # Start backend
    print("[1/3] Starting backend server...")
    proc = run_backend()

    # Wait for it to be ready
    print("[2/3] Waiting for backend to be ready...")
    if not wait_for_backend():
        print("[ERROR] Backend failed to start. Check for errors above.")
        proc.terminate()
        sys.exit(1)
    print(f"      ✓ Backend running on http://127.0.0.1:{BACKEND_PORT}")

    # Open browser
    print("[3/3] Opening FABB in your browser...")
    url = f"file://{FRONTEND_PATH}"
    webbrowser.open(url)
    print(f"      ✓ UI opened: {url}")
    print()
    print("  FABB is running! Press Ctrl+C to stop.")
    print()

    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[FABB] Shutting down...")
        proc.terminate()
        proc.wait()
        print("[FABB] Stopped.")


if __name__ == "__main__":
    main()
