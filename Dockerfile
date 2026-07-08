# syntax=docker/dockerfile:1
#
# Dr. Mundo — multi-stage image that can run BOTH the FastAPI service and the Streamlit
# UI. Build once; the default CMD runs both (single-container demo), while docker-compose
# runs them as two services by overriding `command:`.
#
#   docker build -t dr-mundo .
#   docker run --rm -e OPENAI_API_KEY=sk-... -p 8000:8000 -p 8501:8501 dr-mundo
#
# The OpenAI key is NEVER baked in — it is supplied at runtime only.

# ---- Stage 1: install dependencies into an isolated prefix ----------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
 && pip install --prefix=/install -r requirements.txt

# ---- Stage 2: slim runtime image ------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # Streamlit inside a container: no browser, no telemetry.
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    # When both processes run in ONE container the UI reaches the API on localhost;
    # docker-compose overrides this to http://api:8000 for the split services.
    DR_MUNDO_API_URL=http://localhost:8000

WORKDIR /app

# Bring in the pre-installed dependencies from the builder stage.
COPY --from=builder /install /usr/local

# Copy the application source (see .dockerignore for what is excluded — notably .env,
# the built DB, and the local MLflow store).
COPY . .

# Build the SQLite DB from the committed CSVs at build time (no API key needed).
# embeddings.npz is already committed, so no embedding rebuild happens here.
RUN python data/load_db.py

# Drop root: run as an unprivileged user that owns the app dir (so it can write
# dr_mundo runtime files / mlflow.db).
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 8000 8501

# Default: run BOTH FastAPI and Streamlit. Overridden per-service by docker-compose.
CMD ["bash", "docker/start.sh"]
