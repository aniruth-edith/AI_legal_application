# """
# Router: /analysis
# On-demand analysis endpoints — re-analyse docs, semantic search,
# compare documents, generate per-doc insights without re-uploading.

#   POST /analysis/{doc_id}/reanalyse        — Re-run LLM on existing doc
#   POST /analysis/{case_id}/search          — Semantic search within a case
#   POST /analysis/compare                   — Compare two documents
#   GET  /analysis/{doc_id}                  — Fetch stored analysis for a doc
#   GET  /analysis/{case_id}/insights        — Aggregate insights across all case docs
#   POST /analysis/{case_id}/ask             — Ask a free-form question about a case
# """

# from fastapi import APIRouter, Depends, HTTPException, Body
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from typing import List, Optional
# import json

# from app.models.db import get_db, Document, Case
# from app.models.schemas import AnalysisResult
# from app.utils.auth import get_current_user
# from app.services.nlp_pipeline import run_nlp_pipeline
# from app.services.embeddings import embed_query, embed_text
# from app.services.chroma_store import query_similar, get_all_case_docs
# from app.services.llm_reasoning import analyze_document, ask_case_question
# from app.services.analytics import (
#     compute_citation_frequency,
#     build_entity_timeline,
#     compute_doc_diff,
# )

# router = APIRouter(prefix="/analysis", tags=["Analysis"])


# # ── Helper ─────────────────────────────────────────────────────────────────────

# async def _get_doc_for_user(doc_id: str, user_id: str, db: AsyncSession) -> Document:
#     result = await db.execute(
#         select(Document).where(Document.id == doc_id, Document.user_id == user_id)
#     )
#     doc = result.scalar_one_or_none()
#     if not doc:
#         raise HTTPException(404, "Document not found or access denied")
#     return doc


# async def _get_case_for_user(case_id: str, user_id: str, db: AsyncSession) -> Case:
#     result = await db.execute(
#         select(Case).where(Case.id == case_id, Case.user_id == user_id)
#     )
#     case = result.scalar_one_or_none()
#     if not case:
#         raise HTTPException(404, "Case not found or access denied")
#     return case


# # ── Endpoints ──────────────────────────────────────────────────────────────────


# @router.get("/{doc_id}", summary="Get stored analysis for a document")
# async def get_analysis(
#     doc_id: str,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Return the full stored LLM analysis for a previously uploaded document."""
#     doc = await _get_doc_for_user(doc_id, user.id, db)
#     if not doc.analysis:
#         raise HTTPException(404, "No analysis found. Try re-analysing.")
#     return {
#         "doc_id": doc.id,
#         "filename": doc.filename,
#         "doc_type": doc.doc_type,
#         "uploaded_at": doc.uploaded_at,
#         "analysis": doc.analysis,
#     }


# @router.post("/{doc_id}/reanalyse", response_model=AnalysisResult, summary="Re-run analysis on a doc")
# async def reanalyse_document(
#     doc_id: str,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Re-run the full NLP + LLM pipeline on an existing document.
#     Useful after model updates or when you want fresh insights.
#     """
#     doc = await _get_doc_for_user(doc_id, user.id, db)

#     if not doc.raw_text:
#         raise HTTPException(422, "Raw text not available for re-analysis")

#     # Re-run NLP
#     nlp_out = run_nlp_pipeline(doc.raw_text)

#     # Re-embed and search similar
#     query_emb = embed_query(nlp_out["extractive_summary"])
#     similar = query_similar(user.id, query_emb, case_id=doc.case_id, n_results=3)

#     # Previous docs context
#     prev_result = await db.execute(
#         select(Document)
#         .where(
#             Document.case_id == doc.case_id,
#             Document.user_id == user.id,
#             Document.id != doc_id,
#         )
#         .order_by(Document.uploaded_at.desc())
#         .limit(3)
#     )
#     prev_docs = prev_result.scalars().all()
#     prev_summary = None
#     if prev_docs:
#         summaries = [
#             f"[{d.filename}] {d.analysis.get('case_summary', '')}"
#             for d in reversed(prev_docs)
#             if d.analysis
#         ]
#         prev_summary = "\n".join(summaries)

#     # Fresh LLM analysis
#     llm_result = analyze_document(nlp_out, similar, prev_summary)

#     # Update stored analysis
#     doc.analysis = {
#         **llm_result,
#         "nlp_meta": {
#             "doc_type": nlp_out["doc_type"],
#             "entities": nlp_out["entities"],
#             "act_sections": [a["match"] for a in nlp_out["act_sections"]],
#         },
#         "reanalysed_at": __import__("datetime").datetime.utcnow().isoformat(),
#     }
#     await db.commit()

#     return AnalysisResult(
#         doc_id=doc.id,
#         case_id=doc.case_id,
#         extracted=nlp_out,
#         summary=llm_result.get("case_summary", ""),
#         classification=nlp_out["doc_type"],
#         laws_suggested=llm_result.get("suggested_laws", []),
#         future_scope=llm_result.get("future_scope", []),
#         follow_up=llm_result.get("follow_up"),
#     )


# # @router.post("/{case_id}/search", summary="Semantic search within a case")
# # async def semantic_search(
# #     case_id: str,
# #     query: str = Body(..., embed=True, description="Natural language query"),
# #     n_results: int = Body(5, embed=True, ge=1, le=20),
# #     user=Depends(get_current_user),
# #     db: AsyncSession = Depends(get_db),
# # ):
# #     """
# #     Search across all documents in a case using semantic similarity.
# #     Returns the most relevant document chunks with scores.
# #     Example query: 'bail application grounds under section 437'
# #     """
# #     await _get_case_for_user(case_id, user.id, db)

# #     query_emb = embed_query(query)
# #     results = query_similar(user.id, query_emb, case_id=case_id, n_results=n_results)

# #     if not results:
# #         return {"query": query, "results": [], "message": "No matching documents found"}

# #     return {
# #         "query": query,
# #         "results": [
# #             {
# #                 "score": round(r["score"], 4),
# #                 "filename": r["metadata"].get("filename", "unknown"),
# #                 "doc_type": r["metadata"].get("doc_type", "unknown"),
# #                 "excerpt": r["text"][:500],
# #                 "uploaded_at": r["metadata"].get("uploaded_at"),
# #             }
# #             for r in results
# #         ],
# #     }

# # @router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
# # async def ask_about_case(
# #     case_id: str,
# #     question: str = Body(..., embed=True, description="Legal question about this case"),
# #     user=Depends(get_current_user),
# #     db: AsyncSession = Depends(get_db),
# # ):
# #     await _get_case_for_user(case_id, user.id, db)

# #     query_emb = embed_query(question)
# #     relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

# #     if not relevant_docs:
# #         raise HTTPException(404, "No relevant documents found for this question")

# #     result = ask_case_question(question=question, context_docs=relevant_docs)

# #     return {
# #         "question": question,
# #         **result,  # ✅ spreads answer, reasoning, relevant_laws, confidence, caveats at top level
# #         "sources": [
# #             {
# #                 "filename": d["metadata"].get("filename", "unknown"),
# #                 "score": round(d["score"], 3),
# #                 "excerpt": d["text"][:200],
# #             }
# #             for d in relevant_docs
# #         ],
# #     }

# @router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
# async def ask_about_case(
#     case_id: str,
#     question: str = Body(..., embed=True, description="Legal question about this case"),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     await _get_case_for_user(case_id, user.id, db)

#     # Fast-path: aggregate/counting questions answered from DB, not RAG
#     if _is_aggregate_question(question):
#         result = await _answer_aggregate_question(question, case_id, user.id, db)
#         return {"question": question, **result, "sources": []}

#     # Otherwise, normal semantic-search + LLM path
#     query_emb = embed_query(question)
#     relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

#     if not relevant_docs:
#         raise HTTPException(404, "No relevant documents found for this question")

#     result = ask_case_question(question=question, context_docs=relevant_docs)

#     return {
#         "question": question,
#         **result,
#         "sources": [
#             {
#                 "filename": d["metadata"].get("filename", "unknown"),
#                 "score": round(d["score"], 3),
#                 "excerpt": d["text"][:200],
#             }
#             for d in relevant_docs
#         ],
#     }   


# @router.post("/compare", summary="Compare two documents side by side")
# async def compare_documents(
#     doc_id_a: str = Body(..., embed=True),
#     doc_id_b: str = Body(..., embed=True),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Compare two documents analytically.
#     Highlights differences in parties, laws cited, arguments, and outcomes.
#     Useful for tracking how a case evolved between hearings.
#     """
#     doc_a = await _get_doc_for_user(doc_id_a, user.id, db)
#     doc_b = await _get_doc_for_user(doc_id_b, user.id, db)

#     if not doc_a.analysis or not doc_b.analysis:
#         raise HTTPException(422, "Both documents must have completed analysis")

#     # Structural diff
#     diff = compute_doc_diff(doc_a.analysis, doc_b.analysis)

#     # LLM-powered narrative comparison
#     comparison = ask_case_question(
#         question=f"""Compare these two legal documents and explain:
# 1. What changed between them (parties, claims, laws, arguments)?
# 2. How did the legal position evolve?
# 3. What new laws or sections appeared or disappeared?

# Document A ({doc_a.filename}):
# {json.dumps(doc_a.analysis.get('case_summary', ''), indent=1)}

# Document B ({doc_b.filename}):
# {json.dumps(doc_b.analysis.get('case_summary', ''), indent=1)}

# Respond as a JSON object with keys: narrative_comparison, new_laws_in_b, removed_laws_in_b, 
# position_change, recommendation.""",
#         context_docs=[],
#     )

#     return {
#         "doc_a": {"id": doc_id_a, "filename": doc_a.filename, "doc_type": doc_a.doc_type},
#         "doc_b": {"id": doc_id_b, "filename": doc_b.filename, "doc_type": doc_b.doc_type},
#         "structural_diff": diff,
#         "llm_comparison": comparison,
#     }


# @router.get("/{case_id}/insights", summary="Aggregate insights across all docs in a case")
# async def case_insights(
#     case_id: str,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Returns aggregated analytics across all documents in a case:
#     - Most cited acts/sections and their frequencies
#     - Entity timeline (who appeared in which document)
#     - Risk flags across all documents
#     - Consolidated key insights
#     """
#     await _get_case_for_user(case_id, user.id, db)

#     result = await db.execute(
#         select(Document)
#         .where(Document.case_id == case_id, Document.user_id == user.id)
#         .order_by(Document.uploaded_at.asc())
#     )
#     docs = result.scalars().all()

#     if not docs:
#         raise HTTPException(404, "No documents found in this case")

#     all_analyses = [d.analysis for d in docs if d.analysis]
#     all_nlp_meta = [a.get("nlp_meta", {}) for a in all_analyses]

#     # Citation frequency
#     citation_freq = compute_citation_frequency(all_nlp_meta)

#     # Entity timeline
#     entity_timeline = build_entity_timeline(docs)

#     # Consolidated risk flags
#     all_risks = []
#     for a in all_analyses:
#         flags = a.get("risk_flags", [])
#         all_risks.extend(flags)
#     unique_risks = list(dict.fromkeys(all_risks))  # deduplicate, preserve order

#     # Key insights from all docs
#     all_insights = []
#     for i, a in enumerate(all_analyses):
#         for insight in a.get("key_insights", []):
#             all_insights.append({
#                 "document": docs[i].filename,
#                 "insight": insight,
#                 "date": str(docs[i].uploaded_at.date()),
#             })

#     return {
#         "case_id": case_id,
#         "total_documents": len(docs),
#         "citation_frequency": citation_freq,
#         "entity_timeline": entity_timeline,
#         "all_risk_flags": unique_risks,
#         "all_key_insights": all_insights,
#         "doc_type_breakdown": _count_doc_types(docs),
#     }


# @router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
# async def ask_about_case(
#     case_id: str,
#     question: str = Body(..., embed=True, description="Legal question about this case"),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Ask any question about the case — the system retrieves relevant
#     document chunks using semantic search and answers using the LLM.
    
#     Example: 'What are the strongest grounds for bail in this case?'
#     Example: 'Which sections of IPC are most relevant here?'
#     Example: 'Has the court addressed the alibi argument?'
#     """
#     await _get_case_for_user(case_id, user.id, db)

#     # Semantic search for relevant context
#     query_emb = embed_query(question)
#     relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

#     if not relevant_docs:
#         raise HTTPException(404, "No relevant documents found for this question")

#     answer = ask_case_question(question=question, context_docs=relevant_docs)

#     return {
#         "question": question,
#         "answer": answer,
#         "sources": [
#             {
#                 "filename": d["metadata"].get("filename", "unknown"),
#                 "score": round(d["score"], 3),
#                 "excerpt": d["text"][:200],
#             }
#             for d in relevant_docs
#         ],
#     }

# from app.services.statute_identifier import identify_statutes, get_model_status

# @router.get("/statute-model/status", summary="Check LeSICiN model status")
# async def statute_model_status(user=Depends(get_current_user)):
#     """Check if the LeSICiN statute identification model is loaded."""
#     return get_model_status()


# @router.post("/{case_id}/statutes", summary="Run statute identification on a document")
# async def run_statute_identification(
#     case_id: str,
#     doc_id: str = Body(..., embed=True),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Re-run LeSICiN statute identification on an existing document.
#     Returns raw statute predictions with confidence scores.
#     """
#     doc = await _get_doc_for_user(doc_id, user.id, db)
#     if not doc.raw_text:
#         raise HTTPException(422, "Raw text not available")

#     result = await identify_statutes(doc.raw_text)

#     # Update stored analysis with new statute data
#     if doc.analysis and result.model_available:
#         doc.analysis["identified_statutes"] = result.statutes
#         doc.analysis["statute_raw_predictions"] = result.raw_predictions
#         await db.commit()

#     return {
#         "doc_id":     doc_id,
#         "statutes":   result.statutes,
#         "count":      len(result.statutes),
#         "model_available": result.model_available,
#         "error":      result.error,
#     }


# # ── Internal helpers ────────────────────────────────────────────────────────────

# def _count_doc_types(docs: list) -> dict:
#     counts = {}
#     for d in docs:
#         counts[d.doc_type] = counts.get(d.doc_type, 0) + 1
#     return counts

# import re
# from app.services.analytics import compute_case_progress_score

# # ── Aggregate question detection ────────────────────────────────────────────

# _AGGREGATE_PATTERNS = [
#     r"\bhow many\b", r"\bnumber of\b", r"\btotal\b.*\bdocument", 
#     r"\blist all\b", r"\ball documents\b", r"\bcount\b",
#     r"\bwhich documents\b", r"\bwhat documents\b",
# ]

# def _is_aggregate_question(question: str) -> bool:
#     q = question.lower()
#     return any(re.search(p, q) for p in _AGGREGATE_PATTERNS)


# async def _answer_aggregate_question(question: str, case_id: str, user_id: str, db) -> dict:
#     """Answer counting/listing questions directly from the DB — no RAG, no LLM guesswork."""
#     result = await db.execute(
#         select(Document).where(Document.case_id == case_id, Document.user_id == user_id)
#         .order_by(Document.uploaded_at.asc())
#     )
#     docs = result.scalars().all()

#     doc_list = [
#         {"filename": d.filename, "doc_type": d.doc_type, "uploaded_at": d.uploaded_at.isoformat()}
#         for d in docs
#     ]

#     return {
#         "answer": f"There are {len(docs)} documents in this case: " +
#                   ", ".join(f"{d['filename']} ({d['doc_type']})" for d in doc_list),
#         "reasoning": "Answered directly from the case's document records (not via semantic search, which only retrieves a relevance-ranked sample).",
#         "relevant_laws": [],
#         "confidence": "high",
#         "caveats": "",
#         "_doc_list": doc_list,  # optional, frontend can ignore or use
#     }


"""
Router: /analysis
On-demand analysis endpoints — re-analyse docs, semantic search,
compare documents, generate per-doc insights without re-uploading.

  POST /analysis/{doc_id}/reanalyse        — Re-run LLM on existing doc
  POST /analysis/{case_id}/search          — Semantic search within a case
  POST /analysis/compare                   — Compare two documents
  GET  /analysis/{doc_id}                  — Fetch stored analysis for a doc
  GET  /analysis/{case_id}/insights        — Aggregate insights across all case docs
  POST /analysis/{case_id}/ask             — Ask a free-form question about a case
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import json

from app.models.db import get_db, Document, Case
from app.models.schemas import AnalysisResult
from app.utils.auth import get_current_user
from app.services.nlp_pipeline import run_nlp_pipeline
from app.services.embeddings import embed_query, embed_text
from app.services.chroma_store import query_similar, get_all_case_docs
from app.services.llm_reasoning import analyze_document, ask_case_question
from app.services.analytics import (
    compute_citation_frequency,
    build_entity_timeline,
    compute_doc_diff,
)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ── Helper ─────────────────────────────────────────────────────────────────────

async def _get_doc_for_user(doc_id: str, user_id: str, db: AsyncSession) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found or access denied")
    return doc


async def _get_case_for_user(case_id: str, user_id: str, db: AsyncSession) -> Case:
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found or access denied")
    return case


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.get("/{doc_id}", summary="Get stored analysis for a document")
async def get_analysis(
    doc_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the full stored LLM analysis for a previously uploaded document."""
    doc = await _get_doc_for_user(doc_id, user.id, db)
    if not doc.analysis:
        raise HTTPException(404, "No analysis found. Try re-analysing.")
    return {
        "doc_id": doc.id,
        "filename": doc.filename,
        "doc_type": doc.doc_type,
        "uploaded_at": doc.uploaded_at,
        "analysis": doc.analysis,
    }


@router.post("/{doc_id}/reanalyse", response_model=AnalysisResult, summary="Re-run analysis on a doc")
async def reanalyse_document(
    doc_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run the full NLP + LLM pipeline on an existing document.
    Useful after model updates or when you want fresh insights.
    """
    doc = await _get_doc_for_user(doc_id, user.id, db)

    if not doc.raw_text:
        raise HTTPException(422, "Raw text not available for re-analysis")

    # Re-run NLP
    nlp_out = await run_nlp_pipeline(doc.raw_text)

    # Re-embed and search similar
    query_emb = embed_query(nlp_out["extractive_summary"])
    similar = query_similar(user.id, query_emb, case_id=doc.case_id, n_results=3)

    # Previous docs context
    prev_result = await db.execute(
        select(Document)
        .where(
            Document.case_id == doc.case_id,
            Document.user_id == user.id,
            Document.id != doc_id,
        )
        .order_by(Document.uploaded_at.desc())
        .limit(3)
    )
    prev_docs = prev_result.scalars().all()
    prev_summary = None
    if prev_docs:
        summaries = [
            f"[{d.filename}] {d.analysis.get('case_summary', '')}"
            for d in reversed(prev_docs)
            if d.analysis
        ]
        prev_summary = "\n".join(summaries)

    # Fresh LLM analysis
    llm_result = analyze_document(nlp_out, similar, prev_summary)

    # Update stored analysis
    doc.analysis = {
        **llm_result,
        "nlp_meta": {
            "doc_type": nlp_out["doc_type"],
            "entities": nlp_out["entities"],
            "act_sections": [a["match"] for a in nlp_out["act_sections"]],
        },
        "identified_statutes": nlp_out.get("identified_statutes", []),
        "statute_model_available": nlp_out.get("statute_model_available", False),
        "statute_raw_predictions": nlp_out.get("statute_raw_predictions", []),
        "reanalysed_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    await db.commit()

    return AnalysisResult(
        doc_id=doc.id,
        case_id=doc.case_id,
        extracted=nlp_out,
        summary=llm_result.get("case_summary", ""),
        classification=nlp_out["doc_type"],
        laws_suggested=llm_result.get("suggested_laws", []),
        future_scope=llm_result.get("future_scope", []),
        follow_up=llm_result.get("follow_up"),
        identified_statutes=nlp_out.get("identified_statutes", []),
        statute_model_available=nlp_out.get("statute_model_available", False),
    )


# @router.post("/{case_id}/search", summary="Semantic search within a case")
# async def semantic_search(
#     case_id: str,
#     query: str = Body(..., embed=True, description="Natural language query"),
#     n_results: int = Body(5, embed=True, ge=1, le=20),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Search across all documents in a case using semantic similarity.
#     Returns the most relevant document chunks with scores.
#     Example query: 'bail application grounds under section 437'
#     """
#     await _get_case_for_user(case_id, user.id, db)

#     query_emb = embed_query(query)
#     results = query_similar(user.id, query_emb, case_id=case_id, n_results=n_results)

#     if not results:
#         return {"query": query, "results": [], "message": "No matching documents found"}

#     return {
#         "query": query,
#         "results": [
#             {
#                 "score": round(r["score"], 4),
#                 "filename": r["metadata"].get("filename", "unknown"),
#                 "doc_type": r["metadata"].get("doc_type", "unknown"),
#                 "excerpt": r["text"][:500],
#                 "uploaded_at": r["metadata"].get("uploaded_at"),
#             }
#             for r in results
#         ],
#     }

# @router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
# async def ask_about_case(
#     case_id: str,
#     question: str = Body(..., embed=True, description="Legal question about this case"),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     await _get_case_for_user(case_id, user.id, db)

#     query_emb = embed_query(question)
#     relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

#     if not relevant_docs:
#         raise HTTPException(404, "No relevant documents found for this question")

#     result = ask_case_question(question=question, context_docs=relevant_docs)

#     return {
#         "question": question,
#         **result,  # ✅ spreads answer, reasoning, relevant_laws, confidence, caveats at top level
#         "sources": [
#             {
#                 "filename": d["metadata"].get("filename", "unknown"),
#                 "score": round(d["score"], 3),
#                 "excerpt": d["text"][:200],
#             }
#             for d in relevant_docs
#         ],
#     }

@router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
async def ask_about_case(
    case_id: str,
    question: str = Body(..., embed=True, description="Legal question about this case"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_case_for_user(case_id, user.id, db)

    # Fast-path: aggregate/counting questions answered from DB, not RAG
    if _is_aggregate_question(question):
        result = await _answer_aggregate_question(question, case_id, user.id, db)
        return {"question": question, **result, "sources": []}

    # Otherwise, normal semantic-search + LLM path
    query_emb = embed_query(question)
    relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

    if not relevant_docs:
        raise HTTPException(404, "No relevant documents found for this question")

    result = ask_case_question(question=question, context_docs=relevant_docs)

    return {
        "question": question,
        **result,
        "sources": [
            {
                "filename": d["metadata"].get("filename", "unknown"),
                "score": round(d["score"], 3),
                "excerpt": d["text"][:200],
            }
            for d in relevant_docs
        ],
    }


@router.post("/compare", summary="Compare two documents side by side")
async def compare_documents(
    doc_id_a: str = Body(..., embed=True),
    doc_id_b: str = Body(..., embed=True),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare two documents analytically.
    Highlights differences in parties, laws cited, arguments, and outcomes.
    Useful for tracking how a case evolved between hearings.
    """
    doc_a = await _get_doc_for_user(doc_id_a, user.id, db)
    doc_b = await _get_doc_for_user(doc_id_b, user.id, db)

    if not doc_a.analysis or not doc_b.analysis:
        raise HTTPException(422, "Both documents must have completed analysis")

    # Structural diff
    diff = compute_doc_diff(doc_a.analysis, doc_b.analysis)

    # LLM-powered narrative comparison
    comparison = ask_case_question(
        question=f"""Compare these two legal documents and explain:
1. What changed between them (parties, claims, laws, arguments)?
2. How did the legal position evolve?
3. What new laws or sections appeared or disappeared?

Document A ({doc_a.filename}):
{json.dumps(doc_a.analysis.get('case_summary', ''), indent=1)}

Document B ({doc_b.filename}):
{json.dumps(doc_b.analysis.get('case_summary', ''), indent=1)}

Respond as a JSON object with keys: narrative_comparison, new_laws_in_b, removed_laws_in_b, 
position_change, recommendation.""",
        context_docs=[],
    )

    return {
        "doc_a": {"id": doc_id_a, "filename": doc_a.filename, "doc_type": doc_a.doc_type},
        "doc_b": {"id": doc_id_b, "filename": doc_b.filename, "doc_type": doc_b.doc_type},
        "structural_diff": diff,
        "llm_comparison": comparison,
    }


@router.get("/{case_id}/insights", summary="Aggregate insights across all docs in a case")
async def case_insights(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated analytics across all documents in a case:
    - Most cited acts/sections and their frequencies
    - Entity timeline (who appeared in which document)
    - Risk flags across all documents
    - Consolidated key insights
    """
    await _get_case_for_user(case_id, user.id, db)

    result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = result.scalars().all()

    if not docs:
        raise HTTPException(404, "No documents found in this case")

    all_analyses = [d.analysis for d in docs if d.analysis]
    all_nlp_meta = [a.get("nlp_meta", {}) for a in all_analyses]

    # Citation frequency
    citation_freq = compute_citation_frequency(all_nlp_meta)

    # Entity timeline
    entity_timeline = build_entity_timeline(docs)

    # Consolidated risk flags
    all_risks = []
    for a in all_analyses:
        flags = a.get("risk_flags", [])
        all_risks.extend(flags)
    unique_risks = list(dict.fromkeys(all_risks))  # deduplicate, preserve order

    # Key insights from all docs
    all_insights = []
    for i, a in enumerate(all_analyses):
        for insight in a.get("key_insights", []):
            all_insights.append({
                "document": docs[i].filename,
                "insight": insight,
                "date": str(docs[i].uploaded_at.date()),
            })

    return {
        "case_id": case_id,
        "total_documents": len(docs),
        "citation_frequency": citation_freq,
        "entity_timeline": entity_timeline,
        "all_risk_flags": unique_risks,
        "all_key_insights": all_insights,
        "doc_type_breakdown": _count_doc_types(docs),
    }


@router.post("/{case_id}/ask", summary="Ask a free-form question about a case")
async def ask_about_case(
    case_id: str,
    question: str = Body(..., embed=True, description="Legal question about this case"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Ask any question about the case — the system retrieves relevant
    document chunks using semantic search and answers using the LLM.
    
    Example: 'What are the strongest grounds for bail in this case?'
    Example: 'Which sections of IPC are most relevant here?'
    Example: 'Has the court addressed the alibi argument?'
    """
    await _get_case_for_user(case_id, user.id, db)

    # Semantic search for relevant context
    query_emb = embed_query(question)
    relevant_docs = query_similar(user.id, query_emb, case_id=case_id, n_results=5)

    if not relevant_docs:
        raise HTTPException(404, "No relevant documents found for this question")

    answer = ask_case_question(question=question, context_docs=relevant_docs)

    return {
        "question": question,
        "answer": answer,
        "sources": [
            {
                "filename": d["metadata"].get("filename", "unknown"),
                "score": round(d["score"], 3),
                "excerpt": d["text"][:200],
            }
            for d in relevant_docs
        ],
    }

from app.services.statute_identifier import identify_statutes, get_model_status

@router.get("/statute-model/status", summary="Check LeSICiN model status")
async def statute_model_status(user=Depends(get_current_user)):
    """Check if the LeSICiN statute identification model is loaded."""
    return get_model_status()


@router.post("/{case_id}/statutes", summary="Run statute identification on a document")
async def run_statute_identification(
    case_id: str,
    doc_id: str = Body(..., embed=True),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Re-run LeSICiN statute identification on an existing document.
    Returns raw statute predictions with confidence scores.
    """
    doc = await _get_doc_for_user(doc_id, user.id, db)
    if not doc.raw_text:
        raise HTTPException(422, "Raw text not available")

    result = await identify_statutes(doc.raw_text)

    # Update stored analysis with new statute data
    if doc.analysis and result.model_available:
        doc.analysis["identified_statutes"] = result.statutes
        doc.analysis["statute_raw_predictions"] = result.raw_predictions
        await db.commit()

    return {
        "doc_id":     doc_id,
        "statutes":   result.statutes,
        "count":      len(result.statutes),
        "model_available": result.model_available,
        "error":      result.error,
    }


# ── Internal helpers ────────────────────────────────────────────────────────────

def _count_doc_types(docs: list) -> dict:
    counts = {}
    for d in docs:
        counts[d.doc_type] = counts.get(d.doc_type, 0) + 1
    return counts

import re
from app.services.analytics import compute_case_progress_score

# ── Aggregate question detection ────────────────────────────────────────────

_AGGREGATE_PATTERNS = [
    r"\bhow many\b", r"\bnumber of\b", r"\btotal\b.*\bdocument", 
    r"\blist all\b", r"\ball documents\b", r"\bcount\b",
    r"\bwhich documents\b", r"\bwhat documents\b",
]

def _is_aggregate_question(question: str) -> bool:
    q = question.lower()
    return any(re.search(p, q) for p in _AGGREGATE_PATTERNS)


async def _answer_aggregate_question(question: str, case_id: str, user_id: str, db) -> dict:
    """Answer counting/listing questions directly from the DB — no RAG, no LLM guesswork."""
    result = await db.execute(
        select(Document).where(Document.case_id == case_id, Document.user_id == user_id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = result.scalars().all()

    doc_list = [
        {"filename": d.filename, "doc_type": d.doc_type, "uploaded_at": d.uploaded_at.isoformat()}
        for d in docs
    ]

    return {
        "answer": f"There are {len(docs)} documents in this case: " +
                  ", ".join(f"{d['filename']} ({d['doc_type']})" for d in doc_list),
        "reasoning": "Answered directly from the case's document records (not via semantic search, which only retrieves a relevance-ranked sample).",
        "relevant_laws": [],
        "confidence": "high",
        "caveats": "",
        "_doc_list": doc_list,  # optional, frontend can ignore or use
    }