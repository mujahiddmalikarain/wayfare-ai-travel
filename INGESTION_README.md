# Ingestion Pipeline

The ingestion pipeline loads and enriches Inside Airbnb data for the booking and AI layers of the application.

It is designed to be:

- **Re-runnable** — the full pipeline can be executed more than once safely.
- **Idempotent** — completed records are skipped unless explicitly forced.
- **Stage-based** — each stage can run independently.
- **Scalable** — loading is optimized for datasets ranging from tens of thousands to more than one million rows.
- **Cost-aware** — OpenAI-powered enrichment is batched, retried, and bounded by configuration.
- **Single-engine** — relational, vector, and geospatial data remain in one PostgreSQL database using PostGIS and pgvector.

The pipeline supports both the traditional booking experience and the AI features, including structured search, semantic retrieval, review intelligence, and itinerary generation.

---

## Architecture

The ingestion system uses a lightweight **Pipeline / Stage** orchestration pattern.

Each stage has one responsibility and can be:

- run as part of the complete pipeline
- executed independently
- resumed from a specific point
- skipped when not required
- forced to recompute existing enrichment data

The default execution order is:

```text
schema
  ↓
load_listings
  ↓
load_calendar
  ↓
load_reviews
  ↓
percentile
  ↓
embeddings
  ↓
review_summary
```

Equivalent compact view:

```text
schema → load_listings → load_calendar → load_reviews
       → percentile → embeddings → review_summary
```

This separation keeps the pipeline easy to reason about and avoids coupling raw-data loading with AI enrichment.

---

## Pipeline Stages

### 1. `schema`

Creates the required PostgreSQL extensions, tables, constraints, and indexes.

The schema supports:

- relational booking data
- listing and review records
- availability calendar data
- vector embeddings through pgvector
- geospatial coordinates and distance queries through PostGIS
- precomputed review summaries
- structured review aspect scores

Schema creation uses idempotent SQL statements such as:

```sql
CREATE EXTENSION IF NOT EXISTS ...
CREATE TABLE IF NOT EXISTS ...
CREATE INDEX IF NOT EXISTS ...
```

This allows the stage to be rerun without recreating or damaging existing objects.

---

### 2. `load_listings`

Loads property listings for every configured city.

The listing loader:

- reads `.csv.gz` or decompressed `.csv` files
- streams records instead of loading the full dataset into memory
- writes source rows into temporary staging tables
- uses PostgreSQL `COPY` for fast bulk loading
- upserts final records using `ON CONFLICT`
- preserves previously generated enrichment columns
- can be rerun safely

Listing data is later used for:

- traditional filtered search
- property detail pages
- map results
- semantic retrieval
- neighbourhood pricing analysis
- itinerary generation

---

### 3. `load_calendar`

Loads listing-level availability and pricing records.

The calendar loader follows the same high-throughput pattern:

```text
CSV or CSV.GZ
    ↓
streaming parser
    ↓
temporary staging table
    ↓
PostgreSQL COPY
    ↓
ON CONFLICT upsert
```

Calendar ingestion is intentionally bounded by `CALENDAR_MONTHS`.

This keeps the calendar table manageable and prevents unnecessary storage and query overhead for dates outside the supported booking window.

Increase `CALENDAR_MONTHS` when a production deployment requires a longer availability horizon.

---

### 4. `load_reviews`

Loads review records for each listing.

The review loader:

- supports compressed and decompressed source files
- streams large files
- loads through temporary staging tables
- uses `COPY` for bulk performance
- upserts with `ON CONFLICT`
- preserves enrichment results
- optionally detects review language

Review data powers:

- property review pages
- AI-generated review summaries
- review citations
- aspect scoring
- future review-level semantic retrieval

At the current scale, `langdetect` is the slowest part of this loading stage.

Language detection can be disabled with:

```env
DETECT_LANGUAGE=false
```

For significantly larger datasets, replacing `langdetect` with fastText `lid.176` would improve throughput.

---

### 5. `percentile`

Calculates each listing’s price percentile within its neighbourhood.

This enrichment is:

- deterministic
- computed entirely in SQL
- free from external API cost
- based on a SQL window operation
- safe to recompute

The result provides useful local pricing context, such as whether a property is inexpensive, average, or premium relative to nearby listings.

---

### 6. `embeddings`

Generates semantic embeddings for listings using:

```text
text-embedding-3-small
```

The embedding stage is:

- batched
- retried on transient failures
- keyset-paginated
- resumable
- cost-aware
- skipped for rows that already contain embeddings unless `--force` is used

Listing embeddings support natural-language and hybrid search.

The application combines:

- structured filters
- vector cosine similarity
- geospatial distance

inside one PostgreSQL query.

Per-review embeddings are intentionally not generated in the current implementation.

Semantic search operates at the listing level, while review intelligence reads precomputed property summaries.

---

### 7. `review_summary`

Generates one review summary and a set of aspect scores for each eligible property.

The stage uses:

```text
gpt-4o-mini
```

with Structured Outputs.

The review-summary process includes:

- bounded concurrency
- retry handling
- keyset pagination
- resumable execution
- skipping completed rows by default
- optional forced regeneration
- explicit grounding in supplied review text
- per-property precomputation

The model is instructed to use only the reviews supplied to it.

This is part of the hallucination-control strategy: the model is not expected to introduce unsupported facts about the property.

Precomputing summaries during ingestion keeps the serving path:

- faster
- less expensive
- more predictable
- cache-friendly

The detail page and AI layer can read the stored result instead of generating a new summary for every request.

---

## Loading Strategy

The raw-data stages are optimized for large CSV files.

### Streaming input

Files are read incrementally, which avoids loading the entire source file into memory.

Supported formats:

```text
.csv.gz
.csv
```

### Temporary staging tables

Each loader first copies data into a temporary PostgreSQL staging table.

This separates raw parsing from final-table updates.

### PostgreSQL `COPY`

`COPY` is used for bulk insertion because it is substantially faster than inserting rows one at a time.

The approach is suitable for:

- approximately 50,000 listings
- hundreds of thousands of calendar rows
- more than one million reviews

### Upsert behavior

After staging, records are inserted into the final tables using:

```sql
ON CONFLICT ...
```

This makes repeated runs safe and allows source records to be refreshed.

The loaders do not overwrite enrichment columns that were generated by later stages.

---

## Enrichment Strategy

Enrichment stages use keyset pagination instead of offset pagination.

This provides more stable performance as the dataset grows.

By default, enrichment stages skip rows that are already complete.

For example:

- a listing with an embedding is not embedded again
- a property with a review summary is not summarized again

Use `--force` when regeneration is required.

This behavior allows interrupted runs to resume without repeating all completed work.

---

## Enrichments at a Glance

| Enrichment | Method | External cost | Purpose |
|---|---|---:|---|
| Amenity normalization | Deterministic normalization | None | Standardizes inconsistent amenity labels |
| Neighbourhood price percentile | SQL window calculation | None | Adds local price context |
| Listing embeddings | `text-embedding-3-small` | OpenAI embedding cost | Supports semantic and hybrid retrieval |
| Review summary and aspect scores | `gpt-4o-mini` Structured Outputs | OpenAI generation cost | Supports review intelligence and property insights |

---

## Amenity Normalization

Amenity values in source datasets are often inconsistent.

Normalization converts equivalent or near-equivalent source values into predictable application-level values.

This enrichment is:

- deterministic
- repeatable
- free
- independent of the LLM

Normalized amenities improve:

- filtering
- display consistency
- natural-language filter extraction
- comparison between listings

---

## Setup

Install the Python dependencies:

```bash
pip install -r requirements.txt
```

Create the local environment file:

```bash
cp .env.example .env
```

At minimum, configure:

```env
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
```

The database must support:

- PostgreSQL
- PostGIS
- pgvector

The provided Docker environment already includes these requirements.

---

## Data Source

Download the per-city datasets from Inside Airbnb:

```text
https://insideairbnb.com/get-the-data/
```

The project currently uses:

- Lisbon
- Barcelona

For each city, download:

- listings
- calendar
- reviews

---

## Required Data Layout

Place the source files inside the project’s `data/` directory:

```text
data/
├── lisbon/
│   ├── listings.csv.gz
│   ├── calendar.csv.gz
│   └── reviews.csv.gz
└── barcelona/
    ├── listings.csv.gz
    ├── calendar.csv.gz
    └── reviews.csv.gz
```

The compact equivalent is:

```text
data/
  lisbon/{listings,calendar,reviews}.csv[.gz]
  barcelona/{listings,calendar,reviews}.csv[.gz]
```

Both compressed and decompressed files are supported:

```text
listings.csv.gz
listings.csv
```

The loader automatically handles either format.

---

## Running the Pipeline

### Run the complete pipeline

```bash
python -m ingestion
```

This executes every stage in the configured order:

```text
schema
load_listings
load_calendar
load_reviews
percentile
embeddings
review_summary
```

---

### Run only one stage

```bash
python -m ingestion --only embeddings
```

This runs only the listing-embedding stage.

Another example:

```bash
python -m ingestion --only review_summary
```

---

### Resume from a specific stage

```bash
python -m ingestion --from percentile
```

This skips the earlier stages and executes:

```text
percentile
embeddings
review_summary
```

This is useful when the raw data has already been loaded successfully.

---

### Skip a stage

```bash
python -m ingestion --skip review_summary
```

This runs the rest of the pipeline without generating LLM review summaries.

It is useful for:

- local development
- database-loading tests
- reducing initial API cost
- verifying search before AI enrichment

---

### Force regeneration

```bash
python -m ingestion --only review_summary --force
```

This regenerates review summaries even when a stored summary already exists.

The same approach can be used for another enrichment stage when its output must be rebuilt.

Use `--force` carefully because it can increase:

- processing time
- OpenAI token usage
- API cost

---

## Command Reference

| Command | Purpose |
|---|---|
| `python -m ingestion` | Run the full pipeline |
| `python -m ingestion --only embeddings` | Run only listing embeddings |
| `python -m ingestion --from percentile` | Resume from the percentile stage |
| `python -m ingestion --skip review_summary` | Run without review summarization |
| `python -m ingestion --only review_summary --force` | Rebuild all eligible review summaries |

---

## Runtime Reporting

During execution, the pipeline prints operational information including:

- rows touched
- token usage
- estimated OpenAI cost in USD

This makes it easier to understand:

- whether a stage performed work
- how much enrichment remains
- how much LLM usage occurred
- the approximate financial impact of the run

---

## Cost Control

The deterministic enrichments do not use external AI APIs.

These stages are free apart from infrastructure cost:

- amenity normalization
- neighbourhood price percentile

The AI-powered stages are:

- listing embeddings
- review summaries and aspect scores

To reduce cost during development:

1. Run raw loading and deterministic enrichment first.
2. Skip `review_summary` when testing database ingestion.
3. Generate summaries for a bounded subset of properties.
4. Avoid `--force` unless regeneration is necessary.
5. Resume interrupted stages instead of restarting all enrichment.

---

## Idempotency and Recovery

The pipeline is designed to recover cleanly from partial execution.

### Raw-data stages

Raw loads use staging tables and upserts.

Re-running them updates source-controlled fields without deleting stored enrichment values.

### Enrichment stages

Enrichment stages skip completed rows by default.

If a run stops halfway through, restarting the same stage processes only the remaining rows.

### Forced execution

`--force` disables the skip behavior for the selected enrichment stage.

Use it when:

- the embedding model changes
- summary prompts change
- aspect-score structure changes
- existing enrichment data is invalid
- a complete rebuild is intentionally required

---

## Performance Characteristics

### Bulk loading

The combination of streaming, temporary tables, `COPY`, and upserts is designed for large source files.

It avoids the overhead of issuing one insert per source row.

### Keyset pagination

Keyset pagination avoids the increasing cost associated with large SQL offsets.

It also makes long enrichment jobs easier to resume.

### Bounded concurrency

Review-summary calls use bounded concurrency so the pipeline does not issue an uncontrolled number of simultaneous LLM requests.

This helps control:

- API rate limits
- memory usage
- retry pressure
- cost spikes

### Precomputation

Review summaries are generated once during ingestion.

This avoids performing an LLM call whenever a user opens a listing or asks for review intelligence.

---

## Hallucination Control

The review-summary stage is grounded in the property’s supplied review text.

The model is instructed to:

- use only the provided reviews
- avoid unsupported claims
- return a structured response
- generate summary and aspect data from the available evidence

The serving layer can then expose the stored summary alongside citations to the source reviews.

This approach is more reliable than asking the model to summarize a property without a constrained evidence set.

---

## Design Decisions and Trade-offs

### One PostgreSQL engine

The project stores:

- relational listing data
- calendar data
- reviews
- geospatial values
- vector embeddings

inside one PostgreSQL engine.

PostGIS handles geospatial queries, while pgvector handles semantic similarity.

This makes it possible to combine filters, vector similarity, and distance in one SQL query.

A separate vector database is not required at the current scale.

---

### No per-review embeddings

Per-review embeddings are intentionally excluded from the current implementation.

Semantic retrieval runs over listing embeddings.

Review intelligence uses precomputed property-level summaries and aspect scores.

This reduces:

- embedding volume
- storage usage
- ingestion time
- indexing complexity
- API cost

Per-review embeddings are the logical next addition when review-level semantic search is required.

---

### Review summaries are generated during ingestion

Review summaries are not generated at request time.

This improves:

- API latency
- cost predictability
- repeat-query performance
- user experience
- cache effectiveness

The trade-off is that summaries must be regenerated when the underlying reviews or summary prompt materially change.

---

### Language detection can be expensive

`langdetect` is the slowest part of the review-loading stage.

For faster ingestion:

```env
DETECT_LANGUAGE=false
```

For very large corpora, use fastText `lid.176` as a higher-throughput replacement.

Disabling detection improves load performance but removes stored language metadata unless another detector is used.

---

### Calendar data is windowed

Calendar ingestion is limited by:

```env
CALENDAR_MONTHS=...
```

This prevents the calendar table from growing without a practical bound.

The trade-off is that availability search works only within the ingested window.

Increase `CALENDAR_MONTHS` when a longer booking horizon is required.

---

## Recommended Execution Flow

For a new environment, use the following sequence.

### 1. Start the database

Ensure PostgreSQL with PostGIS and pgvector is running.

### 2. Configure the environment

```bash
cp .env.example .env
```

Set:

```env
DATABASE_URL=...
OPENAI_API_KEY=...
```

### 3. Add the source files

```text
data/lisbon/
data/barcelona/
```

### 4. Run the complete pipeline

```bash
python -m ingestion
```

### 5. Verify the result

Confirm that the database contains:

- listings for both cities
- calendar records
- reviews
- normalized amenities
- neighbourhood percentiles
- listing embeddings
- review summaries
- aspect scores

---

## Development Workflow

During backend or frontend development, it may be unnecessary to run every expensive stage.

A lower-cost development run can use:

```bash
python -m ingestion --skip review_summary
```

After validating traditional and semantic search, generate summaries separately:

```bash
python -m ingestion --only review_summary
```

When only missing summaries should be created, do not add `--force`.

When every summary must be rebuilt:

```bash
python -m ingestion --only review_summary --force
```

---

## Troubleshooting

### The pipeline cannot find the data files

Verify the directory names and filenames:

```text
data/lisbon/listings.csv.gz
data/lisbon/calendar.csv.gz
data/lisbon/reviews.csv.gz
data/barcelona/listings.csv.gz
data/barcelona/calendar.csv.gz
data/barcelona/reviews.csv.gz
```

The loader also accepts `.csv` files.

---

### PostgreSQL extension creation fails

Confirm that the database image or server has:

- PostGIS
- pgvector

The database user also needs sufficient permissions to enable the required extensions.

---

### Loading is slow during reviews

Language detection may be the bottleneck.

Disable it:

```env
DETECT_LANGUAGE=false
```

For a long-term high-volume solution, replace `langdetect` with fastText `lid.176`.

---

### Embeddings are missing

Check:

- `OPENAI_API_KEY`
- database connectivity
- OpenAI rate-limit errors
- retry logs
- whether the embedding stage was skipped
- whether eligible rows already appeared complete

To retry only missing embeddings:

```bash
python -m ingestion --only embeddings
```

To regenerate all embeddings:

```bash
python -m ingestion --only embeddings --force
```

---

### Review summaries are missing

Check:

- `OPENAI_API_KEY`
- whether `review_summary` was skipped
- whether the property has enough review text
- LLM errors in the ingestion logs
- any configured summary limit

Retry incomplete summaries:

```bash
python -m ingestion --only review_summary
```

Regenerate existing summaries:

```bash
python -m ingestion --only review_summary --force
```

---

### Calendar searches return no availability

Check:

- whether the calendar stage completed
- the configured `CALENDAR_MONTHS`
- whether the requested dates fall inside the ingested window
- whether the source city calendar file contains those dates

---

## Summary

The ingestion pipeline provides a reliable bridge between the raw Inside Airbnb datasets and the application’s booking and AI capabilities.

Its core design choices are:

- a lightweight Pipeline / Stage architecture
- independent and idempotent stages
- streaming CSV and CSV.GZ loading
- temporary staging tables
- PostgreSQL `COPY`
- `ON CONFLICT` upserts
- keyset-paginated enrichment
- listing-level embeddings
- precomputed review summaries
- bounded LLM concurrency
- cost and token reporting
- one PostgreSQL engine for relational, vector, and geospatial workloads

This design keeps the system practical for the current dataset while leaving clear extension points for larger-scale ingestion and review-level semantic search.
