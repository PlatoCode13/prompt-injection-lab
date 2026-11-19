"""
Demo server for the prompt-injection presentation.

  python3 demo_server.py

Starts two local servers (nothing is reachable from outside this laptop):
  * http://localhost:8000                   : serves the slides
  * http://localhost:8765                   : the fake "attacker server" that receives
                                              every email the agent sends and prints
                                              stolen data in this terminal.
"""
import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
SLIDES_PORT = 8000
ATTACKER_PORT = 8765
CANARY = "CANARY-7F3A"

RED, GREEN, YELLOW, DIM, BOLD, RESET = "\033[91m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
if os.name == "nt":
    os.system("")  # enables ANSI colours in the Windows terminal

inbox = []
lock = threading.Lock()


class AttackerHandler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/health"):
            return self._json({"ok": True})
        if self.path.startswith("/log"):
            since = 0
            if "since=" in self.path:
                try:
                    since = int(self.path.split("since=")[1].split("&")[0])
                except ValueError:
                    pass
            with lock:
                items = [m for m in inbox if m["id"] > since]
            return self._json({"items": items})
        self._json({"error": "not found"}, 404)

    def do_POST(self):
        if not self.path.startswith("/send"):
            return self._json({"error": "not found"}, 404)
        length = int(self.headers.get("Content-Length", 0))
        try:
            msg = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        with lock:
            msg["id"] = len(inbox) + 1
            msg.setdefault("time", time.strftime("%Y-%m-%dT%H:%M:%S"))
            inbox.append(msg)
        text = f"{msg.get('subject','')} {msg.get('body','')}"
        if msg.get("external"):
            leaked = CANARY in text.upper()
            colour = RED if leaked else YELLOW
            print(f"\n{colour}{BOLD}{'=' * 60}")
            print("  ☠  INCOMING DATA AT ATTACKER SERVER" + ("  (CANARY STOLEN!)" if leaked else ""))
            print(f"{'=' * 60}{RESET}")
            print(f"{BOLD}to:{RESET}      {msg.get('to')}")
            print(f"{BOLD}subject:{RESET} {msg.get('subject')}")
            print(f"{BOLD}body:{RESET}\n{msg.get('body')}\n")
        else:
            print(f"{GREEN}✉  internal email to {msg.get('to')} (not stolen){RESET}")
        self._json({"ok": True, "id": msg["id"]})

    def log_message(self, *args):  # keep the terminal clean
        pass


def openai_error_message(error):
    if error.code == 429:
        with error:
            try:
                details = json.loads(error.read(16_384)).get("error", {})
            except (ValueError, AttributeError):
                details = {}
        if not isinstance(details, dict):
            details = {}
        code = details.get("code")
        if code in ("organization_spend_limit_exceeded", "project_spend_limit_exceeded", "api_key_spend_limit_exceeded", "organization_usage_limit_exceeded", "usage_limit_exceeded"):
            return "OpenAI's API spend or usage limit was reached. Check the limits for this key's project and organization."
        if code in ("insufficient_quota", "credit_balance_exhausted", "billing_not_active") or details.get("type") == "insufficient_quota":
            return "OpenAI API billing or credits are unavailable for this key's organization. Check API Billing."
        if code in ("rate_limit_exceeded", "slow_down") or details.get("type") == "rate_limit_error":
            return "OpenAI temporarily rate-limited this request. Wait briefly before testing again."
        return "OpenAI returned HTTP 429. Check API Billing and Limits for this key's organization, or wait before trying again."
    if error.code == 401:
        return "OpenAI could not authenticate this API key. Check the key in Settings."
    if error.code in (403, 404):
        return "OpenAI could not access this model. Check the model ID and the key's project permissions."
    return f"OpenAI returned HTTP {error.code}."


class QuietStatic(SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.command in {"GET", "HEAD"}:
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path != "/api/openai/summary":
            return self.send_error(404)

        host = self.headers.get("Host")
        port = self.server.server_port
        if host not in {f"localhost:{port}", f"127.0.0.1:{port}"} or self.headers.get("Origin") != f"http://{host}":
            return self._json({"error": "Open the presentation from the local slide server."}, 403)

        authorization = self.headers.get("Authorization", "")
        if not re.fullmatch(r"Bearer sk-[A-Za-z0-9_-]{20,512}", authorization):
            return self._json({"error": "Enter an OpenAI API key in Settings."}, 401)

        try:
            length = int(self.headers.get("Content-Length", ""))
            if not 0 < length <= 16_384:
                raise ValueError
            data = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeError):
            return self._json({"error": "Invalid summary request."}, 400)

        model = data.get("model") if isinstance(data, dict) else None
        if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", model):
            return self._json({"error": "Enter a valid OpenAI model ID."}, 400)
        text = data.get("text")
        if not isinstance(text, str) or len(text) > 4000:
            return self._json({"error": "Provide slide text of up to 4,000 characters."}, 400)

        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps({
                "model": model,
                "instructions": "Summarize the slide in two sentences." if text else "Reply with the single word: ready.",
                "input": text or "Connection test.",
                "max_output_tokens": 256,
                "store": False,
            }).encode("utf-8"),
            headers={"Authorization": authorization, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                result = json.load(response)
        except HTTPError as error:
            return self._json({"error": openai_error_message(error)}, 502)
        except (URLError, TimeoutError, ValueError):
            return self._json({"error": "The local server could not get a response from OpenAI."}, 502)

        answer = "".join(
            part["text"]
            for item in result.get("output", []) if item.get("type") == "message"
            for part in item.get("content", []) if part.get("type") == "output_text"
        ).strip()
        if not answer:
            return self._json({"error": "OpenAI did not return a text answer."}, 502)
        return self._json({"text": answer}, 200)

    def _json(self, data, status):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    attacker = HTTPServer((HOST, ATTACKER_PORT), AttackerHandler)
    slides = ThreadingHTTPServer((HOST, SLIDES_PORT), QuietStatic)
    threading.Thread(target=attacker.serve_forever, daemon=True).start()
    threading.Thread(target=slides.serve_forever, daemon=True).start()
    print(f"{BOLD}Presentation server running.{RESET}")
    page = "" if os.path.exists("index.html") else "Presentation.html"
    print(f"  Open slides in your browser  {GREEN}http://localhost:{SLIDES_PORT}/{page}{RESET}")
    print(f"  Attacker server              {RED}http://localhost:{ATTACKER_PORT}{RESET}")
    print(f"{DIM}Keep this terminal open while presenting. Ctrl+C stops the server.{RESET}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nPresentation server stopped.")


if __name__ == "__main__":
    main()
