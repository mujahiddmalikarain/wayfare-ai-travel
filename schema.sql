-- schema.sql — single Postgres engine: relational + vector (pgvector) + geospatial (PostGIS).
-- Idempotent: safe to run on every boot.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ─────────────────────────────────────────────────────────────────────────────
-- properties
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS properties (
    id                       BIGINT PRIMARY KEY,
    name                     TEXT,
    property_type            TEXT,
    room_type                TEXT,
    city                     TEXT          NOT NULL,
    neighbourhood            TEXT,
    lat                      DOUBLE PRECISION,
    lng                      DOUBLE PRECISION,
    geom                     GEOGRAPHY(POINT, 4326),
    price                    NUMERIC,
    beds                     INT,
    bedrooms                 INT,
    accommodates             INT,
    amenities                TEXT[]        NOT NULL DEFAULT '{}',   -- normalized
    amenities_raw            JSONB,
    photo_url                TEXT,
    host_id                  BIGINT,
    host_name                TEXT,
    review_count             INT           NOT NULL DEFAULT 0,
    rating                   NUMERIC,
    -- enrichments (filled by the pipeline, never overwritten by re-loads)
    neighbourhood_price_pct  NUMERIC,                               -- SQL window
    review_summary           TEXT,                                  -- gpt-4o-mini
    review_aspects           JSONB,                                 -- {cleanliness,...}
    embedding                VECTOR(1536),                          -- text-embedding-3-small
    ingested_at              TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS properties_geom_idx      ON properties USING GIST (geom);
CREATE INDEX IF NOT EXISTS properties_embedding_idx ON properties USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS properties_city_idx      ON properties (city);
CREATE INDEX IF NOT EXISTS properties_price_idx     ON properties (price);
CREATE INDEX IF NOT EXISTS properties_amenities_idx ON properties USING GIN (amenities);

-- ─────────────────────────────────────────────────────────────────────────────
-- calendar  (availability + nightly price per day)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calendar (
    property_id  BIGINT  NOT NULL,
    date         DATE    NOT NULL,
    available    BOOLEAN NOT NULL,
    price        NUMERIC,
    PRIMARY KEY (property_id, date)
);

CREATE INDEX IF NOT EXISTS calendar_lookup_idx ON calendar (property_id, date);

-- ─────────────────────────────────────────────────────────────────────────────
-- reviews
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id           BIGINT PRIMARY KEY,
    property_id  BIGINT NOT NULL,
    date         DATE,
    reviewer     TEXT,
    rating       NUMERIC,           -- null for Inside Airbnb (no per-review score)
    text         TEXT,
    language     TEXT,
    aspects      TEXT[] NOT NULL DEFAULT '{}',  -- topics touched (deterministic tagger)
    sentiment    TEXT               -- positive | negative | neutral (deterministic)
);

-- Idempotent migration for DBs created before per-review enrichment existed.
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS aspects   TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS sentiment TEXT;

CREATE INDEX IF NOT EXISTS reviews_property_idx  ON reviews (property_id);
CREATE INDEX IF NOT EXISTS reviews_language_idx  ON reviews (language);
CREATE INDEX IF NOT EXISTS reviews_aspects_idx   ON reviews USING GIN (aspects);
CREATE INDEX IF NOT EXISTS reviews_sentiment_idx ON reviews (sentiment);
