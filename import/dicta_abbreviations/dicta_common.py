"""Shared helpers for the Dicta abbreviation pipeline (query_dicta.py, apply_dicta.py).

Cache file format (JSONL, one object per headword, later lines win):
  {"hw": "<headword>", "abbr": [{"word": "<token>", "options": ["<expansion>", ...]}, ...]}
`abbr` lists every abbreviation token Dicta found in the headword, options in Dicta's ranked order.
"""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SOURCE = os.path.join(ROOT, "source")
sys.path.insert(0, ROOT)
import tsv  # noqa: E402

# ASCII " and ', Hebrew gershayim/geresh, typographic quotes.
QUOTES = "\"'״׳“”‘’"
_QUOTE_RE = re.compile("[" + re.escape(QUOTES) + "]")
_NIKUD_RE = re.compile("[֑-ׇ]")
_FINALS = str.maketrans("ךםןףץ", "כמנפצ")
_NONLETTER_RE = re.compile("[^א-ת ]+")


def is_abbreviation(headword):
    return bool(_QUOTE_RE.search(headword))


def abbreviation_headwords():
    """(id, headword) of every abbreviation headword, by id."""
    return [(int(r["id"]), r["headword"]) for r in tsv.read(os.path.join(SOURCE, "words.tsv"))
            if is_abbreviation(r["headword"])]


def normalize(text):
    """Letters and single spaces only: no nikud, quotes or punctuation, final letters folded."""
    t = _NIKUD_RE.sub("", text or "").translate(_FINALS)
    t = _NONLETTER_RE.sub(" ", t)
    return " ".join(t.split())


def is_self(option, abbreviation):
    """Dicta lists the abbreviation itself (same letters) when unsure: not an expansion."""
    return normalize(option).replace(" ", "") == normalize(abbreviation).replace(" ", "")


def initials_fit(option, abbreviation):
    """True when the abbreviation's letters are, in order, non-empty prefixes of the option's
    words (one prefix per word, every word used): e.g. RShB"Y = Rabbi Shimon Bar Yochai."""
    letters = normalize(abbreviation).replace(" ", "")
    words = normalize(option).split()
    if len(words) < 2 or not letters:
        return False
    memo = {}

    def fit(li, wi):
        if wi == len(words):
            return li == len(letters)
        key = (li, wi)
        if key not in memo:
            w = words[wi]
            memo[key] = any(fit(li + k, wi + 1) for k in range(1, len(w) + 1)
                            if li + k <= len(letters) and letters[li:li + k] == w[:k])
        return memo[key]

    return fit(0, 0)


def sense_parts(text):
    """A sense text may hold several expansions ("X, Y", "X; Y", "X (note)")."""
    t = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text or "")
    parts = {normalize(p) for p in re.split(r"[,;/|]| - | – ", t)}
    parts.add(normalize(text))
    return {p for p in parts if p}


def read_cache(path):
    done = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    o = json.loads(line)
                    done[o["hw"]] = o
    return done


def ranked_options(entry):
    """Dicta's ranked real expansions for a cached headword (self-options dropped). Only a
    headword that is ONE abbreviation token gets options; multi-token headwords get none."""
    abbr = entry.get("abbr") or []
    if len(abbr) != 1 or normalize(abbr[0]["word"]) != normalize(entry["hw"]):
        return []
    word = abbr[0]["word"]
    seen, out = set(), []
    for o in abbr[0].get("options") or []:
        n = normalize(o)
        if n and not is_self(o, word) and n not in seen:
            seen.add(n)
            out.append(o)
    return out


def utf8_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
