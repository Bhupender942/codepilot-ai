import logging
import os
from pathlib import Path

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(os.environ.get("MODEL_CACHE_DIR", "/tmp/codepilot_models/all-MiniLM-L6-v2"))
_DIM = 384
_MAX_SEQ_LEN = 128

_session = None
_tokenizer = None


def _download_file(url: str, dest: Path) -> None:
    """Download a file from url to dest if it doesn't exist."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    import requests
    logger.info("Downloading %s -> %s", url, dest)
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    logger.info("Downloaded %s", dest)


def _ensure_model_files() -> tuple[Path, Path]:
    """Ensure ONNX model and tokenizer are downloaded. Return (model_path, tokenizer_path)."""
    base_url = "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/main"
    model_path = _MODEL_DIR / "model.onnx"
    tokenizer_path = _MODEL_DIR / "tokenizer.json"
    _download_file(f"{base_url}/onnx/model.onnx", model_path)
    _download_file(f"{base_url}/tokenizer.json", tokenizer_path)
    return model_path, tokenizer_path


def get_model():
    """Lazily load and cache the ONNX embedding model + tokenizer."""
    global _session, _tokenizer
    if _session is not None and _tokenizer is not None:
        return (_session, _tokenizer)

    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_path, tokenizer_path = _ensure_model_files()
        logger.info("Loading ONNX model from %s", model_path)
        _session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        _tokenizer = Tokenizer.from_file(str(tokenizer_path))
        _tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", length=_MAX_SEQ_LEN)
        _tokenizer.enable_truncation(max_length=_MAX_SEQ_LEN)
        logger.info("ONNX embedding model loaded successfully")
        return (_session, _tokenizer)
    except ImportError:
        logger.warning("onnxruntime or tokenizers not installed; falling back to zero-vector embeddings")
        return None
    except Exception as exc:
        logger.error("Failed to load ONNX embedding model: %s", exc)
        return None


def _encode_texts(texts: list[str]) -> list[list[float]]:
    """Encode a list of texts into embedding vectors using ONNX."""
    model = get_model()
    if model is None:
        return [[0.0] * _DIM for _ in texts]

    session, tokenizer = model
    encodings = tokenizer.encode_batch(texts)

    input_ids = np.array([e.ids for e in encodings], dtype=np.int64)
    attention_mask = np.array([e.attention_mask for e in encodings], dtype=np.int64)
    token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

    outputs = session.run(
        None,
        {"input_ids": input_ids, "attention_mask": attention_mask, "token_type_ids": token_type_ids},
    )

    # outputs[0] is last_hidden_state: (batch, seq_len, dim)
    token_embeddings = outputs[0]

    # Mean pooling
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
    sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
    sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
    mean_pooled = sum_embeddings / sum_mask

    # L2 normalize
    norms = np.linalg.norm(mean_pooled, axis=1, keepdims=True)
    norms = np.clip(norms, a_min=1e-9, a_max=None)
    normalized = mean_pooled / norms

    return normalized.tolist()


def embed_chunks(chunks: list[dict], batch_size: int = 64) -> list[tuple[str, list[float]]]:
    """Embed a list of chunk dicts in batches. Each chunk must have 'id' and 'text' keys."""
    if not chunks:
        return []

    texts = [chunk["text"] for chunk in chunks]
    chunk_ids = [chunk["id"] for chunk in chunks]

    results: list[tuple[str, list[float]]] = []
    try:
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_ids = chunk_ids[i : i + batch_size]
            vectors = _encode_texts(batch_texts)
            for cid, vec in zip(batch_ids, vectors):
                results.append((cid, vec))
        logger.debug("Embedded %d chunks", len(results))
    except Exception as exc:
        logger.error("Error during chunk embedding: %s", exc)
        results = [(cid, [0.0] * _DIM) for cid in chunk_ids]

    return results


def embed_query(query: str) -> list[float]:
    """Embed a single query string and return the vector."""
    try:
        vectors = _encode_texts([query])
        return vectors[0]
    except Exception as exc:
        logger.error("Error embedding query: %s", exc)
        return [0.0] * _DIM

