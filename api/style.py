import json
import logging
import os
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
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=4096,
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

        text = "\n".join(block.text for block in response.content if block.type == "text")
        if not text:
            logger.error("Anthropic returned no text content")
            return self.send_json(502, {"code": "failed", "error": "The AI service returned no text"})
        return self.send_json(200, {"text": text})

    def do_GET(self):
        return self.send_json(405, {"code": "method_not_allowed", "error": "Method not allowed"})
