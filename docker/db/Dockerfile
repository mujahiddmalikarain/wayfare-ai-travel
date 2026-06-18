# Postgres 16 with BOTH PostGIS and pgvector.
# The official postgis image already has PGDG apt configured, so pgvector is one
# package away. This is the cleanest single-engine setup for relational + vector
# + geospatial.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*

# Extensions are CREATEd by the ingestion pipeline's schema stage; this image
# only needs to ship the binaries.
