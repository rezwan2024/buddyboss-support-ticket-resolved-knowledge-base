"""Shared word rules for the KB index and for search_kb.py.

search_kb.py in the reply skill carries an exact copy of everything between
the BEGIN and END markers. Change both together.
"""

# BEGIN normalize
import re
import unicodedata

STOPWORDS = {
    "the", "and", "for", "with", "not", "after", "when", "from", "this", "that",
    "are", "was", "has", "have", "does", "into", "only", "all", "any", "but",
    "can", "our", "you", "your",
}


def _clean(text):
    return unicodedata.normalize("NFKC", text or "").lower()


def phrase_list(synonyms):
    """Multi-word phrases from synonyms.json keys and values, longest first."""
    phrases = set()
    for key, values in (synonyms or {}).items():
        if isinstance(values, str):
            values = [values]
        for p in [key] + list(values):
            words = re.split(r"[^\w]+|_", _clean(p))
            words = [w for w in words if w]
            if len(words) > 1:
                phrases.add(tuple(words))
    return sorted(phrases, key=lambda w: (-len(w), w))


def join_phrases(text, phrases):
    """Add the joined form of each phrase next to it: next gen -> next gen nextgen."""
    for words in phrases:
        pattern = r"(?<![^\W_])" + r"[\W_]+".join(re.escape(w) for w in words) + r"(?![^\W_])"
        joined = "".join(words)
        text = re.sub(pattern, lambda m: m.group(0) + " " + joined, text)
    return text


def stem(term):
    if len(term) > 4 and term.endswith("s") and not term.endswith(("ss", "us", "is")):
        return term[:-1]
    return term


def normalize(text, phrases=()):
    """Text to a list of unique terms, in order of first appearance."""
    text = join_phrases(_clean(text), phrases)
    out = []
    for raw in re.split(r"[\W_]+", text):
        if len(raw) < 2 or raw in STOPWORDS:
            continue
        term = stem(raw)
        if term not in out:
            out.append(term)
    return out


def normalize_error(text):
    """Exact error string key: NFKC, lowercase, single spaces, trimmed."""
    return re.sub(r"\s+", " ", _clean(text)).strip()


def synonym_terms(terms, synonyms, phrases=()):
    """KB terms to add for the synonyms found in a list of query terms."""
    have = set(terms)
    extra = []
    for key, values in (synonyms or {}).items():
        key_terms = normalize(key, phrases)
        if not key_terms:
            continue
        # a phrase key matches on its joined term, a single word on itself
        probe = key_terms[-1] if len(key_terms) > 1 else key_terms[0]
        if probe not in have:
            continue
        if isinstance(values, str):
            values = [values]
        for v in values:
            for t in normalize(v, phrases):
                if t not in have and t not in extra:
                    extra.append(t)
    return extra
# END normalize
