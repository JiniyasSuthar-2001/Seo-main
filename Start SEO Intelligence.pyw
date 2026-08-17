import subprocess
import time
import webbrowser
import os
import sys

# Windows flag to hide the console window when running a subprocess
CREATE_NO_WINDOW = 0x08000000

def main():
    # Get the absolute path to the project root
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    # Determine Python executable to use for backend
    # If a local .venv exists, use it to ensure dependencies are found
    venv_python = os.path.join(backend_dir, ".venv", "Scripts", "python.exe")
    backend_python = venv_python if os.path.exists(venv_python) else sys.executable

    # 1. Start Backend Server hidden
    try:
        subprocess.Popen(
            [backend_python, "-m", "uvicorn", "app.main:app", "--port", "8000"],
            cwd=backend_dir,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        # Silently pass or log to a file if needed, since this is a UI-less launcher
        pass

    # 2. Start Frontend Server hidden
    try:
        subprocess.Popen(
            [sys.executable, "-m", "http.server", "8001"],
            cwd=frontend_dir,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        pass

    # 3. Wait for services to initialize
    time.sleep(3)

    # 4. Open the browser automatically to the dashboard
    webbrowser.open("http://localhost:8001")

if __name__ == "__main__":
    main()
