"""Table-by-table row diff of two Dictionary.db files (build_meta is ignored).

Run: python verify.py <reference.db> <built.db>       exit 1 on any difference
"""

import sqlite3
import sys


def rows(con, table):
    cols = [c[1] for c in con.execute(f"PRAGMA table_info([{table}])")]
    return sorted(con.execute(f"SELECT {','.join('['+c+']' for c in cols)} FROM [{table}]").fetchall(),
                  key=repr)


def main(a, b):
    ca, cb = sqlite3.connect(a), sqlite3.connect(b)
    master = "SELECT type, name, sql FROM sqlite_master WHERE tbl_name <> 'build_meta' ORDER BY name"
    ok = True
    sa, sb = ca.execute(master).fetchall(), cb.execute(master).fetchall()
    print(f"[verify] schema objects: {len(sa)} vs {len(sb)} -> {'same' if sa == sb else 'DIFFERENT'}")
    ok &= sa == sb
    tables = [n for t, n, _ in sa if t == "table"]
    for t in tables:
        ra, rb = rows(ca, t), rows(cb, t)
        same = ra == rb
        ok &= same
        extra = "" if same else f"  (only-in-ref {len(set(ra)-set(rb))}, only-in-built {len(set(rb)-set(ra))})"
        print(f"[verify] {t}: {len(ra)} vs {len(rb)} rows -> {'same' if same else 'DIFFERENT'}{extra}")
    print("[verify] RESULT:", "IDENTICAL CONTENT" if ok else "DIFFERENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
