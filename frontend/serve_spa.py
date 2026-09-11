import http.server
import socketserver
import os
import sys

HOST = os.environ.get("FRONTEND_HOST", "0.0.0.0")
PORT = int(os.environ.get("FRONTEND_PORT") or os.environ.get("PORT") or "8030")
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure standard MIME types are mapped properly
http.server.SimpleHTTPRequestHandler.extensions_map.update({
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
    '.html': 'text/html'
})

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def _resolve_and_serve(self, is_head=False):
        try:
            clean_path = self.path.split('?')[0].split('#')[0]
            rel_path = clean_path.lstrip('/')
            target_path = os.path.join(FRONTEND_DIR, rel_path)

            real_path = os.path.abspath(target_path)
            if not real_path.startswith(FRONTEND_DIR):
                self.send_error(403, "Access Denied")
                return

            if os.path.isfile(real_path):
                if is_head:
                    return super().do_HEAD()
                return super().do_GET()

            segments = rel_path.split('/')
            if len(segments) > 1:
                for idx in range(1, len(segments)):
                    sub_rel = '/'.join(segments[idx:])
                    sub_target = os.path.join(FRONTEND_DIR, sub_rel)
                    if os.path.isfile(sub_target):
                        self.path = '/' + sub_rel
                        if is_head:
                            return super().do_HEAD()
                        return super().do_GET()

            # SPA Fallback: Serve frontend/index.html for client-side routing
            self.path = '/index.html'
            if is_head:
                return super().do_HEAD()
            return super().do_GET()
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            sys.stderr.write(f"[FRONTEND ERROR] {e}\n")
            sys.stderr.flush()

    def do_GET(self):
        self._resolve_and_serve(is_head=False)

    def do_HEAD(self):
        self._resolve_and_serve(is_head=True)

    def log_message(self, format, *args):
        sys.stdout.write(f"[FRONTEND HTTP] {args[0]} - {args[1]}\n")
        sys.stdout.flush()

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    # On Windows, allow_reuse_address=False prevents silent port collision/hijacking
    allow_reuse_address = False if sys.platform == "win32" else True

if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    display_host = "127.0.0.1" if HOST in ("", "0.0.0.0") else HOST
    with ThreadedTCPServer((HOST, PORT), SPAHandler) as httpd:
        print(f"[FRONTEND] SPA server running on http://{display_host}:{PORT} (Serving from {FRONTEND_DIR})", flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
