# import re
# import os
# from typing import Dict, Any, List

# # ── InLegalBERT is heavy — load lazily on first use only ──────────────────────
# _ner_pipeline = None
# _cls_pipeline = None
# INLEGALBERT = os.getenv("INLEGALBERT_MODEL", "law-ai/InLegalBERT")

# DOC_TYPES = ["judgment", "petition", "FIR", "chargesheet", "statute",
#              "legal notice", "bail order", "writ", "affidavit"]

# ACT_PATTERNS = [
#     r"(?:Section|Sec\.?|S\.)\s*\d+[A-Z]?(?:\(\d+\))*\s+(?:of\s+the\s+)?[A-Z][A-Za-z\s,]+?(?:Act|Code|Rules?|Regulations?|Order)[\s,\d]*",
#     r"\b(?:IPC|CrPC|CPC|IEA|POCSO|IT Act|Companies Act|Motor Vehicles Act|NDPS Act)\b",
#     r"Article\s+\d+[A-Z]?\s+of\s+the\s+Constitution",
# ]


# def _load_ner():
#     global _ner_pipeline
#     if _ner_pipeline is not None:
#         return _ner_pipeline
#     try:
#         import torch
#         from transformers import (
#             AutoTokenizer,
#             AutoModelForTokenClassification,
#             pipeline,
#         )
#         tok = AutoTokenizer.from_pretrained(INLEGALBERT)
#         model = AutoModelForTokenClassification.from_pretrained(
#             INLEGALBERT, ignore_mismatched_sizes=True   # suppresses warnings
#         )
#         _ner_pipeline = pipeline(
#             "ner",
#             model=model,
#             tokenizer=tok,
#             aggregation_strategy="simple",
#             device=0 if torch.cuda.is_available() else -1,
#         )
#     except Exception as e:
#         print(f"[nlp_pipeline] NER model load failed: {e}. Using fallback.")
#         _ner_pipeline = None
#     return _ner_pipeline


# def _load_cls():
#     global _cls_pipeline
#     if _cls_pipeline is not None:
#         return _cls_pipeline
#     try:
#         import torch
#         from transformers import pipeline
#         _cls_pipeline = pipeline(
#             "zero-shot-classification",
#             model=INLEGALBERT,
#             device=0 if torch.cuda.is_available() else -1,
#         )
#     except Exception as e:
#         print(f"[nlp_pipeline] Classifier load failed: {e}. Using fallback.")
#         _cls_pipeline = None
#     return _cls_pipeline


# def extract_act_sections(text: str) -> List[Dict]:
#     found = []
#     seen = set()
#     for pattern in ACT_PATTERNS:
#         for m in re.finditer(pattern, text, re.IGNORECASE):
#             key = m.group().lower().strip()
#             if key not in seen:
#                 seen.add(key)
#                 found.append({"match": m.group().strip(), "span": list(m.span())})
#     return found


# def classify_document(text: str) -> str:
#     """Classify with InLegalBERT zero-shot, fallback to keyword matching."""
#     cls = _load_cls()
#     if cls is not None:
#         try:
#             result = cls(text[:512], candidate_labels=DOC_TYPES)
#             return result["labels"][0]
#         except Exception as e:
#             print(f"[nlp_pipeline] Classification error: {e}")

#     # Keyword fallback — works without any model
#     text_lower = text.lower()
#     keyword_map = {
#         "fir": "FIR",
#         "first information report": "FIR",
#         "chargesheet": "chargesheet",
#         "charge sheet": "chargesheet",
#         "bail": "bail order",
#         "writ petition": "writ",
#         "habeas corpus": "writ",
#         "mandamus": "writ",
#         "affidavit": "affidavit",
#         "whereas": "petition",
#         "petitioner": "petition",
#         "judgment": "judgment",
#         "hereby ordered": "judgment",
#         "section": "statute",
#         "act, ": "statute",
#     }
#     for kw, doc_type in keyword_map.items():
#         if kw in text_lower:
#             return doc_type
#     return "legal document"


# def extract_entities(text: str) -> Dict[str, List[str]]:
#     """Extract entities with InLegalBERT NER, fallback to regex."""
#     entities = {"PERSON": [], "ORG": [], "COURT": [], "DATE": [], "LOCATION": []}

#     ner = _load_ner()
#     if ner is not None:
#         try:
#             chunks = [text[i:i+400] for i in range(0, min(len(text), 4000), 400)]
#             for chunk in chunks:
#                 results = ner(chunk)
#                 for ent in results:
#                     label = ent.get("entity_group", "").upper()
#                     word = ent.get("word", "").strip()
#                     if label in entities and word and len(word) > 1:
#                         entities[label].append(word)
#             return {k: list(set(v)) for k, v in entities.items()}
#         except Exception as e:
#             print(f"[nlp_pipeline] NER error: {e}")

#     # Regex fallback
#     court_pattern = r"(?:High Court|Supreme Court|District Court|Sessions Court|Magistrate Court)[A-Za-z\s]*"
#     date_pattern = r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
#     vs_pattern = r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+(?:vs?\.?|versus)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)"

#     for m in re.finditer(court_pattern, text):
#         entities["COURT"].append(m.group().strip())
#     for m in re.finditer(date_pattern, text):
#         entities["DATE"].append(m.group().strip())
#     for m in re.finditer(vs_pattern, text):
#         entities["PERSON"].extend([m.group(1).strip(), m.group(2).strip()])

#     return {k: list(set(v))[:10] for k, v in entities.items()}


# def generate_summary(text: str) -> str:
#     paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
#     verdict_kw = ["held", "ordered", "directed", "convicted", "acquitted",
#                   "dismissed", "allowed", "disposed", "bail granted", "bail rejected"]
#     selected = paragraphs[:2]
#     for p in paragraphs[2:]:
#         if any(kw in p.lower() for kw in verdict_kw):
#             selected.append(p)
#         if len(selected) >= 5:
#             break
#     return " ".join(selected)[:2000]


# def run_nlp_pipeline(text: str) -> Dict[str, Any]:
#     return {
#         "doc_type": classify_document(text),
#         "entities": extract_entities(text),
#         "act_sections": extract_act_sections(text),
#         "extractive_summary": generate_summary(text),
#     }


import re
import os
from typing import Dict, Any, List

DOC_TYPES = ["judgment", "petition", "FIR", "chargesheet", "statute",
             "legal notice", "bail order", "writ", "affidavit"]

ACT_PATTERNS = [
    r"(?:Section|Sec\.?|S\.)\s*\d+[A-Z]?(?:\(\d+\))*\s+(?:of\s+the\s+)?[A-Z][A-Za-z\s,]+?(?:Act|Code|Rules?|Regulations?|Order)[\s,\d]*",
    r"\b(?:IPC|CrPC|CPC|IEA|POCSO|IT Act|Companies Act|Motor Vehicles Act|NDPS Act)\b",
    r"Article\s+\d+[A-Z]?\s+of\s+the\s+Constitution",
]


def extract_act_sections(text: str) -> List[Dict]:
    found = []
    seen = set()
    for pattern in ACT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            key = m.group().lower().strip()
            if key not in seen:
                seen.add(key)
                found.append({"match": m.group().strip(), "span": list(m.span())})
    return found


def classify_document(text: str) -> str:
    """Fast keyword-based classification — no model needed."""
    text_lower = text.lower()
    keyword_map = [
        (["first information report", "fir no", "f.i.r"], "FIR"),
        (["chargesheet", "charge sheet", "charge-sheet"], "chargesheet"),
        (["bail", "anticipatory bail", "bail application"], "bail order"),
        (["writ petition", "habeas corpus", "mandamus", "certiorari"], "writ"),
        (["affidavit", "solemnly affirm", "sworn before"], "affidavit"),
        (["petitioner", "respondent", "wherefore it is prayed"], "petition"),
        (["legal notice", "take notice", "demand notice"], "legal notice"),
        (["judgment", "hereby ordered", "court holds", "it is held",
          "convicted", "acquitted", "sentenced"], "judgment"),
        (["whereas", "be it enacted", "section 1", "short title"], "statute"),
    ]
    for keywords, doc_type in keyword_map:
        if any(kw in text_lower for kw in keywords):
            return doc_type
    return "legal document"


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Fast regex-based entity extraction — no model needed."""
    entities = {"PERSON": [], "ORG": [], "COURT": [], "DATE": [], "LOCATION": []}

    # Courts
    court_pattern = r"(?:Supreme Court|High Court|District Court|Sessions Court|" \
                    r"Civil Court|Criminal Court|Magistrate Court|Family Court|" \
                    r"Tribunal|Consumer Forum)[A-Za-z\s]*"
    for m in re.finditer(court_pattern, text, re.IGNORECASE):
        entities["COURT"].append(m.group().strip())

    # Dates
    date_pattern = r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+" \
                   r"(?:January|February|March|April|May|June|July|August|" \
                   r"September|October|November|December)[a-z]*\s+\d{4}"
    for m in re.finditer(date_pattern, text, re.IGNORECASE):
        entities["DATE"].append(m.group().strip())

    # Parties from "X vs Y" pattern
    vs_pattern = r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3})\s+(?:vs?\.?|versus)\s+" \
                 r"([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3})"
    for m in re.finditer(vs_pattern, text):
        entities["PERSON"].extend([m.group(1).strip(), m.group(2).strip()])

    # Organisations
    org_pattern = r"(?:State of [A-Z][a-z]+|Union of India|Government of [A-Z][a-z]+|" \
                  r"[A-Z][a-z]+ (?:Bank|Corporation|Company|Ltd|Limited|Authority|Board))"
    for m in re.finditer(org_pattern, text):
        entities["ORG"].append(m.group().strip())

    return {k: list(set(v))[:10] for k, v in entities.items()}


def generate_summary(text: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
    verdict_kw = ["held", "ordered", "directed", "convicted", "acquitted",
                  "dismissed", "allowed", "disposed", "bail granted", "bail rejected"]
    selected = paragraphs[:2]
    for p in paragraphs[2:]:
        if any(kw in p.lower() for kw in verdict_kw):
            selected.append(p)
        if len(selected) >= 5:
            break
    return " ".join(selected)[:2000]


def run_nlp_pipeline(text: str) -> Dict[str, Any]:
    print("[nlp_pipeline] Running fast regex pipeline...")
    result = {
        "doc_type": classify_document(text),
        "entities": extract_entities(text),
        "act_sections": extract_act_sections(text),
        "extractive_summary": generate_summary(text),
    }
    print(f"[nlp_pipeline] Done. doc_type={result['doc_type']}, "
          f"acts_found={len(result['act_sections'])}")
    return result

# At the top of nlp_pipeline.py, add this import:
from app.services.statute_identifier import identify_statutes, StatuteResult

# Replace run_nlp_pipeline with this async version:

async def run_nlp_pipeline(text: str) -> dict:
    """
    Full NLP pipeline — now includes LeSICiN statute identification.
    Returns enriched analysis dict.
    """
    print("[nlp_pipeline] Running fast regex pipeline...")

    doc_type   = classify_document(text)
    entities   = extract_entities(text)
    act_sections = extract_act_sections(text)
    summary    = generate_summary(text)

    print(f"[nlp_pipeline] Regex done. doc_type={doc_type}, regex_acts={len(act_sections)}")

    # ── LeSICiN statute identification ─────────────────────────────────────────
    print("[nlp_pipeline] Running LeSICiN statute identification...")
    statute_result: StatuteResult = await identify_statutes(text)

    if statute_result.model_available and not statute_result.error:
        print(f"[nlp_pipeline] LeSICiN found {len(statute_result.statutes)} statutes")
    else:
        print(f"[nlp_pipeline] LeSICiN unavailable: {statute_result.error}")

    return {
        "doc_type":        doc_type,
        "entities":        entities,
        "act_sections":    act_sections,          # regex-based (fast, broad)
        "extractive_summary": summary,
        "identified_statutes": statute_result.statutes,       # LeSICiN predictions
        "statute_model_available": statute_result.model_available,
        "statute_raw_predictions": statute_result.raw_predictions,
    }