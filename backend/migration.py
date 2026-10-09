"""Explicit, non-destructive legacy migration for the TB installer only."""
from __future__ import annotations

import base64
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time

DATABASE = Path("state") / "tb-personal.sqlite3"
SETTINGS = ("integrations.json", "translation-settings.json", "tb-knowledge-analysis.json")


def _publish_missing(staging, target):
    """Atomically publish complete bytes; a racing existing destination always wins."""
    try:
        os.link(staging, target)
        return True
    except FileExistsError:
        return False
    except OSError:
        if os.name != "nt":
            raise
        # Windows rename, unlike POSIX rename, never replaces an existing file.
        try:
            os.rename(staging, target)
            return True
        except FileExistsError:
            return False


def _temporary(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, path = tempfile.mkstemp(prefix=".tb-migrate-", suffix=".tmp", dir=target.parent)
    os.close(descriptor)
    return Path(path)


def _comparison_path(path):
    # On Windows, resolving a path while another process creates a parent may
    # return either C:\... or \\?\C:\.... They name the same directory, but
    # pathlib treats the prefixes as different anchors. Normalize only boundary
    # comparisons; retain the resolved original for I/O and long-path support.
    value = os.fspath(path)
    if os.name == "nt":
        if value[:8].upper() == "\\\\?\\UNC\\":
            value = "\\\\" + value[8:]
        elif value.startswith("\\\\?\\") and len(value) >= 7 and value[5:7] in (":\\", ":/"):
            value = value[4:]
    return Path(value)


def _is_within(path, root):
    return _comparison_path(path).is_relative_to(_comparison_path(root))


def _allowed_source(path, state_root):
    # A symlink must not redirect the allow-list to unrelated credentials/files.
    return _is_within(path.resolve(), state_root.resolve()) and path.is_file()


def _copy_database(source, target):
    staging = _temporary(target)
    try:
        deadline = time.monotonic() + 15
        def progress(status, remaining, total):
            if time.monotonic() > deadline:
                raise TimeoutError("legacy database remained busy")
        # mode=ro sees committed WAL transactions from a still-running source.
        # immutable=1 is deliberately avoided because it can omit live WAL data.
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=1)) as legacy:
            legacy.execute("PRAGMA query_only=ON")
            legacy.execute("PRAGMA busy_timeout=1000")
            tables = {row[0] for row in legacy.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"training", "submissions", "drafts"} <= tables:
                raise ValueError("not a TB personal database")
            with closing(sqlite3.connect(staging)) as destination:
                legacy.backup(destination, pages=128, progress=progress, sleep=.05)
                if destination.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("inconsistent personal database")
        with staging.open("rb+") as complete:
            os.fsync(complete.fileno())
        return _publish_missing(staging, target)
    finally:
        staging.unlink(missing_ok=True)


def _copy_json(source, target):
    if source.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("legacy settings exceed limit")
    raw = source.read_bytes()
    value = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("legacy settings must be an object")
    return _write_missing(raw, target)


def _write_missing(raw, target):
    staging = _temporary(target)
    try:
        with staging.open("wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        return _publish_missing(staging, target)
    finally:
        staging.unlink(missing_ok=True)


def _translation_fallback(source_root):
    """Copy only a recognized legacy provider/key into a user-bound DPAPI setting."""
    source_root = Path(source_root).resolve()
    # Fallback recognizes two bounded legacy files; neither may redirect outside
    # the explicitly requested source root, even when configured as a junction.
    candidates = (source_root / "profiles" / "dsh-tui-safe" / "cordis.patch.yml",
                  source_root / ".credentials.yaml")
    if any(not _is_within(path.resolve(), source_root) for path in candidates):
        return None
    from translation_config import existing_provider, local_key, _crypt, PROVIDERS
    detected = existing_provider(home=source_root)
    if not detected or detected.get("provider") not in PROVIDERS:
        return None
    spec = PROVIDERS[detected["provider"]]
    key = local_key(spec["keyEnv"], home=source_root)
    protected = base64.b64encode(_crypt(key.encode("utf-8"))).decode("ascii")
    return {"provider": detected["provider"], "model": detected["model"], "baseUrl": spec["baseUrl"], "protectedKey": protected}


def migrate_legacy(target_root, source_root=None):
    """Return safe counts/status; never log or return code, identities, tokens or keys.

    Call explicitly from the installer or --migrate-local, not at ordinary startup.
    Existing destinations (including a new user identity) are always retained.
    """
    source = Path(source_root) if source_root is not None else Path.home() / ".dsh"
    target = Path(target_root)
    report = {"ok": True, "exitCode": 0, "status": "unchanged", "copied": 0, "skipped": 0,
              "databaseCopied": False, "translationNeedsConfiguration": False, "errors": []}
    try:
        source, target = source.resolve(), target.resolve()
        if _comparison_path(source) == _comparison_path(target):
            report["skipped"] = 1 + len(SETTINGS)
            return report
        if _is_within(target, source):
            report.update(ok=False, exitCode=1, status="error")
            report["errors"].append({"step": "target", "message": "迁移目标不能放在旧数据目录中；原数据保持不变。"})
            return report
        if not source.is_dir():
            report["status"] = "no_legacy"
            return report
        if not _is_within((target / "state").resolve(), target):
            raise ValueError("target state leaves intended directory")
        source_state = source / "state"
        if not _is_within(source_state.resolve(), source):
            raise ValueError("source state leaves intended directory")
        old_database, new_database = source / DATABASE, target / DATABASE
        if new_database.exists():
            report["skipped"] += 1
        elif _allowed_source(old_database, source_state):
            try:
                copied = _copy_database(old_database, new_database)
                report["databaseCopied"] = copied
                report["copied" if copied else "skipped"] += 1
            except (OSError, sqlite3.Error, ValueError, TimeoutError):
                report["errors"].append({"step": "database", "message": "旧个人数据库未能完整迁入；已有记录和源数据库保持不变，请关闭旧软件后重试。"})
        for name in SETTINGS:
            old, new = source_state / name, target / "state" / name
            if new.exists():
                report["skipped"] += 1
                continue
            if _allowed_source(old, source_state):
                try:
                    copied = _copy_json(old, new)
                    report["copied" if copied else "skipped"] += 1
                except (OSError, ValueError, UnicodeError):
                    if name == "translation-settings.json":
                        report["translationNeedsConfiguration"] = True
                    else:
                        report["errors"].append({"step": name, "message": "旧设置未能完整迁入；源文件保持不变，请重新保存设置后重试。"})
            elif name == "translation-settings.json":
                try:
                    value = _translation_fallback(source)
                    if value is not None:
                        copied = _write_missing(json.dumps(value, ensure_ascii=False).encode("utf-8"), new)
                        report["copied" if copied else "skipped"] += 1
                    else:
                        report["translationNeedsConfiguration"] = True
                except Exception:
                    # Optional translation credentials must not block record migration.
                    report["translationNeedsConfiguration"] = True
        if report["errors"]:
            report.update(ok=False, exitCode=1, status="partial" if report["copied"] else "error")
        elif report["copied"]:
            report["status"] = "migrated"
        elif not old_database.exists() and not any((source_state / name).exists() for name in SETTINGS):
            report["status"] = "no_legacy"
    except (OSError, ValueError, TypeError):
        report.update(ok=False, exitCode=1, status="error")
        report["errors"].append({"step": "paths", "message": "迁移目录不可用；原数据保持不变，请检查目录后重试。"})
    return report
