from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[3] / ".cache" / "huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

ENABLE_TRANSLATION = os.getenv("DALAT_ENABLE_TRANSLATION", "0").lower() in {"1", "true", "yes", "y"}
TRANSLATION_MODEL_NAME = os.getenv("DALAT_TRANSLATION_MODEL", "facebook/nllb-200-distilled-600M")

NLLB_LANG_CODES = {
    "vi": "vie_Latn",
    "en": "eng_Latn",
    "ko": "kor_Hang",
    "ru": "rus_Cyrl",
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "th": "tha_Thai",
}

LATIN_RE = re.compile(r"[A-Za-z]")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
HANGUL_RE = re.compile(r"[\uAC00-\uD7AF]")
CJK_RE = re.compile(r"[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF]")
VIETNAMESE_MARK_RE = re.compile(
    r"[ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    re.IGNORECASE,
)

_TRANSLATOR = None
_TRANSLATOR_CHECKED = False


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def strip_accents(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", safe_str(text))
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.replace("đ", "d").replace("Đ", "D")


def text_hash(text: str, source_lang: str, target_lang: str = "vi") -> str:
    raw = f"{source_lang}|{target_lang}|{safe_str(text)}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def infer_language(text: str, existing_language: str = "") -> str:
    existing = safe_str(existing_language).lower()
    if existing in NLLB_LANG_CODES and existing != "en":
        return existing

    raw = safe_str(text)
    if not raw:
        return existing or "unknown"
    if HANGUL_RE.search(raw):
        return "ko"
    if CYRILLIC_RE.search(raw):
        return "ru"
    if CJK_RE.search(raw):
        return "zh"
    if VIETNAMESE_MARK_RE.search(raw):
        return "vi"
    if existing in NLLB_LANG_CODES:
        return existing
    if LATIN_RE.search(raw):
        return "en"
    return existing or "unknown"


def should_translate(text: str, source_lang: str) -> bool:
    if not ENABLE_TRANSLATION:
        return False
    if not safe_str(text):
        return False
    if source_lang in {"", "vi", "unknown"}:
        return False
    return source_lang in NLLB_LANG_CODES


def get_translator():
    global _TRANSLATOR, _TRANSLATOR_CHECKED
    if _TRANSLATOR_CHECKED:
        return _TRANSLATOR
    _TRANSLATOR_CHECKED = True
    if not ENABLE_TRANSLATION:
        return None
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
        model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL_NAME)
        _TRANSLATOR = {"tokenizer": tokenizer, "model": model}
    except Exception:
        _TRANSLATOR = None
    return _TRANSLATOR


def translate_to_vietnamese(text: str, source_lang: str) -> str:
    translator = get_translator()
    if translator is None:
        return ""

    source_code = NLLB_LANG_CODES.get(source_lang)
    target_code = NLLB_LANG_CODES["vi"]
    if not source_code:
        return ""

    tokenizer = translator["tokenizer"]
    model = translator["model"]
    try:
        tokenizer.src_lang = source_code
        encoded = tokenizer(safe_str(text)[:1200], return_tensors="pt", truncation=True, max_length=256)
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(target_code)
        generated = model.generate(
            **encoded,
            forced_bos_token_id=forced_bos_token_id,
            max_length=256,
            num_beams=3,
        )
        return safe_str(tokenizer.batch_decode(generated, skip_special_tokens=True)[0])
    except Exception:
        return ""


def read_translation_cache(path: Path) -> Dict[str, Dict[str, str]]:
    if not path.exists():
        return {}
    try:
        cache_df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception:
        return {}
    cache: Dict[str, Dict[str, str]] = {}
    for _, row in cache_df.iterrows():
        key = safe_str(row.get("translation_key"))
        if key:
            cache[key] = {
                "translated_text_vi": safe_str(row.get("translated_text_vi")),
                "translation_model": safe_str(row.get("translation_model")),
                "translation_source_lang": safe_str(row.get("translation_source_lang")),
            }
    return cache


def write_translation_cache(cache: Dict[str, Dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: List[Dict[str, str]] = []
    for key, value in sorted(cache.items()):
        rows.append({
            "translation_key": key,
            "translation_source_lang": safe_str(value.get("translation_source_lang")),
            "translated_text_vi": safe_str(value.get("translated_text_vi")),
            "translation_model": safe_str(value.get("translation_model")),
        })
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def add_translation_normalization(common: pd.DataFrame, cache_file: Path) -> pd.DataFrame:
    out = common.copy()
    cache = read_translation_cache(cache_file)
    cache_changed = False

    source_langs: List[str] = []
    applied_flags: List[bool] = []
    translated_texts: List[str] = []
    models: List[str] = []
    text_used: List[str] = []

    for _, row in out.iterrows():
        original_text = safe_str(row.get("content_text"))
        source_lang = infer_language(original_text, safe_str(row.get("language")))
        source_langs.append(source_lang)

        translated = ""
        model_name = ""
        applied = False

        if should_translate(original_text, source_lang):
            key = text_hash(original_text, source_lang)
            cached = cache.get(key)
            if cached and safe_str(cached.get("translated_text_vi")):
                translated = safe_str(cached.get("translated_text_vi"))
                model_name = safe_str(cached.get("translation_model")) or TRANSLATION_MODEL_NAME
                applied = True
            else:
                translated = translate_to_vietnamese(original_text, source_lang)
                if translated:
                    model_name = TRANSLATION_MODEL_NAME
                    applied = True
                    cache[key] = {
                        "translation_source_lang": source_lang,
                        "translated_text_vi": translated,
                        "translation_model": model_name,
                    }
                    cache_changed = True

        applied_flags.append(applied)
        translated_texts.append(translated)
        models.append(model_name)
        text_used.append(translated if applied and translated else original_text)

    out["translation_source_lang"] = source_langs
    out["translation_applied"] = applied_flags
    out["translated_text_vi"] = translated_texts
    out["translation_model"] = models
    out["nlp_text_used"] = text_used

    if cache_changed:
        write_translation_cache(cache, cache_file)

    return out
