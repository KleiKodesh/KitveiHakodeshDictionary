"""Writes the readable source files from a Dictionary.db.

Used once to extract the original DB (2026-11-03), and after every import script run:
the import scripts change Dictionary.db (db_path.py), then this script writes the change back
into source/, which is what gets committed.

Run: python export.py [path/to/Dictionary.db]      (default: db_path.py - the app copy, else build/Dictionary.db)
"""

import os
import sqlite3
import sys

import db_path
import tsv

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "source")


def export(db_path):
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    os.makedirs(os.path.join(SOURCE, "senses"), exist_ok=True)

    def step(msg):
        print(f"[export] {msg}", flush=True)

    schema = [s for (s,) in con.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
        "AND name <> 'build_meta' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, rowid")]
    with open(os.path.join(SOURCE, "schema.sql"), "w", encoding="utf-8", newline="\n") as f:
        f.write(";\n\n".join(schema) + ";\n")
    step(f"schema.sql: {len(schema)} statements")

    tsv.write(os.path.join(SOURCE, "source_kind.tsv"), ["id", "name"],
              con.execute("SELECT id, name FROM source_kind ORDER BY id"))
    tsv.write(os.path.join(SOURCE, "link_kind.tsv"), ["id", "name", "explanation"],
              con.execute("SELECT id, name, explanation FROM link_kind ORDER BY id"))
    words = con.execute("SELECT id, headword FROM word ORDER BY id").fetchall()
    tsv.write(os.path.join(SOURCE, "words.tsv"), ["id", "headword"], words)
    step(f"words.tsv: {len(words)} rows")

    # One file per source_kind; senses with no source go to senses/source_none.tsv.
    for f in os.listdir(os.path.join(SOURCE, "senses")):
        os.remove(os.path.join(SOURCE, "senses", f))
    groups = [r[0] for r in con.execute("SELECT DISTINCT source_id FROM sense ORDER BY source_id")]
    for sid in groups:
        rows = con.execute(
            "SELECT s.id, w.headword, s.nikud, s.text FROM sense s JOIN word w ON w.id = s.word_id "
            "WHERE s.source_id IS ? ORDER BY s.id", (sid,)).fetchall()
        name = f"source_{sid:02d}.tsv" if sid is not None else "source_none.tsv"
        tsv.write(os.path.join(SOURCE, "senses", name), ["id", "headword", "nikud", "text"], rows)
        step(f"senses/{name}: {len(rows)} rows")

    rows = con.execute(
        "SELECT l.word_id, l.target_id, l.kind_id, w.headword, t.headword FROM link l "
        "LEFT JOIN word w ON w.id = l.word_id LEFT JOIN word t ON t.id = l.target_id "
        "ORDER BY l.word_id, l.target_id, l.kind_id").fetchall()
    # Ids are authoritative (some links point at word ids that no longer exist: their
    # headword columns are \N). The headword columns are for reading only.
    tsv.write(os.path.join(SOURCE, "links.tsv"),
              ["word_id", "target_id", "kind_id", "headword", "target"], rows)
    step(f"links.tsv: dangling rows (word id missing) = {sum(1 for r in rows if r[3] is None or r[4] is None)}")
    step(f"links.tsv: {len(rows)} rows")

    tsv.write(os.path.join(SOURCE, "seforim_headword_book.tsv"), ["id", "title"],
              con.execute("SELECT id, title FROM seforim_headword_book ORDER BY id"))
    rows = con.execute(
        "SELECT source, bookId, lineIndex, word FROM seforim_headword ORDER BY rowid").fetchall()
    tsv.write(os.path.join(SOURCE, "seforim_headword.tsv"),
              ["source", "bookId", "lineIndex", "word"], rows)
    step(f"seforim_headword.tsv: {len(rows)} rows")
    # Query-planner statistics, kept as-is so the build reproduces the DB exactly.
    tsv.write(os.path.join(SOURCE, "sqlite_stat1.tsv"), ["tbl", "idx", "stat"],
              con.execute("SELECT tbl, idx, stat FROM sqlite_stat1 ORDER BY tbl, idx"))
    con.close()


if __name__ == "__main__":
    export(sys.argv[1] if len(sys.argv) > 1 else db_path.dictionary_db())
