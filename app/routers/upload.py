# """
# Router: /upload
# Handles all document ingestion endpoints.
#   POST /upload/{case_id}           — Upload single document, run full pipeline
#   POST /upload/{case_id}/batch     — Upload multiple documents at once
#   GET  /upload/{case_id}/status    — Check processing status of a document
#   DELETE /upload/{doc_id}          — Delete a document and its vectors
# """

# from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
# from fastapi.responses import JSONResponse
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, delete
# import uuid
# import json
# import asyncio
# from datetime import datetime
# from typing import List

# from app.models.db import get_db, Document, Case
# from app.models.schemas import AnalysisResult, DocumentOut
# from app.utils.auth import get_current_user
# from app.utils.doc_parser import parse_document
# from app.services.nlp_pipeline import run_nlp_pipeline
# from app.services.embeddings import embed_text, embed_query
# from app.services.chroma_store import (
#     upsert_document,
#     query_similar,
#     delete_document as chroma_delete,
# )
# from app.services.llm_reasoning import analyze_document

# router = APIRouter(prefix="/upload", tags=["Upload"])

# # ── In-memory job status tracker ──────────────────────────────────────────────
# # For production, replace with Redis or a DB table
# _job_status: dict[str, dict] = {}

# ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}
# MAX_FILE_SIZE_MB = 50


# def _validate_file(filename: str, size: int):
#     ext = filename.lower().rsplit(".", 1)[-1]
#     if ext not in ALLOWED_EXTENSIONS:
#         raise HTTPException(
#             status_code=415,
#             detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
#         )
#     if size > MAX_FILE_SIZE_MB * 1024 * 1024:
#         raise HTTPException(
#             status_code=413,
#             detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB",
#         )


# async def _get_previous_summary(case_id: str, db: AsyncSession) -> str | None:
#     """Fetch summaries of last 3 docs in the case for follow-up context."""
#     result = await db.execute(
#         select(Document)
#         .where(Document.case_id == case_id)
#         .order_by(Document.uploaded_at.desc())
#         .limit(3)
#     )
#     docs = result.scalars().all()
#     if not docs:
#         return None
#     summaries = []
#     for d in reversed(docs):  # chronological order
#         if d.analysis:
#             s = d.analysis.get("case_summary", "")
#             if s:
#                 summaries.append(f"[{d.filename}] {s}")
#     return "\n".join(summaries) if summaries else None


# async def _run_pipeline(
#     doc_id: str,
#     case_id: str,
#     user_id: str,
#     filename: str,
#     file_bytes: bytes,
#     db: AsyncSession,
# ) -> dict:
#     """
#     Full processing pipeline:
#     1. Parse → 2. NLP → 3. Embed → 4. Similar search → 5. LLM → 6. Store
#     """
#     _job_status[doc_id] = {"status": "parsing", "progress": 10}

#     # 1. Parse document text
#     raw_text = parse_document(filename, file_bytes)
#     if not raw_text or len(raw_text.strip()) < 50:
#         raise ValueError("Could not extract meaningful text from the document.")

#     _job_status[doc_id] = {"status": "nlp_processing", "progress": 30}

#     # 2. NLP pipeline (InLegalBERT)
#     # nlp_out = run_nlp_pipeline(raw_text)
#     nlp_out = await run_nlp_pipeline(raw_text)

#     _job_status[doc_id] = {"status": "embedding", "progress": 50}

#     # 3. Generate embeddings (Qwen3-Embedding-8B)
#     embedding = embed_text(raw_text)
#     query_emb = embed_query(nlp_out["extractive_summary"])

#     _job_status[doc_id] = {"status": "similarity_search", "progress": 60}

#     # 4. Retrieve similar docs from this user's case
#     similar = query_similar(user_id, query_emb, case_id=case_id, n_results=3)

#     # 5. Previous docs context for follow-up
#     prev_summary = await _get_previous_summary(case_id, db)

#     _job_status[doc_id] = {"status": "llm_analysis", "progress": 75}

#     # 6. LLM reasoning (Claude)
#     llm_result = analyze_document(nlp_out, similar, prev_summary)

#     _job_status[doc_id] = {"status": "storing", "progress": 90}

#     # 7. Store vectors in ChromaDB
#     upsert_document(
#         user_id=user_id,
#         doc_id=doc_id,
#         case_id=case_id,
#         embedding=embedding,
#         text_chunk=raw_text[:3000],
#         metadata={
#             "filename": filename,
#             "doc_type": nlp_out["doc_type"],
#             "uploaded_at": datetime.utcnow().isoformat(),
#             "entities": json.dumps(nlp_out["entities"]),
#             "act_sections": json.dumps(
#                 [a["match"] for a in nlp_out["act_sections"]]
#             ),
#         },
#     )

#     # 8. Store full record in SQL
#     doc = Document(
#         id=doc_id,
#         case_id=case_id,
#         user_id=user_id,
#         filename=filename,
#         doc_type=nlp_out["doc_type"],
#         raw_text=raw_text[:15000],  # cap stored text
#         analysis={
#             **llm_result,
#             "nlp_meta": {
#                 "doc_type": nlp_out["doc_type"],
#                 "entities": nlp_out["entities"],
#                 "act_sections": [a["match"] for a in nlp_out["act_sections"]],
#             },
#         },
#     )
#     db.add(doc)
#     await db.commit()

#     _job_status[doc_id] = {"status": "complete", "progress": 100}
#     return {"doc_id": doc_id, "llm_result": llm_result, "nlp_out": nlp_out}


# # ── Endpoints ─────────────────────────────────────────────────────────────────


# @router.post("/{case_id}", response_model=AnalysisResult, summary="Upload & analyse a document")
# async def upload_document(
#     case_id: str,
#     file: UploadFile = File(...),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Upload a single legal document to a case.
#     Runs the full pipeline synchronously and returns analysis.
#     """
#     # Verify case belongs to user
#     case_result = await db.execute(
#         select(Case).where(Case.id == case_id, Case.user_id == user.id)
#     )
#     if not case_result.scalar_one_or_none():
#         raise HTTPException(404, "Case not found or access denied")

#     file_bytes = await file.read()
#     _validate_file(file.filename, len(file_bytes))

#     doc_id = str(uuid.uuid4())
#     _job_status[doc_id] = {"status": "queued", "progress": 0}

#     try:
#         result = await _run_pipeline(
#             doc_id=doc_id,
#             case_id=case_id,
#             user_id=user.id,
#             filename=file.filename,
#             file_bytes=file_bytes,
#             db=db,
#         )
#     except ValueError as e:
#         _job_status[doc_id] = {"status": "failed", "error": str(e)}
#         raise HTTPException(422, str(e))
#     except Exception as e:
#         _job_status[doc_id] = {"status": "failed", "error": str(e)}
#         raise HTTPException(500, f"Pipeline failed: {str(e)}")

#     llm = result["llm_result"]
#     nlp = result["nlp_out"]

#     return AnalysisResult(
#         doc_id=doc_id,
#         case_id=case_id,
#         extracted=nlp,
#         summary=llm.get("case_summary", ""),
#         classification=nlp["doc_type"],
#         laws_suggested=llm.get("suggested_laws", []),
#         future_scope=llm.get("future_scope", []),
#         follow_up=llm.get("follow_up"),
#     )


# @router.post("/{case_id}/batch", summary="Upload multiple documents")
# async def upload_batch(
#     case_id: str,
#     background_tasks: BackgroundTasks,
#     files: List[UploadFile] = File(...),
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Upload multiple documents at once. Processing runs in background.
#     Returns job IDs — poll /upload/{doc_id}/status for progress.
#     """
#     if len(files) > 10:
#         raise HTTPException(400, "Maximum 10 files per batch upload")

#     case_result = await db.execute(
#         select(Case).where(Case.id == case_id, Case.user_id == user.id)
#     )
#     if not case_result.scalar_one_or_none():
#         raise HTTPException(404, "Case not found or access denied")

#     job_ids = []
#     for file in files:
#         file_bytes = await file.read()
#         try:
#             _validate_file(file.filename, len(file_bytes))
#         except HTTPException as e:
#             job_ids.append({"filename": file.filename, "error": e.detail})
#             continue

#         doc_id = str(uuid.uuid4())
#         _job_status[doc_id] = {"status": "queued", "progress": 0, "filename": file.filename}
#         job_ids.append({"filename": file.filename, "doc_id": doc_id, "status": "queued"})

#         # Run in background — note: needs a new DB session per background task
#         async def _bg(did=doc_id, cid=case_id, uid=user.id, fn=file.filename, fb=file_bytes):
#             async with db.__class__(db.bind) as bg_db:
#                 try:
#                     await _run_pipeline(did, cid, uid, fn, fb, bg_db)
#                 except Exception as ex:
#                     _job_status[did] = {"status": "failed", "error": str(ex)}

#         background_tasks.add_task(_bg)

#     return {
#         "message": f"Batch of {len(files)} file(s) queued for processing",
#         "jobs": job_ids,
#     }


# @router.get("/status/{doc_id}", summary="Check processing status")
# async def get_status(doc_id: str, user=Depends(get_current_user)):
#     """Poll this endpoint after batch upload to track processing progress."""
#     status = _job_status.get(doc_id)
#     if not status:
#         raise HTTPException(404, "Job not found or already cleaned up")
#     return {"doc_id": doc_id, **status}


# @router.get("/{case_id}/documents", response_model=List[DocumentOut], summary="List all docs in a case")
# async def list_documents(
#     case_id: str,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """List all uploaded documents for a specific case."""
#     result = await db.execute(
#         select(Document)
#         .where(Document.case_id == case_id, Document.user_id == user.id)
#         .order_by(Document.uploaded_at.asc())
#     )
#     docs = result.scalars().all()
#     return [
#         DocumentOut(
#             id=d.id,
#             filename=d.filename,
#             doc_type=d.doc_type,
#             uploaded_at=d.uploaded_at,
#         )
#         for d in docs
#     ]


# @router.delete("/{doc_id}", summary="Delete a document")
# async def delete_document(
#     doc_id: str,
#     user=Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """Delete a document from both SQL and ChromaDB vector store."""
#     result = await db.execute(
#         select(Document).where(Document.id == doc_id, Document.user_id == user.id)
#     )
#     doc = result.scalar_one_or_none()
#     if not doc:
#         raise HTTPException(404, "Document not found or access denied")

#     # Remove from ChromaDB
#     try:
#         chroma_delete(user_id=user.id, doc_id=doc_id)
#     except Exception:
#         pass  # Don't fail if chroma delete errors

#     # Remove from SQL
#     await db.execute(delete(Document).where(Document.id == doc_id))
#     await db.commit()

#     return {"message": f"Document '{doc.filename}' deleted successfully"}

"""
Router: /upload
Handles all document ingestion endpoints.
  POST /upload/{case_id}           — Upload single document, run full pipeline
  POST /upload/{case_id}/batch     — Upload multiple documents at once
  GET  /upload/{case_id}/status    — Check processing status of a document
  DELETE /upload/{doc_id}          — Delete a document and its vectors
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
import json
import asyncio
from datetime import datetime
from typing import List

from app.models.db import get_db, Document, Case
from app.models.schemas import AnalysisResult, DocumentOut
from app.utils.auth import get_current_user
from app.utils.doc_parser import parse_document
from app.services.nlp_pipeline import run_nlp_pipeline
from app.services.embeddings import embed_text, embed_query
from app.services.chroma_store import (
    upsert_document,
    query_similar,
    delete_document as chroma_delete,
)
from app.services.llm_reasoning import analyze_document

router = APIRouter(prefix="/upload", tags=["Upload"])

# ── In-memory job status tracker ──────────────────────────────────────────────
# For production, replace with Redis or a DB table
_job_status: dict[str, dict] = {}

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}
MAX_FILE_SIZE_MB = 50


def _validate_file(filename: str, size: int):
    ext = filename.lower().rsplit(".", 1)[-1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
        )
    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB",
        )


async def _get_previous_summary(case_id: str, db: AsyncSession) -> str | None:
    """Fetch summaries of last 3 docs in the case for follow-up context."""
    result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.uploaded_at.desc())
        .limit(3)
    )
    docs = result.scalars().all()
    if not docs:
        return None
    summaries = []
    for d in reversed(docs):  # chronological order
        if d.analysis:
            s = d.analysis.get("case_summary", "")
            if s:
                summaries.append(f"[{d.filename}] {s}")
    return "\n".join(summaries) if summaries else None


async def _run_pipeline(
    doc_id: str,
    case_id: str,
    user_id: str,
    filename: str,
    file_bytes: bytes,
    db: AsyncSession,
) -> dict:
    """
    Full processing pipeline:
    1. Parse → 2. NLP → 3. Embed → 4. Similar search → 5. LLM → 6. Store
    """
    _job_status[doc_id] = {"status": "parsing", "progress": 10}

    # 1. Parse document text
    raw_text = parse_document(filename, file_bytes)
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Could not extract meaningful text from the document.")

    _job_status[doc_id] = {"status": "nlp_processing", "progress": 30}

    # 2. NLP pipeline (InLegalBERT)
    # nlp_out = run_nlp_pipeline(raw_text)
    nlp_out = await run_nlp_pipeline(raw_text)

    _job_status[doc_id] = {"status": "embedding", "progress": 50}

    # 3. Generate embeddings (Qwen3-Embedding-8B)
    embedding = embed_text(raw_text)
    query_emb = embed_query(nlp_out["extractive_summary"])

    _job_status[doc_id] = {"status": "similarity_search", "progress": 60}

    # 4. Retrieve similar docs from this user's case
    similar = query_similar(user_id, query_emb, case_id=case_id, n_results=3)

    # 5. Previous docs context for follow-up
    prev_summary = await _get_previous_summary(case_id, db)

    _job_status[doc_id] = {"status": "llm_analysis", "progress": 75}

    # 6. LLM reasoning (Claude)
    llm_result = analyze_document(nlp_out, similar, prev_summary)

    _job_status[doc_id] = {"status": "storing", "progress": 90}

    # 7. Store vectors in ChromaDB
    upsert_document(
        user_id=user_id,
        doc_id=doc_id,
        case_id=case_id,
        embedding=embedding,
        text_chunk=raw_text[:3000],
        metadata={
            "filename": filename,
            "doc_type": nlp_out["doc_type"],
            "uploaded_at": datetime.utcnow().isoformat(),
            "entities": json.dumps(nlp_out["entities"]),
            "act_sections": json.dumps(
                [a["match"] for a in nlp_out["act_sections"]]
            ),
        },
    )

    # 8. Store full record in SQL
    doc = Document(
        id=doc_id,
        case_id=case_id,
        user_id=user_id,
        filename=filename,
        doc_type=nlp_out["doc_type"],
        raw_text=raw_text[:15000],  # cap stored text
        analysis={
            **llm_result,
            "nlp_meta": {
                "doc_type": nlp_out["doc_type"],
                "entities": nlp_out["entities"],
                "act_sections": [a["match"] for a in nlp_out["act_sections"]],
            },
            "identified_statutes": nlp_out.get("identified_statutes", []),
            "statute_model_available": nlp_out.get("statute_model_available", False),
            "statute_raw_predictions": nlp_out.get("statute_raw_predictions", []),
        },
    )
    db.add(doc)
    await db.commit()

    _job_status[doc_id] = {"status": "complete", "progress": 100}
    return {"doc_id": doc_id, "llm_result": llm_result, "nlp_out": nlp_out}


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/{case_id}", response_model=AnalysisResult, summary="Upload & analyse a document")
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a single legal document to a case.
    Runs the full pipeline synchronously and returns analysis.
    """
    # Verify case belongs to user
    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    if not case_result.scalar_one_or_none():
        raise HTTPException(404, "Case not found or access denied")

    file_bytes = await file.read()
    _validate_file(file.filename, len(file_bytes))

    doc_id = str(uuid.uuid4())
    _job_status[doc_id] = {"status": "queued", "progress": 0}

    try:
        result = await _run_pipeline(
            doc_id=doc_id,
            case_id=case_id,
            user_id=user.id,
            filename=file.filename,
            file_bytes=file_bytes,
            db=db,
        )
    except ValueError as e:
        _job_status[doc_id] = {"status": "failed", "error": str(e)}
        raise HTTPException(422, str(e))
    except Exception as e:
        _job_status[doc_id] = {"status": "failed", "error": str(e)}
        raise HTTPException(500, f"Pipeline failed: {str(e)}")

    llm = result["llm_result"]
    nlp = result["nlp_out"]

    return AnalysisResult(
        doc_id=doc_id,
        case_id=case_id,
        extracted=nlp,
        summary=llm.get("case_summary", ""),
        classification=nlp["doc_type"],
        laws_suggested=llm.get("suggested_laws", []),
        future_scope=llm.get("future_scope", []),
        follow_up=llm.get("follow_up"),
        identified_statutes=nlp.get("identified_statutes", []),
        statute_model_available=nlp.get("statute_model_available", False),
    )


@router.post("/{case_id}/batch", summary="Upload multiple documents")
async def upload_batch(
    case_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload multiple documents at once. Processing runs in background.
    Returns job IDs — poll /upload/{doc_id}/status for progress.
    """
    if len(files) > 10:
        raise HTTPException(400, "Maximum 10 files per batch upload")

    case_result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user.id)
    )
    if not case_result.scalar_one_or_none():
        raise HTTPException(404, "Case not found or access denied")

    job_ids = []
    for file in files:
        file_bytes = await file.read()
        try:
            _validate_file(file.filename, len(file_bytes))
        except HTTPException as e:
            job_ids.append({"filename": file.filename, "error": e.detail})
            continue

        doc_id = str(uuid.uuid4())
        _job_status[doc_id] = {"status": "queued", "progress": 0, "filename": file.filename}
        job_ids.append({"filename": file.filename, "doc_id": doc_id, "status": "queued"})

        # Run in background — note: needs a new DB session per background task
        async def _bg(did=doc_id, cid=case_id, uid=user.id, fn=file.filename, fb=file_bytes):
            async with db.__class__(db.bind) as bg_db:
                try:
                    await _run_pipeline(did, cid, uid, fn, fb, bg_db)
                except Exception as ex:
                    _job_status[did] = {"status": "failed", "error": str(ex)}

        background_tasks.add_task(_bg)

    return {
        "message": f"Batch of {len(files)} file(s) queued for processing",
        "jobs": job_ids,
    }


@router.get("/status/{doc_id}", summary="Check processing status")
async def get_status(doc_id: str, user=Depends(get_current_user)):
    """Poll this endpoint after batch upload to track processing progress."""
    status = _job_status.get(doc_id)
    if not status:
        raise HTTPException(404, "Job not found or already cleaned up")
    return {"doc_id": doc_id, **status}


@router.get("/{case_id}/documents", response_model=List[DocumentOut], summary="List all docs in a case")
async def list_documents(
    case_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded documents for a specific case."""
    result = await db.execute(
        select(Document)
        .where(Document.case_id == case_id, Document.user_id == user.id)
        .order_by(Document.uploaded_at.asc())
    )
    docs = result.scalars().all()
    return [
        DocumentOut(
            id=d.id,
            filename=d.filename,
            doc_type=d.doc_type,
            uploaded_at=d.uploaded_at,
        )
        for d in docs
    ]


@router.delete("/{doc_id}", summary="Delete a document")
async def delete_document(
    doc_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document from both SQL and ChromaDB vector store."""
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found or access denied")

    # Remove from ChromaDB
    try:
        chroma_delete(user_id=user.id, doc_id=doc_id)
    except Exception:
        pass  # Don't fail if chroma delete errors

    # Remove from SQL
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()

    return {"message": f"Document '{doc.filename}' deleted successfully"}