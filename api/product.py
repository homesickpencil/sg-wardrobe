import importlib.util
import json
import logging
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)
SERVER_PATH = Path(__file__).resolve().parents[1] / "wardrobe-server.py"
SPEC = importlib.util.spec_from_file_location("wardrobe_local_server", SERVER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load the wardrobe product reader")
WARDROBE_SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WARDROBE_SERVER)


class handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def is_same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlsplit(origin)
        return parsed.scheme in ("http", "https") and parsed.netloc.lower() == self.headers.get("Host", "").lower()

    def do_POST(self):
        if self.path != "/api/product":
            return self.send_json(404, {"code": "not_found", "error": "Not found"})
        if not self.is_same_origin():
            return self.send_json(403, {"code": "forbidden", "error": "Forbidden"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send_json(400, {"code": "bad_request", "error": "Invalid request"})
        if not 0 < size <= 60_000:
            return self.send_json(413, {"code": "request_too_large", "error": "Request too large"})
        try:
            body = json.loads(self.rfile.read(size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {"code": "bad_request", "error": "Invalid request"})
        url = body.get("url") if isinstance(body, dict) else None
        if not isinstance(url, str) or not url.strip():
            return self.send_json(400, {"code": "bad_request", "error": "Invalid URL"})
        try:
            status, result = WARDROBE_SERVER.read_product(url.strip())
        except Exception:
            logger.exception("Product-page reading failed")
            return self.send_json(502, {"code": "unreachable", "error": "Could not read the shop page"})
        return self.send_json(status, result)

    def do_GET(self):
        return self.send_json(405, {"code": "method_not_allowed", "error": "Method not allowed"})
