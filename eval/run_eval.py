"""Eval harness for the agent system.

Runs the golden set against a live API and computes the metrics that can be
checked automatically:

  * intent_accuracy   — fraction of expected structured fields extracted correctly
  * constraint_adher. — fraction of top-K candidates satisfying hard constraints
  * citation_validity — fraction of cited review ids that resolve to real reviews
  * latency_ms / tokens — read back from /api/metrics/{request_id}

Relevance and faithfulness are judgment calls — scored by hand in EVAL.md.

Usage:
    pip install -r eval/requirements.txt
    API_URL=http://localhost:8000 python -m eval.run_eval
"""
from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml

API = os.environ.get("API_URL", "http://localhost:8000")
TOPK = 5


@dataclass
class Result:
    id: str
    intent_accuracy: float | None = None
    constraint_adherence: float | None = None
    citation_validity: float | None = None
    latency_ms: float | None = None
    tokens: int | None = None
    graceful: bool | None = None
    notes: list[str] = field(default_factory=list)


# ── helpers ───────────────────────────────────────────────────────────────────
def score_intent(expect: dict, intent: dict) -> float:
    checks: list[bool] = []
    for key in ("city", "max_price", "guests", "room_type", "multi_stop"):
        if key in expect:
            checks.append(intent.get(key) == expect[key])
    if "amenities" in expect:
        got = set(intent.get("amenities") or [])
        checks.append(set(expect["amenities"]).issubset(got))
    if "exclude_neighbourhoods" in expect:
        got = {n.lower() for n in (intent.get("exclude_neighbourhoods") or [])}
        want = {n.lower() for n in expect["exclude_neighbourhoods"]}
        checks.append(want.issubset(got))
    return round(sum(checks) / len(checks), 2) if checks else None


def _as_float(v: object) -> float | None:
    """Prices come back as strings on some endpoints (NUMERIC -> str); coerce."""
    try:
        return float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def constraint_adherence(expect: dict, listings: list[dict]) -> float | None:
    sample = listings[:TOPK]
    if not sample:
        return None
    ok = 0
    for l in sample:
        good = True
        price = _as_float(l.get("price"))
        if expect.get("max_price") and price is not None and price > expect["max_price"]:
            good = False
        if expect.get("amenities"):
            if not set(expect["amenities"]).issubset(set(l.get("amenities") or [])):
                good = False
        if expect.get("exclude_neighbourhoods"):
            bad = {n.lower() for n in expect["exclude_neighbourhoods"]}
            if (l.get("neighbourhood") or "").lower() in bad:
                good = False
        ok += good
    return round(ok / len(sample), 2)


def citation_validity(insights: dict | None, candidates: list[dict]) -> float | None:
    if not insights or not insights.get("highlights"):
        return None
    cited = {rid for h in insights["highlights"] for rid in h.get("review_ids", [])}
    if not cited:
        return None
    valid: set[int] = set()
    for c in candidates[:TOPK]:
        try:
            reviews = requests.get(
                f"{API}/api/properties/{c['id']}/reviews", params={"limit": 50}, timeout=30
            ).json()
            valid |= {r["id"] for r in reviews}
        except requests.RequestException:
            continue
    return round(len(cited & valid) / len(cited), 2)


def stream_concierge(message: str, city: str | None) -> tuple[dict, dict, str | None]:
    """Returns (intent_from_first_step, final_result, request_id)."""
    intent: dict = {}
    final: dict = {}
    request_id: str | None = None
    with requests.post(
        f"{API}/api/concierge/stream",
        json={"message": message, "city": city},
        stream=True, timeout=120,
    ) as resp:
        request_id = resp.headers.get("X-Request-Id")
        for raw in resp.iter_lines():
            if not raw or not raw.startswith(b"data:"):
                continue
            payload = raw[5:].strip()
            if payload == b"[DONE]":
                break
            event = json.loads(payload)
            if event.get("type") == "step" and event.get("node") == "intent":
                intent = event.get("data", {})
            elif event.get("type") == "result":
                final = event
    return intent, final, request_id


def fetch_metrics(request_id: str | None) -> dict:
    if not request_id:
        return {}
    try:
        return requests.get(f"{API}/api/metrics/{request_id}", timeout=30).json()
    except requests.RequestException:
        return {}


# ── per-case runners ──────────────────────────────────────────────────────────
def run_nl(case: dict) -> Result:
    r = Result(id=case["id"])
    resp = requests.post(
        f"{API}/api/nl-search",
        json={"message": case["query"], "city": case.get("city")},
        timeout=60,
    )
    if resp.status_code == 422:
        r.graceful = case["expect"].get("graceful", False)
        r.notes.append("422 (no city) — handled")
        return r
    data = resp.json()
    r.intent_accuracy = score_intent(case["expect"], data.get("intent", {}))
    r.constraint_adherence = constraint_adherence(case["expect"], data.get("results", []))
    r.latency_ms = fetch_metrics(resp.headers.get("X-Request-Id")).get("latency_ms")
    return r


def run_concierge(case: dict) -> Result:
    r = Result(id=case["id"])
    intent, final, rid = stream_concierge(case["query"], case.get("city"))
    if case["expect"].get("graceful"):
        r.graceful = bool(final) and not final.get("candidates")
        r.notes.append("no city — degraded without crashing" if r.graceful else "did not degrade")
        return r
    r.intent_accuracy = score_intent(case["expect"], intent)
    r.constraint_adherence = constraint_adherence(case["expect"], final.get("candidates", []))
    r.citation_validity = citation_validity(final.get("review_insights"), final.get("candidates", []))
    expected_path = case["expect"].get("path")
    if expected_path == "itinerary":
        r.notes.append("itinerary produced" if final.get("itinerary") else "MISSING itinerary")
    metrics = fetch_metrics(rid)
    r.latency_ms = metrics.get("latency_ms")
    tok = metrics.get("tokens", {})
    r.tokens = (tok.get("input", 0) + tok.get("output", 0)) if tok else None
    return r


# ── reporting ─────────────────────────────────────────────────────────────────
def pct(v: float | None) -> str:
    return "—" if v is None else f"{v * 100:.0f}%"


def main() -> None:
    cases = yaml.safe_load(Path("eval/golden.yaml").read_text())
    results = [run_nl(c) if c["type"] == "nl" else run_concierge(c) for c in cases]

    print(f"\nEval against {API}  (top-{TOPK})\n")
    hdr = ("id", "intent", "constraints", "citations", "latency", "tokens")
    print("| {:<28} | {:>6} | {:>11} | {:>9} | {:>8} | {:>6} |".format(*hdr))
    print("|" + "-" * 30 + "|" + "-" * 8 + "|" + "-" * 13 + "|" + "-" * 11 + "|" + "-" * 10 + "|" + "-" * 8 + "|")
    for r in results:
        lat = "—" if r.latency_ms is None else f"{r.latency_ms:.0f}ms"
        tok = "—" if r.tokens is None else str(r.tokens)
        print("| {:<28} | {:>6} | {:>11} | {:>9} | {:>8} | {:>6} |".format(
            r.id, pct(r.intent_accuracy), pct(r.constraint_adherence),
            pct(r.citation_validity), lat, tok))
        for n in r.notes:
            print(f"|   ↳ {n}")

    def avg(attr: str) -> float | None:
        vals = [getattr(r, attr) for r in results if getattr(r, attr) is not None]
        return round(statistics.mean(vals), 2) if vals else None

    print("\nAggregates:")
    print(f"  mean intent accuracy   : {pct(avg('intent_accuracy'))}")
    print(f"  mean constraint adher. : {pct(avg('constraint_adherence'))}")
    print(f"  mean citation validity : {pct(avg('citation_validity'))}")
    lat = avg("latency_ms")
    print(f"  mean latency           : {'—' if lat is None else f'{lat:.0f}ms'}")


if __name__ == "__main__":
    main()
