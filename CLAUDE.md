# Rule: this repo is the source of truth for Dictionary.db

- Everything that makes `Dictionary.db` lives here: `source/` TSV files, import scripts,
  audit data, fetch scripts. Never only in a temp dir, a local install or another repo.
- Never hand-edit a `Dictionary.db` anywhere (not in the app repo either). Change
  `source/` (directly or via `import/` + `python export.py`), then `python build.py`.
- CI (`.github/workflows/build-dictionary.yml`) builds on every push to `main` and
  publishes a GitHub Release marked latest, with `Dictionary.db` attached.
- The app (KleiKodeshProject, where this repo is a git submodule) always downloads the
  latest release at build time. It never ships a committed copy.
- `python verify.py <old.db> <new.db>` must show only the rows you meant to change.

# Rule: every source is tracked in sources.json

One entry per source: name, description, origin URL, exact pin (upstream commit SHA,
release tag or download date), sha256 of the raw file as fetched, license + attribution,
the fetch script, and which tables / source_kinds it feeds.

- Fetch scripts verify the sha256 and fail on a mismatch. A changed upstream file means a
  deliberate manifest update (new pin + new sha256) in the same commit.
- `build.py` stamps the sources.json sha256, every pin and every source-file sha256 into
  the DB's `build_meta` table; the release notes list them.
- A source whose origin is unknown is marked
  `"pin": "frozen: extracted from Dictionary.db on 2026-11-03"`; its TSV is now the original.
- Adding a source = new `sources.json` entry + fetch script (if downloadable) + import script.

Example: Otzaria `assets/dictionary.json` is pinned to commit a4c54cd2 with its sha256;
`fetch/fetch_sources.py` downloads exactly that file.

# Commits

Every commit body ends with `User-facing: ...` and `User-facing-he: ...` lines as in the
KleiKodeshProject CLAUDE.md (dictionary content changes are user-facing: Area = Dictionary).

# Later consideration: auto-chaining dictionary -> SearchExpansion

Decision of 2026-11-03: there is NO automatic chaining yet. A new dictionary release does
not rebuild SearchExpansion; SearchExpansion picks up the new dictionary only on its next
push or manual workflow run.

Option for later: the dictionary release workflow could trigger the SearchExpansion build
through `repository_dispatch` (event_type `dictionary-released`, which
`build-expansion.yml` already accepts). That needs a PAT secret in the dictionary repo and
a `gh api repos/KleiKodesh/SearchExpansion/dispatches` step.
