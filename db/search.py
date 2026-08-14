"""Embedding-similarity catalog search (the RAG retrieval front door).

`search_catalog` matches a user's free-text phrase against BOTH the covered-procedure
names and the outpatient-service names, returning ranked candidates. The agent uses
these candidates + scores to decide which path to take (covered vs outpatient) and
whether it needs to ask the user to disambiguate.

Embeddings for the catalog are precomputed (data/build_embeddings.py). Only the user's
query is embedded at runtime.
"""

from functools import lru_cache

import numpy as np

from config import EMBEDDING_MODEL, EMBEDDINGS_PATH, get_openai_client
from db.aliases import match_aliases

# Cosine score below this = not a real match. Tuned for text-embedding-3-small, where
# a genuine procedure/service match typically scores well above ~0.5.
SIMILARITY_FLOOR = 0.35

# Added to a candidate's score when a curated alias phrase matches the query, pinning
# the canonical procedure/service above raw-embedding neighbours. > max cosine (1.0).
ALIAS_BOOST = 1.0

# Confidence bands over the top candidate's score and its margin to the runner-up. This
# mirrors the classic high/medium/low intent-confidence routing: a clear winner is priced
# directly, while a weak top match or a near-tie is flagged so the agent asks the user to
# clarify instead of guessing (see the confidence note in the system prompts).
CONFIDENCE_STRONG = 0.8   # a genuine catalogue match usually scores well above this
CONFIDENCE_MARGIN = 0.08  # the top must beat the runner-up by this much to be unambiguous


@lru_cache(maxsize=1)
def _load_embeddings() -> dict:
    if not EMBEDDINGS_PATH.exists():
        raise RuntimeError(
            f"Embeddings not found at {EMBEDDINGS_PATH}. Build them first: "
            "python -m data.build_embeddings"
        )
    data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    return {
        "covered_vecs": data["covered_vecs"],
        "covered_keys": data["covered_keys"],
        "covered_names": data["covered_names"],
        "outpatient_vecs": data["outpatient_vecs"],
        "outpatient_keys": data["outpatient_keys"],
        "outpatient_names": data["outpatient_names"],
    }


def _embed_query(text: str) -> np.ndarray:
    client = get_openai_client()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    vec = np.asarray(resp.data[0].embedding, dtype=np.float32)
    norm = np.linalg.norm(vec)
    return vec / norm if norm else vec


def _rank(query_vec: np.ndarray, vecs: np.ndarray, keys, names, kind: str) -> list[dict]:
    # vecs are pre-normalized, query_vec is normalized -> dot product == cosine.
    scores = vecs @ query_vec
    return [
        {
            "kind": kind,
            "key": str(keys[i]),
            "name": str(names[i]),
            "score": float(scores[i]),
            "via": "embedding",
        }
        for i in range(len(scores))
    ]


def _apply_alias_boost(candidates: list[dict], query_text: str) -> None:
    """Pin curated alias matches above raw-embedding neighbours, in place."""
    hits = match_aliases(query_text)
    if not hits:
        return
    index = {(c["kind"], c["key"]): c for c in candidates}
    for kind, key in hits:
        cand = index.get((kind, key))
        if cand is not None:
            cand["score"] += ALIAS_BOOST
            cand["via"] = "alias"


def assess_confidence(candidates: list[dict]) -> dict:
    """Summarise how confident the top match is: 'high' | 'medium' | 'low' | 'ambiguous'.

    Alias-boosted hits (score > 1.0) are always 'high'. A decent top score that sits too
    close to the runner-up is 'ambiguous' -- the agent should clarify rather than guess."""
    if not candidates:
        return {"level": "none", "top_score": 0.0, "runner_up_score": 0.0, "margin": 0.0}
    top = candidates[0]["score"]
    runner = candidates[1]["score"] if len(candidates) > 1 else 0.0
    margin = round(top - runner, 3)
    if top >= 1.0 or (top >= CONFIDENCE_STRONG and margin >= CONFIDENCE_MARGIN):
        level = "high"
    elif top >= SIMILARITY_FLOOR and margin < CONFIDENCE_MARGIN:
        level = "ambiguous"       # good-enough top match, but too close to call
    elif top >= 0.5:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "top_score": round(top, 3),
            "runner_up_score": round(runner, 3), "margin": margin}


def search_catalog(query_text: str, top_k: int = 5) -> dict:
    """Rank covered procedures AND outpatient services against `query_text`.

    Returns:
        {"candidates": [{kind, key, name, score, via}, ...],
         "confidence": {level, top_score, runner_up_score, margin}}
    `via` is "alias" if a curated phrase pinned it, else "embedding". Only candidates at
    or above SIMILARITY_FLOOR are returned (alias-boosted ones always clear it). The
    `confidence` block lets the agent decide whether to price the top match directly or
    ask the user to clarify (empty candidates / 'ambiguous' / 'low' -> clarify).
    """
    query_text = (query_text or "").strip()
    if not query_text:
        return {"candidates": [], "confidence": assess_confidence([])}

    emb = _load_embeddings()
    qvec = _embed_query(query_text)

    candidates = _rank(qvec, emb["covered_vecs"], emb["covered_keys"], emb["covered_names"], "covered")
    candidates += _rank(
        qvec, emb["outpatient_vecs"], emb["outpatient_keys"], emb["outpatient_names"], "outpatient"
    )
    _apply_alias_boost(candidates, query_text)
    candidates.sort(key=lambda c: c["score"], reverse=True)
    ranked = [c for c in candidates if c["score"] >= SIMILARITY_FLOOR][:top_k]
    return {"candidates": ranked, "confidence": assess_confidence(ranked)}


if __name__ == "__main__":
    # Quick manual smoke test across both paths + Taglish + an out-of-catalog phrase.
    tests = [
        "how much is an appendectomy",
        "manganak / normal delivery",
        "CT scan",
        "MRI of the brain",
        "cholecystectomy gallbladder removal",
        "kidney transplant",  # covered procedure with NO hospital price
        "how to bake bread",  # nonsense -> should return little/nothing
    ]
    for t in tests:
        result = search_catalog(t, top_k=3)
        conf = result["confidence"]
        print(f"\nQUERY: {t}   [confidence={conf['level']} "
              f"top={conf['top_score']} margin={conf['margin']}]")
        for c in result["candidates"]:
            print(f"  [{c['kind']:10}] {c['score']:.3f}  {c['key']:8}  {c['name'][:55]}")
