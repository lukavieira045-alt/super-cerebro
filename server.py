"""Servidor web local do Super Cérebro."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from agent.brain import build_agent
from agent.health import run_health_checks

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
BRAIN = build_agent()


class Handler(BaseHTTPRequestHandler):
    server_version = "SuperCerebro/1.0"

    def _json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, content_type: str) -> None:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            self._json(404, {"error": "arquivo não encontrado"})
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            report = run_health_checks()
            self._json(200 if report.ok else 503, {
                "ok": report.ok,
                "checks": [
                    {"name": check.name, "ok": check.ok, "detail": check.detail}
                    for check in report.checks
                ],
            })
            return

        routes = {
            "/": (WEB / "index.html", "text/html; charset=utf-8"),
            "/web/index.html": (WEB / "index.html", "text/html; charset=utf-8"),
            "/web/style.css": (WEB / "style.css", "text/css; charset=utf-8"),
            "/web/app.js": (WEB / "app.js", "application/javascript; charset=utf-8"),
        }
        route = routes.get(self.path)
        if route is None:
            self._json(404, {"error": "rota não encontrada"})
            return
        self._file(*route)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self._json(404, {"error": "rota não encontrada"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 25_000:
                raise ValueError("corpo da requisição inválido")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            text = str(payload.get("message", "")).strip()
            if not text:
                raise ValueError("mensagem vazia")
            if len(text) > 20_000:
                raise ValueError("mensagem muito longa")
            answer = BRAIN.ask(text)
            self._json(200, {"answer": answer})
        except RuntimeError as exc:
            self._json(502, {"error": str(exc)})
        except Exception as exc:
            self._json(400, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        print(f"[web] {self.address_string()} - {format % args}")


def main() -> None:
    port = 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Super Cérebro web: http://127.0.0.1:{port}")
    print("Núcleo: Vireonix Auto")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
