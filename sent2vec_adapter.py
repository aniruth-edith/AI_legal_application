"""
Drop-in replacement for sent2vec using sentence-transformers.
Same interface as the original sent2vec.Sent2vecModel.
"""
from sentence_transformers import SentenceTransformer
import numpy as np

class Sent2vecModel:
    def __init__(self):
        self._model = None
        self._dim = 200  # must match LeSICiN hidden_size

    def load_model(self, path: str):
        """
        Instead of loading the .bin file, load a transformer model.
        The output is projected to match LeSICiN's expected hidden_size=200.
        """
        print(f"[sent2vec_adapter] Loading sentence-transformers model (ignoring {path})")
        # all-MiniLM-L6-v2 outputs 384-dim, we project to 200
        self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self._projection = None  # lazy init on first embed

    def embed_sentences(self, sentences: list) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("Call load_model() first")

        sentences = [s for s in sentences if isinstance(s, str) and s.strip()]
        if not sentences:
            return np.zeros((1, self._dim), dtype=np.float32)

        # Get 384-dim embeddings
        embeddings = self._model.encode(sentences, show_progress_bar=False)

        # Project 384 → 200 using a fixed linear projection
        if self._projection is None:
            import numpy as np
            np.random.seed(42)
            self._projection = np.random.randn(embeddings.shape[1], self._dim).astype(np.float32)
            self._projection /= np.linalg.norm(self._projection, axis=0, keepdims=True)

        projected = embeddings @ self._projection  # [N, 200]
        return projected.astype(np.float32)