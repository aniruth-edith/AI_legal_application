from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class CaseCreate(BaseModel):
    title: str
    description: Optional[str] = None

# class CaseOut(BaseModel):
#     id: str
#     title: str
#     description: Optional[str]
#     created_at: datetime
#     document_count: int = 0

class CaseOut(BaseModel):
    id:             str
    title:          str
    description:    Optional[str]
    created_at:     datetime
    document_count: int = 0
    last_activity:  Optional[str] = None   # ← ADD

class DocumentOut(BaseModel):
    id: str
    filename: str
    doc_type: str
    uploaded_at: datetime

class AnalysisResult(BaseModel):
    doc_id: str
    case_id: str
    extracted: Dict[str, Any]    # NER, sections, parties
    summary: str
    classification: str
    laws_suggested: List[Dict]   # act, section, relevance
    future_scope: List[str]
    follow_up: Optional[str]     # diff vs previous docs in case

class CaseDashboard(BaseModel):
    case: CaseOut
    documents: List[DocumentOut]
    cumulative_summary: str
    all_laws: List[Dict]
    timeline: List[Dict]
    follow_up_brief: str
    future_scope: List[str]


class IdentifiedStatute(BaseModel):
    section_id:   str
    display_name: str
    confidence:   float
    description:  str
    source:       str = "LeSICiN"

# class AnalysisResult(BaseModel):
#     doc_id:       str
#     case_id:      str
#     extracted:    Dict[str, Any]
#     summary:      str
#     classification: str
#     laws_suggested: List[Dict]
#     future_scope: List[str]
#     follow_up:    Optional[str]
#     # ── NEW ──
#     identified_statutes: List[IdentifiedStatute] = []
#     statute_model_available: bool = True

# Single AnalysisResult — remove the duplicate definition
class AnalysisResult(BaseModel):
    doc_id:                  str
    case_id:                 str
    extracted:               Dict[str, Any]
    summary:                 str
    classification:          str
    laws_suggested:          List[Dict]
    future_scope:            List[str]
    follow_up:               Optional[str]
    identified_statutes:     List[IdentifiedStatute] = []
    statute_model_available: bool = True