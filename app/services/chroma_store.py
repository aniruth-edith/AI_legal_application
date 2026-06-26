import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")

_client = None


def get_client() -> chromadb.Client:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def collection_name(user_id: str) -> str:
    # One collection per user — all their case docs
    return f"user_{user_id}"


def upsert_document(
    user_id: str,
    doc_id: str,
    case_id: str,
    embedding: List[float],
    text_chunk: str,
    metadata: Dict[str, Any],
):
    client = get_client()
    col = client.get_or_create_collection(
        name=collection_name(user_id),
        metadata={"hnsw:space": "cosine"},
    )
    col.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text_chunk],
        metadatas=[{**metadata, "case_id": case_id, "user_id": user_id}],
    )


def query_similar(
    user_id: str,
    query_embedding: List[float],
    case_id: str | None = None,
    n_results: int = 5,
) -> List[Dict]:
    client = get_client()
    col = client.get_or_create_collection(name=collection_name(user_id))
    where = {"case_id": case_id} if case_id else None
    results = col.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    output = []
    for i, doc in enumerate(results["documents"][0]):
        output.append({
            "text": doc,
            "metadata": results["metadatas"][0][i],
            "score": 1 - results["distances"][0][i],  # cosine similarity
        })
    return output


def get_all_case_docs(user_id: str, case_id: str) -> List[Dict]:
    client = get_client()
    col = client.get_or_create_collection(name=collection_name(user_id))
    results = col.get(
        where={"case_id": case_id},
        include=["documents", "metadatas"],
    )
    return [
        {"text": t, "metadata": m}
        for t, m in zip(results["documents"], results["metadatas"])
    ]

def delete_document(user_id: str, doc_id: str) -> bool:
    """Delete a single document from the user's ChromaDB collection."""
    try:
        client = get_client()
        col = client.get_or_create_collection(name=collection_name(user_id))
        col.delete(ids=[doc_id])
        return True
    except Exception as e:
        print(f"ChromaDB delete error: {e}")
        return False