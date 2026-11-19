"""Search over the index, same steps as search_kb.py in the reply skill.

Used locally by build_index.py (tests) and find_similar.py. load(path) returns
parsed JSON for a path under index/, or None when the file does not exist.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normalize import normalize, normalize_error, phrase_list, synonym_terms  # noqa: E402

MAX_PREFIX_FILES = 12


def search(load, query, type_=None, error=None, limit=3, exclude=()):
    synonyms = load("synonyms.json") or {}
    phrases = phrase_list(synonyms)
    terms = normalize(query, phrases)
    terms += synonym_terms(terms, synonyms, phrases)

    scores = {}  # case id -> [matched terms set, type, error hit]

    def entry(cid, ctype):
        if cid not in scores:
            scores[cid] = [set(), ctype, False]
        elif ctype and not scores[cid][1]:
            scores[cid][1] = ctype
        return scores[cid]

    if error:
        errors = load("errors.json") or {}
        for cid in errors.get(normalize_error(error), []):
            entry(cid, None)[2] = True

    prefixes = []
    for t in terms:
        if t[:2] not in prefixes:
            prefixes.append(t[:2])
    prefixes = prefixes[:MAX_PREFIX_FILES]
    for p in prefixes:
        words = load("words/%s.json" % p) or {}
        for t in terms:
            if t[:2] != p:
                continue
            for item in words.get(t, []):
                cid, _, ctype = item.rpartition(":")
                entry(cid, ctype)[0].add(t)

    ranked = []
    for cid, (matched, ctype, err_hit) in scores.items():
        if cid in exclude:
            continue
        if not err_hit and len(matched) < 2:
            continue
        score = len(matched) + (10 if err_hit else 0)
        if type_ and ctype == type_:
            score += 1
        ranked.append((score, ticket_number(cid), cid))
    ranked.sort(key=lambda r: (-r[0], -r[1]))
    top = [cid for _, _, cid in ranked[:limit]]

    results = []
    titles_cache = {}
    for cid in top:
        folder = cid.split("/")[0]
        if folder not in titles_cache:
            titles_cache[folder] = load("titles/%s.json" % folder) or {}
        info = titles_cache[folder].get(cid, {})
        results.append(("cases/%s.md" % cid, info.get("title", "")))
    return results


def ticket_number(cid):
    name = cid.split("/")[-1]
    base, _, part = name.partition("-")
    try:
        return int(base) + (int(part) if part else 0) / 100.0
    except ValueError:
        return 0
