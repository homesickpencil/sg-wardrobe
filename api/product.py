import importlib.util
import json
import logging
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# Only people signed in to the app may use these functions, so a stranger with the link cannot spend the API key.
# The app's Supabase project confirms the sign-in token; its URL and publishable key are public by design.
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://balctnrvfvzvtaolsrgg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_ywsmooShGztUuNIwqsj1mA_Uw-1L5fc")
_CONFIRMED = {}  # token -> when Supabase last confirmed it, so a burst of requests checks once a minute


def signed_in(authorization):
    """True if the request carries a live sign-in, False if not, None if Supabase could not be reached."""
    token = authorization[7:].strip() if authorization and authorization.startswith("Bearer ") else ""
    if not token or len(token) > 4096:
        return False
    now = time.time()
    if _CONFIRMED.get(token, 0) > now - 60:
        return True
    request = urllib.request.Request(SUPABASE_URL + "/auth/v1/user", headers={"apikey": SUPABASE_KEY, "Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status != 200:
                return False
    except urllib.error.HTTPError:
        return False
    except Exception:
        logger.exception("Could not reach Supabase to check the sign-in")
        return None
    if len(_CONFIRMED) > 1000:
        _CONFIRMED.clear()
    _CONFIRMED[token] = now
    return True
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
        allowed = signed_in(self.headers.get("Authorization"))
        if allowed is None:
            return self.send_json(503, {"code": "offline", "error": "Could not check your sign-in"})
        if not allowed:
            return self.send_json(401, {"code": "signed_out", "error": "Sign in to use this"})
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
