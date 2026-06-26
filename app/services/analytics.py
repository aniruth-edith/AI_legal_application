"""
Service: analytics.py
Core analytics engine — operates on already-extracted NLP and LLM data.
No model inference here; pure data aggregation and graph building.

Functions:
  compute_citation_frequency   — Act/section citation counts across docs
  build_entity_timeline        — Who appeared in which document and when
  build_law_graph              — Co-citation network graph for Plotly
  compute_doc_diff             — Structural diff between two document analyses
  compute_case_progress_score  — Heuristic progress score for a case
  get_case_statistics          — Full stats object for analytics tab
"""

from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from datetime import datetime
import re


# ── Citation frequency ─────────────────────────────────────────────────────────

def compute_citation_frequency(
    all_nlp_meta: List[Dict],
) -> List[Dict]:
    """
    Count how often each act/section appears across all documents.

    Input: list of nlp_meta dicts, each with 'act_sections' key
    Returns: sorted list of {act, section, count, display_label}
    """
    counter: Counter = Counter()
    act_sections_raw: Dict[str, str] = {}  # label -> act name

    for meta in all_nlp_meta:
        sections = meta.get("act_sections", [])
        for raw in sections:
            # Normalise: strip extra whitespace
            clean = " ".join(raw.split())
            counter[clean] += 1

            # Try to extract act name from the match string
            act_name = _extract_act_name(clean)
            act_sections_raw[clean] = act_name

    result = []
    for label, count in counter.most_common():
        result.append({
            "citation": label,
            "act": act_sections_raw.get(label, "Other"),
            "section": _extract_section_number(label),
            "count": count,
            "display_label": label[:60],  # truncate for display
        })

    return result


def _extract_act_name(citation: str) -> str:
    known_acts = [
        "Indian Penal Code", "IPC",
        "Code of Criminal Procedure", "CrPC",
        "Code of Civil Procedure", "CPC",
        "Indian Evidence Act", "IEA",
        "POCSO", "IT Act",
        "Companies Act", "Motor Vehicles Act",
        "Negotiable Instruments Act",
        "Consumer Protection Act",
        "Arbitration and Conciliation Act",
        "Prevention of Corruption Act",
        "Narcotic Drugs and Psychotropic Substances Act", "NDPS",
        "Constitution of India",
    ]
    for act in known_acts:
        if act.lower() in citation.lower():
            return act
    return "Other"


def _extract_section_number(citation: str) -> str:
    m = re.search(r"(?:Section|Sec\.?|S\.)\s*(\d+[A-Z]?(?:/\d+[A-Z]?)*)", citation, re.I)
    if m:
        return m.group(1)
    m2 = re.search(r"Article\s+(\d+[A-Z]?)", citation, re.I)
    if m2:
        return f"Art.{m2.group(1)}"
    return ""


# ── Entity timeline ────────────────────────────────────────────────────────────

def build_entity_timeline(docs: List) -> List[Dict]:
    """
    Build a timeline of entities (people, courts, orgs) across documents.
    Tracks first appearance and all subsequent mentions.

    Returns list of {entity, type, first_seen, appearances}
    """
    entity_history: Dict[str, Dict] = {}

    for doc in docs:
        analysis = doc.analysis or {}
        nlp_meta = analysis.get("nlp_meta", {})
        entities = nlp_meta.get("entities", {})
        date_str = doc.uploaded_at.strftime("%Y-%m-%d")
        filename = doc.filename

        for entity_type, names in entities.items():
            for name in names:
                name = name.strip()
                if len(name) < 2:
                    continue
                key = f"{entity_type}::{name.lower()}"
                if key not in entity_history:
                    entity_history[key] = {
                        "entity": name,
                        "type": entity_type,
                        "first_seen": date_str,
                        "first_document": filename,
                        "appearances": [],
                    }
                entity_history[key]["appearances"].append({
                    "date": date_str,
                    "document": filename,
                    "doc_id": doc.id,
                })

    # Sort by first appearance
    timeline = sorted(entity_history.values(), key=lambda x: x["first_seen"])
    return timeline


# ── Law co-citation graph ──────────────────────────────────────────────────────

def build_law_graph(all_nlp_meta: List[Dict]) -> Dict:
    """
    Build a co-citation network graph for Plotly Network/Dash visualization.
    Two acts are connected if they are cited in the same document.

    Returns: {nodes: [...], edges: [...]} compatible with Plotly graph objects.
    """
    # Collect act sets per document
    doc_act_sets: List[set] = []
    act_freq: Counter = Counter()

    for meta in all_nlp_meta:
        sections = meta.get("act_sections", [])
        acts_in_doc = set()
        for raw in sections:
            act = _extract_act_name(raw)
            if act != "Other":
                acts_in_doc.add(act)
                act_freq[act] += 1
        if acts_in_doc:
            doc_act_sets.append(acts_in_doc)

    # Build co-citation edge weights
    edge_weights: Dict[tuple, int] = defaultdict(int)
    for act_set in doc_act_sets:
        acts = sorted(act_set)
        for i in range(len(acts)):
            for j in range(i + 1, len(acts)):
                edge = (acts[i], acts[j])
                edge_weights[edge] += 1

    # Assign simple positions (circular layout)
    import math
    unique_acts = list(act_freq.keys())
    n = len(unique_acts)
    positions = {}
    for i, act in enumerate(unique_acts):
        angle = 2 * math.pi * i / max(n, 1)
        positions[act] = {
            "x": round(math.cos(angle), 4),
            "y": round(math.sin(angle), 4),
        }

    nodes = [
        {
            "id": act,
            "label": act,
            "frequency": act_freq[act],
            "x": positions[act]["x"],
            "y": positions[act]["y"],
            "size": min(40, 10 + act_freq[act] * 5),  # scale for display
        }
        for act in unique_acts
    ]

    edges = [
        {
            "source": src,
            "target": tgt,
            "weight": w,
            "x0": positions[src]["x"],
            "y0": positions[src]["y"],
            "x1": positions[tgt]["x"],
            "y1": positions[tgt]["y"],
        }
        for (src, tgt), w in edge_weights.items()
    ]

    return {"nodes": nodes, "edges": edges}


# ── Document diff ──────────────────────────────────────────────────────────────

def compute_doc_diff(analysis_a: Dict, analysis_b: Dict) -> Dict:
    """
    Structural diff between two document analyses.
    Compares laws, parties, insights, and risk flags.
    """
    def _to_set(analysis: Dict, field: str, sub_key: str | None = None) -> set:
        items = analysis.get(field, [])
        if sub_key:
            return {str(i.get(sub_key, "")) for i in items if isinstance(i, dict)}
        return {str(i) for i in items if i}

    laws_a = _to_set(analysis_a, "applicable_laws", "section")
    laws_b = _to_set(analysis_b, "applicable_laws", "section")

    risks_a = _to_set(analysis_a, "risk_flags")
    risks_b = _to_set(analysis_b, "risk_flags")

    insights_a = _to_set(analysis_a, "key_insights")
    insights_b = _to_set(analysis_b, "key_insights")

    nlp_a = analysis_a.get("nlp_meta", {})
    nlp_b = analysis_b.get("nlp_meta", {})

    parties_a = set(nlp_a.get("entities", {}).get("PERSON", []))
    parties_b = set(nlp_b.get("entities", {}).get("PERSON", []))

    acts_a = set(nlp_a.get("act_sections", []))
    acts_b = set(nlp_b.get("act_sections", []))

    return {
        "laws": {
            "added": list(laws_b - laws_a),
            "removed": list(laws_a - laws_b),
            "unchanged": list(laws_a & laws_b),
        },
        "acts_cited": {
            "added": list(acts_b - acts_a),
            "removed": list(acts_a - acts_b),
        },
        "parties": {
            "added": list(parties_b - parties_a),
            "removed": list(parties_a - parties_b),
            "unchanged": list(parties_a & parties_b),
        },
        "risk_flags": {
            "new_in_b": list(risks_b - risks_a),
            "resolved_in_b": list(risks_a - risks_b),
        },
        "insights": {
            "new_in_b": list(insights_b - insights_a),
            "dropped_in_b": list(insights_a - insights_b),
        },
    }


# ── Case progress score ────────────────────────────────────────────────────────

def compute_case_progress_score(docs: List) -> Dict:
    """
    Heuristic 0-100 score indicating how far along a case is based on
    document types present and key outcome signals in LLM analyses.

    Scoring logic:
    - FIR present: +10
    - Chargesheet: +15
    - Bail order: +10
    - Petition/writ: +10
    - Judgment present: +30
    - Conviction/acquittal signals: +25
    Capped at 100.
    """
    score = 0
    stage_flags = {
        "has_fir": False,
        "has_chargesheet": False,
        "has_bail_order": False,
        "has_petition": False,
        "has_judgment": False,
        "has_final_order": False,
    }

    doc_types_seen = {d.doc_type.lower() for d in docs}
    all_summaries = " ".join(
        (d.analysis or {}).get("case_summary", "") for d in docs
    ).lower()

    if "fir" in doc_types_seen:
        score += 10; stage_flags["has_fir"] = True
    if "chargesheet" in doc_types_seen:
        score += 15; stage_flags["has_chargesheet"] = True
    if "bail" in doc_types_seen or "bail order" in doc_types_seen:
        score += 10; stage_flags["has_bail_order"] = True
    if any(t in doc_types_seen for t in ["petition", "writ", "legal notice"]):
        score += 10; stage_flags["has_petition"] = True
    if "judgment" in doc_types_seen:
        score += 30; stage_flags["has_judgment"] = True
    if any(kw in all_summaries for kw in ["convicted", "acquitted", "dismissed", "disposed"]):
        score += 25; stage_flags["has_final_order"] = True

    score = min(score, 100)

    stage_label = "Pre-trial"
    if score >= 80:
        stage_label = "Concluded"
    elif score >= 60:
        stage_label = "Judgment stage"
    elif score >= 40:
        stage_label = "Trial in progress"
    elif score >= 20:
        stage_label = "Charges framed"

    return {
        "score": score,
        "stage": stage_label,
        "stage_flags": stage_flags,
        "total_documents": len(docs),
        "doc_types": list(doc_types_seen),
    }


# ── Full stats object ──────────────────────────────────────────────────────────

def get_case_statistics(docs: List, all_analyses: List[Dict]) -> Dict:
    """
    Comprehensive statistics object for the analytics dashboard tab.
    Combines all analytics functions into one payload.
    """
    all_nlp_meta = [a.get("nlp_meta", {}) for a in all_analyses]

    return {
        "citation_frequency": compute_citation_frequency(all_nlp_meta),
        "entity_timeline": build_entity_timeline(docs),
        "law_graph": build_law_graph(all_nlp_meta),
        "progress": compute_case_progress_score(docs),
        "risk_summary": _aggregate_risks(all_analyses),
        "insight_summary": _aggregate_insights(all_analyses, docs),
        "outcome_signals": _extract_outcome_signals(all_analyses),
    }


def _aggregate_risks(all_analyses: List[Dict]) -> Dict:
    all_risks = []
    for a in all_analyses:
        all_risks.extend(a.get("risk_flags", []))
    freq = Counter(all_risks)
    return {
        "all_risks": list(dict.fromkeys(all_risks)),  # unique, order-preserved
        "most_frequent": freq.most_common(5),
        "total_unique": len(set(all_risks)),
    }


def _aggregate_insights(all_analyses: List[Dict], docs: List) -> List[Dict]:
    result = []
    for i, a in enumerate(all_analyses):
        filename = docs[i].filename if i < len(docs) else "Unknown"
        for insight in a.get("key_insights", []):
            result.append({
                "insight": insight,
                "source": filename,
                "date": docs[i].uploaded_at.strftime("%Y-%m-%d") if i < len(docs) else "",
            })
    return result


def _extract_outcome_signals(all_analyses: List[Dict]) -> List[str]:
    signals = []
    kw_map = {
        "convicted": "Conviction signal found",
        "acquitted": "Acquittal signal found",
        "bail granted": "Bail granted",
        "bail rejected": "Bail rejected",
        "dismissed": "Case dismissed",
        "disposed": "Case disposed",
        "appeal allowed": "Appeal allowed",
        "appeal dismissed": "Appeal dismissed",
    }
    combined = " ".join(
        a.get("case_summary", "") + " " + a.get("outcome_likelihood", "")
        for a in all_analyses
    ).lower()
    for kw, label in kw_map.items():
        if kw in combined:
            signals.append(label)
    return list(dict.fromkeys(signals))