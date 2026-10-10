import json
import os
from http.server import BaseHTTPRequestHandler

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, *",
}

_DATA = None


def load_data():
    global _DATA
    if _DATA is None:
        here = os.path.dirname(os.path.abspath(__file__))
        for p in (
            os.path.join(here, "q-vercel-latency.json"),
            os.path.join(os.getcwd(), "api", "q-vercel-latency.json"),
            os.path.join(os.getcwd(), "q-vercel-latency.json"),
        ):
            if os.path.exists(p):
                with open(p) as f:
                    _DATA = json.load(f)
                break
        else:
            raise FileNotFoundError("q-vercel-latency.json not found")
    return _DATA


def percentile(values, p):
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def compute(regions, threshold):
    data = load_data()
    out = {}
    for r in regions:
        rows = [d for d in data if d["region"] == r]
        if not rows:
            continue
        lat = [d["latency_ms"] for d in rows]
        up = [d["uptime_pct"] for d in rows]
        out[r] = {
            "avg_latency": sum(lat) / len(lat),
            "p95_latency": percentile(lat, 95),
            "avg_uptime": sum(up) / len(up),
            "breaches": sum(1 for x in lat if x > threshold),
        }
    return out


class handler(BaseHTTPRequestHandler):
    def _send(self, code, body=None):
        self.send_response(code)
        for k, v in CORS.items():
            self.send_header(k, v)
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode()
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def do_OPTIONS(self):
        self._send(204)

    def do_GET(self):
        self._send(200, {
            "status": "ok",
            "usage": 'POST {"regions": ["emea","apac"], "threshold_ms": 180}',
        })

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(n) or b"{}")
            regions = payload.get("regions", [])
            threshold = payload.get("threshold_ms", 180)
            self._send(200, {"regions": compute(regions, threshold)})
        except Exception as e:
            self._send(500, {"error": str(e)})