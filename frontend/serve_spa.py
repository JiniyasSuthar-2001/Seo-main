import http.server
import socketserver
import os

PORT = 8020

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Check if the requested path exists as a file or directory
        path = self.translate_path(self.path)
        if os.path.exists(path) and not os.path.isdir(path):
            # If it's a real file (like .js, .css, .ico), serve it normally
            return super().do_GET()
        else:
            # If it's not a file (like a route e.g., /internal-links), serve index.html
            self.path = '/index.html'
            return super().do_GET()

with socketserver.TCPServer(("", PORT), SPAHandler) as httpd:
    print(f"Serving SPA on port {PORT}")
    httpd.serve_forever()
