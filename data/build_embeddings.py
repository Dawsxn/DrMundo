"""Precompute embeddings for the retrieval catalog (build step, run once).

We embed two name sets so the agent can match a user's phrase to the right thing:
  - covered procedures : every philhealth_procedure_rates.procedure  (keyed by rvs_code)
  - outpatient services: every distinct hospital_prices.service       (keyed by name)

The vectors are L2-normalized and saved to data/embeddings.npz so runtime cosine
similarity is a single dot product, and so the app can do retrieval without re-calling
the embedding API for the catalog (only the user's query is embedded at runtime).

Usage:
    python -m data.build_embeddings
"""

import numpy as np

from config import EMBEDDING_MODEL, EMBEDDINGS_PATH, get_openai_client
from db.connection import get_connection

BATCH_SIZE = 1000  # text-embedding-3-small accepts many inputs per request


def load_catalog() -> tuple[list[dict], list[dict]]:
    """Return (covered, outpatient) catalog entries from the DB."""
    conn = get_connection()
    covered = [
        {"kind": "covered", "key": r["rvs_code"], "name": r["procedure"]}
        for r in conn.execute(
            "SELECT rvs_code, procedure FROM philhealth_procedure_rates ORDER BY rvs_code"
        )
    ]
    outpatient = [
        {"kind": "outpatient", "key": r["service"], "name": r["service"]}
        for r in conn.execute(
            "SELECT DISTINCT service FROM hospital_prices ORDER BY service"
        )
    ]
    conn.close()
    return covered, outpatient


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a list of strings in batches, returning an (N, dim) float32 array."""
    client = get_openai_client()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend(d.embedding for d in resp.data)
        print(f"  embedded {min(start + BATCH_SIZE, len(texts))}/{len(texts)}")
    arr = np.asarray(vectors, dtype=np.float32)
    # L2-normalize so cosine similarity == dot product at runtime.
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def build() -> None:
    covered, outpatient = load_catalog()
    print(f"Catalog: {len(covered)} covered procedures, {len(outpatient)} outpatient services")

    print("Embedding covered procedures...")
    covered_vecs = embed_texts([e["name"] for e in covered])
    print("Embedding outpatient services...")
    outpatient_vecs = embed_texts([e["name"] for e in outpatient])

    np.savez_compressed(
        EMBEDDINGS_PATH,
        model=EMBEDDING_MODEL,
        covered_vecs=covered_vecs,
        covered_keys=np.array([e["key"] for e in covered], dtype=object),
        covered_names=np.array([e["name"] for e in covered], dtype=object),
        outpatient_vecs=outpatient_vecs,
        outpatient_keys=np.array([e["key"] for e in outpatient], dtype=object),
        outpatient_names=np.array([e["name"] for e in outpatient], dtype=object),
    )
    print(
        f"\nSaved {covered_vecs.shape[0] + outpatient_vecs.shape[0]} vectors "
        f"(dim={covered_vecs.shape[1]}) to {EMBEDDINGS_PATH}"
    )


if __name__ == "__main__":
    build()
