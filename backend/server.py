"""
FABB Backend Server - Pure Python stdlib HTTP server
Run: python3 backend/server.py
"""
import json
import os
import sys

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_index.indexer import FileIndexer
from pipeline.runner import run_pipeline

CONFIG_PATH = os.path.expanduser("~/.fabb/config.json")
indexer = FileIndexer()


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"folder": "", "api_key": "", "api_provider": "openai"}


def save_config(data):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


class FABBHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/config":
            self.send_json(load_config())
        elif path == "/api/files":
            self.send_json({"files": indexer.get_all()})
        elif path == "/health":
            self.send_json({"status": "ok"})
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if path == "/api/config":
            cfg = load_config()
            cfg.update(body)
            save_config(cfg)
            if "folder" in body and os.path.isdir(body["folder"]):
                indexer.index(body["folder"])
            self.send_json({"ok": True})

        elif path == "/api/chat":
            prompt  = body.get("prompt", "").strip()
            history = body.get("history", [])   # full conversation history from frontend
            if not prompt:
                self.send_json({"error": "Empty prompt"}, 400)
                return
            cfg = load_config()
            result = run_pipeline(prompt, indexer, cfg, history=history)
            self.send_json(result)

        elif path == "/api/refresh":
            cfg    = load_config()
            folder = cfg.get("folder", "")
            if not folder or not os.path.isdir(folder):
                self.send_json({"error": "No valid folder set"}, 400)
                return
            files = indexer.index(folder)
            self.send_json({"files": files, "count": len(files)})

        else:
            self.send_json({"error": "Not found"}, 404)


def run(port=8765):
    server = HTTPServer(("127.0.0.1", port), FABBHandler)
    print(f"[FABB] Backend running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
