import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import lib.broadcaster
from web import runner as web_runner

bc = lib.broadcaster.Broadcaster()
current_runner = None
current_thread = None

WEB_DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/":
            return self._serve_file("index.html")
        if path == "/api/stream":
            return self._sse_stream()
        if path == "/api/state":
            return self._json_response(self._get_current_state())
        if path == "/api/runs":
            return self._json_response(self._list_runs())
        if path.startswith("/api/runs/"):
            if path.endswith("/summary"):
                return self._handle_summary(path)
            return self._handle_run_path(path)
        if path.startswith("/static/"):
            return self._serve_file(path[1:])

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/run":
            return self._start_run()

        self.send_error(404)

    def _serve_file(self, rel_path):
        full = os.path.normpath(os.path.join(WEB_DIR, rel_path))
        if not full.startswith(os.path.normpath(WEB_DIR)):
            self.send_error(403)
            return
        if not os.path.isfile(full):
            self.send_error(404)
            return
        ext = os.path.splitext(full)[1].lower()
        ct = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css",
            ".js": "application/javascript",
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".ttf": "font/ttf",
        }.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _json_response(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def _sse_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        q = bc.subscribe()
        try:
            while True:
                try:
                    msg = q.get(timeout=30)
                    line = f"event: {msg['event']}\ndata: {json.dumps(msg['data'], ensure_ascii=False)}\n\n"
                    self.wfile.write(line.encode("utf-8"))
                    self.wfile.flush()
                except Exception:
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except Exception:
                        break
        finally:
            bc.unsubscribe(q)

    def _get_current_state(self):
        global current_runner
        if current_runner and os.path.exists(current_runner.state_path):
            with open(current_runner.state_path, encoding="utf-8") as f:
                return json.load(f)
        return {"plan": [], "runs": []}

    def _list_runs(self):
        output_dir = os.path.join(PROJECT_ROOT, "output")
        if not os.path.isdir(output_dir):
            return []
        runs = []
        for name in sorted(os.listdir(output_dir), reverse=True):
            state_path = os.path.join(output_dir, name, "state.json")
            if os.path.isfile(state_path):
                runs.append({"id": name, "goal": name.rsplit("_", 1)[0]})
        return runs

    def _handle_run_path(self, path):
        parts = path.split("/", 4)
        if len(parts) < 4:
            self.send_error(404)
            return
        run_id = parts[3]
        rest = parts[4] if len(parts) > 4 else ""
        run_dir = os.path.join(PROJECT_ROOT, "output", run_id)
        if not os.path.isdir(run_dir):
            self.send_error(404)
            return

        if rest == "" or rest == "state":
            state_path = os.path.join(run_dir, "state.json")
            if os.path.isfile(state_path):
                with open(state_path, encoding="utf-8") as f:
                    return self._json_response(json.load(f))
            self.send_error(404)
            return

        file_path = os.path.join(run_dir, rest)
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_error(404)

    def _handle_summary(self, path):
        # /api/runs/<run_id>/summary
        rest = path[len("/api/runs/"):]
        run_id = rest.rsplit("/summary", 1)[0]
        run_dir = os.path.join(PROJECT_ROOT, "output", run_id)
        if not os.path.isdir(run_dir):
            self.send_error(404)
            return
        result = {"thinking": "", "result": ""}
        for f in os.listdir(run_dir):
            if f.startswith("summary_") and f.endswith("_thinking.md"):
                with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
                    result["thinking"] = fh.read()
            elif f.startswith("summary_") and f.endswith(".md") and "_thinking" not in f:
                with open(os.path.join(run_dir, f), encoding="utf-8") as fh:
                    result["result"] = fh.read()
        self._json_response(result)

    def _start_run(self):
        global current_runner, current_thread
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)
        try:
            req = json.loads(body)
        except Exception:
            self.send_error(400, "invalid JSON")
            return

        goal = req.get("goal", "").strip()
        if not goal:
            self.send_error(400, "goal required")
            return

        config = web_runner.load_base_config()
        config["goal"] = goal
        current_runner = web_runner.WebRunner(config, bc)
        current_thread = threading.Thread(target=current_runner.run, daemon=True)
        current_thread.start()

        self._json_response({"status": "started", "plan_id": current_runner.plan_id})

    def log_message(self, format, *args):
        pass


def main():
    config = web_runner.load_base_config()
    port = config.get("web_port", 8080)
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[web] http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
