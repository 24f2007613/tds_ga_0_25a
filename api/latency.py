import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

app = FastAPI()

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "*",
}


@app.middleware("http")
async def add_cors(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS_HEADERS)
    response = await call_next(request)
    response.headers.update(CORS_HEADERS)
    return response


DATA = json.loads(
    (Path(__file__).resolve().parent.parent / "q-vercel-latency.json").read_text()
)
# If the file wraps the records in an object, use the first list inside it
if isinstance(DATA, dict):
    DATA = next(v for v in DATA.values() if isinstance(v, list))


class Query(BaseModel):
    regions: list[str]
    threshold_ms: float


def field(rec, *names):
    for n in names:
        if n in rec:
            return rec[n]
    raise KeyError(names)


@app.options("/{path:path}")
def preflight(path: str):
    return Response(status_code=204, headers=CORS_HEADERS)


@app.post("/")
@app.post("/api/latency")
def latency(q: Query):
    out = {}
    for region in q.regions:
        recs = [r for r in DATA if r["region"] == region]
        if not recs:
            continue
        lat = np.array([field(r, "latency_ms", "latency") for r in recs], float)
        up = np.array([field(r, "uptime_pct", "uptime") for r in recs], float)
        out[region] = {
            "avg_latency": float(lat.mean()),
            "p95_latency": float(np.percentile(lat, 95)),
            "avg_uptime": float(up.mean()),
            "breaches": int((lat > q.threshold_ms).sum()),
        }
    return {"regions": out}