# Backend API

FastAPI service exposing the **traditional booking surface** and the
**multi-agent AI concierge**, over the single Postgres engine the ingestion
pipeline populates.

## Layout

```
api/
  main.py            app factory, lifespan (pool/redis/graph), trace middleware
  config.py          env-driven settings
  db.py              async psycopg pool
  cache.py           Redis JSON cache (+ deterministic key hashing)
  observability.py   per-request trace: tokens, latency, agent steps
  llm.py             AsyncOpenAI wrapper (embed / structured parse / chat)
  repository.py      ALL sql: search, detail, reviews, hybrid retrieval, quote
  schemas.py         request/response + structured LLM output models
  agents/
    state.py         AgentState + Deps
    intent.py        NL -> TravelQuery
    retrieval.py     hybrid (vector + filter + geo) + rationale, cached
    review.py        review synthesis with citations + hallucination guard
    itinerary.py     multi-day, multi-property plan
    graph.py         LangGraph wiring + SSE streaming runner
  routers/
    search.py        /api/search, /properties/{id}[/reviews|availability|quote]
    concierge.py     /api/nl-search, /api/concierge/stream (SSE)
    batch.py         /api/batch/compare, /api/batch/summaries
    metrics.py       /api/metrics/{request_id}
```

## Why LangGraph
Explicit `StateGraph` with typed state gives observable, individually-streamable
agent steps, trivial conditional routing (review vs itinerary), and an additive
`trace` reducer that feeds both the SSE stream and the metrics endpoint — with
far less glue than hand-rolled orchestration.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env          # DATABASE_URL, REDIS_URL, OPENAI_API_KEY
uvicorn api.main:app --reload
```

## Key endpoints
- `GET  /api/search` — availability-aware filtered search, sort, pagination.
- `POST /api/nl-search` — free text → filter chips + results (powers the NL bar).
- `POST /api/concierge/stream` — SSE: per-agent step events, then a result event
  with candidates, cited review insights, or an itinerary.
- `POST /api/batch/compare` — AI verdict over 2–5 listings.
- `POST /api/batch/summaries` — parallel review syntheses for up to 20 listings.
- `GET  /api/metrics/{request_id}` — token usage, latency, and the agent trace
  for any request (id returned in the `X-Request-Id` header).

## Design notes
- **Hybrid retrieval** runs filters + cosine similarity + geo distance in one SQL
  statement (pgvector `<=>`, PostGIS `ST_Distance`); no candidate shuffling
  between stores.
- **Caching** keys on parsed intent and on candidate-id sets, so repeated travel
  queries and review syntheses are near-free.
- **Hallucination control**: the review agent is handed an explicit id→text map,
  told to cite only those ids, and any stray id is dropped post-hoc.
- **Async throughout** with a psycopg pool; batch routes fan out under a semaphore.
