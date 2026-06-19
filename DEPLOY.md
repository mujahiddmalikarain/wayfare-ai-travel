# Deployment Guide

This project supports two deployment approaches:

- **Path A:** Render for the backend and Vercel for the frontend
- **Path B:** A single VPS using Docker Compose

Both approaches use the same core architecture:

- **PostgreSQL with PostGIS and pgvector** for relational, geospatial, and vector search
- **Redis** for caching repeated retrieval results and review synthesis outputs
- **FastAPI** for the backend API
- **Next.js** for the frontend application

Keeping relational data, vectors, availability, and geospatial data in one PostgreSQL engine allows hybrid retrieval to remain a single SQL query.

The backend services and frontend are deployed independently:

- `travel-api` — FastAPI backend
- `travel-db` — PostgreSQL with PostGIS and pgvector
- `travel-redis` — Redis cache
- `web/` — Next.js frontend

The frontend only requires `NEXT_PUBLIC_API_URL` to point to the publicly accessible backend URL.

The API currently allows requests from all origins:

```python
allow_origins=["*"]
```

For a production system, this should be restricted to the trusted frontend domains.

---

## Path A — Render Backend and Vercel Frontend

This is the recommended managed-cloud deployment path.

### Architecture

```text
Vercel
└── Next.js frontend
        │
        │ REST and SSE
        ▼
Render
├── FastAPI backend
├── PostgreSQL with PostGIS and pgvector
└── Redis
```

---

## 1. Deploy the Backend on Render

The repository includes a [`render.yaml`](render.yaml) Blueprint that provisions the required backend services:

- `travel-db` — private PostgreSQL service using the project’s PostGIS and pgvector image, with persistent disk storage
- `travel-redis` — managed Redis service
- `travel-api` — Docker-based FastAPI service

### Deployment steps

1. Sign in to Render.
2. Select **New → Blueprint**.
3. Connect the GitHub repository.
4. Render will automatically detect and read `render.yaml`.
5. Provide the environment variables marked with `sync: false`.
6. Create and deploy the Blueprint.

### Required environment variables

#### `OPENAI_API_KEY`

Add your OpenAI API key:

```env
OPENAI_API_KEY=sk-...
```

#### `DATABASE_URL`

Use the internal hostname of the `travel-db` service:

```env
DATABASE_URL=postgresql://postgres:<POSTGRES_PASSWORD>@<travel-db-host>:5432/travel
```

To construct this value:

1. Open the `travel-db` service in Render.
2. Copy the automatically generated `POSTGRES_PASSWORD`.
3. Copy the internal database hostname.
4. Insert both values into the connection string.

The API should use the **internal** database URL because the API and database run inside Render’s private network.

### Verify the backend deployment

After deployment, Render will display the public API URL.

The production API for this project is:

```text
https://wayfare-ai-travel.onrender.com
```

Verify the following endpoints:

```text
https://wayfare-ai-travel.onrender.com/health
https://wayfare-ai-travel.onrender.com/docs
```

The health endpoint confirms that the API is running. The documentation endpoint opens the FastAPI Swagger interface.

---

## 2. Seed the Deployed Database

Deploying the services does not automatically load the Inside Airbnb dataset.

The ingestion pipeline must be run once to:

- enable the required PostgreSQL extensions
- create tables and indexes
- load listings
- load calendar records
- load reviews
- calculate neighbourhood price percentiles
- generate listing embeddings
- generate precomputed review summaries

The `schema` stage uses idempotent statements such as:

```sql
CREATE EXTENSION IF NOT EXISTS ...
CREATE TABLE IF NOT EXISTS ...
CREATE INDEX IF NOT EXISTS ...
```

The pipeline is safe to rerun.

### Option 1 — Run a Render one-off job

Create a one-off job using the same backend image and required environment variables.

Make sure the Inside Airbnb files are available to the job before starting the ingestion process.

### Option 2 — Run ingestion locally against Render

This is usually the easiest approach when the dataset already exists on your local machine.

Use the database’s **external** connection string because the command is running outside Render’s private network.

```bash
DATABASE_URL="postgresql://postgres:<pw>@<external-host>:5432/travel" \
OPENAI_API_KEY="sk-..." \
SUMMARY_MAX_LISTINGS=2000 \
CITIES=lisbon,barcelona \
python -m ingestion
```

Run the command from the repository root with the required data files available under:

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

The ingestion pipeline also supports decompressed `.csv` files.

### Review-summary cost guardrail

`SUMMARY_MAX_LISTINGS` controls how many property-level review summaries are generated with the LLM.

For a demo deployment:

```env
SUMMARY_MAX_LISTINGS=2000
```

The pipeline prioritizes the listings with the highest number of reviews.

To generate summaries for every eligible listing, use:

```env
SUMMARY_MAX_LISTINGS=0
```

A full-corpus run increases ingestion time and OpenAI API cost.

---

## 3. Deploy the Frontend on Vercel

The frontend is located in the `web/` directory.

### Deployment steps

1. Sign in to Vercel.
2. Select **Add New → Project**.
3. Import the GitHub repository.
4. Set the **Root Directory** to:

```text
web
```

5. Add the following environment variable:

```env
NEXT_PUBLIC_API_URL=https://wayfare-ai-travel.onrender.com
```

6. Confirm that the framework preset is **Next.js**.
7. Deploy the project.

Vercel detects the Next.js application automatically. The file `web/vercel.json` also pins the framework configuration.

### Important build configuration

Use the following Vercel settings:

| Setting | Value |
|---|---|
| Root Directory | `web` |
| Framework Preset | `Next.js` |
| Output Directory | Leave empty |
| API environment variable | `NEXT_PUBLIC_API_URL=https://wayfare-ai-travel.onrender.com` |

Next.js builds into `.next`, and Vercel manages this output automatically.

Do not configure `public` as the output directory.

---

## Vercel Error: “No Output Directory named public”

This error means Vercel is treating the project as a static site instead of a Next.js application.

Open:

**Project Settings → Build & Development Settings**

Then verify:

1. **Root Directory** is set to `web`, not the repository root.
2. **Framework Preset** is set to **Next.js**.
3. **Output Directory** is empty.
4. There is no production override setting the output directory to `public`.

If Vercel displays a yellow warning banner for an output-directory override, remove that override and redeploy.

Do not use:

```text
public
```

Next.js uses:

```text
.next
```

Vercel handles `.next` internally, so it should not normally be entered manually.

---

## Hosting the Frontend on Render Instead of Vercel

The frontend can also run as a Render web service.

The Next.js start command must bind to the port supplied by Render:

```bash
next start -p $PORT
```

Set the frontend environment variable to the public API origin:

```env
NEXT_PUBLIC_API_URL=https://wayfare-ai-travel.onrender.com
```

---

## Path B — Single VPS with Docker Compose

This is the most reliable self-hosted deployment path because all services run in one controlled environment.

The repository’s [`docker-compose.yml`](docker-compose.yml) already connects:

- PostgreSQL with PostGIS and pgvector
- Redis
- FastAPI
- Next.js

### 1. Clone and configure the project

```bash
git clone <repo>
cd <repo>
cp .env.example .env
```

Update `.env` with at least:

```env
OPENAI_API_KEY=sk-...
SUMMARY_MAX_LISTINGS=2000
CITIES=lisbon,barcelona
```

Also review the PostgreSQL, Redis, API, and frontend values defined in `.env.example`.

### 2. Add the Inside Airbnb datasets

Place the source files under:

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

Both `.csv.gz` and decompressed `.csv` files are supported.

### 3. Start the backend services

```bash
make up
```

This starts:

- PostgreSQL with PostGIS and pgvector
- Redis
- FastAPI

The API is available locally at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

### 4. Seed the database

```bash
make seed
```

The ingestion pipeline is re-runnable and idempotent.

### 5. Start the frontend

```bash
docker compose --profile web up -d web
```

The frontend is available at:

```text
http://localhost:3000
```

The web container’s `NEXT_PUBLIC_API_URL` must point to the API URL that is reachable from the user’s browser.

For a public deployment, do not leave it set to a container-only hostname unless the browser can resolve that hostname.

---

## Reverse Proxy Configuration

For a VPS deployment, place Caddy or Nginx in front of the application services.

A typical setup is:

```text
https://travel.example.com      → frontend on port 3000
https://api.travel.example.com  → backend on port 8000
```

Set:

```env
NEXT_PUBLIC_API_URL=https://api.travel.example.com
```

The reverse proxy should also handle:

- HTTPS certificates
- HTTP-to-HTTPS redirects
- proxy headers
- SSE-compatible buffering settings
- request-size limits
- timeouts for long-running API requests

Because the concierge uses Server-Sent Events, proxy buffering should be disabled for the streaming endpoint.

You may also expose ports `3000` and `8000` directly, but a reverse proxy with HTTPS is safer for production.

---

## CORS Configuration

The API currently uses:

```python
allow_origins=["*"]
```

This is convenient for testing and evaluation because it allows the frontend to call the API from any origin.

For production, restrict it to the deployed frontend domains:

```python
allow_origins=[
    "https://wayfare-ai-travel.vercel.app",
    "https://travel.example.com",
]
```

Include local development origins when needed:

```python
allow_origins=[
    "http://localhost:3000",
    "https://wayfare-ai-travel.vercel.app",
]
```

---

## Post-Deployment Verification

After deploying, verify the system in this order.

### 1. API health

```bash
curl https://wayfare-ai-travel.onrender.com/health
```

### 2. API documentation

Open:

```text
https://wayfare-ai-travel.onrender.com/docs
```

### 3. Database contents

Confirm that the ingestion pipeline loaded:

- both cities
- listings
- reviews
- calendar records
- embeddings
- review summaries

### 4. Traditional search

Test structured filters such as:

- city
- dates
- guest count
- price
- rating
- property type
- amenities

### 5. Natural-language search

Verify that a free-text query is converted into visible structured filters.

### 6. Concierge streaming

Confirm that the concierge returns agent steps over SSE without proxy buffering or timeout errors.

### 7. Property details

Verify:

- review summary
- aspect scores
- review citations
- availability calendar
- price breakdown
- map location

### 8. Frontend-to-backend connection

Open the browser developer tools and confirm that frontend requests are sent to the correct `NEXT_PUBLIC_API_URL`.

---

## Common Deployment Issues

### Render API wakes slowly

Render services on lower-cost plans may experience cold-start delays. The frontend should handle the first request gracefully.

### Database connection fails from the API

Check that the API uses Render’s **internal** PostgreSQL hostname rather than the external hostname.

### Local ingestion cannot connect to Render

Use the database’s **external** connection string when running ingestion from your machine.

### Frontend still calls localhost

`NEXT_PUBLIC_API_URL` is embedded during the Next.js build.

After changing it in Vercel or Render, trigger a new frontend deployment.

### SSE works locally but not behind a proxy

Disable proxy buffering and increase read timeouts for the concierge streaming route.

### Search returns no listings

Confirm that:

- ingestion completed successfully
- the requested city is Lisbon or Barcelona
- calendar data covers the requested dates
- filters are not too restrictive

### Review summaries are missing

Check:

- `OPENAI_API_KEY`
- `SUMMARY_MAX_LISTINGS`
- whether the listing was included in the summary limit
- ingestion logs for failed LLM requests

---

## Live URLs

| Service | URL |
|---|---|
| Web application | https://wayfare-ai-travel.vercel.app/ |
| API documentation | https://wayfare-ai-travel.onrender.com/docs |
| API health check | https://wayfare-ai-travel.onrender.com/health |

---

## Deployment Summary

| Component | Managed-cloud path | Single-VPS path |
|---|---|---|
| Frontend | Vercel | Docker Compose |
| API | Render | Docker Compose |
| PostgreSQL | Render private service | Docker Compose |
| Redis | Render managed Redis | Docker Compose |
| Data ingestion | Render one-off job or local machine | `make seed` |
| Reverse proxy | Managed by Vercel and Render | Caddy or Nginx |
| HTTPS | Managed automatically | Configure through reverse proxy |
