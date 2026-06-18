"""Re-runnable ingestion pipeline for the AI travel app.

Loads Inside Airbnb CSVs into a single Postgres engine (relational + pgvector +
PostGIS) and enriches them with neighbourhood price percentiles, listing
embeddings, and precomputed per-property review summaries.
"""

__all__ = ["Settings", "Pipeline", "build_pipeline"]

from .config import Settings
from .pipeline import Pipeline, build_pipeline
