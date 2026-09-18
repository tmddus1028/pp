"""TEST ONLY: HTTP Ollama protocol double. Never a live model or semantic quality test."""

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_revisions import mock_assessment  # noqa: E402

from backend.improvements.service import local_review  # noqa: E402

calls = {"improvement": 0, "revision": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(calls).encode())

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        context = json.loads(data["messages"][-1]["content"])
        if "revised_claim" in context:
            calls["revision"] += 1
            result = mock_assessment(context, "UNCERTAIN")
        else:
            calls["improvement"] += 1
            result = local_review(context)
            result.issue_summary = "TEST MOCK ONLY: " + result.issue_summary
        body = json.dumps(
            {"done": True, "done_reason": "stop", "message": {"content": result.model_dump_json()}},
            ensure_ascii=False,
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 11435), Handler).serve_forever()
