#!/usr/bin/env python3
"""Serve the study plan locally and keep progress in progress.json next to this file.

    python3 serve.py            # http://localhost:8765
    python3 serve.py --port 9000 --host 0.0.0.0   # reachable from other devices on your network

Standard library only. Every save writes progress.json atomically and keeps the
previous version as progress.json.bak.
"""

import argparse
import json
import os
import tempfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "progress.json"
MAX_BYTES = 5 * 1024 * 1024


def _read_progress():
    try:
        return json.loads(DATA.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        raise


def _write_progress(state):
    if DATA.exists():
        DATA.replace(DATA.with_suffix(".json.bak"))
    fd, tmp = tempfile.mkstemp(dir=ROOT, prefix=".progress-")
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, DATA)


def create_app():
    try:
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse
        from starlette.routing import Mount, Route
        from starlette.staticfiles import StaticFiles
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the app dependencies with: pip install uvicorn starlette") from exc

    async def api_progress(request):
        if request.method == "GET":
            try:
                return JSONResponse(_read_progress())
            except json.JSONDecodeError:
                return JSONResponse({"error": "progress.json is not valid JSON"}, status_code=500)

        if request.method == "PUT":
            body = await request.body()
            if len(body) <= 0 or len(body) > MAX_BYTES:
                return JSONResponse({"error": "bad size"}, status_code=413)
            try:
                state = json.loads(body)
                assert isinstance(state, dict)
            except Exception:
                return JSONResponse({"error": "body must be a JSON object"}, status_code=400)
            _write_progress(state)
            return JSONResponse({"ok": True})

        return JSONResponse({"detail": "Method not allowed"}, status_code=405)

    async def deny_file(request):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    app = Starlette(
        routes=[
            Route("/api/progress", api_progress, methods=["GET", "PUT"]),
            Route("/progress.json", deny_file, methods=["GET", "HEAD"]),
            Route("/serve.py", deny_file, methods=["GET", "HEAD"]),
            Mount("/", app=StaticFiles(directory=str(ROOT), html=True), name="static"),
        ]
    )
    return app


try:  # uvicorn imports `serve:app` when the dependency is installed.
    app = create_app()
except RuntimeError:
    app = None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/progress":
            try:
                return self._json(200, json.loads(DATA.read_text()))
            except FileNotFoundError:
                return self._json(200, {})
            except json.JSONDecodeError:
                return self._json(500, {"error": "progress.json is not valid JSON"})
        if self.path.startswith("/progress.json") or self.path.startswith("/serve.py"):
            return self.send_error(404)
        return super().do_GET()

    def do_PUT(self):
        if self.path.split("?")[0] != "/api/progress":
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0 or n > MAX_BYTES:
            return self._json(413, {"error": "bad size"})
        try:
            state = json.loads(self.rfile.read(n))
            assert isinstance(state, dict)
        except Exception:
            return self._json(400, {"error": "body must be a JSON object"})
        if DATA.exists():
            DATA.replace(DATA.with_suffix(".json.bak"))
        fd, tmp = tempfile.mkstemp(dir=ROOT, prefix=".progress-")
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, DATA)
        return self._json(200, {"ok": True})

    def log_message(self, fmt, *args):
        if "/api/" not in self.path:
            super().log_message(fmt, *args)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    print(f"Study plan at http://{'localhost' if a.host == '127.0.0.1' else a.host}:{a.port}  (progress -> {DATA})")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
