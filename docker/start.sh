#!/usr/bin/env bash
# Launch BOTH services in a single container: the FastAPI API and the Streamlit UI.
# Used by the image's default CMD (single-container demo). docker-compose does NOT use
# this script — it runs one process per service instead.
#
# If either process exits, we stop the other and exit non-zero so an orchestrator can
# restart the container.
set -uo pipefail

uvicorn api.main:app --host 0.0.0.0 --port 8000 &
api_pid=$!

streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0 &
ui_pid=$!

echo "Dr. Mundo up: API on :8000, UI on :8501 (api_pid=$api_pid ui_pid=$ui_pid)"

# Wait for whichever process exits first, then tear the other down.
wait -n
status=$?
kill "$api_pid" "$ui_pid" 2>/dev/null || true
exit "$status"
