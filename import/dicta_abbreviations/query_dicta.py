"""Asks Dicta's abbreviation expander about every abbreviation headword; resumable.

Every headword in source/words.tsv that contains a quote mark (" ' gershayim geresh) is sent,
many per request (joined by newlines). Answers are appended to a JSONL cache after every batch
(see dicta_common.py); a rerun skips every headword already in the cache, so a failed or
stopped run just continues. With --git-push DIR the cache (inside the git checkout DIR) is
committed and pushed after every batch, so progress survives a cancelled CI run.

Run: python import/dicta_abbreviations/query_dicta.py --cache PATH [--batch-size 50]
       [--max-batches N] [--deadline-minutes 330] [--limit N] [--git-push DIR]
Exit code 0 also on a clean early stop (deadline, max batches, blocked); 1 only on a bug.
"""

import argparse
import json
import os
import random
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dicta_common as dc  # noqa: E402

HOSTS = ["https://nakdan-u2-1a.loadbalancer.dicta.org.il/api",
         "https://nakdan-u1-0.loadbalancer.dicta.org.il/api",
         "https://nakdan-5-1.loadbalancer.dicta.org.il/api"]

# Chain verification stays on; only Python 3.13+'s extra strict-X509 checks are relaxed, which
# some filtering proxies' CA certificates fail.
_SSL = ssl.create_default_context()
_SSL.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)


class Blocked(Exception):
    pass


def post(host, text, timeout):
    body = json.dumps({"task": "abbrexp", "data": text, "genre": "rabbinic",
                       "useTokenization": True, "userData": "gave permission"}).encode("utf-8")
    req = urllib.request.Request(host, body, {"Content-Type": "text/plain;charset=UTF-8",
                                              "User-Agent": "KitveiHakodeshDictionary-builder"})
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL) as r:
        return json.load(r)


def ask(headwords, attempts, timeout):
    """One batch -> {headword: [ {word, options}, ... ]}. Retries with backoff across hosts."""
    text = "\n".join(headwords)
    last = None
    for attempt in range(attempts):
        host = HOSTS[attempt % len(HOSTS)]
        try:
            data = post(host, text, timeout)["data"]
            break
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code} from {host}"
            wait = 2 ** attempt * 5
            if e.code == 429 and e.headers.get("Retry-After", "").isdigit():
                wait = max(wait, int(e.headers["Retry-After"]))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError) as e:
            last = f"{type(e).__name__} from {host}: {e}"
            wait = 2 ** attempt * 5
        wait = min(wait, 300) + random.uniform(0, 2)
        print(f"  retry {attempt + 1}/{attempts} in {wait:.0f}s: {last}", flush=True)
        time.sleep(wait)
    else:
        raise Blocked(last)

    lines, cur = [], []
    for tok in data:
        if tok.get("str") == "\n":
            lines.append(cur)
            cur = []
        elif tok.get("abbreviation"):
            a = tok["abbreviation"]
            cur.append({"word": a.get("word", tok.get("str")), "options": a.get("options") or []})
    lines.append(cur)
    if len(lines) != len(headwords):
        raise Blocked(f"answer has {len(lines)} lines for {len(headwords)} headwords")
    return dict(zip(headwords, lines))


def git_push(repo, path, message):
    rel = os.path.relpath(path, repo)
    subprocess.run(["git", "-C", repo, "add", rel], check=True)
    if subprocess.run(["git", "-C", repo, "diff", "--cached", "--quiet"]).returncode == 0:
        return
    subprocess.run(["git", "-C", repo, "commit", "-q", "-m", message], check=True)
    for attempt in range(5):
        if subprocess.run(["git", "-C", repo, "push", "-q", "origin", "HEAD"]).returncode == 0:
            return
        time.sleep(5 * (attempt + 1))
    raise RuntimeError("git push of the cache failed 5 times")


def main():
    dc.utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--max-batches", type=int, default=0, help="0 = no limit")
    ap.add_argument("--deadline-minutes", type=float, default=330)
    ap.add_argument("--limit", type=int, default=0, help="only the first N abbreviations (sample)")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between batches")
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--max-failed-batches", type=int, default=5,
                    help="stop after this many batches in a row fail every retry (blocked)")
    ap.add_argument("--git-push", metavar="REPO_DIR")
    a = ap.parse_args()

    start = time.time()
    todo_all = [hw for _, hw in dc.abbreviation_headwords()]
    if a.limit:
        todo_all = todo_all[:a.limit]
    done = dc.read_cache(a.cache)
    todo = [hw for hw in todo_all if hw not in done]
    print(f"[dicta] abbreviations {len(todo_all)}, already cached {len(todo_all) - len(todo)}, "
          f"to do {len(todo)}, batch size {a.batch_size}", flush=True)

    os.makedirs(os.path.dirname(os.path.abspath(a.cache)), exist_ok=True)
    batches = failed_batches = failed_in_row = new = 0
    stop = "all done"
    for i in range(0, len(todo), a.batch_size):
        if a.max_batches and batches >= a.max_batches:
            stop = "max batches reached"
            break
        if (time.time() - start) / 60 > a.deadline_minutes:
            stop = "deadline reached"
            break
        chunk = todo[i:i + a.batch_size]
        batches += 1
        try:
            answers = ask(chunk, a.attempts, a.timeout)
            failed_in_row = 0
        except Blocked as e:
            failed_batches += 1
            failed_in_row += 1
            print(f"[dicta] batch {batches} FAILED ({e}); left for a rerun", flush=True)
            if failed_in_row >= a.max_failed_batches:
                stop = f"{failed_in_row} batches in a row failed - blocked or down"
                break
            continue
        with open(a.cache, "a", encoding="utf-8", newline="\n") as f:
            for hw in chunk:
                f.write(json.dumps({"hw": hw, "abbr": answers[hw]}, ensure_ascii=False) + "\n")
        new += len(chunk)
        if a.git_push:
            git_push(a.git_push, a.cache, f"dicta cache: +{len(chunk)} ({len(done) + new} total)")
        print(f"[dicta] batch {batches}: +{len(chunk)}, done {len(todo_all) - len(todo) + new}"
              f"/{len(todo_all)}, {time.time() - start:.0f}s", flush=True)
        time.sleep(a.pause)

    done = dc.read_cache(a.cache)
    cached = [hw for hw in todo_all if hw in done]
    with_opts = [hw for hw in cached if dc.ranked_options(done[hw])]
    print(f"[dicta] STOP: {stop}", flush=True)
    print(f"[dicta] SUMMARY total {len(todo_all)} | done {len(cached)} | remaining "
          f"{len(todo_all) - len(cached)} | failed batches this run {failed_batches} | "
          f"with expansions {len(with_opts)}", flush=True)
    for hw in with_opts[-8:]:
        print(f"[dicta] sample {hw} -> {' | '.join(dc.ranked_options(done[hw])[:4])}", flush=True)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"remaining={len(todo_all) - len(cached)}\n")


if __name__ == "__main__":
    main()
