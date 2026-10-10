import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA = json.loads(
    (Path(__file__).parent.parent / "q-vercel-latency.json").read_text()
)


class Query(BaseModel):
    regions: list[str]
    threshold_ms: float


def field(rec, *names):
    for n in names:
        if n in rec:
            return rec[n]
    raise KeyError(names)


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