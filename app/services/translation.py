"""
Service: translation.py
Multilingual translation using ai4bharat/indictrans2-en-indic-1B (InLegalTrans).

Supports translation from English to all major Indian languages:
  hi  — Hindi
  bn  — Bengali
  ta  — Tamil
  te  — Telugu
  mr  — Marathi
  gu  — Gujarati
  kn  — Kannada
  ml  — Malayalam
  pa  — Punjabi
  or  — Odia
  ur  — Urdu

Usage:
  from app.services.translation import translate_text, translate_batch
  translated = await translate_text("The court held that...", target_lang="hi")
"""

import os
import asyncio
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("INLEGALTRANS_MODEL", "ai4bharat/indictrans2-en-indic-1B")

# IndicTrans2 uses language tags in this format
LANG_CODE_MAP = {
    "hi": "hin_Deva",   # Hindi — Devanagari
    "bn": "ben_Beng",   # Bengali
    "ta": "tam_Taml",   # Tamil
    "te": "tel_Telu",   # Telugu
    "mr": "mar_Deva",   # Marathi — Devanagari
    "gu": "guj_Gujr",   # Gujarati
    "kn": "kan_Knda",   # Kannada
    "ml": "mal_Mlym",   # Malayalam
    "pa": "pan_Guru",   # Punjabi — Gurmukhi
    "or": "ory_Orya",   # Odia
    "ur": "urd_Arab",   # Urdu — Arabic script
    "as": "asm_Beng",   # Assamese
    "en": "eng_Latn",   # English (source)
}

SUPPORTED_LANGUAGES = {
    "hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
    "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
    "pa": "Punjabi", "or": "Odia", "ur": "Urdu", "as": "Assamese",
}

# Max tokens per chunk — IndicTrans2 has a 512 token limit
MAX_CHUNK_TOKENS = 400
MAX_INPUT_CHARS = 1500  # approximate char limit per chunk

_model = None
_tokenizer = None
_model_lock = asyncio.Lock()


# ── Model loading ──────────────────────────────────────────────────────────────

async def _load_model():
    """Lazy-load the InLegalTrans model (thread-safe)."""
    global _model, _tokenizer
    async with _model_lock:
        if _model is not None:
            return
        logger.info(f"Loading InLegalTrans model: {MODEL_NAME}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True,
        )
        _model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_NAME,
            trust_remote_code=True,
        ).to(device)
        _model.eval()
        logger.info(f"InLegalTrans loaded on {device}")


# ── Core translation ───────────────────────────────────────────────────────────

def _translate_chunk(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    Translate a single chunk of text using InLegalTrans.
    Runs synchronously — wrap in asyncio.to_thread for async use.
    """
    if _model is None or _tokenizer is None:
        raise RuntimeError("Translation model not loaded")

    device = next(_model.parameters()).device

    # IndicTrans2 requires language tag as a prefix token
    inputs = _tokenizer(
        text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    ).to(device)

    # Set forced bos token to target language id
    tgt_lang_id = _tokenizer.convert_tokens_to_ids(tgt_lang)

    with torch.no_grad():
        generated = _model.generate(
            **inputs,
            forced_bos_token_id=tgt_lang_id,
            max_new_tokens=512,
            num_beams=4,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )

    translated = _tokenizer.batch_decode(generated, skip_special_tokens=True)
    return translated[0] if translated else text


def _split_into_chunks(text: str, max_chars: int = MAX_INPUT_CHARS) -> List[str]:
    """
    Split long text into sentence-aware chunks for translation.
    Respects sentence boundaries to preserve legal context.
    """
    if len(text) <= max_chars:
        return [text]

    # Split on sentence-ending punctuation
    import re
    sentences = re.split(r'(?<=[.।?!])\s+', text)

    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            # Handle sentences longer than max_chars
            if len(sentence) > max_chars:
                # Hard split by character
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


# ── Public API ─────────────────────────────────────────────────────────────────

async def translate_text(
    text: str,
    target_lang: str,
    source_lang: str = "en",
) -> str:
    """
    Translate text from English to a target Indian language.

    Args:
        text: English text to translate
        target_lang: ISO 639-1 code — 'hi', 'bn', 'ta', 'te', etc.
        source_lang: Source language code (default 'en')

    Returns:
        Translated text string
    """
    if not text or not text.strip():
        return text

    if target_lang == source_lang or target_lang == "en":
        return text  # No translation needed

    if target_lang not in LANG_CODE_MAP:
        logger.warning(f"Unsupported target language: {target_lang}. Returning original.")
        return text

    await _load_model()

    src_code = LANG_CODE_MAP[source_lang]
    tgt_code = LANG_CODE_MAP[target_lang]

    # Split into manageable chunks
    chunks = _split_into_chunks(text)

    # Translate each chunk in a thread (CPU/GPU-bound)
    translated_chunks = []
    for chunk in chunks:
        translated = await asyncio.to_thread(
            _translate_chunk, chunk, src_code, tgt_code
        )
        translated_chunks.append(translated)

    return " ".join(translated_chunks)


async def translate_batch(
    texts: List[str],
    target_lang: str,
    source_lang: str = "en",
) -> List[str]:
    """
    Translate a list of strings. Runs translations concurrently.

    Args:
        texts: List of English strings
        target_lang: Target language code
        source_lang: Source language (default 'en')

    Returns:
        List of translated strings in same order
    """
    if target_lang == source_lang or target_lang == "en":
        return texts

    tasks = [translate_text(t, target_lang, source_lang) for t in texts]
    return await asyncio.gather(*tasks)


async def translate_analysis(
    analysis: dict,
    target_lang: str,
) -> dict:
    """
    Translate all human-readable fields in an analysis dict.
    Preserves structure; only translates string and list-of-string values.

    Fields translated:
      - case_summary
      - key_insights (list)
      - future_scope (list)
      - follow_up
      - outcome_likelihood
      - risk_flags (list)
      - case_trajectory
      - recommended_actions (list)
    """
    if target_lang == "en":
        return analysis

    translated = dict(analysis)  # shallow copy

    # Single string fields
    string_fields = [
        "case_summary", "follow_up", "outcome_likelihood",
        "case_trajectory", "cumulative_summary", "follow_up_brief",
        "risk_assessment",
    ]
    for field in string_fields:
        if field in translated and isinstance(translated[field], str):
            translated[field] = await translate_text(
                translated[field], target_lang
            )

    # List of strings fields
    list_fields = [
        "key_insights", "future_scope", "risk_flags", "recommended_actions",
    ]
    for field in list_fields:
        if field in translated and isinstance(translated[field], list):
            translated[field] = await translate_batch(
                [item for item in translated[field] if isinstance(item, str)],
                target_lang,
            )

    # Law fields — translate the 'reason' and 'relevance' keys
    for law_field in ["applicable_laws", "suggested_laws"]:
        if law_field in translated and isinstance(translated[law_field], list):
            new_laws = []
            for law in translated[law_field]:
                if isinstance(law, dict):
                    law = dict(law)
                    for key in ["relevance", "reason"]:
                        if key in law and isinstance(law[key], str):
                            law[key] = await translate_text(law[key], target_lang)
                new_laws.append(law)
            translated[law_field] = new_laws

    return translated


def get_supported_languages() -> dict:
    """Return dict of supported language codes and names."""
    return SUPPORTED_LANGUAGES


def is_supported(lang_code: str) -> bool:
    return lang_code in LANG_CODE_MAP


# ── Fallback: Rule-based transliteration for legal terms ──────────────────────

LEGAL_TERM_GLOSSARY = {
    "hi": {
        "judgment": "निर्णय",
        "bail": "ज़मानत",
        "petition": "याचिका",
        "court": "न्यायालय",
        "section": "धारा",
        "accused": "आरोपी",
        "complainant": "शिकायतकर्ता",
        "evidence": "साक्ष्य",
        "sentence": "सज़ा",
        "acquittal": "बरी",
        "conviction": "दोषसिद्धि",
        "appeal": "अपील",
        "writ": "रिट",
        "affidavit": "शपथपत्र",
        "advocate": "अधिवक्ता",
    },
    "bn": {
        "judgment": "রায়",
        "bail": "জামিন",
        "petition": "আবেদন",
        "court": "আদালত",
        "section": "ধারা",
        "accused": "অভিযুক্ত",
        "evidence": "সাক্ষ্য",
        "appeal": "আপিল",
        "advocate": "আইনজীবী",
    },
    "ta": {
        "judgment": "தீர்ப்பு",
        "bail": "ஜாமீன்",
        "petition": "மனு",
        "court": "நீதிமன்றம்",
        "section": "பிரிவு",
        "evidence": "சாட்சியம்",
        "appeal": "மேல்முறையீடு",
    },
}


def apply_legal_glossary(text: str, lang: str) -> str:
    """
    Post-process translation by enforcing standardised legal term translations.
    Use after model translation to correct common legal terminology.
    """
    glossary = LEGAL_TERM_GLOSSARY.get(lang, {})
    for en_term, translated_term in glossary.items():
        # Case-insensitive replace of English term that slipped through
        import re
        text = re.sub(
            r'\b' + re.escape(en_term) + r'\b',
            translated_term,
            text,
            flags=re.IGNORECASE,
        )
    return text


async def translate_and_polish(
    text: str,
    target_lang: str,
) -> str:
    """
    Full pipeline: translate then apply legal glossary corrections.
    Recommended for user-facing output.
    """
    translated = await translate_text(text, target_lang)
    return apply_legal_glossary(translated, target_lang)