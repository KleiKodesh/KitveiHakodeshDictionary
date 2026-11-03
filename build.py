"""Builds Dictionary.db from source/ (the source of truth).

Also writes a build_meta table: the sha256 of sources.json, each source's pin, and the
sha256 of every source file, so a built DB says exactly what it was built from.

Run: python build.py [--out PATH]   (default: db_path.py - the app copy when this repo sits
     inside KleiKodeshProject, else build/Dictionary.db)
"""

import argparse
import hashlib
import json
import os
import sqlite3
import time

import db_path
import tsv

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "source")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def step(msg):
    print(f"[build] {msg}", flush=True)


def build(out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    with open(os.path.join(SOURCE, "schema.sql"), encoding="utf-8") as f:
        con.executescript(f.read())
    step("schema created")

    def load(name, table, cols, convert=None):
        rows = [tuple(r[c] for c in cols) for r in tsv.read(os.path.join(SOURCE, name))]
        if convert:
            rows = [convert(r) for r in rows]
        con.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES "
                        f"({','.join('?' * len(cols))})", rows)
        step(f"{table} <- {name}: {len(rows)} rows")

    load("source_kind.tsv", "source_kind", ["id", "name"], lambda r: (int(r[0]), r[1]))
    load("link_kind.tsv", "link_kind", ["id", "name", "explanation"], lambda r: (int(r[0]),) + r[1:])
    load("words.tsv", "word", ["id", "headword"], lambda r: (int(r[0]), r[1]))
    word_id = dict((h, i) for i, h in con.execute("SELECT id, headword FROM word"))

    senses = []
    for name in sorted(os.listdir(os.path.join(SOURCE, "senses"))):
        sid = None if name == "source_none.tsv" else int(name[len("source_"):-len(".tsv")])
        n = 0
        for r in tsv.read(os.path.join(SOURCE, "senses", name)):
            senses.append((int(r["id"]), word_id[r["headword"]], r["nikud"], r["text"], sid))
            n += 1
        step(f"senses/{name}: {n} rows")
    senses.sort()
    con.executemany("INSERT INTO sense (id, word_id, nikud, text, source_id) VALUES (?,?,?,?,?)", senses)

    links = [(int(r["word_id"]), int(r["target_id"]), int(r["kind_id"]))
             for r in tsv.read(os.path.join(SOURCE, "links.tsv"))]
    con.executemany("INSERT INTO link (word_id, target_id, kind_id) VALUES (?,?,?)", links)
    step(f"link <- links.tsv: {len(links)} rows")

    load("seforim_headword_book.tsv", "seforim_headword_book", ["id", "title"],
         lambda r: (int(r[0]), r[1]))
    load("seforim_headword.tsv", "seforim_headword", ["source", "bookId", "lineIndex", "word"],
         lambda r: (r[0], int(r[1]), int(r[2]), r[3]))

    # sqlite_sequence follows max(id) on insert; the original DB matches that.
    con.commit()
    # Restore the recorded planner statistics (ANALYZE on a tiny table creates sqlite_stat1).
    con.execute("ANALYZE link_kind")
    con.execute("DELETE FROM sqlite_stat1")
    con.executemany("INSERT INTO sqlite_stat1 (tbl, idx, stat) VALUES (?, ?, ?)",
                    [(r["tbl"], r["idx"], r["stat"]) for r in tsv.read(os.path.join(SOURCE, "sqlite_stat1.tsv"))])

    # Provenance stamp.
    manifest = os.path.join(ROOT, "sources.json")
    con.execute("CREATE TABLE build_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    meta = {"built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sources_json_sha256": sha256_file(manifest)}
    with open(manifest, encoding="utf-8") as f:
        for s in json.load(f)["sources"]:
            meta[f"pin:{s['id']}"] = s["pin"]
    for dirpath, _, files in os.walk(SOURCE):
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            meta["file:" + os.path.relpath(p, ROOT).replace(os.sep, "/")] = sha256_file(p)
    if os.environ.get("GITHUB_SHA"):
        meta["git_commit"] = os.environ["GITHUB_SHA"]
    con.executemany("INSERT INTO build_meta VALUES (?, ?)", sorted(meta.items()))
    con.commit()
    con.execute("VACUUM")
    con.close()
    os.replace(tmp, out)
    step(f"done -> {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=db_path.dictionary_db())
    build(ap.parse_args().out)
