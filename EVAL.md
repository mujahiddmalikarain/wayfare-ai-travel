# EVAL.md — measuring agent quality

This documents how we judge whether the AI layer is actually good, not just
whether it runs. The brief asks for "hallucination control on real data" and
"basic eval thinking", so the eval is built around two questions: **did the
system understand the request**, and **can we trust what it claims**.

## What we measure and why

| Metric | What it captures | How |
|---|---|---|
| **Intent accuracy** | Did NL → structured query extract the right city, budget, dates, amenities, constraints? Everything downstream depends on this. | Automatic — compare parsed fields to expected (`eval/run_eval.py`) |
| **Constraint adherence** | Do the top-5 returned stays actually respect the *hard* constraints (≤ budget, has required amenities, not in an excluded area)? Catches retrieval that ignores filters. | Automatic |
| **Citation validity** | Do the review ids the agent cites resolve to real reviews of the candidate stays? This is our core hallucination signal. | Automatic |
| **Faithfulness** | Are the agent's *claims* supported by the cited reviews (not just valid ids)? | Manual, 1–5 |
| **Relevance** | Would a traveller accept the top results / itinerary? | Manual, 1–5 |
| **Latency & tokens** | Cost and responsiveness per query. | Automatic, from `/api/metrics/{id}` |

Splitting *automatable* (intent, constraints, citation validity, latency) from
*judgment* (faithfulness, relevance) is deliberate: the automatable metrics can
gate every change cheaply; the manual ones are scored on the small golden set.

### Manual rubric (1–5)
**5** perfect · **4** minor slip, still usable · **3** usable with caveats ·
**2** noticeably wrong · **1** unusable or misleading.

## Hallucination control

Three layers, and the eval probes the last one:
1. **Grounding** — the review agent is handed an explicit `id → text` map and
   instructed to cite only those ids.
2. **Post-hoc guard** — the serving layer drops any cited id that isn't in the
   set it supplied, so the *user-facing* citation validity is 100% by
   construction.
3. **Raw model rate** — because (2) hides model mistakes, we measure the model's
   *unfiltered* hallucination separately: run the review agent offline and count
   `dropped_ids / total_cited_ids`. That's the number to watch when changing the
   prompt or model; a rising raw rate is an early warning even while the guard
   keeps the UI clean.

## Golden set

Eight queries in `eval/golden.yaml`, including the two hard queries from the
brief and one deliberate **failure case** (no city) to check graceful
degradation. Mix of plain NL search and full concierge (review and itinerary
paths).

## Results

Run on the seeded two-city corpus:

```bash
pip install -r eval/requirements.txt
API_URL=http://localhost:8000 python -m eval.run_eval
```

The harness prints the automatable columns (intent / constraints / citation
validity / latency / tokens) and aggregates. Run it once against your seeded
stack and paste the numbers below; the manual columns (faithfulness, relevance)
are scored by hand against the 1–5 rubric above.

_Illustrative shape — replace with your seeded run:_

| Query | Path | Intent | Constraints | Citations | Faithful¹ | Relevance¹ | Latency |
|---|---|---:|---:|---:|---:|---:|---:|
| nl-lisbon-balcony | nl | 100% | 100% | — | — | 5 | 410ms |
| nl-lisbon-pool | nl | 100% | 100% | — | — | 4 | 380ms |
| nl-barcelona-room | nl | 100% | 80% | — | — | 4 | 360ms |
| nl-barcelona-family | nl | 100% | 100% | — | — | 5 | 370ms |
| concierge-lisbon-consistent | review | 100% | 100% | 100% | 5 | 5 | 3.1s |
| concierge-barcelona-itinerary | itinerary | 100% | 100% | — | 4 | 4 | 4.2s |
| concierge-lisbon-water | review | 80% | 80% | 100% | 4 | 4 | 2.9s |
| failure-no-city | — | graceful: degraded, no crash | | | | | 210ms |

_¹ manual, 1–5._ Aggregates (intent / constraints / citation validity) are
printed by the harness.

### Reading the failure case
`failure-no-city` confirms the system degrades instead of crashing: NL search
returns a `422` with a clear message ("could not determine a city"), and the
concierge resolves no city, returns an empty candidate set with a plain answer,
and never fabricates a destination. This is the failure case shown in the Loom.

## Known limitations
- Small golden set (8) — enough to catch regressions and demonstrate the method,
  not a statistically robust benchmark. Next step is 50–100 queries with a couple
  of independent manual scorers and inter-rater agreement.
- Constraint adherence is a *proxy* for relevance — a stay can satisfy every hard
  constraint and still be a poor match on vibe; that's what the manual relevance
  score is for.
- Citation validity measures resolution, not semantic support; faithfulness
  (manual) covers whether the claim is actually backed by the review.
- No regression baseline stored yet — the harness prints current numbers but
  doesn't diff against a saved run. Wiring it into CI with a stored baseline is
  the obvious follow-up.
