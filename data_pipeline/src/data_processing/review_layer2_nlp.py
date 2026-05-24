from __future__ import annotations

import hashlib
import math
import os
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parents[3] / ".cache" / "huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

MAX_LAYER2_SCORE = 0.41
MIN_LAYER2_SCORE = -1.50  # allow heavy spam penalties to accumulate toward 0 intermediate

ENABLE_UNDERTHESEA = os.getenv("DALAT_ENABLE_UNDERTHESEA", "1").lower() in {"1", "true", "yes", "y"}
ENABLE_AI_NLP = os.getenv("DALAT_ENABLE_AI_NLP", "0").lower() in {"1", "true", "yes", "y"}
ENABLE_EMBEDDING = os.getenv("DALAT_ENABLE_EMBEDDING", "0").lower() in {"1", "true", "yes", "y"}

SENTIMENT_MODEL_NAME = os.getenv("DALAT_SENTIMENT_MODEL", "wonrax/phobert-base-vietnamese-sentiment")
NER_MODEL_NAME = os.getenv("DALAT_NER_MODEL", "undertheseanlp/vietnamese-ner-v1.4.0a2")
EMBEDDING_MODEL_NAME = os.getenv("DALAT_EMBEDDING_MODEL", "dangvantuan/vietnamese-embedding")

AI_LOWER = 0.35
AI_UPPER = 0.65
REPETITIVE_MIN_COUNT = 3
EMBEDDING_SIMILARITY_THRESHOLD = 0.90

SEEDING_TERMS = [
    "uy tin",
    "chat luong vuot troi",
    "gia ca hop ly",
    "nhanh tay",
    "inbox",
    "ib",
    "sale",
    "voucher",
    "khuyen mai",
    "cam ket",
    "dich vu hang dau",
]

ADJECTIVE_TERMS = [
    "dep",
    "xau",
    "ngon",
    "do",
    "tuyet",
    "tot",
    "te",
    "sach",
    "ban",
    "lon",
    "nho",
    "nhanh",
    "cham",
    "vui",
    "buon",
    "dat",
    "re",
    "hay",
    "on",
    "chan",
    "la",
    "moi",
    "cu",
    "thoang",
    "mat",
    "lanh",
    "toi",
    "sang",
    "rong",
    "hep",
    "good",
    "bad",
    "great",
    "poor",
    "nice",
    "terrible",
    "beautiful",
    "ugly",
    "clean",
    "dirty",
    "fast",
    "slow",
    "big",
    "small",
    "new",
    "old",
    "fresh",
    "delicious",
    "excellent",
    "amazing",
    "awful",
    "perfect",
    "wonderful",
    "crowded",
    "quiet",
    "noisy",
    "expensive",
    "cheap",
]

SEASONAL_TERMS = {
    "dau tay": {11, 12, 1, 2, 3, 4},
    "hong gion": {9, 10, 11},
    "hong treo gio": {10, 11, 12, 1},
    "atiso": {1, 2, 3, 4, 11, 12},
    "mai anh dao": {1, 2},
    "hoa da quy": {10, 11, 12},
    "hoa cam tu cau": {5, 6, 7, 8},
    "phuong tim": {3, 4},
}

SPECIFICITY_NUMBER_RE = re.compile(
    r"\b\d{1,6}(?:[.,]\d+)?(?:k|d|vnd|usd|\$|%|m|km|nguoi|phut|gio)?\b",
    re.IGNORECASE,
)
SPECIFICITY_TIME_RE = re.compile(
    r"\b(?:\d{1,2}[/:h]\d{2}|sang|chieu|toi|trua|morning|afternoon|evening|noon|midnight)\b",
    re.IGNORECASE,
)
COMPARISON_TERMS = ["hon", "than", "better", "worse", "more", "less", "nhat"]

# Scripts that the Vietnamese sentiment model cannot handle reliably
_UNSUPPORTED_SCRIPT_RE = re.compile(
    r"[Ѐ-ӿ"   # Cyrillic (Russian, Ukrainian...)
    r"가-힣"    # Hangul (Korean)
    r"぀-ヿ"    # Hiragana / Katakana (Japanese)
    r"一-鿿"    # CJK (Chinese)
    r"؀-ۿ"    # Arabic
    r"ऀ-ॿ]"   # Devanagari (Hindi)
)
_UNSUPPORTED_SCRIPT_RATIO_THRESHOLD = 0.05  # skip AI if >5% chars are unsupported

_UNDER_THE_SEA_POS_TAG = None
_UNDER_THE_SEA_CHECKED = False
_SENTIMENT_PIPELINE = None
_SENTIMENT_CHECKED = False
_NER_PIPELINE = None
_NER_CHECKED = False
_EMBEDDING_MODEL = None
_EMBEDDING_CHECKED = False


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    text = safe_str(value)
    if not text:
        return default
    try:
        return float(text.replace(",", "."))
    except Exception:
        return default


def strip_accents(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", safe_str(text))
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.replace("đ", "d").replace("Đ", "D")


def normalize_text(text: Any) -> str:
    text = strip_accents(text).lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^\w\s#.!?%-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def count_words(text: str) -> int:
    words = normalize_text(text).split()
    return len(words)


def count_emoji(text: str) -> int:
    return len(re.findall("[\U0001F300-\U0001FAFF\U00002700-\U000027BF]", safe_str(text)))


def compute_emoji_ratio(text: str) -> float:
    raw = safe_str(text)
    if not raw:
        return 0.0
    return round(count_emoji(raw) / max(len(raw), 1), 4)


def compute_lexical_diversity(text: str) -> float:
    words = normalize_text(text).split()
    if len(words) < 3:
        return 0.0
    return round(len(set(words)) / len(words), 4)


def compute_specificity_score(text: str) -> float:
    normalized = normalize_text(text)
    signals = 0
    if SPECIFICITY_NUMBER_RE.search(normalized):
        signals += 1
    if SPECIFICITY_TIME_RE.search(normalized):
        signals += 1
    if any(term in normalized for term in ["quan", "nhan vien", "ban", "mon", "nuoc", "cafe", "pho", "bun", "com"]):
        signals += 1
    if any(term in normalized for term in COMPARISON_TERMS):
        signals += 1
    return round(min(signals / 4.0, 1.0), 4)


def get_underthesea_pos_tag():
    global _UNDER_THE_SEA_CHECKED, _UNDER_THE_SEA_POS_TAG
    if _UNDER_THE_SEA_CHECKED:
        return _UNDER_THE_SEA_POS_TAG
    _UNDER_THE_SEA_CHECKED = True
    if not ENABLE_UNDERTHESEA:
        return None
    try:
        from underthesea import pos_tag

        _UNDER_THE_SEA_POS_TAG = pos_tag
    except Exception:
        _UNDER_THE_SEA_POS_TAG = None
    return _UNDER_THE_SEA_POS_TAG


def compute_adjective_density(text: str) -> Tuple[float, str]:
    pos_tag = get_underthesea_pos_tag()
    if pos_tag is not None:
        try:
            tagged = pos_tag(safe_str(text))
            if tagged:
                adj_count = sum(1 for _, tag in tagged if safe_str(tag).upper() == "A")
                return round(adj_count / len(tagged), 4), "underthesea"
        except Exception:
            pass

    words = normalize_text(text).split()
    if not words:
        return 0.0, "word_list"
    adj_count = sum(1 for word in words if word in ADJECTIVE_TERMS)
    return round(adj_count / len(words), 4), "word_list"


def detect_seeding_phrase(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in SEEDING_TERMS) or "#" in safe_str(text)


def compute_sentiment_rating_mismatch(sentiment_score: float, rating: float) -> float:
    if rating <= 0:
        return 0.0
    expected = max(-1.0, min(1.0, (rating - 3.0) / 2.0))
    return round(min(abs(sentiment_score - expected), 1.0), 4)


def parse_month(value: Any) -> Optional[int]:
    text = safe_str(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return int(parsed.month)


def compute_temporal_check(text: str, created_at: Any) -> Tuple[bool, str]:
    month = parse_month(created_at)
    if month is None:
        return False, ""
    normalized = normalize_text(text)
    matched_terms: List[str] = []
    mismatched_terms: List[str] = []
    for term, valid_months in SEASONAL_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", normalized):
            matched_terms.append(term)
            if month not in valid_months:
                mismatched_terms.append(term)
    if mismatched_terms:
        return True, "|".join(mismatched_terms)
    return False, "|".join(matched_terms)


def make_text_fingerprint(text: str, n: int = 5) -> str:
    words = normalize_text(text).split()
    if len(words) < n:
        return hashlib.md5(safe_str(text).encode("utf-8", errors="ignore")).hexdigest()
    ngrams = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
    fingerprint = "|".join(sorted(set(ngrams))[:10])
    return hashlib.md5(fingerprint.encode("utf-8", errors="ignore")).hexdigest()


def build_fingerprint_counts(df: pd.DataFrame) -> Dict[str, int]:
    counts: Counter = Counter()
    text_col = "nlp_text_used" if "nlp_text_used" in df.columns else "content_text"
    for text in df[text_col]:
        counts[make_text_fingerprint(safe_str(text))] += 1
    return dict(counts)


def jaccard_similarity(left: str, right: str) -> float:
    left_tokens = set(normalize_text(left).split())
    right_tokens = set(normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def get_embedding_model():
    global _EMBEDDING_CHECKED, _EMBEDDING_MODEL
    if _EMBEDDING_CHECKED:
        return _EMBEDDING_MODEL
    _EMBEDDING_CHECKED = True
    if not ENABLE_EMBEDDING:
        return None
    try:
        from sentence_transformers import SentenceTransformer

        _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
        if hasattr(_EMBEDDING_MODEL, "max_seq_length"):
            _EMBEDDING_MODEL.max_seq_length = min(int(_EMBEDDING_MODEL.max_seq_length), 256)
    except Exception:
        _EMBEDDING_MODEL = None
    return _EMBEDDING_MODEL


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    norm_left = math.sqrt(sum(float(a) * float(a) for a in left))
    norm_right = math.sqrt(sum(float(b) * float(b) for b in right))
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


def compute_similarity_scores(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    scores = pd.Series(0.0, index=df.index)
    model = get_embedding_model()
    text_col = "nlp_text_used" if "nlp_text_used" in df.columns else "content_text"

    if model is not None:
        for _, group in df.groupby("place_id", dropna=False):
            texts = [safe_str(text) for text in group[text_col]]
            if len(texts) < 2:
                continue
            try:
                embedding_texts = [text[:1000] for text in texts]
                embeddings = model.encode(embedding_texts, normalize_embeddings=True, batch_size=16)
            except Exception:
                for i, idx in enumerate(group.index):
                    best = 0.0
                    for j, other in enumerate(texts):
                        if i != j:
                            best = max(best, jaccard_similarity(texts[i], other))
                    scores.loc[idx] = round(best, 4)
                continue
            indices = list(group.index)
            for i, idx in enumerate(indices):
                best = 0.0
                for j, _ in enumerate(indices):
                    if i != j:
                        best = max(best, cosine_similarity(embeddings[i], embeddings[j]))
                scores.loc[idx] = round(best, 4)
        return scores, "sentence_transformers"

    for _, group in df.groupby("place_id", dropna=False):
        indices = list(group.index)
        texts = [safe_str(text) for text in group[text_col]]
        for i, idx in enumerate(indices):
            best = 0.0
            for j, other in enumerate(texts):
                if i != j:
                    best = max(best, jaccard_similarity(texts[i], other))
            scores.loc[idx] = round(best, 4)
    return scores, "jaccard"


def is_supported_language(text: str) -> bool:
    raw = safe_str(text)
    if not raw:
        return False
    unsupported = len(_UNSUPPORTED_SCRIPT_RE.findall(raw))
    return unsupported / max(len(raw), 1) <= _UNSUPPORTED_SCRIPT_RATIO_THRESHOLD


def should_run_ai(preliminary_layer2_score: float, word_count: int, text: str = "") -> bool:
    if not ENABLE_AI_NLP or word_count < 3:
        return False
    if not is_supported_language(text):
        return False
    intermediate = max(0.0, min(1.0, 0.50 + preliminary_layer2_score))
    return AI_LOWER <= intermediate <= AI_UPPER


def get_transformers_pipeline(task: str, model_name: str):
    try:
        from transformers import pipeline

        return pipeline(task, model=model_name, tokenizer=model_name)
    except Exception:
        return None


def get_sentiment_pipeline():
    global _SENTIMENT_CHECKED, _SENTIMENT_PIPELINE
    if _SENTIMENT_CHECKED:
        return _SENTIMENT_PIPELINE
    _SENTIMENT_CHECKED = True
    if ENABLE_AI_NLP:
        _SENTIMENT_PIPELINE = get_transformers_pipeline("text-classification", SENTIMENT_MODEL_NAME)
    return _SENTIMENT_PIPELINE


def sentiment_label_to_score(label: str, confidence: float) -> float:
    label_norm = normalize_text(label)
    if any(token in label_norm for token in ["positive", "pos", "tich cuc", "label_2"]):
        return confidence
    if any(token in label_norm for token in ["negative", "neg", "tieu cuc", "label_0"]):
        return -confidence
    return 0.0


def compute_ai_sentiment(text: str) -> Tuple[Optional[float], str]:
    pipe = get_sentiment_pipeline()
    if pipe is None:
        return None, ""
    try:
        result = pipe(safe_str(text), truncation=True, max_length=256)
        if isinstance(result, list) and result:
            item = result[0]
            label = safe_str(item.get("label"))
            confidence = safe_float(item.get("score"), 0.0)
            return round(sentiment_label_to_score(label, confidence), 4), label
    except Exception:
        return None, ""
    return None, ""


def get_ner_pipeline():
    global _NER_CHECKED, _NER_PIPELINE
    if _NER_CHECKED:
        return _NER_PIPELINE
    _NER_CHECKED = True
    if ENABLE_AI_NLP:
        _NER_PIPELINE = get_transformers_pipeline("token-classification", NER_MODEL_NAME)
    return _NER_PIPELINE


def compute_ner_entity_count(text: str) -> int:
    pipe = get_ner_pipeline()
    if pipe is None:
        return 0
    try:
        result = pipe(safe_str(text)[:512])
        if isinstance(result, list):
            return len(result)
    except Exception:
        return 0
    return 0


def compute_layer2_nlp_scores(common: pd.DataFrame) -> pd.DataFrame:
    out = common.copy()
    fp_counts = build_fingerprint_counts(out)
    similarity_scores, similarity_source = compute_similarity_scores(out)

    records: List[Dict[str, Any]] = []
    for idx, row in out.iterrows():
        text = safe_str(row.get("nlp_text_used", "")) or safe_str(row.get("content_text", ""))
        rating = safe_float(row.get("rating", 0.0))
        sentiment = safe_float(row.get("sentiment_score", 0.0))

        word_count = count_words(text)
        emoji_ratio = compute_emoji_ratio(text)
        lexical_diversity = compute_lexical_diversity(text)
        specificity_score = compute_specificity_score(text)
        adjective_density, adjective_source = compute_adjective_density(text)
        seeding = detect_seeding_phrase(text)
        temporal_mismatch, temporal_terms = compute_temporal_check(text, row.get("content_created_at"))
        mismatch = compute_sentiment_rating_mismatch(sentiment, rating)
        similarity = safe_float(similarity_scores.loc[idx], 0.0)

        fingerprint = make_text_fingerprint(text)
        repetitive = fp_counts.get(fingerprint, 0) >= REPETITIVE_MIN_COUNT

        score = 0.0
        flags: List[str] = []

        # --- PENALTIES ---
        if word_count < 8:
            score -= 0.15
            flags.append("too_short_text")
        if emoji_ratio > 0.2:
            score -= 0.08
            flags.append("emoji_heavy")
        if seeding:
            score -= 0.20
            flags.append("seeding_language")
        if word_count >= 5 and lexical_diversity < 0.4:
            score -= 0.15
            flags.append("low_lexical_diversity")
        if repetitive:
            score -= 0.15
            flags.append("repetitive_template")
        if similarity > EMBEDDING_SIMILARITY_THRESHOLD:
            score -= 0.20
            flags.append("high_embedding_similarity")
        if adjective_density > 0.25:
            score -= 0.08
            flags.append("adjective_heavy")
        if mismatch > 0.5:
            score -= 0.10
            flags.append("sentiment_rating_mismatch")
        if temporal_mismatch:
            score -= 0.08
            flags.append("temporal_mismatch")

        # --- BONUSES ---
        if word_count > 80:
            score += 0.08 + 0.05
            flags.append("very_long_text")
        elif word_count > 30:
            score += 0.08
            flags.append("long_text")
        if specificity_score >= 0.5:
            score += 0.10
            flags.append("specific_content")
        if lexical_diversity > 0.7 and word_count >= 5:
            score += 0.05
            flags.append("high_lexical_diversity")
        if rating > 0 and mismatch <= 0.2:
            score += 0.05
            flags.append("sentiment_matches_rating")

        ai_applied = should_run_ai(score, word_count, text)
        ai_sentiment_score = None
        ai_sentiment_label = ""
        ner_entity_count = 0

        if ai_applied:
            ai_sentiment_score, ai_sentiment_label = compute_ai_sentiment(text)
            if ai_sentiment_score is not None:
                sentiment = ai_sentiment_score
                mismatch = compute_sentiment_rating_mismatch(sentiment, rating)
                if rating > 0 and mismatch > 0.5 and "sentiment_rating_mismatch" not in flags:
                    score -= 0.10
                    flags.append("sentiment_rating_mismatch")

            ner_entity_count = compute_ner_entity_count(text)
            if ner_entity_count > 0 and specificity_score < 0.5:
                specificity_score = min(1.0, specificity_score + 0.25)
                score += 0.05
                flags.append("ner_specific_entity")

        # Credible negative: negative + specific + enough words → highly trustworthy
        if sentiment < -0.2 and specificity_score >= 0.5 and word_count >= 10:
            score += 0.08
            flags.append("credible_negative")

        score = round(max(MIN_LAYER2_SCORE, min(MAX_LAYER2_SCORE, score)), 4)

        records.append(
            {
                "nlp_word_count": word_count,
                "nlp_emoji_ratio": emoji_ratio,
                "nlp_lexical_diversity": lexical_diversity,
                "nlp_specificity_score": specificity_score,
                "nlp_adjective_density": adjective_density,
                "nlp_adjective_source": adjective_source,
                "nlp_seeding_detected": seeding,
                "nlp_repetitive_template": repetitive,
                "nlp_embedding_similarity": similarity,
                "nlp_embedding_source": similarity_source,
                "nlp_sentiment_rating_mismatch": mismatch,
                "nlp_temporal_mismatch": temporal_mismatch,
                "nlp_temporal_terms": temporal_terms,
                "nlp_ai_applied": ai_applied,
                "nlp_ai_sentiment_score": "" if ai_sentiment_score is None else ai_sentiment_score,
                "nlp_ai_sentiment_label": ai_sentiment_label,
                "nlp_ner_entity_count": ner_entity_count,
                "trust_score_layer2": score,
                "trust_flags_layer2": "|".join(flags),
                "trust_flag_count_layer2": len(flags),
            }
        )

    nlp_df = pd.DataFrame(records, index=out.index)
    for col in nlp_df.columns:
        out[col] = nlp_df[col]

    return out
