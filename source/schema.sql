CREATE TABLE link_kind (
        id   INTEGER PRIMARY KEY,
        name TEXT    NOT NULL UNIQUE
    , explanation TEXT);

CREATE TABLE "source_kind" (
        id   INTEGER PRIMARY KEY,
        name TEXT    NOT NULL UNIQUE
    );

CREATE TABLE word (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        headword TEXT    NOT NULL UNIQUE
    );

CREATE TABLE "sense" (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        word_id   INTEGER NOT NULL REFERENCES word(id),
        nikud     TEXT,
        text      TEXT    NOT NULL,
        source_id INTEGER REFERENCES source_kind(id)
    );

CREATE TABLE "link" (
        word_id   INTEGER NOT NULL REFERENCES word(id),
        target_id INTEGER NOT NULL REFERENCES word(id),
        kind_id   INTEGER NOT NULL REFERENCES link_kind(id),
        PRIMARY KEY (word_id, target_id, kind_id)
    );

CREATE TABLE seforim_headword_book (
        id    INTEGER PRIMARY KEY,
        -- The book's title exactly as seforim.db spells it. Resolved to a bookId at lookup
        -- time, because ids are not stable across library rebuilds but titles are.
        title TEXT NOT NULL UNIQUE
    );

CREATE TABLE seforim_headword (
        -- Which reference work this entry belongs to; each one is parsed differently.
        source    TEXT    NOT NULL,
        bookId    INTEGER NOT NULL REFERENCES seforim_headword_book(id),
        -- Position of the headword line within its book. Stable across rebuilds in a way
        -- line.id is not.
        lineIndex INTEGER NOT NULL,
        -- One row per token of the headword, so a lookup on any single word of a
        -- multi-word headword finds the entry. The full headword is not stored: the
        -- caller re-reads it from the line it fetches, which also catches a stale index.
        word      TEXT    NOT NULL
    );

CREATE INDEX index_word_headword  ON word(headword);

CREATE INDEX index_sense_word     ON sense(word_id);

CREATE INDEX index_link_word      ON link(word_id);

CREATE INDEX index_link_target    ON link(target_id);

CREATE INDEX index_seforim_headword_source_word ON seforim_headword(source, word);
