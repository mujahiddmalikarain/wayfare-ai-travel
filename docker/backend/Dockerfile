# Single backend image used by two services:
#   - `api`    -> uvicorn api.main:app
#   - `ingest` -> python -m ingestion   (one-off, `seed` profile)
# Both packages share the same dependencies (Postgres, OpenAI), so one image
# keeps the build cache warm and the footprint small.
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# psycopg[binary], langgraph, openai, etc. all ship wheels — no build toolchain.
COPY api/requirements.txt ./api-requirements.txt
COPY ingestion/requirements.txt ./ingestion-requirements.txt
RUN pip install --no-cache-dir -r api-requirements.txt -r ingestion-requirements.txt

COPY api ./api
COPY ingestion ./ingestion
COPY schema.sql ./schema.sql

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
