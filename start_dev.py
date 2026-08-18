import subprocess
import sys
import os
import time
import threading
import urllib.request
import webbrowser
import socket
import signal

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except OSError:
            return True

def wait_for_server(url, name, timeout=30):
    print(f"[{name}] Waiting for server to become ready at {url}...", flush=True)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as response:
                if response.getcode() in (200, 404):
                    print(f"[{name}] READY", flush=True)
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    print(f"[{name}] FAILED to start or respond within {timeout} seconds.", flush=True)
    return False

def stream_logs(process, prefix):
    try:
        for line in iter(process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='replace').rstrip()
            if decoded_line:
                print(f"[{prefix}] {decoded_line}", flush=True)
    except Exception:
        pass

def kill_process_tree(pid):
    try:
        if sys.platform == "win32":
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
    except Exception:
        pass

def main():
    print("============================================================", flush=True)
    print(" SEO INTELLIGENCE PLATFORM", flush=True)
    print(" One-Click Development Starter", flush=True)
    print("============================================================\n", flush=True)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    venv_python = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    backend_python = venv_python if os.path.exists(venv_python) else sys.executable
    frontend_python = sys.executable

    # Check ports before spawning
    if check_port(8020):
        print("[WARNING] Port 8020 is already in use. Please stop the running backend server.", flush=True)
        sys.exit(1)
    if check_port(8030):
        print("[WARNING] Port 8030 is already in use. Please stop the running frontend server.", flush=True)
        sys.exit(1)

    backend_process = None
    frontend_process = None

    # Windows flags to run in same console without popup windows
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

    try:
        print("[STARTUP] Starting backend on http://127.0.0.1:8020...", flush=True)
        backend_process = subprocess.Popen(
            [backend_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8020"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=creation_flags
        )

        print("[STARTUP] Starting frontend on http://localhost:8030...", flush=True)
        frontend_process = subprocess.Popen(
            [frontend_python, "serve_spa.py"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=creation_flags
        )

        # Output streaming threads to keep terminal active
        t1 = threading.Thread(target=stream_logs, args=(backend_process, "BACKEND"), daemon=True)
        t2 = threading.Thread(target=stream_logs, args=(frontend_process, "FRONTEND"), daemon=True)
        t1.start()
        t2.start()

        # Perform health checks
        backend_ready = wait_for_server("http://127.0.0.1:8020/api/health", "HEALTH")
        frontend_ready = wait_for_server("http://localhost:8030", "HEALTH")

        if backend_ready and frontend_ready:
            print("\n============================================================", flush=True)
            print(" All services are READY.", flush=True)
            print(" Opening browser: http://localhost:8030/", flush=True)
            print(" Press CTRL+C to stop both servers cleanly.", flush=True)
            print("============================================================\n", flush=True)
            
            webbrowser.open("http://localhost:8030/")
        else:
            print("\n[ERROR] Server health checks failed.", flush=True)
            raise KeyboardInterrupt

        # Keep main thread running and monitor processes
        while True:
            time.sleep(1)
            if backend_process.poll() is not None:
                print(f"\n[BACKEND] Stopped (code {backend_process.returncode})", flush=True)
                break
            if frontend_process.poll() is not None:
                print(f"\n[FRONTEND] Stopped (code {frontend_process.returncode})", flush=True)
                break

    except KeyboardInterrupt:
        print("\n--------------------------------------------------", flush=True)
        print("Stopping SEO Intelligence Platform...", flush=True)
        print("--------------------------------------------------", flush=True)
    finally:
        if frontend_process and frontend_process.poll() is None:
            kill_process_tree(frontend_process.pid)
            print("[FRONTEND] Stopped cleanly.", flush=True)

        if backend_process and backend_process.poll() is None:
            kill_process_tree(backend_process.pid)
            print("[BACKEND] Stopped cleanly.", flush=True)

        print("All processes terminated. Goodbye.", flush=True)

if __name__ == "__main__":
    main()
