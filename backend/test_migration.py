"""Installer migration tests are isolated and keep a live legacy WAL writer open."""
from concurrent.futures import ThreadPoolExecutor
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from migration import migrate_legacy


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tb-installer-migration-")
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / "legacy", self.root / "installed"
        (self.source / "state").mkdir(parents=True)
        self.database = self.source / "state" / "tb-personal.sqlite3"
        self.legacy = sqlite3.connect(self.database)
        self.legacy.execute("PRAGMA journal_mode=WAL")
        self.legacy.executescript("""
          CREATE TABLE training(id TEXT PRIMARY KEY,active INTEGER,accepted_at TEXT);
          CREATE TABLE drafts(problem_id TEXT,context TEXT,code TEXT);
          CREATE TABLE submissions(id TEXT PRIMARY KEY,problem_id TEXT,code TEXT,verdict TEXT);
          CREATE TABLE ranking_profile(singleton INTEGER,user_id TEXT,nickname TEXT,auth_token TEXT);
        """)
        self.code = "#include <iostream>\nint main(){std::cout << 42;} // 原始代码 🚀"
        self.legacy.execute("INSERT INTO training VALUES('one',1,'2026-10-08')")
        self.legacy.execute("INSERT INTO drafts VALUES('one','',?)", (self.code,))
        self.legacy.execute("INSERT INTO submissions VALUES('s1','one',?,'AC')", (self.code,))
        self.legacy.execute("INSERT INTO ranking_profile VALUES(1,'unique-user','私有昵称','DO_NOT_PRINT_TOKEN')")
        self.legacy.commit()

    def tearDown(self):
        self.legacy.close()
        self.temp.cleanup()

    def test_online_backup_keeps_committed_wal_and_all_code_with_active_writer(self):
        # Another uncommitted source write must not appear in the target snapshot.
        self.legacy.execute("INSERT INTO submissions VALUES('pending','one','unfinished','QUEUED')")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["databaseCopied"])
        with contextlib.closing(sqlite3.connect(self.target / "state" / "tb-personal.sqlite3")) as copied:
            self.assertEqual(copied.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(copied.execute("SELECT code FROM drafts").fetchone()[0], self.code)
            self.assertEqual(copied.execute("SELECT code FROM submissions").fetchall(), [(self.code,)])
            self.assertEqual(copied.execute("SELECT auth_token FROM ranking_profile").fetchone()[0], "DO_NOT_PRINT_TOKEN")
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(self.code, json.dumps(report))
        self.assertNotIn("DO_NOT_PRINT_TOKEN", json.dumps(report))
        self.legacy.rollback()
        self.assertEqual(self.legacy.execute("SELECT COUNT(*) FROM submissions").fetchone()[0], 1)

    def test_existing_identity_db_and_settings_are_never_overwritten(self):
        target_state = self.target / "state"; target_state.mkdir(parents=True)
        existing_db = target_state / "tb-personal.sqlite3"
        existing_db.write_bytes(b"EXISTING USER DATABASE")
        old = {"settings": {"user": "old"}}
        (self.source / "state" / "integrations.json").write_text(json.dumps(old), encoding="utf-8")
        (target_state / "integrations.json").write_bytes(b'{"settings":{"user":"current"}}')
        (target_state / "translation-settings.json").write_bytes(b'{"protectedKey":"CURRENT_DPAPI"}')
        hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in target_state.iterdir()}
        report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"])
        self.assertFalse(report["databaseCopied"])
        self.assertEqual(report["copied"], 0)
        self.assertEqual({path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in target_state.iterdir()}, hashes)

    def test_allow_list_only_and_original_dpapi_bytes_preserved(self):
        files = {"integrations.json": '{"settings":{"accounts":{}}}', "translation-settings.json": '{"provider":"custom","protectedKey":"OLD_DPAPI","model":"model","baseUrl":"https://api.example.com"}',
                 "tb-knowledge-analysis.json": '{"one":{"tags":["排序"]}}'}
        for name, text in files.items(): (self.source / "state" / name).write_text(text, encoding="utf-8")
        for relative in ("state/http/private.json", "cache/tb-web-profile/Cookies", "logs/private.log", "profiles/private.yml", ".credentials.yaml", "tools/code.py"):
            path = self.source / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("FORBIDDEN SECRET", encoding="utf-8")
        source_hashes = {str(path.relative_to(self.source)): hashlib.sha256(path.read_bytes()).hexdigest() for path in self.source.rglob("*") if path.is_file() and not path.name.endswith(("-wal", "-shm"))}
        report = migrate_legacy(self.target, self.source)
        self.assertEqual(report["copied"], 4)
        expected = {"state/tb-personal.sqlite3", *("state/" + name for name in files)}
        self.assertEqual({path.relative_to(self.target).as_posix() for path in self.target.rglob("*") if path.is_file()}, expected)
        for name, text in files.items(): self.assertEqual((self.target / "state" / name).read_text(encoding="utf-8"), text)
        for relative, digest in source_hashes.items(): self.assertEqual(hashlib.sha256((self.source / relative).read_bytes()).hexdigest(), digest)

    def test_concurrent_migrators_publish_one_complete_db_without_replacing(self):
        # Each round races four callers against a completely absent target while
        # the source WAL writer stays open. One publication must win; every
        # caller must succeed without replacing its identity or snapshot.
        for round_number in range(20):
            with self.subTest(round=round_number):
                target = self.root / ("installed-" + str(round_number))
                start = threading.Barrier(4)
                def migrate(_):
                    start.wait(timeout=15)
                    return migrate_legacy(target, self.source)
                with ThreadPoolExecutor(max_workers=4) as workers:
                    reports = list(workers.map(migrate, range(4)))
                self.assertTrue(all(report["ok"] for report in reports), reports)
                self.assertEqual(sum(report["databaseCopied"] for report in reports), 1)
                self.assertEqual(list((target / "state").glob(".tb-migrate-*.tmp")), [])
                with contextlib.closing(sqlite3.connect(target / "state" / "tb-personal.sqlite3")) as copied:
                    self.assertEqual(copied.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                    self.assertEqual(copied.execute("SELECT code FROM submissions").fetchone()[0], self.code)
                    self.assertEqual(copied.execute("SELECT user_id,auth_token FROM ranking_profile").fetchone(),
                                     ("unique-user", "DO_NOT_PRINT_TOKEN"))

    @unittest.skipUnless(os.name == "nt", "Windows extended-length path resolution")
    def test_transient_extended_prefix_during_target_creation_is_same_directory(self):
        original_resolve = Path.resolve
        def resolve(path, *args, **kwargs):
            actual = original_resolve(path, *args, **kwargs)
            if path == self.target / "state":
                return Path("\\\\?\\" + str(actual))
            return actual
        # Deterministically reproduce Windows returning an extended prefix for
        # state only after the root was resolved without that prefix.
        with patch.object(Path, "resolve", resolve):
            report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["databaseCopied"])
        with contextlib.closing(sqlite3.connect(self.target / "state" / "tb-personal.sqlite3")) as copied:
            self.assertEqual(copied.execute("SELECT code FROM submissions").fetchone()[0], self.code)

    def test_corrupt_db_reports_failure_without_creating_target_or_echoing_contents(self):
        self.legacy.close()
        self.database.write_bytes(b"CORRUPT_SECRET_TOKEN")
        report = migrate_legacy(self.target, self.source)
        self.assertFalse(report["ok"])
        self.assertEqual(report["exitCode"], 1)
        self.assertFalse((self.target / "state" / "tb-personal.sqlite3").exists())
        self.assertNotIn("CORRUPT_SECRET_TOKEN", json.dumps(report))
        self.assertEqual(self.database.read_bytes(), b"CORRUPT_SECRET_TOKEN")

    def test_optional_provider_fallback_uses_dpapi_and_missing_key_is_nonfatal(self):
        with patch("migration._translation_fallback", return_value={"provider": "huoshan", "model": "model", "baseUrl": "https://api.example.com", "protectedKey": "ENCRYPTED_ONLY"}):
            report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"])
        self.assertFalse(report["translationNeedsConfiguration"])
        self.assertEqual(json.loads((self.target / "state" / "translation-settings.json").read_text())["protectedKey"], "ENCRYPTED_ONLY")
        other = self.root / "without-key"
        with patch("migration._translation_fallback", side_effect=RuntimeError("SENSITIVE_KEY_MUST_NOT_ECHO")):
            report = migrate_legacy(other, self.source)
        self.assertTrue(report["ok"])
        self.assertTrue(report["translationNeedsConfiguration"])
        self.assertNotIn("SENSITIVE_KEY", json.dumps(report))

    @unittest.skipUnless(os.name == "nt", "DPAPI binds to the current Windows user")
    def test_recognized_legacy_key_is_reencrypted_without_copying_global_credentials(self):
        from translation_config import PROVIDERS, _crypt
        import base64
        source_config = self.source / "profiles" / "dsh-tui-safe" / "cordis.patch.yml"
        source_config.parent.mkdir(parents=True)
        source_config.write_text("providers:\n  huoshan:\n    baseURL: " + PROVIDERS["huoshan"]["baseUrl"] + "\n    apiKeyEnv: HUOSHAN_API_KEY\n    models:\n      - id: fixture-model\n", encoding="utf-8")
        fake_key = "THIS_IS_ONLY_A_PRIVATE_FIXTURE_KEY"
        (self.source / ".credentials.yaml").write_text('refs:\n  HUOSHAN_API_KEY: "' + fake_key + '"\n  UNRELATED_KEY: "DO_NOT_COPY"\n', encoding="utf-8")
        output = io.StringIO()
        with patch.dict(os.environ, {"HUOSHAN_API_KEY": ""}), contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"])
        value = json.loads((self.target / "state" / "translation-settings.json").read_text(encoding="utf-8"))
        self.assertEqual(value["provider"], "huoshan")
        self.assertEqual(value["model"], "fixture-model")
        self.assertEqual(_crypt(base64.b64decode(value["protectedKey"]), True).decode(), fake_key)
        self.assertNotIn(fake_key, (self.target / "state" / "translation-settings.json").read_text())
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(fake_key, json.dumps(report))
        self.assertFalse((self.target / ".credentials.yaml").exists())
        self.assertFalse((self.target / "profiles").exists())

    def test_corrupt_optional_translation_is_nonfatal_and_never_echoes_key(self):
        original = b'{"apiKey":"PRIVATE_FIXTURE_TOKEN"'
        (self.source / "state" / "translation-settings.json").write_bytes(original)
        report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["databaseCopied"])
        self.assertTrue(report["translationNeedsConfiguration"])
        self.assertEqual(report["errors"], [])
        self.assertFalse((self.target / "state" / "translation-settings.json").exists())
        self.assertNotIn("PRIVATE_FIXTURE_TOKEN", json.dumps(report))
        self.assertEqual((self.source / "state" / "translation-settings.json").read_bytes(), original)

    def _directory_link(self, target, link):
        try:
            if os.name == "nt":
                import _winapi
                _winapi.CreateJunction(str(target), str(link))
            else:
                link.symlink_to(target, target_is_directory=True)
        except (OSError, AttributeError):
            self.skipTest("Directory links are unavailable in this test environment")

    def test_source_and_target_junctions_cannot_escape_allow_list(self):
        outside = self.root / "outside"; outside.mkdir()
        sentinel = outside / "integrations.json"
        sentinel.write_bytes(b'{"private":"MUST_NOT_COPY"}')
        redirected_source = self.root / "redirected-legacy"; redirected_source.mkdir()
        self._directory_link(outside, redirected_source / "state")
        report = migrate_legacy(self.target, redirected_source)
        self.assertFalse(report["ok"])
        self.assertEqual(report["copied"], 0)
        self.assertFalse(self.target.exists())
        self.assertEqual(sentinel.read_bytes(), b'{"private":"MUST_NOT_COPY"}')
        redirected_target = self.root / "redirected-target"; redirected_target.mkdir()
        self._directory_link(outside, redirected_target / "state")
        report = migrate_legacy(redirected_target, self.source)
        self.assertFalse(report["ok"])
        self.assertEqual(report["copied"], 0)
        self.assertFalse((outside / "tb-personal.sqlite3").exists())

    def test_translation_fallback_does_not_follow_external_profile_junction(self):
        outside = self.root / "external-profile"; outside.mkdir()
        profile = self.source / "profiles"; profile.mkdir()
        self._directory_link(outside, profile / "dsh-tui-safe")
        with patch("translation_config.existing_provider") as detect:
            report = migrate_legacy(self.target, self.source)
        self.assertTrue(report["ok"])
        self.assertTrue(report["databaseCopied"])
        self.assertTrue(report["translationNeedsConfiguration"])
        detect.assert_not_called()

    def test_no_legacy_and_same_source_are_noop(self):
        self.assertEqual(migrate_legacy(self.target, self.root / "missing")["status"], "no_legacy")
        self.assertFalse(self.target.exists())
        before = self.database.read_bytes()
        report = migrate_legacy(self.source, self.source)
        self.assertEqual(report["status"], "unchanged")
        self.assertEqual(self.database.read_bytes(), before)


if __name__ == "__main__": unittest.main()
