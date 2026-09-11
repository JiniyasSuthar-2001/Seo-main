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

def get_pids_for_port(port):
    pids = set()
    try:
        if sys.platform == "win32":
            res = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                errors="replace"
            )
            for line in res.stdout.splitlines():
                line = line.strip()
                if f":{port} " in line or line.endswith(f":{port}"):
                    parts = line.split()
                    if len(parts) >= 5 and parts[-1].isdigit():
                        pid = int(parts[-1])
                        if pid > 0 and pid != os.getpid():
                            pids.add(pid)
        else:
            try:
                res = subprocess.run(
                    ["lsof", "-t", f"-i:{port}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True
                )
                if res.returncode == 0 and res.stdout.strip():
                    for p in res.stdout.strip().split():
                        if p.isdigit() and int(p) != os.getpid():
                            pids.add(int(p))
            except FileNotFoundError:
                pass
    except Exception:
        pass
    return pids

def free_port_if_in_use(port):
    """
    Cross-platform port reclamation.
    Identifies and terminates ONLY the specific process occupying the target port,
    including any orphaned multiprocessing child workers.
    Never kills unrelated processes.
    Supports Windows, macOS, and Linux.
    """
    pids = get_pids_for_port(port)
    is_busy = check_port("0.0.0.0", port) or len(pids) > 0

    if not is_busy:
        return True

    print(f"[PORT] Port {port} is currently occupied (detected PIDs: {list(pids) or 'system'}). Attempting reclamation...", flush=True)

    for pid in pids:
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                wmic_res = subprocess.run(["wmic", "process", "where", f"CommandLine like '%parent_pid={pid}%'", "get", "ProcessId"], capture_output=True, text=True, errors="replace")
                for line in wmic_res.stdout.splitlines():
                    line = line.strip()
                    if line.isdigit() and int(line) != os.getpid():
                        subprocess.run(["taskkill", "/F", "/PID", line], capture_output=True)
            else:
                os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    time.sleep(1.0)
    remaining = get_pids_for_port(port)
    is_free = not check_port("0.0.0.0", port) and len(remaining) == 0

    if is_free:
        print(f"[PORT] Port {port} successfully freed.", flush=True)
    else:
        print(f"[WARNING] Port {port} could not be automatically freed.", flush=True)

    return is_free

def wait_for_server(url, name, port=None, process=None, timeout=25):
    print(f"[{name}] Waiting for server to respond at {url}...", flush=True)
    start_time = time.time()
    while time.time() - start_time < timeout:
        if process and process.poll() is not None:
            print(f"[{name}] FAILED: Server process terminated prematurely (exit code {process.returncode})", flush=True)
            return False

        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "SEO-Platform-Checker/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as response:
                if response.getcode() in (200, 301, 302, 404):
                    print(f"[{name}] READY (HTTP {response.getcode()})", flush=True)
                    return True
        except Exception:
            pass
        time.sleep(0.5)

    print(f"[{name}] FAILED to respond within {timeout} seconds.", flush=True)
    return False

def stream_logs(process, prefix):
    try:
        for line in iter(process.stdout.readline, ''):
            decoded_line = line.rstrip()
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

    try:
        print(f"[STARTUP] Starting backend on {host}:{port}...", flush=True)
        env_backend = os.environ.copy()
        env_backend["HOST"] = host
        env_backend["PORT"] = str(port)
        env_backend["PYTHONUNBUFFERED"] = "1"
        backend_process = subprocess.Popen(
            [backend_python, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port), "--reload"],
            cwd=backend_dir,
            env=env_backend,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace"
        )

        print(f"[STARTUP] Starting frontend on {frontend_host}:{frontend_port}...", flush=True)
        env_frontend = os.environ.copy()
        env_frontend["FRONTEND_HOST"] = frontend_host
        env_frontend["FRONTEND_PORT"] = str(frontend_port)
        env_frontend["PYTHONUNBUFFERED"] = "1"
        frontend_process = subprocess.Popen(
            [frontend_python, "serve_spa.py"],
            cwd=frontend_dir,
            env=env_frontend,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace"
        )

        # Output streaming threads to keep terminal active
        t1 = threading.Thread(target=stream_logs, args=(backend_process, "BACKEND"), daemon=True)
        t2 = threading.Thread(target=stream_logs, args=(frontend_process, "FRONTEND"), daemon=True)
        t1.start()
        t2.start()

        # Perform health checks using loopback IP (checking actual HTTP responses)
        backend_ready = wait_for_server(f"http://127.0.0.1:{port}/api/health", "HEALTH (Backend)", port=port, process=backend_process)
        frontend_ready = wait_for_server(f"http://127.0.0.1:{frontend_port}/", "HEALTH (Frontend)", port=frontend_port, process=frontend_process)

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
            
            try:
                webbrowser.open(f"http://127.0.0.1:{frontend_port}/")
            except Exception:
                pass
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
