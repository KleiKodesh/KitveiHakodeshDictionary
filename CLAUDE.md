# Rule: this repo is the source of truth for Dictionary.db

- Everything that makes `Dictionary.db` lives here: `source/` TSV files, import scripts,
  audit data, fetch scripts. Never only in a temp dir, a local install or another repo.
- The ONE working copy of the DB is the app's
  `KleiKodeshProject/KitveiHakodesh/CSharpBackend/KitveiHakodesh.Core/Dictionary/Dictionary.db`.
  When this repo is cloned as a sibling folder inside KleiKodeshProject, `build.py`,
  `export.py` and every `import/` script read and write that file directly (`db_path.py`);
  otherwise they use `build/Dictionary.db`. This repo never commits a DB.
- Change `source/` (directly, or edit the DB / run an `import/` script and then
  `python export.py`), then `python build.py`. Commit `source/` here and the DB in KleiKodeshProject.
- CI (`.github/workflows/build-dictionary.yml`) only verifies: on every push it checks the
  pinned sources, builds the DB and runs the round-trip check. It publishes no releases
  (old releases stay as history; nothing downloads them any more).
- `python verify.py <old.db> <new.db>` must show only the rows you meant to change.

# Rule: every source is tracked in sources.json

One entry per source: name, description, origin URL, exact pin (upstream commit SHA,
release tag or download date), sha256 of the raw file as fetched, license + attribution,
the fetch script, and which tables / source_kinds it feeds.

- Fetch scripts verify the sha256 and fail on a mismatch. A changed upstream file means a
  deliberate manifest update (new pin + new sha256) in the same commit.
- `build.py` stamps the sources.json sha256, every pin and every source-file sha256 into
  the DB's `build_meta` table.
- A source whose origin is unknown is marked
  `"pin": "frozen: extracted from Dictionary.db on 2026-11-03"`; its TSV is now the original.
- Adding a source = new `sources.json` entry + fetch script (if downloadable) + import script.

Example: Otzaria `assets/dictionary.json` is pinned to commit a4c54cd2 with its sha256;
`fetch/fetch_sources.py` downloads exactly that file.

# Commits

Every commit body ends with `User-facing: ...` and `User-facing-he: ...` lines as in the
KleiKodeshProject CLAUDE.md (dictionary content changes are user-facing: Area = Dictionary).

# Later consideration: auto-chaining dictionary -> SearchExpansion

None. SearchExpansion reads the dictionary from the app's Dictionary.db (or this repo's
build/) whenever it is built; rebuild it after a dictionary change.
