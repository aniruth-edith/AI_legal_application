# from sentence_transformers import SentenceTransformer
# import torch
# import os

# _embed_model = None
# QWEN_MODEL = os.getenv("QWEN_EMBED_MODEL", "Qwen/Qwen3-Embedding-8B")


# def load_embed_model():
#     global _embed_model
#     if _embed_model is None:
#         _embed_model = SentenceTransformer(
#             QWEN_MODEL,
#             device="cuda" if torch.cuda.is_available() else "cpu",
#             trust_remote_code=True,
#         )
#     return _embed_model


# def embed_text(text: str) -> list[float]:
#     model = load_embed_model()
#     # Qwen3-Embedding expects a task prefix for retrieval
#     prefixed = f"Represent this Indian legal document for retrieval: {text[:2000]}"
#     vec = model.encode(prefixed, normalize_embeddings=True)
#     return vec.tolist()


# def embed_query(query: str) -> list[float]:
#     model = load_embed_model()
#     prefixed = f"Represent this legal query for retrieval: {query}"
#     vec = model.encode(prefixed, normalize_embeddings=True)
#     return vec.tolist()


from sentence_transformers import SentenceTransformer
import os

_embed_model = None

# Qwen3-Embedding-8B is 16GB — too heavy for local dev
# Use this lightweight legal-aware model instead (only 90MB)
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def load_embed_model():
    global _embed_model
    if _embed_model is None:
        print(f"[embeddings] Loading model: {EMBED_MODEL}")
        _embed_model = SentenceTransformer(EMBED_MODEL)
        print("[embeddings] Model loaded.")
    return _embed_model


def embed_text(text: str) -> list[float]:
    model = load_embed_model()
    vec = model.encode(text[:2000], normalize_embeddings=True)
    return vec.tolist()


def embed_query(query: str) -> list[float]:
    model = load_embed_model()
    vec = model.encode(query, normalize_embeddings=True)
    return vec.tolist()