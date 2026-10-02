#!/usr/bin/env python3
"""A LOCAL STUB of agent A's edge (the-release-infrastructure-this-week: "until
agent A lands, B and D build against a local stub that returns 200").

    tools/edge-stub.py [port]        # default 8787, the stub URLs in catalog.json

POST /requests   200 and a request id; logs what a real intake would refuse on
                 (no photo, no licence tick) but stores nothing.
GET  /downloads  200 and a line naming the subject a signed link would be for.
Every answer carries CORS headers, so the catalog served from another port can
post to it. It is a stub: nothing is moderated, signed or kept.
"""
import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Stub(BaseHTTPRequestHandler):
    def _send(self, code, body, kind="application/json"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, "")

    def do_POST(self):
        if urlparse(self.path).path != "/requests":
            return self._send(404, json.dumps({"error": "no such route"}))
        size = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(size)
        has_photo = b'name="photo"; filename=' in body
        has_licence = b'name="licence"' in body
        rid = uuid.uuid4().hex[:12]
        print("stub intake: %d bytes, photo=%s, licence=%s -> request %s" % (size, has_photo, has_licence, rid),
              flush=True)
        self._send(200, json.dumps({"request": rid, "stub": True}))

    def do_GET(self):
        u = urlparse(self.path)
        if u.path != "/downloads":
            return self._send(404, json.dumps({"error": "no such route"}))
        subject = parse_qs(u.query).get("subject", ["?"])[0]
        self._send(200, "stub: a signed link for the finer builds of %s would be issued here\n" % subject,
                   "text/plain")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    print("edge stub on http://127.0.0.1:%d" % port, flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Stub).serve_forever()
