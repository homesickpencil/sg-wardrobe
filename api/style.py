import json
import logging
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from anthropic import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Anthropic,
    AuthenticationError,
    RateLimitError,
)

MAX_REQUEST_BYTES = 60_000
MAX_PROMPT_CHARS = 50_000
SYSTEM = "You are a personal stylist. Reply with JSON only."
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
        if self.path != "/api/style":
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
        if not 0 < size <= MAX_REQUEST_BYTES:
            return self.send_json(413, {"code": "request_too_large", "error": "Request too large"})
        try:
            body = json.loads(self.rfile.read(size))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self.send_json(400, {"code": "bad_request", "error": "Invalid request"})

        prompt = body.get("prompt") if isinstance(body, dict) else None
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT_CHARS:
            return self.send_json(400, {"code": "bad_request", "error": "Invalid prompt"})

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return self.send_json(503, {"code": "misconfigured", "error": "The AI service is not configured"})

        try:
            client = Anthropic(api_key=api_key, timeout=45.0, max_retries=0)
            response = client.beta.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                max_tokens=16000,
                output_config={"effort": "low"},  # short JSON answers: low effort keeps replies quick
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # if Sonnet declines, Anthropic retries on its recommended model
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
        except RateLimitError:
            return self.send_json(429, {"code": "rate_limited", "error": "The AI service is busy"})
        except APITimeoutError:
            return self.send_json(504, {"code": "timeout", "error": "The AI service took too long"})
        except AuthenticationError:
            logger.exception("Anthropic rejected the configured API key")
            return self.send_json(503, {"code": "misconfigured", "error": "The AI service is not configured"})
        except APIConnectionError:
            logger.exception("Could not connect to Anthropic")
            return self.send_json(502, {"code": "offline", "error": "Could not reach the AI service"})
        except APIStatusError:
            logger.exception("Anthropic returned an API error")
            return self.send_json(502, {"code": "failed", "error": "The AI service returned an error"})

        if response.stop_reason == "refusal":
            return self.send_json(502, {"code": "refused", "error": "The AI declined this request"})
        text = "\n".join(block.text for block in response.content if block.type == "text")
        if not text:
            logger.error("Anthropic returned no text content")
            return self.send_json(502, {"code": "failed", "error": "The AI service returned no text"})
        return self.send_json(200, {"text": text})

    def do_GET(self):
        # lets the app know whether AI is set up, so it can switch its AI features off cleanly when it is not
        if self.path.split("?")[0] == "/api/style":
            return self.send_json(200, {"ai": bool(os.environ.get("ANTHROPIC_API_KEY"))})
        return self.send_json(404, {"code": "not_found", "error": "Not found"})
