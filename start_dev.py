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
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except OSError:
            return True

def free_port_if_in_use(port):
    """
    Cross-platform port reclamation.
    Identifies and terminates ONLY the specific process occupying the target port.
    Never kills unrelated processes.
    Supports Windows, macOS, and Linux.
    """
    if not check_port("0.0.0.0", port):
        return True

    print(f"[PORT] Port {port} is currently occupied. Attempting cross-platform reclamation...", flush=True)

    try:
        if sys.platform == "win32":
            # Windows: Extract specific PID for port from netstat and kill ONLY that PID
            cmd = f'for /f "tokens=5" %a in (\'netstat -aon ^| findstr /r /c:":{port} "\') do taskkill /F /PID %a'
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # macOS / Linux: Use lsof or fuser to target ONLY the specific PID
            freed = False
            try:
                res = subprocess.run(
                    ["lsof", "-t", f"-i:{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                if res.returncode == 0 and res.stdout.strip():
                    pids = res.stdout.strip().split()
                    for p in pids:
                        try:
                            os.kill(int(p), signal.SIGKILL)
                        except Exception:
                            pass
                    freed = True
            except FileNotFoundError:
                pass

            if not freed:
                try:
                    subprocess.run(
                        ["fuser", "-k", "-n", "tcp", str(port)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    freed = True
                except FileNotFoundError:
                    print(f"[WARNING] Neither 'lsof' nor 'fuser' is installed on this system to auto-free port {port}.", flush=True)

        time.sleep(1.0)
    except Exception as e:
        print(f"[WARNING] Exception during port {port} reclamation: {e}", flush=True)

    is_free = not check_port("0.0.0.0", port)
    if is_free:
        print(f"[PORT] Port {port} successfully freed.", flush=True)
    else:
        print(f"[WARNING] Port {port} could not be automatically freed.", flush=True)

    return is_free

def wait_for_server(url, name, port=None, timeout=30):
    print(f"[{name}] Waiting for server to respond at {url}...", flush=True)
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "SEO-Platform-Checker/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.getcode() in (200, 301, 302, 404):
                    print(f"[{name}] READY (HTTP {response.getcode()})", flush=True)
                    return True
        except Exception:
            if port:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1.0)
                        if s.connect_ex(("127.0.0.1", port)) == 0:
                            print(f"[{name}] READY (Socket connected)", flush=True)
                            return True
                except Exception:
                    pass
        time.sleep(0.5)

    print(f"[{name}] FAILED to respond within {timeout} seconds.", flush=True)
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

    # Automatically free ports if occupied by leftover background processes
    if not free_port_if_in_use(port):
        print(f"[WARNING] Port {port} is already in use. Please stop the running backend server.", flush=True)
        sys.exit(1)
    if not free_port_if_in_use(frontend_port):
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
        backend_ready = wait_for_server(f"http://127.0.0.1:{port}/api/health", "HEALTH (Backend)", port=port)
        frontend_ready = wait_for_server(f"http://127.0.0.1:{frontend_port}", "HEALTH (Frontend)", port=frontend_port)

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
            print("Stopping frontend...", flush=True)
            try:
                if frontend_process.poll() is None:
                    kill_process_tree(frontend_process.pid)
            except Exception:
                pass
            print("Frontend stopped.", flush=True)

        if backend_process:
            print("Stopping backend...", flush=True)
            try:
                if backend_process.poll() is None:
                    kill_process_tree(backend_process.pid)
            except Exception:
                pass
            print("Backend stopped.", flush=True)

        print("\nSEO Intelligence Platform stopped cleanly.", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
