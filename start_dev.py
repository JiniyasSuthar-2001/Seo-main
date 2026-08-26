import subprocess
import sys
import os
import time
import threading
import urllib.request
import webbrowser
import socket
import signal

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
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
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    venv_python = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    backend_python = venv_python if os.path.exists(venv_python) else sys.executable
    frontend_python = sys.executable

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8020"))
    frontend_host = os.environ.get("FRONTEND_HOST", "0.0.0.0")
    frontend_port = int(os.environ.get("FRONTEND_PORT", "8030"))

    lan_ip = get_lan_ip()

    # Check ports before spawning
    if check_port("0.0.0.0", port):
        print(f"[WARNING] Port {port} is already in use. Please stop the running backend server.", flush=True)
        sys.exit(1)
    if check_port("0.0.0.0", frontend_port):
        print(f"[WARNING] Port {frontend_port} is already in use. Please stop the running frontend server.", flush=True)
        sys.exit(1)

    backend_process = None
    frontend_process = None

    # Windows flags to run in same console without popup windows
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)

    try:
        print(f"[STARTUP] Starting backend on {host}:{port}...", flush=True)
        env_backend = os.environ.copy()
        env_backend["HOST"] = host
        env_backend["PORT"] = str(port)
        backend_process = subprocess.Popen(
            [backend_python, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port), "--reload"],
            cwd=backend_dir,
            env=env_backend,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            creationflags=creation_flags
        )

        print(f"[STARTUP] Starting frontend on {frontend_host}:{frontend_port}...", flush=True)
        env_frontend = os.environ.copy()
        env_frontend["FRONTEND_HOST"] = frontend_host
        env_frontend["FRONTEND_PORT"] = str(frontend_port)
        frontend_process = subprocess.Popen(
            [frontend_python, "serve_spa.py"],
            cwd=frontend_dir,
            env=env_frontend,
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

        # Perform health checks using loopback IP
        backend_ready = wait_for_server(f"http://127.0.0.1:{port}/api/health", "HEALTH")
        frontend_ready = wait_for_server(f"http://127.0.0.1:{frontend_port}", "HEALTH")

        if backend_ready and frontend_ready:
            print("\n============================================================", flush=True)
            print("SEO PLATFORM DEVELOPMENT SERVERS", flush=True)
            print("============================================================\n", flush=True)
            print("Backend:", flush=True)
            print(f"  Local: http://127.0.0.1:{port}", flush=True)
            print(f"  LAN:   http://{lan_ip}:{port}\n", flush=True)
            print("Frontend:", flush=True)
            print(f"  Local: http://127.0.0.1:{frontend_port}", flush=True)
            print(f"  LAN:   http://{lan_ip}:{frontend_port}\n", flush=True)
            print("Google OAuth:", flush=True)
            print("  Local development login: ENABLED\n", flush=True)
            print("============================================================", flush=True)
            print("Press CTRL+C to stop both servers", flush=True)
            print("============================================================\n", flush=True)
            
            webbrowser.open(f"http://127.0.0.1:{frontend_port}/")
        else:
            print("\n[ERROR] Server health checks failed.", flush=True)
            raise KeyboardInterrupt

        # Keep main thread running and monitor processes
        while True:
            time.sleep(0.5)
            if backend_process and backend_process.poll() is not None:
                print(f"\n[BACKEND] Stopped (code {backend_process.returncode})", flush=True)
                break
            if frontend_process and frontend_process.poll() is not None:
                print(f"\n[FRONTEND] Stopped (code {frontend_process.returncode})", flush=True)
                break

    except KeyboardInterrupt:
        print("\n--------------------------------------------------", flush=True)
        print("Stopping SEO Intelligence Platform...", flush=True)
        print("--------------------------------------------------", flush=True)
    finally:
        if frontend_process:
            try:
                if frontend_process.poll() is None:
                    kill_process_tree(frontend_process.pid)
            except Exception:
                pass
            print("[FRONTEND] Stopped cleanly.", flush=True)

        if backend_process:
            try:
                if backend_process.poll() is None:
                    kill_process_tree(backend_process.pid)
            except Exception:
                pass
            print("[BACKEND] Stopped cleanly.", flush=True)

        print("SEO Intelligence Platform stopped cleanly. Goodbye.", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
