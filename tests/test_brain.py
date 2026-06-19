#!/usr/bin/env python3
"""Comprehensive test suite for SecondBrain (scripts/brain.py).

Run with:  python -m unittest tests/test_brain.py
or:        python tests/test_brain.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Allow importing from the sibling scripts/ directory regardless of cwd.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from brain import SecondBrain


class TestBrain(unittest.TestCase):
    """All tests share a single class; each test gets a fresh DB via setUp."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        db_path = Path(self.tmpdir) / "brain.db"
        self.b = SecondBrain(db_path)

    def tearDown(self):
        try:
            self.b.close()
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # 1. Basic CRUD
    # -----------------------------------------------------------------------

    def test_add_returns_concept_with_correct_fields(self):
        dr = self.b.add("Alpha", "hello world", collection="notes", tags=["a", "b"])
        self.assertEqual(dr["title"], "Alpha")
        self.assertEqual(dr["content"], "hello world")
        self.assertEqual(dr["collection"], "notes")
        self.assertIn("a", dr["tags"])
        self.assertIn("b", dr["tags"])
        self.assertIsNotNone(dr["id"])

    def test_get_returns_none_for_missing(self):
        result = self.b.get("nonexistent-id")
        self.assertIsNone(result)

    def test_get_roundtrip(self):
        dr = self.b.add("Beta", "some content")
        fetched = self.b.get(dr["id"])
        self.assertEqual(fetched["id"], dr["id"])
        self.assertEqual(fetched["title"], "Beta")
        self.assertEqual(fetched["content"], "some content")

    def test_update_changes_title_and_content(self):
        dr = self.b.add("Old Title", "old content")
        updated = self.b.update(dr["id"], title="New Title", content="new content")
        self.assertEqual(updated["title"], "New Title")
        self.assertEqual(updated["content"], "new content")

    def test_update_returns_none_for_missing(self):
        result = self.b.update("nonexistent", content="x")
        self.assertIsNone(result)

    def test_delete_soft_removes_from_get(self):
        dr = self.b.add("ToDelete", "bye")
        self.b.delete(dr["id"])
        self.assertIsNone(self.b.get(dr["id"]))

    def test_delete_hard_removes_from_db(self):
        dr = self.b.add("HardGone", "poof")
        self.b.delete(dr["id"], hard=True)
        self.assertIsNone(self.b.get(dr["id"]))
        row = self.b.con.execute(
            "SELECT 1 FROM concepts WHERE id=?", (dr["id"],)
        ).fetchone()
        self.assertIsNone(row)

    def test_delete_returns_false_for_missing(self):
        result = self.b.delete("no-such-id")
        self.assertFalse(result)

    def test_list_excludes_deleted(self):
        dr = self.b.add("Visible", "yes")
        self.b.add("Hidden", "no")
        self.b.delete(
            self.b.get_by_title("Hidden")[0]["id"]
        )
        titles = [d["title"] for d in self.b.list(limit=100)]
        self.assertIn("Visible", titles)
        self.assertNotIn("Hidden", titles)

    # -----------------------------------------------------------------------
    # 2. FTS triggers: update — old content gone, new content findable
    # -----------------------------------------------------------------------

    def test_fts_update_old_content_gone(self):
        dr = self.b.add("FTSUpdate", "unique_old_keyword_xyz")
        # Old content should be findable.
        results = self.b.search("unique_old_keyword_xyz")
        self.assertTrue(any(r["id"] == dr["id"] for r in results))

        # Update — old content replaced.
        self.b.update(dr["id"], content="completely different text now")
        results_after = self.b.search("unique_old_keyword_xyz")
        self.assertFalse(any(r["id"] == dr["id"] for r in results_after))

    def test_fts_update_new_content_findable(self):
        dr = self.b.add("FTSUpdate2", "original stuff")
        self.b.update(dr["id"], content="brand_new_content_abc")
        results = self.b.search("brand_new_content_abc")
        self.assertTrue(any(r["id"] == dr["id"] for r in results))

    # -----------------------------------------------------------------------
    # 3. FTS triggers: hard delete — content gone from search
    # -----------------------------------------------------------------------

    def test_fts_hard_delete_removes_from_search(self):
        dr = self.b.add("FTSDelete", "findable_before_delete_qqq")
        results_before = self.b.search("findable_before_delete_qqqq")
        # The AFTER DELETE trigger should clean up the FTS index.
        self.b.delete(dr["id"], hard=True)
        results_after = self.b.search("findable_before_delete_qqqq")
        self.assertEqual(len(results_after), 0)

    def test_fts_hard_delete_ad_trigger(self):
        """Directly verify the FTS rowid is gone from the index after hard delete."""
        dr = self.b.add("TriggerCheck", "canary_word_for_ad_trigger")
        rowid = self.b.con.execute(
            "SELECT rowid FROM concepts WHERE id=?", (dr["id"],)
        ).fetchone()[0]
        self.b.delete(dr["id"], hard=True)
        # The FTS shadow table content should not contain the canary word anymore.
        fts_hit = self.b.con.execute(
            "SELECT rowid FROM concepts_fts WHERE concepts_fts MATCH 'canary_word_for_ad_trigger'"
        ).fetchall()
        self.assertEqual(len(fts_hit), 0)

    # -----------------------------------------------------------------------
    # 4. Soft delete: concept hidden; restore brings it back with wikilinks
    # -----------------------------------------------------------------------

    def test_soft_delete_hidden_from_search(self):
        target = self.b.add("SoftTarget", "content alpha")
        self.b.delete(target["id"])
        results = self.b.search("content alpha")
        ids = [r["id"] for r in results]
        # Soft-deleted row must be absent from FTS join (deleted_at IS NULL filter).
        self.assertNotIn(target["id"], ids)

    def test_soft_delete_hidden_from_list(self):
        dr = self.b.add("SoftListed", "some text")
        self.b.delete(dr["id"])
        listed = self.b.list(limit=100)
        ids = [d["id"] for d in listed]
        self.assertNotIn(dr["id"], ids)

    def test_restore_brings_back_concept(self):
        dr = self.b.add("Resurrect", "I will return")
        self.b.delete(dr["id"])
        self.assertIsNone(self.b.get(dr["id"]))
        ok = self.b.restore(dr["id"])
        self.assertTrue(ok)
        restored = self.b.get(dr["id"])
        self.assertIsNotNone(restored)
        self.assertEqual(restored["title"], "Resurrect")

    def test_restore_rederives_wikilinks(self):
        """After restoring a concept that references another, the wikilink
        relation must be re-established."""
        target = self.b.add("RestoredTarget", "I am the target")
        src = self.b.add("RestoredSource", "See [[RestoredTarget]] for details")
        # Confirm link was created.
        rels_before = self.b.related(src["id"])
        self.assertTrue(any(r["id"] == target["id"] for r in rels_before))

        # Soft-delete and restore the source.
        self.b.delete(src["id"])
        self.b.restore(src["id"])
        rels_after = self.b.related(src["id"])
        self.assertTrue(any(r["id"] == target["id"] for r in rels_after))

    def test_restore_returns_false_for_live_concept(self):
        dr = self.b.add("NeverDeleted", "alive")
        self.assertFalse(self.b.restore(dr["id"]))

    # -----------------------------------------------------------------------
    # 5. Wikilink resolution at add time
    # -----------------------------------------------------------------------

    def test_wikilink_resolved_at_add_time(self):
        target = self.b.add("Target Node", "I am the target")
        source = self.b.add("Source Node", "This references [[Target Node]].")
        rels = self.b.related(source["id"])
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]["id"], target["id"])
        self.assertEqual(rels[0]["dir"], "out")

    def test_wikilink_relation_type_is_references(self):
        target = self.b.add("WikiTarget", "content")
        source = self.b.add("WikiSource", "[[WikiTarget]]")
        rels = self.b.related(source["id"], source="wikilink")
        self.assertTrue(any(r["relation_type"] == "references" for r in rels))

    def test_wikilink_no_self_loop(self):
        dr = self.b.add("SelfRef", "I mention [[SelfRef]] here")
        rels = self.b.related(dr["id"])
        # Must not contain a self-referential edge.
        self.assertFalse(any(r["id"] == dr["id"] for r in rels))

    def test_wikilink_case_insensitive_resolution(self):
        target = self.b.add("CaseTarget", "content here")
        source = self.b.add("CaseSource", "Link to [[casetarget]]")
        rels = self.b.related(source["id"])
        self.assertTrue(any(r["id"] == target["id"] for r in rels))

    # -----------------------------------------------------------------------
    # 6. Pending links
    # -----------------------------------------------------------------------

    def test_pending_link_created_for_unknown_target(self):
        src = self.b.add("PendSource", "Mentions [[FutureConcept]] which doesn't exist")
        pending = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["target_title"], "FutureConcept")

    def test_pending_link_resolves_when_target_added(self):
        src = self.b.add("EarlySource", "Waiting for [[LateTarget]]")
        # Confirm pending.
        pending_before = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending_before), 1)

        # Now add the target.
        target = self.b.add("LateTarget", "I have arrived")

        # Pending row should be gone.
        pending_after = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending_after), 0)

        # A real relation must now exist.
        rels = self.b.related(src["id"])
        self.assertTrue(any(r["id"] == target["id"] for r in rels))

    def test_pending_link_resolves_on_retitle(self):
        """Renaming a concept to match a pending link target resolves the link."""
        src = self.b.add("WaitingSource", "Waiting for [[EventualName]]")
        existing = self.b.add("WorkingName", "I'll be renamed")

        pending_before = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending_before), 1)

        # Rename to the pending title.
        self.b.update(existing["id"], title="EventualName")

        pending_after = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending_after), 0)

        rels = self.b.related(src["id"])
        self.assertTrue(any(r["id"] == existing["id"] for r in rels))

    def test_no_pending_link_when_target_exists(self):
        target = self.b.add("AlreadyThere", "pre-existing")
        src = self.b.add("EagerSource", "I link to [[AlreadyThere]]")
        pending = self.b.con.execute(
            "SELECT * FROM pending_links WHERE from_id=?", (src["id"],)
        ).fetchall()
        self.assertEqual(len(pending), 0)

    # -----------------------------------------------------------------------
    # 7. Archive atomicity
    # -----------------------------------------------------------------------

    def test_archive_moves_old_concept_to_archive_db(self):
        fresh = self.b.add("Fresh", "just added")
        cold = self.b.add("Cold", "very old content")

        # Age the cold concept past the threshold.
        self.b.con.execute(
            "UPDATE concepts SET updated_at=datetime('now','-200 days') WHERE id=?",
            (cold["id"],),
        )
        self.b.con.commit()

        archive_path = Path(self.tmpdir) / "archive.db"
        result = self.b.archive(str(archive_path), older_than_days=180)

        # Cold concept must be gone from the working brain.
        self.assertIsNone(self.b.get(cold["id"]))

        # Fresh concept must remain.
        self.assertIsNotNone(self.b.get(fresh["id"]))

        # Archive DB must contain the cold concept.
        archive = SecondBrain(archive_path)
        try:
            archived_dr = archive.con.execute(
                "SELECT * FROM concepts WHERE id=?", (cold["id"],)
            ).fetchone()
            self.assertIsNotNone(archived_dr)
            self.assertEqual(archived_dr["title"], "Cold")
        finally:
            archive.close()

    def test_archive_result_counts_are_correct(self):
        self.b.add("Keeper", "fresh note")
        cold = self.b.add("OldNote", "stale content")
        self.b.con.execute(
            "UPDATE concepts SET updated_at=datetime('now','-200 days') WHERE id=?",
            (cold["id"],),
        )
        self.b.con.commit()

        archive_path = Path(self.tmpdir) / "archive2.db"
        result = self.b.archive(str(archive_path), older_than_days=180)
        self.assertEqual(result["archived"], 1)
        self.assertEqual(result["remaining"], 1)

    # -----------------------------------------------------------------------
    # 8. Archive refuses-all protection
    # -----------------------------------------------------------------------

    def test_archive_refuses_when_all_concepts_would_be_removed(self):
        """archive() must raise ValueError if every alive concept would be archived."""
        only = self.b.add("OnlyConcept", "all alone")
        self.b.con.execute(
            "UPDATE concepts SET updated_at=datetime('now','-200 days') WHERE id=?",
            (only["id"],),
        )
        self.b.con.commit()

        archive_path = Path(self.tmpdir) / "refuse_archive.db"
        with self.assertRaises(ValueError):
            self.b.archive(str(archive_path), older_than_days=180)

    def test_archive_refuses_multiple_concepts_all_old(self):
        """Same protection with more than one concept, all old."""
        for i in range(3):
            dr = self.b.add(f"OldNote{i}", f"content {i}")
            self.b.con.execute(
                "UPDATE concepts SET updated_at=datetime('now','-200 days') WHERE id=?",
                (dr["id"],),
            )
        self.b.con.commit()

        archive_path = Path(self.tmpdir) / "refuse_all.db"
        with self.assertRaises(ValueError):
            self.b.archive(str(archive_path), older_than_days=180)

    # -----------------------------------------------------------------------
    # 9. Markdown export uses YAML frontmatter
    # -----------------------------------------------------------------------

    def test_markdown_export_has_yaml_frontmatter(self):
        self.b.add(
            "ExportMe", "some body text",
            collection="research", tags=["foo", "bar"]
        )
        md = self.b.export(fmt="markdown")
        self.assertIn("---", md)

    def test_markdown_export_frontmatter_contains_id(self):
        dr = self.b.add("WithID", "body")
        md = self.b.export(fmt="markdown")
        self.assertIn("id:", md)
        self.assertIn(dr["id"], md)

    def test_markdown_export_frontmatter_contains_collection(self):
        self.b.add("WithCollection", "body", collection="mygroup")
        md = self.b.export(fmt="markdown")
        self.assertIn("collection:", md)
        self.assertIn("mygroup", md)

    def test_markdown_export_frontmatter_contains_tags_as_list(self):
        """Tags must appear as a proper YAML list (lines starting with '  - ')."""
        self.b.add("WithTags", "body", tags=["alpha", "beta"])
        md = self.b.export(fmt="markdown")
        self.assertIn("tags:", md)
        self.assertIn("  - alpha", md)
        self.assertIn("  - beta", md)

    def test_markdown_export_collection_collection_filter(self):
        self.b.add("InColl", "coll content", collection="kept")
        self.b.add("NotInColl", "other content", collection="other")
        md = self.b.export(collection="kept", fmt="markdown")
        self.assertIn("InColl", md)
        self.assertNotIn("NotInColl", md)

    # -----------------------------------------------------------------------
    # 10. export_vault writes one .md file per concept
    # -----------------------------------------------------------------------

    def test_export_vault_creates_directory(self):
        self.b.add("VaultA", "content a")
        self.b.add("VaultB", "content b")
        vault_dir = Path(self.tmpdir) / "vault_out"
        self.b.export_vault(str(vault_dir))
        self.assertTrue(vault_dir.exists())
        self.assertTrue(vault_dir.is_dir())

    def test_export_vault_one_file_per_concept(self):
        concepts = [
            self.b.add(f"VaultNote{i}", f"body {i}") for i in range(3)
        ]
        vault_dir = Path(self.tmpdir) / "vault_files"
        self.b.export_vault(str(vault_dir))
        md_files = list(vault_dir.glob("*.md"))
        self.assertEqual(len(md_files), 3)

    def test_export_vault_file_contains_title(self):
        dr = self.b.add("UniqueVaultTitle", "vault content here")
        vault_dir = Path(self.tmpdir) / "vault_single"
        self.b.export_vault(str(vault_dir))
        md_files = list(vault_dir.glob("*.md"))
        self.assertEqual(len(md_files), 1)
        content = md_files[0].read_text()
        self.assertIn("UniqueVaultTitle", content)

    def test_export_vault_file_contains_yaml_frontmatter(self):
        self.b.add("FrontmatterVault", "body text", tags=["x"])
        vault_dir = Path(self.tmpdir) / "vault_fm"
        self.b.export_vault(str(vault_dir))
        md_files = list(vault_dir.glob("*.md"))
        self.assertEqual(len(md_files), 1)
        text = md_files[0].read_text()
        self.assertIn("---", text)
        self.assertIn("id:", text)

    def test_export_vault_excludes_soft_deleted(self):
        live = self.b.add("LiveVault", "stays")
        dead = self.b.add("DeadVault", "goes away")
        self.b.delete(dead["id"])
        vault_dir = Path(self.tmpdir) / "vault_del"
        self.b.export_vault(str(vault_dir))
        md_files = list(vault_dir.glob("*.md"))
        # Only the live concept should appear.
        all_text = "".join(f.read_text() for f in md_files)
        self.assertIn("LiveVault", all_text)
        self.assertNotIn("DeadVault", all_text)

    # -----------------------------------------------------------------------
    # 11. import_ from vault directory round-trips correctly
    # -----------------------------------------------------------------------

    def test_vault_roundtrip_id_preserved(self):
        dr = self.b.add("RoundtripID", "content for id test",
                        collection="rt", tags=["t1"])
        vault_dir = Path(self.tmpdir) / "vault_rt_id"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_id.db"
        b2 = SecondBrain(db2_path)
        try:
            b2.import_(str(vault_dir), mode="merge")
            fetched = b2.get(dr["id"])
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["id"], dr["id"])
        finally:
            b2.close()

    def test_vault_roundtrip_title_preserved(self):
        dr = self.b.add("RoundtripTitle", "body text")
        vault_dir = Path(self.tmpdir) / "vault_rt_title"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_title.db"
        b2 = SecondBrain(db2_path)
        try:
            b2.import_(str(vault_dir), mode="merge")
            fetched = b2.get(dr["id"])
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["title"], "RoundtripTitle")
        finally:
            b2.close()

    def test_vault_roundtrip_content_preserved(self):
        dr = self.b.add("RoundtripContent", "very specific body content xyz")
        vault_dir = Path(self.tmpdir) / "vault_rt_content"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_content.db"
        b2 = SecondBrain(db2_path)
        try:
            b2.import_(str(vault_dir), mode="merge")
            fetched = b2.get(dr["id"])
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["content"], "very specific body content xyz")
        finally:
            b2.close()

    def test_vault_roundtrip_collection_preserved(self):
        dr = self.b.add("RoundtripColl", "body", collection="testcollection")
        vault_dir = Path(self.tmpdir) / "vault_rt_coll"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_coll.db"
        b2 = SecondBrain(db2_path)
        try:
            b2.import_(str(vault_dir), mode="merge")
            fetched = b2.get(dr["id"])
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["collection"], "testcollection")
        finally:
            b2.close()

    def test_vault_roundtrip_tags_preserved(self):
        dr = self.b.add("RoundtripTags", "body", tags=["tagA", "tagB"])
        vault_dir = Path(self.tmpdir) / "vault_rt_tags"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_tags.db"
        b2 = SecondBrain(db2_path)
        try:
            b2.import_(str(vault_dir), mode="merge")
            fetched = b2.get(dr["id"])
            self.assertIsNotNone(fetched)
            self.assertIn("tagA", fetched["tags"])
            self.assertIn("tagB", fetched["tags"])
        finally:
            b2.close()

    def test_vault_roundtrip_multiple_concepts(self):
        ids = []
        for i in range(5):
            dr = self.b.add(f"Multi{i}", f"body {i}", tags=[f"tag{i}"])
            ids.append(dr["id"])

        vault_dir = Path(self.tmpdir) / "vault_rt_multi"
        self.b.export_vault(str(vault_dir))

        db2_path = Path(self.tmpdir) / "brain2_multi.db"
        b2 = SecondBrain(db2_path)
        try:
            result = b2.import_(str(vault_dir), mode="merge")
            self.assertEqual(result["added"], 5)
            self.assertEqual(result["skipped"], 0)
            for did in ids:
                self.assertIsNotNone(b2.get(did))
        finally:
            b2.close()

    def test_vault_roundtrip_merge_skips_existing(self):
        dr = self.b.add("MergeSkip", "original content")
        vault_dir = Path(self.tmpdir) / "vault_merge_skip"
        self.b.export_vault(str(vault_dir))

        # Import into a brain that already has the same concept.
        db2_path = Path(self.tmpdir) / "brain2_merge.db"
        b2 = SecondBrain(db2_path)
        try:
            # First import adds it.
            b2.import_(str(vault_dir), mode="merge")
            # Second import should skip it.
            result2 = b2.import_(str(vault_dir), mode="merge")
            self.assertEqual(result2["added"], 0)
            self.assertEqual(result2["skipped"], 1)
        finally:
            b2.close()

    # -----------------------------------------------------------------------
    # 12. import_ from JSON (existing behavior)
    # -----------------------------------------------------------------------

    def test_import_json_adds_concepts(self):
        import json, tempfile as _tf
        concepts_data = [
            {
                "id": "aabbcc001",
                "title": "JSONImported",
                "content": "from a json file",
                "collection": "imported",
                "tags": ["itag"],
                "sources": [],
                "metadata": {},
            }
        ]
        with _tf.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=self.tmpdir
        ) as f:
            json.dump(concepts_data, f)
            json_path = f.name

        result = self.b.import_(json_path, mode="merge")
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["skipped"], 0)

        fetched = self.b.get("aabbcc001")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "JSONImported")
        self.assertEqual(fetched["content"], "from a json file")
        self.assertEqual(fetched["collection"], "imported")
        self.assertIn("itag", fetched["tags"])

    def test_import_json_merge_skips_existing(self):
        import json, tempfile as _tf
        dr = self.b.add("PreExisting", "already here")
        concepts_data = [
            {
                "id": dr["id"],
                "title": "PreExisting",
                "content": "already here",
                "collection": None,
                "tags": [],
                "sources": [],
                "metadata": {},
            }
        ]
        with _tf.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=self.tmpdir
        ) as f:
            json.dump(concepts_data, f)
            json_path = f.name

        result = self.b.import_(json_path, mode="merge")
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["skipped"], 1)

    def test_import_json_replace_overwrites(self):
        import json, tempfile as _tf
        dr = self.b.add("ToOverwrite", "original")
        concepts_data = [
            {
                "id": dr["id"],
                "title": "ToOverwrite",
                "content": "replaced content",
                "collection": None,
                "tags": [],
                "sources": [],
                "metadata": {},
            }
        ]
        with _tf.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=self.tmpdir
        ) as f:
            json.dump(concepts_data, f)
            json_path = f.name

        self.b.import_(json_path, mode="replace")
        fetched = self.b.get(dr["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["content"], "replaced content")

    def test_import_json_resolves_wikilinks_after_bulk(self):
        """After a JSON import the cross-refs between the imported concepts
        should be resolved (wikilinks re-synced over the full set)."""
        import json, tempfile as _tf
        id_a = "wljson_aaa"
        id_b = "wljson_bbb"
        concepts_data = [
            {
                "id": id_a,
                "title": "JSONNoteA",
                "content": "References [[JSONNoteB]]",
                "collection": None,
                "tags": [],
                "sources": [],
                "metadata": {},
            },
            {
                "id": id_b,
                "title": "JSONNoteB",
                "content": "I am the target",
                "collection": None,
                "tags": [],
                "sources": [],
                "metadata": {},
            },
        ]
        with _tf.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, dir=self.tmpdir
        ) as f:
            json.dump(concepts_data, f)
            json_path = f.name

        self.b.import_(json_path, mode="merge")
        rels = self.b.related(id_a)
        self.assertTrue(any(r["id"] == id_b for r in rels))

    # -----------------------------------------------------------------------
    # 8. Subjects (G08 / R10)
    # -----------------------------------------------------------------------

    def test_subject_index_populated_on_add(self):
        """live add() registers the default /people/self.md subject even
        when no sb_subject is passed."""
        dr = self.b.add("Title", "body", collection="notes")
        rows = self.b.con.execute(
            "SELECT subject_id FROM concept_subject WHERE concept_id=?", (dr["id"],)
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subject_id"], "/people/self.md")

    def test_subject_subgraph_returns_only_subject_concepts(self):
        """subject_subgraph(path) returns exactly the concepts linked to
        that subject — no leakage from other subjects."""
        # Three concepts about rox, one about alex, one with default
        self.b.add("R1", "r1 body", collection="traits",
                   sb_subject="/people/rox.md")
        self.b.add("R2", "r2 body", collection="traits",
                   sb_subject="/people/rox.md")
        self.b.add("R3", "r3 body", collection="traits",
                   sb_subject="/people/rox.md")
        self.b.add("A1", "a1 body", collection="traits",
                   sb_subject="/people/alex.md")
        self.b.add("Mine", "my body", collection="notes")  # default self
        rox = self.b.subject_subgraph("/people/rox.md")
        self.assertEqual(sorted(c["title"] for c in rox), ["R1", "R2", "R3"])
        alex = self.b.subject_subgraph("/people/alex.md")
        self.assertEqual([c["title"] for c in alex], ["A1"])
        # No leakage
        for c in rox:
            self.assertNotIn(c["title"], ("A1", "Mine"))

    def test_subject_subgraph_default_is_self(self):
        """A concept with no sb_subject is reachable via /people/self.md."""
        self.b.add("Lunch", "ate sandwich", collection="notes")
        mine = self.b.subject_subgraph("/people/self.md")
        self.assertEqual([c["title"] for c in mine], ["Lunch"])

    def test_subject_subgraph_unknown_returns_empty(self):
        """subject_subgraph(unknown) returns [] not raise."""
        self.b.add("A", "a", collection="notes")
        self.assertEqual(self.b.subject_subgraph("/people/ghost.md"), [])

    def test_subject_change_via_update(self):
        """update(id, sb_subject=X) re-links the concept to the new subject."""
        dr = self.b.add("X", "body", collection="notes",
                        sb_subject="/people/rox.md")
        self.assertEqual(
            self.b.con.execute(
                "SELECT subject_id FROM concept_subject WHERE concept_id=?",
                (dr["id"],)).fetchone()["subject_id"],
            "/people/rox.md",
        )
        self.b.update(dr["id"], sb_subject="/people/alex.md")
        row = self.b.con.execute(
            "SELECT subject_id FROM concept_subject WHERE concept_id=?",
            (dr["id"],)).fetchone()
        self.assertEqual(row["subject_id"], "/people/alex.md")

    def test_subjects_lists_known_subjects(self):
        """subjects() returns all distinct subjects with their concept count."""
        self.b.add("R1", "r1", collection="notes", sb_subject="/people/rox.md")
        self.b.add("R2", "r2", collection="notes", sb_subject="/people/rox.md")
        self.b.add("A1", "a1", collection="notes", sb_subject="/people/alex.md")
        self.b.add("M1", "m1", collection="notes")  # default
        subs = {s["sb_id"]: s["concept_count"] for s in self.b.subjects()}
        self.assertEqual(subs["/people/self.md"], 1)
        self.assertEqual(subs["/people/rox.md"], 2)
        self.assertEqual(subs["/people/alex.md"], 1)


if __name__ == "__main__":
    unittest.main()
