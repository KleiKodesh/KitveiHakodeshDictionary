"""Prints release notes (Markdown) for a built Dictionary.db: row counts, the sources.json
hash and every source pin, read back from the DB's build_meta table.

Run: python release_notes.py [build/Dictionary.db]
"""

import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    meta = dict(con.execute("SELECT key, value FROM build_meta"))
    out = ["Dictionary.db built by CI from this repo's `source/` files.", "",
           f"- Commit: `{meta.get('git_commit', 'local build')}`",
           f"- Built (UTC): {meta['built_utc']}",
           f"- sources.json sha256: `{meta['sources_json_sha256']}`", "", "Rows:", ""]
    for t in ["word", "sense", "link", "source_kind", "link_kind",
              "seforim_headword_book", "seforim_headword"]:
        out.append(f"- {t}: {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}")
    out += ["", "Source pins:", ""]
    out += [f"- {k[4:]}: {v}" for k, v in sorted(meta.items()) if k.startswith("pin:")]
    print("\n".join(out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "Dictionary.db"))
