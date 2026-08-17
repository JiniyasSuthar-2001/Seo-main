import subprocess
import sys
import os
import time
import threading
import urllib.request
import webbrowser
import socket

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def wait_for_server(url, name, timeout=30):
    print(f"[{name}] Waiting for server to become ready at {url}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.getcode() == 200 or response.getcode() == 404: 
                    # 404 is fine for backend / or frontend SPA if not found, means server is UP
                    print(f"[{name}] READY")
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    print(f"[{name}] FAILED to start or respond within timeout.")
    return False

def stream_logs(process, prefix):
    try:
        for line in iter(process.stdout.readline, b''):
            decoded_line = line.decode('utf-8', errors='replace').rstrip()
            print(f"[{prefix}] {decoded_line}")
            sys.stdout.flush()
    except Exception:
        pass

def kill_process_tree(pid):
    try:
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def main():
    print("============================================================")
    print(" SEO INTELLIGENCE PLATFORM")
    print(" Development Server")
    print("============================================================\n")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    venv_python = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    backend_python = venv_python if os.path.exists(venv_python) else sys.executable
    frontend_python = sys.executable

    # Port Check
    if check_port(8000):
        print("[WARNING] Port 8000 is already in use. Please close the existing process.")
        sys.exit(1)
    if check_port(8020):
        print("[WARNING] Port 8020 is already in use. Please close the existing process.")
        sys.exit(1)

    backend_process = None
    frontend_process = None

    try:
        # Start Backend
        print("[BACKEND] Starting FastAPI / Uvicorn...")
        backend_process = subprocess.Popen(
            [backend_python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=0 # Make sure we don't hide the window context
        )
        
        # Start Frontend
        print("[FRONTEND] Starting SPA server...")
        frontend_process = subprocess.Popen(
            [frontend_python, "serve_spa.py"],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=0
        )

        # Start log streaming threads
        threading.Thread(target=stream_logs, args=(backend_process, "BACKEND"), daemon=True).start()
        threading.Thread(target=stream_logs, args=(frontend_process, "FRONTEND"), daemon=True).start()

        # Wait for readiness
        backend_ready = wait_for_server("http://127.0.0.1:8000/api/health", "BACKEND")
        frontend_ready = wait_for_server("http://127.0.0.1:8020", "FRONTEND")

        if backend_ready and frontend_ready:
            print("\n------------------------------------------------------------")
            print("All services are READY. Opening browser...")
            print("Press CTRL+C to stop all services.")
            print("------------------------------------------------------------\n")
            webbrowser.open("http://localhost:8020")
        else:
            print("\n[ERROR] One or both services failed to start properly.")
            raise KeyboardInterrupt # Trigger cleanup

        # Keep alive
        while True:
            time.sleep(1)
            # Check if any process died unexpectedly
            if backend_process.poll() is not None:
                print(f"[BACKEND] Process exited unexpectedly with code {backend_process.returncode}")
                break
            if frontend_process.poll() is not None:
                print(f"[FRONTEND] Process exited unexpectedly with code {frontend_process.returncode}")
                break

    except KeyboardInterrupt:
        print("\n--------------------------------------------------")
        print("Stopping SEO Intelligence Platform...")
        print("--------------------------------------------------")
    finally:
        if frontend_process and frontend_process.poll() is None:
            print("[FRONTEND] Stopping...")
            kill_process_tree(frontend_process.pid)
            print("[FRONTEND] Stopped.")
            
        if backend_process and backend_process.poll() is None:
            print("[BACKEND] Stopping...")
            kill_process_tree(backend_process.pid)
            print("[BACKEND] Stopped.")
            
        print("\nAll development services stopped.")
        print("Goodbye.")

if __name__ == "__main__":
    main()
