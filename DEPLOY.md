# Deployment

Two supported paths. Both keep a single Postgres engine (PostGIS + pgvector) so
hybrid retrieval stays one SQL query, and a Redis cache for repeated retrievals
and review syntheses.

The backend (`travel-api`, `travel-db`, `travel-redis`) and the frontend (`web/`)
deploy independently; the frontend only needs `NEXT_PUBLIC_API_URL` pointing at
the public API URL. CORS on the API is already open (`allow_origins=["*"]`).

---

## Path A — Render (backend) + Vercel (frontend)

### 1. Backend on Render (Blueprint)

The repo ships [`render.yaml`](render.yaml), which provisions:

- `travel-db` — private service running our PostGIS + pgvector image with a disk
- `travel-redis` — managed Redis
- `travel-api` — the FastAPI service (Docker)

Steps:

1. In Render: **New → Blueprint**, point it at this repo. Render reads `render.yaml`.
2. Fill the `sync: false` values when prompted:
   - `OPENAI_API_KEY` — your key.
   - `DATABASE_URL` — `postgresql://postgres:<POSTGRES_PASSWORD>@<travel-db-host>:5432/travel`.
     Copy `POSTGRES_PASSWORD` (auto-generated) and the internal host from the
     `travel-db` service.
3. Deploy. The API comes up at `https://travel-api-XXXX.onrender.com`; check
   `/health` and `/docs`.

### 2. Seed the deployed database

The schema and data are created by the ingestion pipeline (the `schema` stage
runs `CREATE EXTENSION/TABLE/INDEX IF NOT EXISTS`). Run it once against the
deployed DB. Easiest is a **Render one-off job** (or run locally pointed at the
DB's *external* connection string):

```bash
# locally, with the data/ folder present and the DB's external URL:
DATABASE_URL="postgresql://postgres:<pw>@<external-host>:5432/travel" \
OPENAI_API_KEY=sk-... \
SUMMARY_MAX_LISTINGS=2000 \
CITIES=lisbon,barcelona \
python -m ingestion
```

`SUMMARY_MAX_LISTINGS` bounds the per-property review-summary LLM spend for a
demo seed (it prioritizes the most-reviewed listings). Set `0` for a full run.

### 3. Frontend on Vercel

1. **New Project** → import this repo → set **Root Directory** to `web`.
2. Environment variable: `NEXT_PUBLIC_API_URL=https://travel-api-XXXX.onrender.com`.
3. Deploy. Vercel detects Next.js automatically.

> If you instead host the frontend on Render as a web service, change the start
> script to bind Render's port: `next start -p $PORT`.

---

## Path B — Single VPS with docker-compose (most reliable)

Everything is already wired in [`docker-compose.yml`](docker-compose.yml).

```bash
git clone <repo> && cd <repo>
cp .env.example .env            # set OPENAI_API_KEY (and SUMMARY_MAX_LISTINGS)
# place Inside Airbnb CSVs in ./data/lisbon and ./data/barcelona
make up                         # db (postgis+pgvector) + redis + api
make seed                       # ingest (re-runnable, idempotent)
docker compose --profile web up -d web   # frontend on :3000
```

Put a reverse proxy (Caddy/Nginx) in front of `:8000` (API) and `:3000` (web),
or expose them directly. Set the web container's `NEXT_PUBLIC_API_URL` to the
public API origin.

---

## Live URL

- API:  `<fill after deploy>`
- Web:  `<fill after deploy>`
