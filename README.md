# KitveiHakodeshDictionary

The source of the dictionary database (`Dictionary.db`) used by Kitvei Hakodesh
(KleiKodesh). Everything needed to rebuild it lives here, as readable UTF-8 TSV files.

## Where the DB lives

The app's one working copy is
`KleiKodeshProject/KitveiHakodesh/CSharpBackend/KitveiHakodesh.Core/Dictionary/Dictionary.db`
(committed in KleiKodeshProject). Clone this repo as a sibling folder there:

    cd KleiKodeshProject
    git clone https://github.com/KleiKodesh/KitveiHakodeshDictionary.git

and every script here reads and writes that file directly (see `db_path.py`). In a
stand-alone clone they use `build/Dictionary.db`. This repo does not commit a DB and
publishes no releases.

## Layout

| Path | What |
|---|---|
| `source/schema.sql` | table and index definitions |
| `source/source_kind.tsv`, `source/link_kind.tsv` | source and link kinds |
| `source/words.tsv` | every headword with its id |
| `source/senses/source_NN.tsv` | the senses of source_kind NN (one file per source) |
| `source/links.tsv` | links between words (ids authoritative, headwords for reading) |
| `source/seforim_headword*.tsv` | headword index into reference works in seforim.db |
| `source/sqlite_stat1.tsv` | query-planner statistics |
| `sources.json` | manifest: origin, pin, sha256, license, fetch script, what each source feeds |
| `fetch/fetch_sources.py` | downloads the re-fetchable sources, verifies sha256 |
| `import/` | import scripts and audit data (how each source got in) |
| `import/thesaurus_links/` | older one-off synonym-link tools, moved from the app repo as-is (their paths are the old app layout) |
| `build.py` / `export.py` / `verify.py` | build the DB / write a DB back to `source/` / row-diff two DBs |
| `db_path.py` | where the DB is: the app copy when found, else `build/Dictionary.db` |
| `.github/workflows/build-dictionary.yml` | CI on push: verify pinned sources, build, round-trip check (no release) |

TSV format: header line, tab-separated, LF, escapes `\\ \t \n \r`, NULL = `\N` (see `tsv.py`).

## Build

    python build.py                 # -> the app's Dictionary.db, or build/Dictionary.db (Python 3.9+, stdlib only)

## Change the dictionary

    python build.py                            # DB = source/ (overwrites local DB edits!)
    python -I fetch/fetch_sources.py           # only if the import needs an upstream file
    python import/<script>.py                  # or edit the DB by hand; changes the DB in place
    python export.py                           # writes the change into source/
    python build.py && git add source sources.json && git commit
    # then commit the updated Dictionary.db in KleiKodeshProject

## Licenses

Per-source licenses and attribution are in `sources.json`. Data from the Otzaria project
(github.com/Otzaria/otzaria) is used under its license with attribution.
