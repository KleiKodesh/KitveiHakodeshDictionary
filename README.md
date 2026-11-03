# KitveiHakodeshDictionary

The source of the dictionary database (`Dictionary.db`) used by Kitvei Hakodesh
(KleiKodesh). Everything needed to rebuild it lives here, as readable UTF-8 TSV files.

## Download

Latest build (published by CI on every push to `main`):

    https://github.com/KleiKodesh/KitveiHakodeshDictionary/releases/latest/download/Dictionary.db

Each release also carries `Dictionary.db.sha256` and the `sources.json` it was built from.

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
| `build.py` / `export.py` / `verify.py` | build the DB / write a DB back to `source/` / row-diff two DBs |

TSV format: header line, tab-separated, LF, escapes `\\ \t \n \r`, NULL = `\N` (see `tsv.py`).

## Build

    python build.py                 # -> build/Dictionary.db (Python 3.9+, stdlib only)

## Change the dictionary

    python build.py
    python -I fetch/fetch_sources.py           # only if the import needs an upstream file
    python import/<script>.py                  # changes build/Dictionary.db
    python export.py                           # writes the change into source/
    python build.py && git add source sources.json && git commit

## Licenses

Per-source licenses and attribution are in `sources.json`. Data from the Otzaria project
(github.com/Otzaria/otzaria) is used under its license with attribution.
