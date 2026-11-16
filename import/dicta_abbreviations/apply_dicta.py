"""Turns the Dicta cache (query_dicta.py) into source/ changes. Idempotent: rerun any time.

1. New senses (source_kind 12, source/senses/source_12.tsv): for each abbreviation, Dicta's
   top --new-max real expansions that no existing sense already carries, and only when the
   expansion's words fit the abbreviation's letters (one prefix per word, e.g. RShB"Y =
   Rabbi Shimon Bar Yochai). This keeps out Dicta's single-word guesses for truncations
   (VKV' -> words that merely start with those letters).
2. Ranks (source/sense_rank.tsv -> sense.rank): every sense of an abbreviation where at least
   one sense matches a Dicta option gets rank 1..n: matched senses in Dicta's order, then the
   unmatched ones in their current (id) order. A sense matches when its text, or one of its
   comma/semicolon parts, equals an option after normalizing (no nikud, quotes, punctuation).
3. source_kind.tsv gets row 12, sources.json gets/updates the source entry (pin + sha256 of the cache).

Run: python import/dicta_abbreviations/apply_dicta.py --cache PATH [--pin TEXT] [--new-max 3]
Then: python build.py  (and commit source/ + sources.json).
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dicta_common as dc  # noqa: E402
from dicta_common import tsv, SOURCE, ROOT  # noqa: E402

KIND_ID = 12
KIND_NAME = "דיקטה - ראשי תיבות"  # Dicta - rashei teivot
SENSES_DIR = os.path.join(SOURCE, "senses")
KIND_FILE = os.path.join(SENSES_DIR, f"source_{KIND_ID:02d}.tsv")
RANK_FILE = os.path.join(SOURCE, "sense_rank.tsv")
SOURCE_ID = "dicta_abbreviation_expander"


def main():
    dc.utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--pin", default=None, help="e.g. 'dicta-cache branch commit <sha>'")
    ap.add_argument("--new-max", type=int, default=3)
    a = ap.parse_args()
    cache = dc.read_cache(a.cache)

    # All senses except our own kind (rebuilt from scratch below, keeping old ids).
    senses = {}            # headword -> [(id, text)]
    max_id = 0
    for name in sorted(os.listdir(SENSES_DIR)):
        for r in tsv.read(os.path.join(SENSES_DIR, name)):
            sid = int(r["id"])
            max_id = max(max_id, sid)
            if name != os.path.basename(KIND_FILE):
                senses.setdefault(r["headword"], []).append((sid, r["text"]))
    old_ids = {}
    if os.path.exists(KIND_FILE):
        old_ids = {(r["headword"], r["text"]): int(r["id"]) for r in tsv.read(KIND_FILE)}

    new_rows, ranks = [], []
    words = asked = with_opts = reordered = 0
    samples = []
    for _, hw in dc.abbreviation_headwords():
        words += 1
        if hw not in cache:
            continue
        asked += 1
        opts = dc.ranked_options(cache[hw])
        if not opts:
            continue
        with_opts += 1
        own = senses.get(hw, [])
        have = set().union(*(dc.sense_parts(t) for _, t in own)) if own else set()
        added = []
        for o in opts[:a.new_max]:
            n = dc.normalize(o)
            if n in have or not dc.initials_fit(o, hw):
                continue
            sid = old_ids.get((hw, o))
            if sid is None:
                max_id += 1
                sid = max_id
            have.add(n)
            added.append((sid, o))
            new_rows.append((sid, hw, None, o))
        all_s = sorted(own + added)
        norm_opts = [dc.normalize(o) for o in opts]

        def key(s):
            parts = dc.sense_parts(s[1])
            hit = [i for i, n in enumerate(norm_opts) if n in parts]
            return (hit[0] if hit else len(norm_opts), s[0])

        ordered = sorted(all_s, key=key)
        if not any(key(s)[0] < len(norm_opts) for s in all_s):
            continue
        if [s[0] for s in ordered] != [s[0] for s in all_s]:
            reordered += 1
            if len(samples) < 6:
                samples.append((hw, [t for _, t in ordered][:4]))
        ranks += [(sid, rank, hw, text) for rank, (sid, text) in enumerate(ordered, 1)]

    new_rows.sort()
    ranks.sort()
    tsv.write(KIND_FILE, ["id", "headword", "nikud", "text"], new_rows)
    tsv.write(RANK_FILE, ["sense_id", "rank", "headword", "text"], ranks)

    kinds = [(int(r["id"]), r["name"]) for r in tsv.read(os.path.join(SOURCE, "source_kind.tsv"))]
    if KIND_ID not in dict(kinds):
        kinds.append((KIND_ID, KIND_NAME))
        tsv.write(os.path.join(SOURCE, "source_kind.tsv"), ["id", "name"], sorted(kinds))

    manifest = os.path.join(ROOT, "sources.json")
    with open(a.cache, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    entry = {
        "id": SOURCE_ID,
        "name": f"Dicta abbreviation expander (source_kind {KIND_ID}) + sense ranks",
        "description": "Ranked expansions from Dicta's abbreviation expander (task abbrexp, genre "
                       "rabbinic) for every abbreviation headword, queried by "
                       "import/dicta_abbreviations/query_dicta.py and applied by apply_dicta.py.",
        "origin": "https://nakdan-u2-1a.loadbalancer.dicta.org.il/api (cache: branch dicta-cache, "
                  "dicta_abbreviations.jsonl)",
        "pin": a.pin or "cache file as recorded by sha256",
        "sha256": sha,
        "license": "Dicta (dicta.org.il), used with permission for bulk use; attribution: Dicta",
        "fetch": "import/dicta_abbreviations/query_dicta.py (resumable; CI workflow dicta-abbreviations.yml)",
        "feeds": [f"sense: source/senses/source_{KIND_ID:02d}.tsv", "sense.rank: source/sense_rank.tsv",
                  "source_kind: source/source_kind.tsv"],
    }
    # Edit the text, not a json.dump of the whole file, so the rest keeps its hand formatting.
    with open(manifest, encoding="utf-8") as f:
        text = f.read()
    block = "    {\n" + ",\n".join(
        f"      {json.dumps(k)}: " + (("[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in v) + "]")
                                    if isinstance(v, list) else json.dumps(v, ensure_ascii=False))
        for k, v in entry.items()) + "\n    },\n"
    start = text.find('    {\n      "id": "' + SOURCE_ID + '"')
    if start >= 0:
        end = text.index("\n    },\n", start) + len("\n    },\n")
        text = text[:start] + block + text[end:]
    else:
        anchor = text.index('    {\n      "id": "links"')
        text = text[:anchor] + block + text[anchor:]
    json.loads(text)  # still valid
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    print(f"[apply] abbreviations {words} | in cache {asked} | with Dicta expansions {with_opts} | "
          f"new senses {len(new_rows)} | ranked words {len({r[2] for r in ranks})} | "
          f"reordered {reordered}")
    for hw, order in samples:
        print(f"[apply] reordered {hw}: {' | '.join(order)}")


if __name__ == "__main__":
    main()
