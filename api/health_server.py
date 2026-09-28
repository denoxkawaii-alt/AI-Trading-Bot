import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

_started = False

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_response(404); self.end_headers(); return
        body = json.dumps({"status":"ok","service":"ai-trading-bot","mode":"paper"}).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_):
        return

def start_health_server(port: int = 8080):
    global _started
    if _started:
        return
    _started = True
    server = HTTPServer(("0.0.0.0", int(port)), HealthHandler)
    Thread(target=server.serve_forever, daemon=True, name="health-server").start()
