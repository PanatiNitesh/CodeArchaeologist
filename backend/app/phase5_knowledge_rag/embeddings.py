import numpy as np
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global singleton cache for SentenceTransformer model to prevent reloading weights into memory
_SHARED_MODEL = None
_MODEL_LOAD_ATTEMPTED = False

def get_shared_sentence_transformer():
    global _SHARED_MODEL, _MODEL_LOAD_ATTEMPTED
    if _SHARED_MODEL is not None:
        return _SHARED_MODEL
    if _MODEL_LOAD_ATTEMPTED:
        return None
    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        _SHARED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("SentenceTransformer all-MiniLM-L6-v2 loaded into singleton cache.")
        return _SHARED_MODEL
    except Exception as e:
        logger.warning(f"Could not load SentenceTransformer ({e}), using TF-IDF LSA engine.")
        return None

class EmbeddingEngine:
    """
    Semantic embedding generator with dual-engine support:
    1. Sentence-Transformers (Local neural model, cached globally)
    2. High-performance Scikit-learn TF-IDF LSA semantic vectorizer fallback (instant, zero download)
    """

    def __init__(self, use_neural: bool = True):
        self.use_neural = use_neural
        self.vectorizer = None
        self.dim = 384 if use_neural else 128
        self.model = get_shared_sentence_transformer() if use_neural else None
        if not self.model and use_neural:
            self.dim = 128

    def fit_and_embed(self, documents: List[str]) -> np.ndarray:
        if not documents:
            return np.empty((0, self.dim))

        if self.model:
            try:
                embeddings = self.model.encode(documents, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
                return embeddings
            except Exception as e:
                logger.warning(f"Neural embed failed, falling back to TF-IDF: {e}")

        # TF-IDF + SVD LSA semantic representation
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import TruncatedSVD

        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words="english", ngram_range=(1, 2))
        tfidf_matrix = self.vectorizer.fit_transform(documents)

        n_components = min(self.dim, max(2, tfidf_matrix.shape[1] - 1), tfidf_matrix.shape[0])
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        dense_vectors = svd.fit_transform(tfidf_matrix)

        # Pad to self.dim if smaller
        if dense_vectors.shape[1] < self.dim:
            padding = np.zeros((dense_vectors.shape[0], self.dim - dense_vectors.shape[1]))
            dense_vectors = np.hstack([dense_vectors, padding])

        # Normalize
        norms = np.linalg.norm(dense_vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.svd = svd
        return (dense_vectors / norms).astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if self.model:
            try:
                return self.model.encode([query], show_progress_bar=False, convert_to_numpy=True)[0]
            except Exception:
                pass

        if self.vectorizer and hasattr(self, 'svd'):
            tfidf = self.vectorizer.transform([query])
            dense = self.svd.transform(tfidf)
            if dense.shape[1] < self.dim:
                padding = np.zeros((dense.shape[0], self.dim - dense.shape[1]))
                dense = np.hstack([dense, padding])
            norm = np.linalg.norm(dense)
            if norm > 0:
                dense = dense / norm
            return dense[0].astype(np.float32)

        # Basic fallback non-zero vector
        vec = np.zeros(self.dim, dtype=np.float32)
        for i, char in enumerate(query[:self.dim]):
            vec[i] = ord(char) / 255.0
        norm = np.linalg.norm(vec)
        return (vec / norm) if norm > 0 else vec
