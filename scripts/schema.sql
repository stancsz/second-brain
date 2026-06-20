-- SecondBrain schema v3.0 (OKF v0.1)
-- v2.1 -> v3.0: 'drawers' -> 'concepts', 'drawer_tags' -> 'concept_tags',
-- 'drawer_id' -> 'concept_id'. FTS5 + triggers renamed to match.
-- Migration is performed by SecondBrain._migrate_v21_to_concepts() BEFORE
-- this script runs, so on a v2.1 DB the table list is already
-- 'concepts'-flavored and the IF NOT EXISTS clauses below are no-ops.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

-- ---------------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS concepts (
    id          TEXT      PRIMARY KEY,
    title       TEXT      NOT NULL,
    content     TEXT      NOT NULL,
    collection  TEXT      DEFAULT NULL,
    sources     TEXT      DEFAULT '[]',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at  TIMESTAMP DEFAULT NULL,
    metadata    TEXT      DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_concepts_collection
    ON concepts(collection) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_concepts_updated
    ON concepts(updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_concepts_title_nocase
    ON concepts(title COLLATE NOCASE) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS tags (
    id         TEXT      PRIMARY KEY,
    name       TEXT      NOT NULL UNIQUE,
    color      TEXT      DEFAULT '#3b82f6',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS concept_tags (
    concept_id TEXT NOT NULL,
    tag_id     TEXT NOT NULL,
    PRIMARY KEY (concept_id, tag_id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)     REFERENCES tags(id)     ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_concept_tags_tag ON concept_tags(tag_id);

CREATE TABLE IF NOT EXISTS relations (
    id            TEXT      PRIMARY KEY,
    from_id       TEXT      NOT NULL,
    to_id         TEXT      NOT NULL,
    relation_type TEXT      NOT NULL DEFAULT 'related',
    strength      REAL               DEFAULT 0.5,
    source        TEXT               DEFAULT 'manual',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (to_id)   REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE (from_id, to_id, source)
);
CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_id);
CREATE INDEX IF NOT EXISTS idx_relations_to   ON relations(to_id);

CREATE TABLE IF NOT EXISTS pending_links (
    id            TEXT PRIMARY KEY,
    from_id       TEXT NOT NULL,
    target_title  TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_id) REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE (from_id, target_title)
);
CREATE INDEX IF NOT EXISTS idx_pending_target
    ON pending_links(target_title COLLATE NOCASE);

-- ---------------------------------------------------------------------------
-- Full-text search (external-content FTS5 over concepts)
-- ---------------------------------------------------------------------------

CREATE VIRTUAL TABLE IF NOT EXISTS concepts_fts USING fts5(
    title, content,
    content=concepts,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS concepts_ai AFTER INSERT ON concepts BEGIN
  INSERT INTO concepts_fts(rowid, title, content)
  VALUES (new.rowid, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS concepts_ad AFTER DELETE ON concepts BEGIN
  INSERT INTO concepts_fts(concepts_fts, rowid, title, content)
  VALUES ('delete', old.rowid, old.title, old.content);
END;

CREATE TRIGGER IF NOT EXISTS concepts_au AFTER UPDATE ON concepts BEGIN
  INSERT INTO concepts_fts(concepts_fts, rowid, title, content)
  VALUES ('delete', old.rowid, old.title, old.content);
  INSERT INTO concepts_fts(rowid, title, content)
  VALUES (new.rowid, new.title, new.content);
END;

-- ---------------------------------------------------------------------------
-- Meta
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS _meta (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO _meta VALUES ('schema_version', '2', CURRENT_TIMESTAMP);

-- ---------------------------------------------------------------------------
-- Psychological subjects (G08 / R10)
-- Derived from concepts; one row per `type: Person` Concept path, plus the
-- implicit `/people/self.md` default. sb_id stores the Bundle path (e.g.
-- `/people/rox.md`), not a UUID — the OKF Concept's path IS its identity, and
-- `sb_subject` frontmatter uses the same path.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS subjects (
    sb_id        TEXT PRIMARY KEY,   -- the path, e.g. /people/rox.md or /people/self.md
    slug         TEXT NOT NULL,      -- last path segment without .md, e.g. "rox"
    display_name TEXT,               -- title of the Person Concept (or 'self')
    kind         TEXT NOT NULL DEFAULT 'Person'
);

CREATE TABLE IF NOT EXISTS concept_subject (
    concept_id  TEXT NOT NULL,
    subject_id  TEXT NOT NULL,
    PRIMARY KEY (concept_id, subject_id),
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(sb_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_concept_subject_subject ON concept_subject(subject_id);

-- ---------------------------------------------------------------------------
-- Structured affect (G10 / R12)
-- One row per Concept that carries an `sb_affect` mapping. Dimensions follow the
-- circumplex model (valence/arousal in [-1,1]) plus a free-text `emotion` label
-- and `intensity` in [0,1]. All dimensions are nullable: a memory may name an
-- emotion without scoring it, or score valence without the rest. The row exists
-- iff the Concept has affect — affectless Concepts have NO row. Derived from
-- concepts.metadata.sb_affect; rebuilt by SecondBrain.rebuild_affect_index().
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS affect (
    concept_id TEXT PRIMARY KEY,
    valence    REAL,   -- pleasant(+1) .. unpleasant(-1)
    arousal    REAL,   -- activated(+1) .. calm(-1 / 0)
    emotion    TEXT,   -- free-text label, e.g. "grief", "joy"
    intensity  REAL,   -- 0 (faint) .. 1 (overwhelming)
    FOREIGN KEY (concept_id) REFERENCES concepts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_affect_emotion   ON affect(emotion);
CREATE INDEX IF NOT EXISTS ix_affect_intensity ON affect(intensity);
