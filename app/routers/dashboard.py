"""
Router: /dashboard
Serves pre-computed dashboard data to the Streamlit frontend.

  GET /dashboard/summary              — User-level summary (all cases)
  GET /dashboard/{case_id}            — Full case dashboard
  GET /dashboard/{case_id}/timeline   — Chronological doc timeline
  GET /dashboard/{case_id}/laws       — Law/statute breakdown with graph data
  GET /dashboard/{case_id}/followup   — Latest follow-up brief
  GET /dashboard/{case_id}/export     — Export full case report as JSON
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
import json
from datetime import datetime, timedelta

from app.models.db import get_db, Document, Case, User
from app.utils.auth import get_current_user
from app.services.analytics import (
    compute_citation_frequency,
    build_entity_timeline,
    build_law_graph,
    compute_case_progress_score,
)
from app.services.llm_reasoning import generate_case_dashboard
from app.services.translation import translate_text

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ── User-level summary ─────────────────────────────────────────────────────────

@router.get("/summary", summary="User-level summary across all cases")
async def user_summary(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    High-level stats for the user's landing page:
    - Total cases and documents
    - Recent activity
    - Cases needing attention (new docs, pending follow-ups)
    """
    # Count cases
    cases_result = await db.execute(
        select(Case).where(Case.user_id == user.id)
    )
    cases = cases_result.scalars().all()

    # Count docs and get recent ones
    docs_result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.uploaded_at.desc())
        .limit(10)
    )
    recent_docs = docs_result.scalars().all()

    # Aggregate doc counts per case
    case_summaries = []
    for case in cases:
        doc_count_result = await db.execute(
            select(func.count(Document.id)).where(Document.case_id == case.id)
        )
        doc_count = doc_count_result.scalar()

        # Last upload date
        last_doc_result = await db.execute(
            select(Document.uploaded_at)
            .where(Document.case_id == case.id)
            .order_by(Document.uploaded_at.desc())
            .limit(1)
        )
        last_upload = last_doc_result.scalar()

        case_summaries.append({
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "created_at": case.created_at.isoformat(),
            "document_count": doc_count,
            "last_activity": last_upload.isoformat() if last_upload else None,
            "days_since_activity": (
                (datetime.utcnow() - last_upload).days if last_upload else None
            ),
        })

    # Sort by last activity
    case_summaries.sort(
        key=lambda x: x["last_activity"] or "", reverse=True
    )

    return {
        "user": user.username,
        "total_cases": len(cases),
        "total_documents": len(recent_docs),
        "cases": case_summaries,
        "recent_uploads": [
            {
                "doc_id": d.id,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "case_id": d.case_id,
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in recent_docs
        ],
    }


# ── Full case dashboard ────────────────────────────────────────────────────────

@router.get("/{case_id}", summary="Full case dashboard data")
async def case_dashboard(
    case_id: str,
    language: Optional[str] = Query(
        None,
        description="Output language: 'hi' (Hindi), 'bn' (Bengali), 'ta' (Tamil), 'te' (Telugu). Default: English."
    ),
    regenerate: bool = Query(False, description="Force regeneration of LLM dashboard"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Full pre-computed dashboard for a case:
    - Cumulative summary
    - Consolidated laws
    - Case trajectory + status
    - Follow-up brief
    - Future scope
    - Timeline
    - Analytics data (chart-ready)
    
    Set `language` to get output translated via InLegalTrans.
    """
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found or access denied")

    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = docs_result.scalars().all()

    if not docs:
        raise HTTPException(404, "No documents in this case yet")

    all_analyses = [d.analysis for d in docs if d.analysis]
    all_nlp_meta = [a.get("nlp_meta", {}) for a in all_analyses]

    # Build timeline
    timeline = [
        {
            "date": d.uploaded_at.strftime("%Y-%m-%d"),
            "datetime": d.uploaded_at.isoformat(),
            "doc_id": d.id,
            "filename": d.filename,
            "doc_type": d.doc_type,
            "summary": (d.analysis or {}).get("case_summary", "")[:200],
        }
        for d in docs
    ]

    # Analytics
    citation_freq = compute_citation_frequency(all_nlp_meta)
    entity_timeline = build_entity_timeline(docs)
    law_graph = build_law_graph(all_nlp_meta)
    progress_score = compute_case_progress_score(docs)

    # LLM dashboard (regenerate or use latest doc's cached result)
    llm_dash = generate_case_dashboard(case.title, all_analyses, timeline)

    # Chart-ready law data (for Plotly in Streamlit)
    chart_laws = _build_chart_data(citation_freq)

    # Translate if requested
    if language and language != "en":
        llm_dash = await _translate_dashboard(llm_dash, language)

    return {
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "created_at": case.created_at.isoformat(),
        },
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "uploaded_at": d.uploaded_at.isoformat(),
                "analysis": d.analysis,   # ← ADD THIS
            }
            for d in docs
        ],
        "timeline": timeline,
        "llm_dashboard": llm_dash,
        # "analytics": {
        #     "citation_frequency": citation_freq,
        #     "entity_timeline": entity_timeline,
        #     "law_graph": law_graph,
        #     "progress_score": progress_score,
        #     "chart_data": chart_laws,
        #     "doc_type_counts": _count_types(docs),
        # },
        # In case_dashboard(), change this in the return dict:
        "analytics": {
            "citation_frequency": citation_freq,
            "entity_timeline":    entity_timeline,
            "law_graph":          law_graph,
            "progress":           progress_score,   # ← was "progress_score", frontend reads "progress"
            "chart_data":         chart_laws,
            "doc_type_counts":    _count_types(docs),
        },
        "language": language or "en",
    }


# ── Timeline endpoint ──────────────────────────────────────────────────────────

@router.get("/{case_id}/timeline", summary="Chronological document timeline")
async def case_timeline(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the full chronological timeline of documents and events for a case.
    Each entry includes date, document type, key summary, and laws cited that day.
    """
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    if not case_result.scalar_one_or_none():
        raise HTTPException(404, "Case not found")

    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = docs_result.scalars().all()

    events = []
    for i, doc in enumerate(docs):
        analysis = doc.analysis or {}
        nlp_meta = analysis.get("nlp_meta", {})

        events.append({
            "index": i + 1,
            "date": doc.uploaded_at.strftime("%Y-%m-%d"),
            "doc_id": doc.id,
            "filename": doc.filename,
            "doc_type": doc.doc_type,
            "summary": analysis.get("case_summary", "No summary available"),
            "key_insights": analysis.get("key_insights", []),
            "laws_cited": nlp_meta.get("act_sections", []),
            "parties": nlp_meta.get("entities", {}).get("PERSON", []),
            "follow_up": analysis.get("follow_up"),
            "outcome_likelihood": analysis.get("outcome_likelihood"),
        })

    return {"case_id": case_id, "total_events": len(events), "events": events}


# ── Laws breakdown ─────────────────────────────────────────────────────────────

@router.get("/{case_id}/laws", summary="Law and statute breakdown")
async def case_laws(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns:
    - Frequency of every act/section cited across case documents
    - Network graph data (nodes = acts, edges = co-citation)
    - Suggested but not yet cited laws
    - Constitution article references
    """
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    if not case_result.scalar_one_or_none():
        raise HTTPException(404, "Case not found")

    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
    )
    docs = docs_result.scalars().all()

    all_nlp_meta = [
        (d.analysis or {}).get("nlp_meta", {}) for d in docs
    ]
    all_analyses = [d.analysis or {} for d in docs]

    citation_freq = compute_citation_frequency(all_nlp_meta)
    law_graph = build_law_graph(all_nlp_meta)

    # Aggregate all suggested laws from LLM
    suggested_laws = []
    seen = set()
    for a in all_analyses:
        for law in a.get("suggested_laws", []):
            key = f"{law.get('act')}_{law.get('section')}"
            if key not in seen:
                seen.add(key)
                suggested_laws.append(law)

    return {
        "case_id": case_id,
        "citation_frequency": citation_freq,
        "law_graph": law_graph,
        "suggested_laws": suggested_laws,
        "total_unique_citations": len(citation_freq),
    }


# ── Follow-up endpoint ─────────────────────────────────────────────────────────

@router.get("/{case_id}/followup", summary="Latest follow-up brief for a case")
async def case_followup(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the follow-up brief showing what changed with the most recent document
    and what actions are recommended next.
    Also returns a full chronological diff history across all documents.
    """
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    if not case_result.scalar_one_or_none():
        raise HTTPException(404, "Case not found")

    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = docs_result.scalars().all()

    if not docs:
        return {"follow_up": "No documents uploaded yet", "history": []}

    latest = docs[-1]
    latest_analysis = latest.analysis or {}

    # Follow-up history from all docs
    history = []
    for doc in docs:
        a = doc.analysis or {}
        fu = a.get("follow_up")
        if fu and fu != "null":
            history.append({
                "date": doc.uploaded_at.strftime("%Y-%m-%d"),
                "filename": doc.filename,
                "follow_up": fu,
                "recommended_actions": a.get("recommended_actions", []),
            })

    return {
        "case_id": case_id,
        "latest_document": {
            "filename": latest.filename,
            "uploaded_at": latest.uploaded_at.isoformat(),
            "doc_type": latest.doc_type,
        },
        "follow_up_brief": latest_analysis.get("follow_up", "No follow-up generated"),
        "recommended_actions": latest_analysis.get("recommended_actions", []),
        "case_status": (latest.analysis or {}).get("case_status", "Unknown"),
        "risk_flags": latest_analysis.get("risk_flags", []),
        "history": history,
    }


# ── Export ─────────────────────────────────────────────────────────────────────

@router.get("/{case_id}/export", summary="Export full case report as JSON")
async def export_case(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a comprehensive case report with all documents, analyses,
    timelines, and recommendations. Suitable for saving as a case file.
    """
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    case = case_result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found")

    docs_result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = docs_result.scalars().all()

    return {
        "export_metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "exported_by": user.username,
            "system": "Judiciary AI v1.0",
        },
        "case": {
            "id": case.id,
            "title": case.title,
            "description": case.description,
            "created_at": case.created_at.isoformat(),
        },
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "doc_type": d.doc_type,
                "uploaded_at": d.uploaded_at.isoformat(),
                "analysis": d.analysis,
            }
            for d in docs
        ],
    }


# ── Internal helpers ────────────────────────────────────────────────────────────

def _build_chart_data(citation_freq: list) -> dict:
    """Format citation frequency for Plotly charts in Streamlit."""
    return {
        "acts": [c["act"] for c in citation_freq],
        "sections": [c.get("section", "") for c in citation_freq],
        "frequencies": [c["count"] for c in citation_freq],
        "labels": [
            f"{c['act']} §{c.get('section', '')}" for c in citation_freq
        ],
    }


def _count_types(docs: list) -> dict:
    counts = {}
    for d in docs:
        counts[d.doc_type] = counts.get(d.doc_type, 0) + 1
    return counts


async def _translate_dashboard(dash: dict, lang: str) -> dict:
    """Translate key text fields in the dashboard via InLegalTrans."""
    text_fields = [
        "cumulative_summary", "case_trajectory", "follow_up_brief", "risk_assessment"
    ]
    for field in text_fields:
        if field in dash and dash[field]:
            dash[field] = await translate_text(dash[field], target_lang=lang)

    # Translate list fields
    for list_field in ["future_scope", "recommended_actions"]:
        if list_field in dash and isinstance(dash[list_field], list):
            translated = []
            for item in dash[list_field]:
                translated.append(await translate_text(item, target_lang=lang))
            dash[list_field] = translated

    return dash