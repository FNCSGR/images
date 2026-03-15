import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

PORT = 8765

# Root directory allowed for writes
PROJECT_ROOT = os.path.abspath(os.getcwd())


class SaveHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        if self.command == "POST" and self.path == "/save":
            super().log_message(format, *args)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):

        if self.path != "/save":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)

        try:

            payload = json.loads(body)

            requested_path = payload["path"]
            data = payload["data"]

            # Normalize path
            safe_path = os.path.abspath(os.path.join(PROJECT_ROOT, requested_path))

            # Prevent directory traversal
            if not safe_path.startswith(PROJECT_ROOT):
                raise Exception("Invalid path outside project directory")

            # Ensure directory exists
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)

            with open(safe_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            print("Saved:", safe_path)

            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b"Saved")

        except Exception as e:

            print("Save failed:", e)

            self.send_response(500)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(str(e).encode())


server = HTTPServer(("localhost", PORT), SaveHandler)

print("Save server running")
print("Project root:", PROJECT_ROOT)
print(f"http://localhost:{PORT}")

server.serve_forever()