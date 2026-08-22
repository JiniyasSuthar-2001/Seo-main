import http.server
import socketserver
import os
import sys

HOST = os.environ.get("FRONTEND_HOST") or os.environ.get("HOST") or "127.0.0.1"
PORT = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT") or "8030")
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        # Extract clean path without query parameters or hash fragments
        clean_path = self.path.split('?')[0].split('#')[0]
        rel_path = clean_path.lstrip('/')
        target_path = os.path.join(FRONTEND_DIR, rel_path)
        
        # Guard against path traversal outside frontend directory
        real_path = os.path.abspath(target_path)
        if not real_path.startswith(FRONTEND_DIR):
            self.send_error(403, "Access Denied")
            return

        # If requesting a real static asset file inside frontend/, serve it
        if os.path.isfile(real_path):
            return super().do_GET()
        else:
            # SPA Fallback: Serve frontend/index.html for client-side routing
            self.path = '/index.html'
            return super().do_GET()

    def log_message(self, format, *args):
        # Keep frontend HTTP request log output clean in developer terminal
        sys.stdout.write(f"[FRONTEND HTTP] {args[0]} - {args[1]}\n")
        sys.stdout.flush()

if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), SPAHandler) as httpd:
        print(f"[FRONTEND] SPA server running on http://{HOST}:{PORT} (Serving from {FRONTEND_DIR})", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
