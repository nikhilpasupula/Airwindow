"""Run AirWindow locally with no AWS account:  python local_server.py  ->  http://localhost:8000
Uses the in-memory store; alerts and Bedrock are off. Set TINYFISH_API_KEY to try the station check."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import api_handler  # noqa: E402


class H(BaseHTTPRequestHandler):
    def _go(self, method):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        event = {
            "rawPath": u.path,
            "requestContext": {"http": {"method": method}},
            "queryStringParameters": dict(parse_qsl(u.query)) or None,
            "body": self.rfile.read(n).decode() if n else None,
        }
        r = api_handler.handler(event)
        body = r["body"].encode()
        self.send_response(r["statusCode"])
        for k, v in r["headers"].items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._go("GET")

    def do_POST(self):
        self._go("POST")


if __name__ == "__main__":
    print("AirWindow on http://localhost:8000")
    HTTPServer(("", 8000), H).serve_forever()
