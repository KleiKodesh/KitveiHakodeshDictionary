"""Downloads the re-fetchable sources listed in sources.json and checks their sha256.

Fails (exit 1) on any mismatch: a changed upstream file must be a deliberate manifest
update (new pin + new sha256), never a silent change.

Run: python -I fetch/fetch_sources.py [source-id ...]      (default: every fetchable source)
"""

import hashlib
import json
import os
import sys
import subprocess
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def download(url):
    """urllib first; curl as fallback (uses the OS certificate store, e.g. behind a
    filtering proxy whose CA Python rejects). The sha256 check guards either way."""
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    except OSError as e:
        print(f"[fetch] urllib failed ({e.__class__.__name__}); retrying with curl", flush=True)
        return subprocess.run(["curl", "-fsSL", "--max-time", "300", url],
                              check=True, capture_output=True).stdout


def main(wanted):
    with open(os.path.join(ROOT, "sources.json"), encoding="utf-8") as f:
        sources = [s for s in json.load(f)["sources"] if s.get("fetch")]
    if wanted:
        sources = [s for s in sources if s["id"] in wanted]
    failed = 0
    for s in sources:
        dest = os.path.join(ROOT, s["local_path"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"[fetch] {s['id']}: {s['origin']}", flush=True)
        data = download(s["origin"])
        digest = hashlib.sha256(data).hexdigest()
        if digest != s["sha256"]:
            print(f"[fetch] SHA256 MISMATCH for {s['id']}: got {digest}, manifest {s['sha256']}")
            failed += 1
            continue
        with open(dest, "wb") as f:
            f.write(data)
        print(f"[fetch] ok -> {s['local_path']} ({len(data)} bytes, sha256 verified)", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
