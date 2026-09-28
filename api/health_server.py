import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import time
from pathlib import Path

logger = logging.getLogger(__name__)
_started = False
_started_at = time()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] != "/health":
            self.send_response(404); self.end_headers(); return
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            storage_ok = os.access(data_dir, os.W_OK)
        except OSError:
            storage_ok = False
        body = json.dumps({
            "status": "ok",
            "service": "ai-trading-bot",
            "mode": "paper",
            "uptime_seconds": round(time() - _started_at, 1),
            "storage_path": str(data_dir),
            "storage_writable": storage_ok,
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *_):
        return

def start_health_server(port: int = 8080):
    global _started
    if _started:
        return
    port = int(port)
    try:
        server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
        thread = Thread(target=server.serve_forever, daemon=True, name="health-server")
        thread.start()
        _started = True
        logger.info("Health server listening on 0.0.0.0:%d", port)
    except OSError:
        logger.exception("Failed to bind health server on port %d", port)
        raise
