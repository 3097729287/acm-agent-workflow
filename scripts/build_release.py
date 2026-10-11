"""Build TB from explicit frontend/backend/desktop boundaries; stage has no personal data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / 'VERSION').read_text().strip()
NAME = 'TB新版'
PACKAGE = 'TB-' + VERSION + '-win64'


def manifest(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file()}


def build(args):
    stage = args.stage.resolve()
    if (stage / 'dist').exists():
        raise RuntimeError('Use a new stage; existing builds are never overwritten')
    stage.mkdir(parents=True, exist_ok=True)
    paths = [ROOT / 'backend', ROOT / 'backend' / 'common', ROOT / 'desktop']
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
               '--name', NAME, '--distpath', str(stage / 'dist'), '--workpath', str(stage / 'build'),
               '--specpath', str(stage), '--icon', str(ROOT / 'desktop' / 'tb.ico')]
    modules = []
    for directory in paths:
        command += ['--paths', str(directory)]
        modules += [p.stem for p in directory.glob('*.py') if not p.name.startswith('test_')]
    for name in sorted(set(modules + ['webview', 'clr'])):
        command += ['--hidden-import', name]
    subprocess.run(command + [str(ROOT / 'desktop' / 'launch.py')], cwd=ROOT, check=True)
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for directory in paths for p in directory.rglob('*') if p.is_file() and p.suffix in ('.py', '.js', '.json')}
    (stage / 'source-manifest.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding='utf-8')


def assemble(args):
    stage = args.stage.resolve()
    package = stage / 'release' / PACKAGE
    if package.exists():
        raise RuntimeError('Use a new stage; existing packages are never overwritten')
    if not args.compiler_source or not (args.compiler_source / 'ucrt64' / 'bin' / 'g++.exe').is_file():
        raise RuntimeError('--compiler-source must contain a complete ucrt64 compiler')
    if not (ROOT / 'frontend' / 'dist' / 'index.html').is_file():
        raise RuntimeError('Build the frontend before assembling')
    seed = ROOT / 'data' / 'library.sqlite3'
    source = ROOT / 'data' / 'library'
    if not seed.is_file() and source.is_dir():
        sys.path.insert(0, str(ROOT / 'backend'))
        sys.path.insert(0, str(ROOT / 'backend' / 'common'))
        from library import LibraryDatabase
        LibraryDatabase.from_source(source, seed)
    with sqlite3.connect(seed.as_uri() + '?mode=ro', uri=True) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Invalid bundled SQLite library')
        problems = db.execute('SELECT COUNT(*) FROM problems').fetchone()[0]
        solutions = db.execute('SELECT COUNT(*) FROM solutions').fetchone()[0]
        if problems < solutions or solutions < 607:
            raise RuntimeError('Bundled solutions are incomplete')
        for raw, in db.execute('SELECT raw FROM problems'):
            row = json.loads(raw)
            if row['状态'] != '未做' or row['日期']:
                raise RuntimeError('The distribution contains personal progress')
    shutil.copytree(stage / 'dist' / NAME, package)
    shutil.copytree(ROOT / 'frontend' / 'dist', package / 'frontend' / 'dist')
    shutil.copytree(ROOT / 'backend' / 'resources', package / 'resources')
    shutil.copytree(args.compiler_source, package / 'compiler')
    shutil.copytree(ROOT / 'licenses', package / 'licenses')
    (package / 'data').mkdir()
    shutil.copy2(seed, package / 'data' / 'library.sqlite3')
    shutil.copy2(ROOT / 'desktop' / 'official_languages.js', package / 'official_languages.js')
    shutil.copy2(ROOT / 'desktop' / 'official_nowcoder.js', package / 'official_nowcoder.js')
    shutil.copy2(ROOT / 'desktop' / 'official_luogu.js', package / 'official_luogu.js')
    shutil.copy2(ROOT / 'desktop' / 'tb.ico', package / 'tb.ico')
    for name in ('VERSION', 'LICENSE', 'THIRDPARTY.md', 'TOOLCHAIN-SOURCES.md', 'third-party-inventory.json'):
        shutil.copy2(ROOT / name, package / name)
    shutil.copy2(ROOT / 'docs' / 'usage.md', package / '使用说明.md')
    files = manifest(package)
    forbidden = [key for key in files if key.startswith(('state/', 'cache/', 'logs/', 'backups/'))]
    if forbidden:
        raise RuntimeError('Package contains runtime data')
    (stage / 'release-manifest.json').write_text(json.dumps(files, ensure_ascii=False, indent=2), encoding='utf-8')
    (stage / 'assembly.json').write_text(json.dumps({'version': VERSION, 'package': str(package), 'problems': problems, 'solutions': solutions, 'files': len(files)}, ensure_ascii=False, indent=2), encoding='utf-8')
    destination = stage / 'release' / (PACKAGE + '.zip')
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for relative in files:
            output.write(package / relative, Path(PACKAGE) / relative)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip():
            raise RuntimeError('Corrupt portable archive')
    print(json.dumps({'package': str(package), 'zipBytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}))


def installer(args):
    if not args.inno or not args.webview2:
        raise RuntimeError('--inno ISCC.exe and --webview2 OFFLINE.exe are required')
    subprocess.run([str(args.inno), '/DPackageDir=' + str(args.stage.resolve() / 'release' / PACKAGE),
                    '/DOutputDir=' + str(args.stage.resolve() / 'release'), '/DWebViewInstaller=' + str(args.webview2),
                    '/DAppVersion=' + VERSION, str(ROOT / 'packaging' / 'installer' / 'tb.iss')], check=True)


def main():
    parser = argparse.ArgumentParser(description='Build TB without patching production sources')
    parser.add_argument('action', choices=['build', 'assemble', 'installer'])
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--compiler-source', type=Path)
    parser.add_argument('--inno', type=Path)
    parser.add_argument('--webview2', type=Path)
    args = parser.parse_args()
    globals()[args.action](args)


if __name__ == '__main__':
    main()
