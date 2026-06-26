# """
# app/services/statute_identifier.py

# Wraps the LeSICiN model (AAAI 2022) as a clean inference service.
# Exposes a single public function:

#     identify_statutes(text: str) -> StatuteResult

# LeSICiN uses a heterogeneous graph + sent2vec to predict which IPC sections
# are relevant to a given legal document text.

# Loading is lazy and cached — the model loads once on first call and stays
# in memory. Subsequent calls are fast (~0.5–2s depending on doc length).
# """

# import os
# import sys
# import json
# import string
# import pickle as pkl
# import asyncio
# import logging
# from pathlib import Path
# from dataclasses import dataclass, field
# from typing import List, Optional
# from functools import partial

# logger = logging.getLogger(__name__)

# # ── Path setup ────────────────────────────────────────────────────────────────
# # Add statute_identification/ to sys.path so its internal imports work
# STATUTE_DIR = Path(__file__).resolve().parents[2] / "statute_identification"
# if str(STATUTE_DIR) not in sys.path:
#     sys.path.insert(0, str(STATUTE_DIR))

# CONFIG_DIR = STATUTE_DIR / "configs"


# # ── Result dataclass ───────────────────────────────────────────────────────────

# @dataclass
# class StatuteResult:
#     statutes: List[dict] = field(default_factory=list)
#     # e.g. [{"section": "IPC Section 302", "confidence": 0.87, "description": "..."}]
#     raw_predictions: List[str] = field(default_factory=list)
#     model_available: bool = True
#     error: Optional[str] = None

#     def to_dict(self) -> dict:
#         return {
#             "statutes": self.statutes,
#             "raw_predictions": self.raw_predictions,
#             "model_available": self.model_available,
#             "error": self.error,
#         }


# # ── Global model state (lazy-loaded) ──────────────────────────────────────────

# _state = {
#     "loaded": False,
#     "loading": False,
#     "error": None,
#     "model": None,
#     "sec_batch": None,
#     "sent2vec_model": None,
#     "label_vocab": None,
#     "inv_label_vocab": None,
#     "node_vocab": None,
#     "edge_vocab": None,
#     "adjacency": None,
#     "schemas": None,
#     "type_map": None,
#     "hc": None,
#     "dc": None,
#     "section_descriptions": {},   # maps section id → human-readable description
# }

# _load_lock = asyncio.Lock()


# def _load_section_descriptions() -> dict:
#     """
#     Build a map of section_id → description from secs.jsonl.
#     Falls back to label_vocab.json if secs.jsonl isn't available.
#     """
#     descriptions = {}
#     secs_path = STATUTE_DIR / "data" / "secs.jsonl"
#     if secs_path.exists():
#         with open(secs_path) as f:
#             for line in f:
#                 try:
#                     doc = json.loads(line)
#                     sid = doc.get("id", "")
#                     text = doc.get("text", [])
#                     # Take first 2 sentences as description
#                     desc = " ".join(text[:2]) if isinstance(text, list) else str(text)
#                     descriptions[sid] = desc[:300]
#                 except Exception:
#                     continue
#     return descriptions


# def _load_model_sync():
#     """
#     Synchronous model loading — runs in a thread via asyncio.to_thread.
#     Loads all LeSICiN components into _state.
#     """
#     import torch
#     # import sent2vec as s2v
#     import sys
#     sys.path.insert(0, str(STATUTE_DIR))
    
#     from statute_identification.sent2vec_adapter import Sent2vecModel as Sent2vecModelAdapter


#     # Import from statute_identification package
#     from statute_identification.model.model import LeSICiN
#     from statute_identification.data_helper import LSIDataset, collate_func
#     from statute_identification.helper import generate_vocabs, generate_graph

#     with open(CONFIG_DIR / "data_path.json") as f:
#         dc = json.load(f)
#     with open(CONFIG_DIR / "hyperparams.json") as f:
#         hc = json.load(f)

#     _state["dc"] = dc
#     _state["hc"] = hc

#     logger.info("[statute_identifier] Loading Sent2Vec model...")
#     # s2v_model = s2v.Sent2vecModel()
#     # s2v_model.load_model(str(STATUTE_DIR / dc["s2v_path"].replace("statute_identification/", "")))
#     s2v_model = Sent2vecModelAdapter()
#     s2v_model.load_model(str(STATUTE_DIR / "data" / "ils2v.bin"))  # path ignored
#     _state["sent2vec_model"] = s2v_model

#     logger.info("[statute_identifier] Loading section dataset...")
#     sec_cache = STATUTE_DIR / dc["sec_cache"].replace("statute_identification/", "")
#     sec_src   = STATUTE_DIR / dc["sec_src"].replace("statute_identification/", "")

#     if sec_cache.exists():
#         sec_dataset = LSIDataset.load_data(str(sec_cache))
#     else:
#         sec_dataset = LSIDataset(jsonl_file=str(sec_src))
#         sec_dataset.preprocess()
#         sec_dataset.sent_vectorize(s2v_model)
#         sec_cache.parent.mkdir(exist_ok=True)
#         sec_dataset.save_data(str(sec_cache))

#     logger.info("[statute_identifier] Building graph structures...")
#     with open(STATUTE_DIR / dc["type_map"].replace("statute_identification/", "")) as f:
#         type_map = json.load(f)
#     with open(STATUTE_DIR / dc["label_tree"].replace("statute_identification/", "")) as f:
#         label_tree = json.load(f)
#     with open(STATUTE_DIR / dc["citation_network"].replace("statute_identification/", "")) as f:
#         citation_net = json.load(f)
#     with open(STATUTE_DIR / dc["schemas"].replace("statute_identification/", "")) as f:
#         schemas = json.load(f)

#     # Convert schema edge tuples
#     for sch in schemas.values():
#         for path in sch:
#             for i, edge in enumerate(path):
#                 path[i] = tuple(edge)

#     # Build vocab and graph
#     _, label_vocab = generate_vocabs(sec_dataset, sec_dataset)
#     node_vocab, edge_vocab, _, adjacency = generate_graph(
#         label_vocab, type_map, label_tree, citation_net
#     )

#     L = len(label_vocab)
#     N = {k: len(v) for k, v in node_vocab.items()}
#     E = len(edge_vocab)

#     # Pre-compute section batch (static — sections don't change)
#     sec_loader = torch.utils.data.DataLoader(
#         sec_dataset,
#         batch_size=len(label_vocab),
#         collate_fn=partial(
#             collate_func,
#             schemas=schemas["section"],
#             type_map=type_map,
#             node_vocab=node_vocab,
#             edge_vocab=edge_vocab,
#             adjacency=adjacency,
#             max_segments=hc["max_segments"],
#             max_segment_size=hc["max_segment_size"],
#             num_mpath_samples=hc["num_mpath_samples"],
#         ),
#         pin_memory=torch.cuda.is_available(),
#         num_workers=0,  # 0 workers for Windows compatibility
#     )
#     for sec_batch in sec_loader:
#         break  # We only need one batch (all sections)

#     logger.info("[statute_identifier] Loading LeSICiN model weights...")
#     device = "cuda" if torch.cuda.is_available() else "cpu"

#     lsc_model = LeSICiN(
#         hc["hidden_size"],
#         L, N, E,
#         label_weights=None,
#         lambdas=hc["lambdas"],
#         thetas=hc["thetas"],
#         pthresh=hc["pthresh"],
#         drop=0.0,  # no dropout at inference
#     )

#     model_path = STATUTE_DIR / dc["model_load"].replace("statute_identification/", "")
#     if not model_path.exists():
#         raise FileNotFoundError(f"Model weights not found: {model_path}")

#     lsc_model.load_state_dict(
#         torch.load(str(model_path), map_location=device)
#     )
#     lsc_model.to(device)
#     lsc_model.eval()

#     inv_label_vocab = {v: k for k, v in label_vocab.items()}

#     _state.update({
#         "loaded": True,
#         "model": lsc_model,
#         "sec_batch": sec_batch,
#         "label_vocab": label_vocab,
#         "inv_label_vocab": inv_label_vocab,
#         "node_vocab": node_vocab,
#         "edge_vocab": edge_vocab,
#         "adjacency": adjacency,
#         "schemas": schemas,
#         "type_map": type_map,
#         "section_descriptions": _load_section_descriptions(),
#         "device": device,
#     })

#     logger.info(f"[statute_identifier] Model loaded on {device}. "
#                 f"Vocabulary: {len(label_vocab)} IPC sections.")


# async def _ensure_loaded():
#     """Lazy-load the model exactly once."""
#     if _state["loaded"]:
#         return True
#     if _state["error"]:
#         return False

#     async with _load_lock:
#         if _state["loaded"]:
#             return True
#         _state["loading"] = True
#         try:
#             await asyncio.to_thread(_load_model_sync)
#             return True
#         except Exception as e:
#             _state["error"] = str(e)
#             logger.error(f"[statute_identifier] Failed to load model: {e}")
#             return False
#         finally:
#             _state["loading"] = False


# # ── Inference helpers ──────────────────────────────────────────────────────────

# def _preprocess_text(text: str) -> list:
#     """
#     Convert raw text to list of preprocessed sentences,
#     matching LeSICiN's training preprocessing exactly.
#     """
#     import re
#     # Split into sentences
#     sentences = re.split(r'(?<=[.।?!])\s+', text.strip())
#     processed = []
#     for sent in sentences:
#         # Remove punctuation and lowercase (matching data_helper.preprocess)
#         pp = sent.strip().lower().translate(str.maketrans("", "", string.punctuation))
#         if len(pp.split()) > 1:
#             processed.append(pp)
#     return processed if processed else [text.lower()[:500]]


# def _run_inference_sync(text: str) -> StatuteResult:
#     """
#     Run LeSICiN inference on a single document text.
#     Returns StatuteResult with predicted IPC sections.
#     """
#     import torch
#     import numpy as np
#     from statute_identification.data_helper import LSIDataset, collate_func

#     hc      = _state["hc"]
#     device  = _state["device"]
#     model   = _state["model"]
#     s2v     = _state["sent2vec_model"]
#     sec_batch = _state["sec_batch"]
#     inv_lv  = _state["inv_label_vocab"]
#     descs   = _state["section_descriptions"]

#     # Build a single-document inference dataset
#     sentences = _preprocess_text(text)
#     if not sentences:
#         return StatuteResult(model_available=True, error="No processable sentences found")

#     # Embed sentences using Sent2Vec
#     embeddings = s2v.embed_sentences(sentences)
#     # Remove zero-sum rows (unrecognised sentences)
#     embeddings = np.delete(embeddings, np.where(embeddings.sum(axis=1) == 0)[0], axis=0)

#     if embeddings.shape[0] == 0:
#         return StatuteResult(model_available=True, error="Sent2Vec produced zero embeddings")

#     instance = {"id": "infer_doc", "text": embeddings}
#     dataset  = LSIDataset(data_list=[{"id": "infer_doc", "text": sentences}])
#     dataset.sent_vectorized = True
#     dataset.dataset[0]["text"] = embeddings

#     loader = torch.utils.data.DataLoader(
#         dataset,
#         batch_size=1,
#         collate_fn=partial(
#             collate_func,
#             max_segments=hc["max_segments"],
#             max_segment_size=hc["max_segment_size"],
#         ),
#         num_workers=0,
#     )

#     raw_predictions = []
#     statutes = []

#     with torch.no_grad():
#         for fact_batch in loader:
#             if device == "cuda":
#                 fact_batch = fact_batch.cuda()
#                 sb = sec_batch.cuda()
#             else:
#                 sb = sec_batch

#             _, predictions = model(fact_batch, sb, pthresh=hc["pthresh"])

#             # predictions shape: [1, num_sections]
#             pred_indices = torch.nonzero(predictions[0], as_tuple=False).squeeze(1)

#             # Also get raw scores for confidence
#             _, scores = model.match_network(
#                 model.text_encoder(
#                     doc_inputs=fact_batch.doc_inputs if fact_batch.sent_vectorized else None,
#                     tokens=fact_batch.tokens if not fact_batch.sent_vectorized else None,
#                     mask=fact_batch.mask,
#                 ),
#                 model.text_encoder(
#                     doc_inputs=sb.doc_inputs if sb.sent_vectorized else None,
#                     tokens=sb.tokens if not sb.sent_vectorized else None,
#                     mask=sb.mask,
#                 ),
#             )

#             for idx in pred_indices.tolist():
#                 section_id  = inv_lv.get(idx, f"Section_{idx}")
#                 confidence  = float(scores[0, idx].item())
#                 description = descs.get(section_id, "")

#                 raw_predictions.append(section_id)
#                 statutes.append({
#                     "section_id":   section_id,
#                     "display_name": _format_section_name(section_id),
#                     "confidence":   round(confidence, 4),
#                     "description":  description,
#                     "source":       "LeSICiN",
#                 })

#     # Sort by confidence descending
#     statutes.sort(key=lambda x: x["confidence"], reverse=True)

#     return StatuteResult(
#         statutes=statutes,
#         raw_predictions=raw_predictions,
#         model_available=True,
#     )


# def _format_section_name(section_id: str) -> str:
#     """Convert raw section IDs like 'IPC_302' → 'IPC Section 302'."""
#     sid = section_id.strip()
#     # Common patterns: IPC_302, ipc-302, S302, sec_302
#     import re
#     m = re.match(r"(?:IPC[_\-\s]?)?[Ss]?[Ee]?[Cc]?[_\-\s]?(\d+[A-Z]?)", sid, re.I)
#     if m:
#         return f"IPC Section {m.group(1)}"
#     return sid


# # ── Public API ─────────────────────────────────────────────────────────────────

# async def identify_statutes(text: str) -> StatuteResult:
#     """
#     Main entry point. Call this from nlp_pipeline.py.

#     Args:
#         text: Raw legal document text

#     Returns:
#         StatuteResult with list of predicted IPC sections + confidence scores
#     """
#     if not text or len(text.strip()) < 50:
#         return StatuteResult(
#             model_available=True,
#             error="Text too short for statute identification",
#         )

#     loaded = await _ensure_loaded()

#     if not loaded:
#         logger.warning("[statute_identifier] Model unavailable, returning empty result")
#         return StatuteResult(
#             model_available=False,
#             error=_state.get("error", "Model failed to load"),
#         )

#     try:
#         result = await asyncio.to_thread(_run_inference_sync, text)
#         return result
#     except Exception as e:
#         logger.error(f"[statute_identifier] Inference error: {e}")
#         return StatuteResult(
#             model_available=True,
#             error=f"Inference failed: {str(e)[:200]}",
#         )


# def is_model_loaded() -> bool:
#     return _state["loaded"]


# def get_model_status() -> dict:
#     return {
#         "loaded":    _state["loaded"],
#         "loading":   _state["loading"],
#         "error":     _state["error"],
#         "device":    _state.get("device"),
#         "sections":  len(_state["label_vocab"]) if _state["label_vocab"] else 0,
#     }

"""
app/services/statute_identifier.py

Wraps the LeSICiN model (AAAI 2022) as a clean inference service.
Exposes a single public function:

    identify_statutes(text: str) -> StatuteResult

LeSICiN uses a heterogeneous graph + sent2vec to predict which IPC sections
are relevant to a given legal document text.

Loading is lazy and cached — the model loads once on first call and stays
in memory. Subsequent calls are fast (~0.5–2s depending on doc length).
"""

import os
import sys
import json
import string
import pickle as pkl
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
from functools import partial

logger = logging.getLogger(__name__)

# ── Path setup ────────────────────────────────────────────────────────────────
# Add statute_identification/ to sys.path so its internal imports work
STATUTE_DIR = Path(__file__).resolve().parents[2] / "statute_identification"
if str(STATUTE_DIR) not in sys.path:
    sys.path.insert(0, str(STATUTE_DIR))

CONFIG_DIR = STATUTE_DIR / "configs"


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class StatuteResult:
    statutes: List[dict] = field(default_factory=list)
    # e.g. [{"section": "IPC Section 302", "confidence": 0.87, "description": "..."}]
    raw_predictions: List[str] = field(default_factory=list)
    model_available: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "statutes": self.statutes,
            "raw_predictions": self.raw_predictions,
            "model_available": self.model_available,
            "error": self.error,
        }


# ── Global model state (lazy-loaded) ──────────────────────────────────────────

_state = {
    "loaded": False,
    "loading": False,
    "error": None,
    "model": None,
    "sec_batch": None,
    "sent2vec_model": None,
    "label_vocab": None,
    "inv_label_vocab": None,
    "node_vocab": None,
    "edge_vocab": None,
    "adjacency": None,
    "schemas": None,
    "type_map": None,
    "hc": None,
    "dc": None,
    "section_descriptions": {},   # maps section id → human-readable description
}

_load_lock = asyncio.Lock()


def _load_section_descriptions() -> dict:
    """
    Build a map of section_id → description from secs.jsonl.
    Falls back to label_vocab.json if secs.jsonl isn't available.
    """
    descriptions = {}
    secs_path = STATUTE_DIR / "data" / "secs.jsonl"
    if secs_path.exists():
        with open(secs_path) as f:
            for line in f:
                try:
                    doc = json.loads(line)
                    sid = doc.get("id", "")
                    text = doc.get("text", [])
                    # Take first 2 sentences as description
                    desc = " ".join(text[:2]) if isinstance(text, list) else str(text)
                    descriptions[sid] = desc[:300]
                except Exception:
                    continue
    return descriptions


def _load_model_sync():
    """
    Synchronous model loading — runs in a thread via asyncio.to_thread.
    Loads all LeSICiN components into _state.
    """
    import torch
    # import sent2vec as s2v
    import sys
    sys.path.insert(0, str(STATUTE_DIR))
    
    from statute_identification.sent2vec_adapter import Sent2vecModel as Sent2vecModelAdapter


    # Import from statute_identification package
    from statute_identification.model.model import LeSICiN
    from statute_identification.data_helper import LSIDataset, collate_func
    from statute_identification.helper import generate_vocabs, generate_graph

    with open(CONFIG_DIR / "data_path.json") as f:
        dc = json.load(f)
    with open(CONFIG_DIR / "hyperparams.json") as f:
        hc = json.load(f)

    _state["dc"] = dc
    _state["hc"] = hc

    logger.info("[statute_identifier] Loading Sent2Vec model...")
    # s2v_model = s2v.Sent2vecModel()
    # s2v_model.load_model(str(STATUTE_DIR / dc["s2v_path"].replace("statute_identification/", "")))
    s2v_model = Sent2vecModelAdapter()
    s2v_model.load_model(str(STATUTE_DIR / "data" / "ils2v.bin"))  # path ignored
    _state["sent2vec_model"] = s2v_model

    logger.info("[statute_identifier] Loading section dataset...")
    sec_cache = STATUTE_DIR / dc["sec_cache"].replace("statute_identification/", "")
    sec_src   = STATUTE_DIR / dc["sec_src"].replace("statute_identification/", "")

    if sec_cache.exists():
        sec_dataset = LSIDataset.load_data(str(sec_cache))
    else:
        sec_dataset = LSIDataset(jsonl_file=str(sec_src))
        sec_dataset.preprocess()
        sec_dataset.sent_vectorize(s2v_model)
        sec_cache.parent.mkdir(exist_ok=True)
        sec_dataset.save_data(str(sec_cache))

    logger.info("[statute_identifier] Building graph structures...")
    with open(STATUTE_DIR / dc["type_map"].replace("statute_identification/", "")) as f:
        type_map = json.load(f)
    with open(STATUTE_DIR / dc["label_tree"].replace("statute_identification/", "")) as f:
        label_tree = json.load(f)
    with open(STATUTE_DIR / dc["citation_network"].replace("statute_identification/", "")) as f:
        citation_net = json.load(f)
    with open(STATUTE_DIR / dc["schemas"].replace("statute_identification/", "")) as f:
        schemas = json.load(f)

    # Convert schema edge tuples
    for sch in schemas.values():
        for path in sch:
            for i, edge in enumerate(path):
                path[i] = tuple(edge)

    # Build vocab and graph
    _, label_vocab = generate_vocabs(sec_dataset, sec_dataset)
    node_vocab, edge_vocab, _, adjacency = generate_graph(
        label_vocab, type_map, label_tree, citation_net
    )

    L = len(label_vocab)
    N = {k: len(v) for k, v in node_vocab.items()}
    E = len(edge_vocab)

    # Pre-compute section batch (static — sections don't change)
    sec_loader = torch.utils.data.DataLoader(
        sec_dataset,
        batch_size=len(label_vocab),
        collate_fn=partial(
            collate_func,
            schemas=schemas["section"],
            type_map=type_map,
            node_vocab=node_vocab,
            edge_vocab=edge_vocab,
            adjacency=adjacency,
            max_segments=hc["max_segments"],
            max_segment_size=hc["max_segment_size"],
            num_mpath_samples=hc["num_mpath_samples"],
        ),
        pin_memory=torch.cuda.is_available(),
        num_workers=0,  # 0 workers for Windows compatibility
    )
    for sec_batch in sec_loader:
        break  # We only need one batch (all sections)

    logger.info("[statute_identifier] Loading LeSICiN model weights...")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    lsc_model = LeSICiN(
        hc["hidden_size"],
        L, N, E,
        label_weights=None,
        lambdas=hc["lambdas"],
        thetas=hc["thetas"],
        pthresh=hc["pthresh"],
        drop=0.0,  # no dropout at inference
    )

    model_path = STATUTE_DIR / dc["model_load"].replace("statute_identification/", "")
    if not model_path.exists():
        raise FileNotFoundError(f"Model weights not found: {model_path}")

    lsc_model.load_state_dict(
        torch.load(str(model_path), map_location=device)
    )
    lsc_model.to(device)
    lsc_model.eval()

    inv_label_vocab = {v: k for k, v in label_vocab.items()}

    _state.update({
        "loaded": True,
        "model": lsc_model,
        "sec_batch": sec_batch,
        "label_vocab": label_vocab,
        "inv_label_vocab": inv_label_vocab,
        "node_vocab": node_vocab,
        "edge_vocab": edge_vocab,
        "adjacency": adjacency,
        "schemas": schemas,
        "type_map": type_map,
        "section_descriptions": _load_section_descriptions(),
        "device": device,
    })

    logger.info(f"[statute_identifier] Model loaded on {device}. "
                f"Vocabulary: {len(label_vocab)} IPC sections.")


async def _ensure_loaded():
    """Lazy-load the model exactly once."""
    if _state["loaded"]:
        return True
    if _state["error"]:
        return False

    async with _load_lock:
        if _state["loaded"]:
            return True
        _state["loading"] = True
        try:
            await asyncio.to_thread(_load_model_sync)
            return True
        except Exception as e:
            _state["error"] = str(e)
            logger.error(f"[statute_identifier] Failed to load model: {e}")
            return False
        finally:
            _state["loading"] = False


# ── Inference helpers ──────────────────────────────────────────────────────────

def _preprocess_text(text: str) -> list:
    """
    Convert raw text to list of preprocessed sentences,
    matching LeSICiN's training preprocessing exactly.
    """
    import re
    # Split into sentences
    sentences = re.split(r'(?<=[.।?!])\s+', text.strip())
    processed = []
    for sent in sentences:
        # Remove punctuation and lowercase (matching data_helper.preprocess)
        pp = sent.strip().lower().translate(str.maketrans("", "", string.punctuation))
        if len(pp.split()) > 1:
            processed.append(pp)
    return processed if processed else [text.lower()[:500]]


def _run_inference_sync(text: str) -> StatuteResult:
    """
    Run LeSICiN inference on a single document text.
    Returns StatuteResult with predicted IPC sections.
    """
    import torch
    import numpy as np
    from statute_identification.data_helper import LSIDataset, collate_func

    hc      = _state["hc"]
    device  = _state["device"]
    model   = _state["model"]
    s2v     = _state["sent2vec_model"]
    sec_batch = _state["sec_batch"]
    inv_lv  = _state["inv_label_vocab"]
    descs   = _state["section_descriptions"]

    # Build a single-document inference dataset
    sentences = _preprocess_text(text)
    if not sentences:
        return StatuteResult(model_available=True, error="No processable sentences found")

    # Embed sentences using Sent2Vec
    embeddings = s2v.embed_sentences(sentences)
    # Remove zero-sum rows (unrecognised sentences)
    embeddings = np.delete(embeddings, np.where(embeddings.sum(axis=1) == 0)[0], axis=0)

    if embeddings.shape[0] == 0:
        return StatuteResult(model_available=True, error="Sent2Vec produced zero embeddings")

    instance = {"id": "infer_doc", "text": embeddings}
    dataset  = LSIDataset(data_list=[{"id": "infer_doc", "text": sentences}])
    dataset.sent_vectorized = True
    dataset.dataset[0]["text"] = embeddings

    loader = torch.utils.data.DataLoader(
        dataset,
        batch_size=1,
        collate_fn=partial(
            collate_func,
            max_segments=hc["max_segments"],
            max_segment_size=hc["max_segment_size"],
        ),
        num_workers=0,
    )

    raw_predictions = []
    statutes = []

    with torch.no_grad():
        for fact_batch in loader:
            if device == "cuda":
                fact_batch = fact_batch.cuda()
                sb = sec_batch.cuda()
            else:
                sb = sec_batch

            _, predictions, scores = model(fact_batch, sb, pthresh=hc["pthresh"])

            # predictions shape: [1, num_sections]
            pred_indices = torch.nonzero(predictions[0], as_tuple=False).squeeze(1)

            for idx in pred_indices.tolist():
                section_id  = inv_lv.get(idx, f"Section_{idx}")
                confidence  = float(scores[0, idx].item())
                description = descs.get(section_id, "")

                raw_predictions.append(section_id)
                statutes.append({
                    "section_id":   section_id,
                    "display_name": _format_section_name(section_id),
                    "confidence":   round(confidence, 4),
                    "description":  description,
                    "source":       "LeSICiN",
                })

    # Sort by confidence descending
    statutes.sort(key=lambda x: x["confidence"], reverse=True)

    return StatuteResult(
        statutes=statutes,
        raw_predictions=raw_predictions,
        model_available=True,
    )


def _format_section_name(section_id: str) -> str:
    """Convert raw section IDs like 'IPC_302' → 'IPC Section 302'."""
    sid = section_id.strip()
    # Common patterns: IPC_302, ipc-302, S302, sec_302
    import re
    m = re.match(r"(?:IPC[_\-\s]?)?[Ss]?[Ee]?[Cc]?[_\-\s]?(\d+[A-Z]?)", sid, re.I)
    if m:
        return f"IPC Section {m.group(1)}"
    return sid


# ── Public API ─────────────────────────────────────────────────────────────────

async def identify_statutes(text: str) -> StatuteResult:
    """
    Main entry point. Call this from nlp_pipeline.py.

    Args:
        text: Raw legal document text

    Returns:
        StatuteResult with list of predicted IPC sections + confidence scores
    """
    if not text or len(text.strip()) < 50:
        return StatuteResult(
            model_available=True,
            error="Text too short for statute identification",
        )

    loaded = await _ensure_loaded()

    if not loaded:
        logger.warning("[statute_identifier] Model unavailable, returning empty result")
        return StatuteResult(
            model_available=False,
            error=_state.get("error", "Model failed to load"),
        )

    try:
        result = await asyncio.to_thread(_run_inference_sync, text)
        return result
    except Exception as e:
        logger.error(f"[statute_identifier] Inference error: {e}")
        return StatuteResult(
            model_available=True,
            error=f"Inference failed: {str(e)[:200]}",
        )


def is_model_loaded() -> bool:
    return _state["loaded"]


def get_model_status() -> dict:
    return {
        "loaded":    _state["loaded"],
        "loading":   _state["loading"],
        "error":     _state["error"],
        "device":    _state.get("device"),
        "sections":  len(_state["label_vocab"]) if _state["label_vocab"] else 0,
    }