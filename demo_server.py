"""
Demo server for the prompt-injection presentation.

  python demo_server.py

Starts two local servers (nothing is reachable from outside this laptop):
  * http://localhost:8000                   : serves the slides
  * http://localhost:8765                   : the fake "attacker server" that receives
                                              every email the agent sends and prints
                                              stolen data in this terminal.
"""
import json, os, threading, time
from http.server import HTTPServer, SimpleHTTPRequestHandler, BaseHTTPRequestHandler

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


class QuietStatic(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    attacker = HTTPServer((HOST, ATTACKER_PORT), AttackerHandler)
    slides = HTTPServer((HOST, SLIDES_PORT), QuietStatic)
    threading.Thread(target=attacker.serve_forever, daemon=True).start()
    threading.Thread(target=slides.serve_forever, daemon=True).start()
    print(f"{BOLD}Demo running.{RESET}")
    page = "" if os.path.exists("index.html") else "Presentation.html"
    print(f"  Slides:          {GREEN}http://localhost:{SLIDES_PORT}/{page}{RESET}")
    print(f"  Attacker server: {RED}http://localhost:{ATTACKER_PORT}{RESET}  (stolen data appears below)")
    print(f"{DIM}Press Ctrl+C to stop.{RESET}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
