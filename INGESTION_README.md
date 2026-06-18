# Ingestion pipeline

Re-runnable pipeline that loads Inside Airbnb data into a single Postgres engine
(relational + `pgvector` + `PostGIS`) and enriches it for the booking + AI layers.

## Design

A small **Pipeline / Stage** orchestrator. Each stage is independent and
idempotent, so any stage can be re-run in isolation:

```
schema → load_listings → load_calendar → load_reviews
       → percentile → embeddings → review_summary
```

- **Loads** stream gzipped CSVs into TEMP staging tables via `COPY`, then upsert
  with `ON CONFLICT` — fast at 50K–1M rows and safe to re-run. Loads never
  overwrite enrichment columns.
- **Enrichments** are keyset-paginated and skip already-done rows unless
  `--force`, so re-running only fills gaps.

### Enrichments
1. **Amenity normalization** — deterministic, free.
2. **Neighbourhood price percentile** — one SQL window, free.
3. **Listing embeddings** — `text-embedding-3-small`, batched + retried.
4. **Per-property review summary + aspect scores** — `gpt-4o-mini` Structured
   Outputs, bounded concurrency, "use only supplied reviews" for hallucination
   control. Precomputed once so serving is cache-cheap.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # fill DATABASE_URL + OPENAI_API_KEY
```

Data layout (download per-city files from https://insideairbnb.com/get-the-data/):

```
data/
  lisbon/{listings,calendar,reviews}.csv[.gz]
  barcelona/{listings,calendar,reviews}.csv[.gz]
```

Files may be gzipped (`.csv.gz`) or already decompressed (`.csv`) — the loader
handles both.

## Run

```bash
python -m ingestion                     # full pipeline
python -m ingestion --only embeddings   # re-embed only
python -m ingestion --from percentile   # resume from a stage
python -m ingestion --skip review_summary
python -m ingestion --only review_summary --force
```

The run prints rows touched, token usage, and an estimated USD cost.

## Notes / trade-offs
- Per-review embeddings are intentionally skipped; semantic search runs over
  listing embeddings, and review intelligence reads precomputed summaries. Add
  review embeddings later if you need review-level semantic search.
- `langdetect` is the slowest load step. Disable with `DETECT_LANGUAGE=false`,
  or swap for fastText `lid.176` on very large corpora.
- Calendar is windowed to `CALENDAR_MONTHS` to keep the table bounded.
