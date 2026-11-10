"""bge-m3 vectors of each precedent's rejected claims, for hybrid similar-case search.

ollama pull bge-m3
uv run python scripts/build_kr_embeddings.py   # → data/precedents/kr_claim_embeddings.npz

Rebuild after build_kr_claim_history.py. Uses PRECEDENT_EMBEDDING_MODEL (default bge-m3) on
LOCAL_LLM_BASE_URL. Stored as float16 unit vectors keyed by case_id.
"""

import sys
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import Settings  # noqa: E402
from backend.precedents.repository import EMBEDDING_PATH, real_cases  # noqa: E402


def main():
    settings = Settings()
    model = settings.precedent_embedding_model or "bge-m3"
    cases = [c for c in real_cases() if c.get("claims_before")]
    ids, vectors = [], []
    for i in range(0, len(cases), 16):
        batch = cases[i : i + 16]
        response = httpx.post(
            f"{settings.local_llm_base_url}/api/embed",
            json={
                "model": model,
                "input": [(c["claims_before"] + " " + c.get("title", ""))[:4000] for c in batch],
            },
            timeout=600,
        )
        response.raise_for_status()
        ids += [c["case_id"] for c in batch]
        vectors += response.json()["embeddings"]
        print(f"{len(ids)}/{len(cases)}", flush=True)
    matrix = np.asarray(vectors, dtype="float32")
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    np.savez_compressed(EMBEDDING_PATH, ids=np.asarray(ids), vectors=matrix.astype("float16"))
    print(f"{len(ids)} claim vectors ({model}) → {EMBEDDING_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
