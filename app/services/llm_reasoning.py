import json
import os
import time
from typing import List, Dict, Any
# from google import genai
# from google.genai import types

# client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# MODEL = "gemini-3.5-flash"

from groq import Groq  # ← change this

client = Groq(api_key=os.getenv("GROQ_API_KEY"))  # ← and this
MODEL = "llama-3.1-8b-instant" 

SYSTEM_PROMPT = """You are an expert Indian legal analyst with deep knowledge of:
- IPC (Indian Penal Code), CrPC (Code of Criminal Procedure), CPC (Civil Procedure Code)
- Constitution of India, Evidence Act, POCSO, IT Act, and all major Indian statutes
- Supreme Court and High Court judgment precedents
- Legal drafting conventions in Indian judiciary

Always respond in valid JSON only. No preamble, no markdown, no code fences.
"""


# def _call_llm(prompt: str, max_tokens: int = 2000, retries: int = 4) -> str:
#     """Call Gemini with exponential backoff on 503/overload errors."""
#     last_error = None
#     for attempt in range(retries):
#         try:
#             response = client.models.generate_content(
#                 model=MODEL,
#                 contents=prompt,
#                 config=types.GenerateContentConfig(
#                     system_instruction=SYSTEM_PROMPT,
#                     max_output_tokens=max_tokens,
#                     temperature=0.2,
#                     response_mime_type="application/json",
#                 ),
#             )
#             return response.text.strip()

#         except Exception as e:
#             last_error = e
#             error_str = str(e)

#             # Only retry on overload/server errors
#             if any(code in error_str for code in ["503", "429", "UNAVAILABLE", "overloaded", "quota"]):
#                 wait = 2 ** attempt  # 1s, 2s, 4s, 8s
#                 print(f"[Gemini] Attempt {attempt+1} failed ({error_str[:80]}). Retrying in {wait}s...")
#                 time.sleep(wait)
#                 continue

#             # Non-retryable error — raise immediately
#             raise

#     raise Exception(f"Gemini API unavailable after {retries} retries: {last_error}")


def _call_llm(prompt: str, max_tokens: int = 2000, retries: int = 4) -> str:
    last_error = None
    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            error_str = str(e)
            if any(code in error_str for code in ["503", "429", "rate_limit", "overloaded"]):
                wait = 2 ** attempt
                print(f"[Groq] Attempt {attempt+1} failed. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise Exception(f"Groq API unavailable after {retries} retries: {last_error}")

def _safe_parse(raw: str, fallback: dict) -> dict:
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        fallback["_raw"] = raw[:300]
        return fallback


def analyze_document(
    nlp_output: Dict[str, Any],
    similar_cases: List[Dict],
    previous_docs_summary: str | None = None,
) -> Dict[str, Any]:

    similar_text = "\n".join(
        [f"- {c['text'][:200]}" for c in similar_cases[:3]]
    ) if similar_cases else "None found."

    prev_ctx = (
        f"\n\nPrevious documents in this case:\n{previous_docs_summary}"
        if previous_docs_summary else ""
    )

    # ── Format LeSICiN predictions for the prompt ──────────────────────────
    lesicin_statutes = nlp_output.get("identified_statutes", [])
    if lesicin_statutes:
        statute_text = "\n".join([
            f"  - {s['display_name']} (confidence: {s['confidence']:.2f})"
            + (f": {s['description'][:100]}" if s.get('description') else "")
            for s in lesicin_statutes[:10]
        ])
        statute_ctx = f"\n\nLeSICiN Model Identified Statutes (high confidence):\n{statute_text}"
    else:
        statute_ctx = "\n\nLeSICiN statute identification: not available or no statutes found."

    prompt = f"""Analyze the following Indian legal document and return a JSON object.

NLP Extraction:
- Document type: {nlp_output['doc_type']}
- Entities: {json.dumps(nlp_output['entities'])}
- Regex-identified acts/sections: {json.dumps([a['match'] for a in nlp_output['act_sections']])}
- Extractive summary: {nlp_output['extractive_summary'][:1000]}
{statute_ctx}

Similar documents from user database:
{similar_text}{prev_ctx}

Using the LeSICiN statute predictions as high-confidence anchors, return this exact JSON structure:
{{
  "case_summary": "2-3 sentence summary of this document",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "applicable_laws": [
    {{"act": "IPC", "section": "302", "relevance": "Relevant because...", "confidence_source": "LeSICiN/regex"}}
  ],
  "suggested_laws": [
    {{"act": "CrPC", "section": "154", "reason": "Could strengthen the case because..."}}
  ],
  "future_scope": ["Potential appeal ground 1", "Legal strategy recommendation 2"],
  "follow_up": "Changes from previous docs and recommended next steps, or null if first document",
  "risk_flags": ["Any red flags or weaknesses found"],
  "outcome_likelihood": "Assessment of probable outcome based on cited laws and precedents",
  "recommended_actions": ["Action 1", "Action 2"]
}}"""

    raw = _call_llm(prompt, max_tokens=2000)
    # return _safe_parse(raw, { ... })  # keep your existing fallback
    return _safe_parse(raw, {
        "case_summary": "Analysis temporarily unavailable — please retry.",
        "key_insights": [],
        "applicable_laws": [],
        "suggested_laws": [],
        "future_scope": [],
        "follow_up": None,
        "risk_flags": [],
        "outcome_likelihood": "Unavailable",
        "recommended_actions": ["Retry the upload in a few minutes"],
    })


def generate_case_dashboard(
    case_title: str,
    all_doc_analyses: List[Dict],
    timeline: List[Dict],
) -> Dict[str, Any]:
    analyses_text = json.dumps(all_doc_analyses, indent=1)[:4000]

    prompt = f"""Given all documents in case "{case_title}", generate a comprehensive case dashboard.

All document analyses:
{analyses_text}

Timeline: {json.dumps(timeline)}

Return this exact JSON:
{{
  "cumulative_summary": "Comprehensive case summary across all documents",
  "case_status": "Current status: trial/appeal/pending/closed",
  "consolidated_laws": [
    {{"act": "...", "section": "...", "frequency": 3, "significance": "..."}}
  ],
  "case_trajectory": "Overall direction and progression of the case",
  "recommended_actions": ["Action 1", "Action 2"],
  "future_scope": ["Scope 1", "Scope 2"],
  "follow_up_brief": "What changed with the latest document and what to do next",
  "risk_assessment": "Overall risk level and key risks"
}}"""

    raw = _call_llm(prompt, max_tokens=2000)
    return _safe_parse(raw, {
        "cumulative_summary": "Dashboard temporarily unavailable — please refresh.",
        "case_status": "Unknown",
        "consolidated_laws": [],
        "case_trajectory": "",
        "recommended_actions": ["Retry in a few minutes"],
        "future_scope": [],
        "follow_up_brief": "",
        "risk_assessment": "",
    })


def ask_case_question(question: str, context_docs: list) -> dict:
    context_text = "\n\n".join(
        [f"[{i+1}] {d['text'][:400]}" for i, d in enumerate(context_docs)]
    ) if context_docs else "No context documents available."

    prompt = f"""Answer the following Indian legal question based on the provided case document excerpts.

Question: {question}

Relevant document excerpts:
{context_text}

Return this exact JSON:
{{
  "answer": "Direct answer to the question",
  "reasoning": "Legal reasoning behind the answer",
  "relevant_laws": ["IPC Section X", "CrPC Section Y"],
  "confidence": "high / medium / low",
  "caveats": "Any limitations or assumptions in this answer"
}}"""

    raw = _call_llm(prompt, max_tokens=1000)
    return _safe_parse(raw, {
        "answer": "Temporarily unavailable — please retry.",
        "reasoning": "",
        "relevant_laws": [],
        "confidence": "low",
        "caveats": "Gemini API overloaded",
    })