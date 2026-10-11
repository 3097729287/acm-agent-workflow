"""Explicit portable-to-portable migration; source stays read-only, target must be fresh.

All SQLite files use online backup so committed WAL content is included. Browser
preferences/cookies stay private and are never copied into a distribution stage.
Close the old application before copying its LevelDB browser profile.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3


def checksum(path):
    with path.open('rb') as handle:return hashlib.file_digest(handle,'sha256').hexdigest()


def logical_checksum(db):
    digest=hashlib.sha256()
    for line in db.iterdump():digest.update(line.encode('utf-8'));digest.update(b'\n')
    return digest.hexdigest()


def copy_database(source,target):
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=15)) as original:
        original.execute('PRAGMA query_only=ON');original.execute('BEGIN')
        assert original.execute('PRAGMA quick_check').fetchone()[0]=='ok','Source database is inconsistent'
        expected=logical_checksum(original)
        with closing(sqlite3.connect(target)) as copied:
            original.backup(copied,pages=256,sleep=.05)
            assert copied.execute('PRAGMA quick_check').fetchone()[0]=='ok'
            assert logical_checksum(copied)==expected,'Database content changed while copying'
    return expected


def snapshot(source,target):
    target.mkdir(parents=True,exist_ok=False)
    report={'databases':0,'files':0,'runtimeFilesSkipped':0,'digests':{}}
    if not source.is_dir():return report
    for item in sorted(source.rglob('*')):
        name=item.name
        if name in ('LOCK','lockfile','SingletonLock','SingletonCookie','SingletonSocket','DevToolsActivePort','instance.pid') or name.endswith(('-wal','-shm')):
            report['runtimeFilesSkipped']+=int(item.is_file());continue
        assert item.resolve().is_relative_to(source.resolve()),'Source link leaves its approved directory'
        relative=item.relative_to(source);destination=target/relative
        if item.is_dir():destination.mkdir(exist_ok=True);continue
        if not item.is_file():continue
        destination.parent.mkdir(parents=True,exist_ok=True)
        with item.open('rb') as handle:is_sqlite=handle.read(16)==b'SQLite format 3\0'
        if is_sqlite:
            digest=copy_database(item,destination);report['databases']+=1;kind='sqlite'
        else:
            shutil.copy2(item,destination);digest=checksum(item)
            assert checksum(destination)==digest,'File copy differs from source'
            report['files']+=1;kind='bytes'
        report['digests'][relative.as_posix()]={'kind':kind,'sha256':digest}
    return report


def migrate(source,target,backup):
    source,target,backup=(Path(path).resolve() for path in (source,target,backup))
    assert (source/'TB新版.exe').is_file() and (target/'TB新版.exe').is_file(),'Both program directories must be explicit'
    for left,right in ((target,source),(source,target),(backup,source),(source,backup),(backup,target),(target,backup)):
        assert not left.is_relative_to(right),'Migration directories must be separate'
    assert not backup.exists(),'Use a new backup directory'
    assert not any((target/name).exists() for name in ('state','cache')),'Refuse to replace an existing personal destination'
    executable_hash=checksum(source/'TB新版.exe');backup.mkdir(parents=True)
    report={'ok':False,'sourceVersion':(source/'VERSION').read_text().strip(),'targetVersion':(target/'VERSION').read_text().strip(),'verified':{}}
    try:
        for name in ('state','cache'):
            saved=snapshot(source/name,backup/name)
            installed=snapshot(backup/name,target/name)
            assert saved['digests']==installed['digests'],'Private content changed when migrating the snapshot'
            report['verified'][name]={key:saved[key] for key in ('databases','files','runtimeFilesSkipped')}
        assert checksum(source/'TB新版.exe')==executable_hash,'Original executable changed'
        report.update(ok=True,originalExecutableUnchanged=True,allDatabaseContentsVerified=True,allRegularFilesVerified=True)
    finally:
        (backup/'migration-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser()
    for name in ('source','target','backup'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();print(json.dumps(migrate(args.source,args.target,args.backup),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
