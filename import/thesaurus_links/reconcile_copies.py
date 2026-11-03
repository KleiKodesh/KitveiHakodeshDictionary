#!/usr/bin/env python3
"""One-off reconciliation of the two Dictionary.db copies (2026-07-21).

The two copies (service + frontend) had a PRE-EXISTING 3-row drift unrelated to
the thesaurus linker. User chose the SERVICE copy as authoritative. This script:

  1. frontend: retag דוכיפת sense id 82859 -> 82855 (match service)
  2. frontend: word id=5440 headword 'יה' -> 'י-ה' (match service, reverent maqaf form)
  3. both: DELETE junk בין sense id=7483 ("Ender's Game" character, service-only)

Transactional per DB (explicit BEGIN + commit/rollback, never executescript).
Verifies the two copies are byte-identical in content afterward.

    python reconcile_copies.py --dry-run
    python reconcile_copies.py
"""
import argparse
import hashlib
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Dictionary.db location: db_path.py (the app's one copy when cloned inside KleiKodeshProject).
_DB_PATH_PY = os.path.join(os.path.dirname(os.path.dirname(HERE)), "db_path.py")
DICT_DB = __import__("runpy").run_path(_DB_PATH_PY)["dictionary_db"]()
SVC = DICT_DB
# HISTORICAL: the frontend copy no longer exists (one DB copy since 2026-11-03), so this
# one-off cannot run again; pass the old frontend DB path as env RECONCILE_FE_DB to replay it.
FE = os.environ.get("RECONCILE_FE_DB", "")

DIVINE_NAME = "י-ה"   # י-ה  (service value, with maqaf)
JUNK_SENSE_ID = 7483
DUK_FE_ID, DUK_SVC_ID = 82859, 82855


def content_hash(con):
    h = hashlib.sha256()
    for tbl in ["word", "sense", "link", "link_kind"]:
        ncol = len(con.execute(f"SELECT * FROM {tbl} LIMIT 1").description)
        order = ",".join(str(i + 1) for i in range(ncol))
        for row in con.execute(f"SELECT * FROM {tbl} ORDER BY {order}"):
            h.update(repr(row).encode("utf-8"))
    return h.hexdigest()


def fix_frontend(con, dry):
    con.execute("BEGIN")
    # דוכיפת id retag — free the target id if the fe row already sits elsewhere.
    # (82855 is unused in fe; 82859 is the fe row.)
    clash = con.execute("SELECT COUNT(*) FROM sense WHERE id=?", (DUK_SVC_ID,)).fetchone()[0]
    if clash:
        raise RuntimeError(f"frontend already has sense id {DUK_SVC_ID}; manual review needed")
    con.execute("UPDATE sense SET id=? WHERE id=?", (DUK_SVC_ID, DUK_FE_ID))
    # divine-name headword
    con.execute("UPDATE word SET headword=? WHERE id=5440", (DIVINE_NAME,))
    # junk sense (already absent in fe, but delete defensively)
    con.execute("DELETE FROM sense WHERE id=?", (JUNK_SENSE_ID,))
    if dry:
        con.rollback()
    else:
        con.commit()


def fix_service(con, dry):
    con.execute("BEGIN")
    con.execute("DELETE FROM sense WHERE id=?", (JUNK_SENSE_ID,))
    if dry:
        con.rollback()
    else:
        con.commit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    for p in (SVC, FE):
        if not os.path.exists(p):
            sys.exit(f"missing DB: {p}")

    s = sqlite3.connect(SVC)
    f = sqlite3.connect(FE)
    try:
        fix_service(s, a.dry_run)
        fix_frontend(f, a.dry_run)

        if not a.dry_run:
            for c in (s, f):
                ic = c.execute("PRAGMA integrity_check").fetchone()[0]
                if ic != "ok":
                    sys.exit(f"integrity_check failed: {ic}")
                c.execute("PRAGMA wal_checkpoint(TRUNCATE)")

        hs, hf = content_hash(s), content_hash(f)
        ns = s.execute("SELECT COUNT(*) FROM sense").fetchone()[0]
        nf = f.execute("SELECT COUNT(*) FROM sense").fetchone()[0]
        tag = "[dry-run] " if a.dry_run else ""
        print(f"{tag}service sense={ns}  frontend sense={nf}")
        print(f"{tag}content hash svc={hs[:16]}  fe={hf[:16]}")
        print(f"{tag}COPIES IDENTICAL" if hs == hf else f"{tag}STILL DIFFER")
    finally:
        s.close()
        f.close()


if __name__ == "__main__":
    main()
