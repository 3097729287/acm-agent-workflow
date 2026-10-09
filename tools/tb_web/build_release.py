"""Reproducible Windows build. Never mutates the live app or personal state.

python build_release.py prepare --stage BUILD --data-root DATA --compiler-source COMPILER
python build_release.py build --stage BUILD
python build_release.py assemble --stage BUILD --data-root DATA --dictionary DICT
python build_release.py installer --stage BUILD --inno ISCC --webview2 OFFLINE_RUNTIME
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

APP = Path(__file__).resolve().parent
TOOLS = APP.parent
VERSION = '0.5.0'
NAME = 'TB新版'
PACKAGE = 'TB-0.5.0-win64'
COMMON = ['toolutil', 'status_report', 'knowledge_dict', 'tb_inbox', 'status_gui', 'fetch_problem', 'cf_eq']
MODULES = ['launch', 'backend', 'training', 'assets', 'judge', 'reviewed_cases', 'integrations',
           'public_platforms', 'insights', 'official_bridge', 'lectures', 'lecture_library',
           'lecture_curation', 'concept_basics', 'knowledge', 'contestmeta', 'translation',
           'translation_config', 'progression', 'leaderboard', 'migration', 'release_probe']
RESOURCES = ['official_languages.js', 'knowledge_catalog.json', 'knowledge_extensions.json',
             'curated_lectures.json', 'problem_knowledge.json', 'public-problem-metadata.json', 'public-contest-dates.json', 'LICENSE', 'THIRDPARTY.md', 'TOOLCHAIN-SOURCES.md', 'third-party-inventory.json']


def backup(path):
    path = Path(path)
    if path.exists():
        directory = Path.home() / '.dsh' / 'backups' / str(path.parent).replace(':', '').replace('\\', '_').replace('/', '_')
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, directory / (path.name + '.' + dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak'))


def write(path, text):
    path = Path(path)
    backup(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def copy(source, target):
    target = Path(target)
    if target.is_file() and target.read_bytes() == Path(source).read_bytes():
        return
    backup(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def patch(path, old, new):
    text = path.read_text(encoding='utf-8-sig')
    if old not in text:
        raise RuntimeError('Source changed; inspect the build patch for ' + path.name + ': ' + old[:100])
    write(path, text.replace(old, new, 1))


def prepare(args):
    stage = args.stage
    source = stage / 'src'
    source.mkdir(parents=True, exist_ok=True)
    common_root = APP / 'common' if (APP / 'common').is_dir() else TOOLS
    for name in COMMON:
        copy(common_root / (name + '.py'), source / (name + '.py'))
    for name in MODULES:
        copy(APP / (name + '.py'), source / (name + '.py'))
    copy(APP / 'tb.ico', source / 'tb.ico')
    patch(source / 'launch.py', 'APP_DIR = Path(__file__).resolve().parent\nDSH_DIR = APP_DIR.parent.parent',
          'APP_DIR = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent\nDSH_DIR = APP_DIR if getattr(sys,"frozen",False) else APP_DIR.parent.parent\nif getattr(sys,"frozen",False):\n    os.environ.pop("AGENT_CP_CONFIG",None)\n    os.environ["PATH"] = str(APP_DIR/"compiler"/"ucrt64"/"bin")+os.pathsep+os.environ.get("PATH","")')
    patch(source / 'launch.py', 'PORT = 18765', 'PORT = int(os.environ.get("TB_PACKAGE_PORT","18765"))')
    patch(source / 'launch.py', 'server = start_server(port=PORT)',
          'server = start_server(port=PORT, integration_auto_start=False if os.environ.get("TB_PACKAGE_NO_SYNC")=="1" else None)')
    patch(source / 'launch.py', 'raise RuntimeError(f"本地端口 {PORT} 暂时不可用。请关闭占用该端口的程序后重试。") from exc',
          'LOG.info("Default port unavailable; choosing a free local port")\n            server = start_server(port=0, integration_auto_start=False if os.environ.get("TB_PACKAGE_NO_SYNC")=="1" else None)')
    patch(source / 'launch.py', 'MUTEX_NAME = "Local\\\\DSH.TB.React.Desktop"',
          'MUTEX_NAME = "Local\\\\TB.Standalone."+str(PORT)+"."+__import__("hashlib").sha256(str(APP_DIR).lower().encode()).hexdigest()[:16]')
    patch(source / 'backend.py', 'TOOLS = Path(__file__).resolve().parent.parent',
          'APP_DIR = Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent\nROOT = APP_DIR if getattr(sys,"frozen",False) else APP_DIR.parent.parent\nTOOLS = APP_DIR if getattr(sys,"frozen",False) else APP_DIR.parent')
    for old, new in [('TOOLS.parent / "logs"', 'ROOT / "logs"'),
                     ('(Path(__file__).resolve().parent / "dist")', '(APP_DIR / "dist")'),
                     ('TOOLS.parent / "state"', 'ROOT / "state"')]:
        patch(source / 'backend.py', old, new)
    patch(source / 'training.py', 'Path(__file__).resolve().parents[2] / "backups" / mirror',
          'Path(__import__("toolutil").BACKUP_ROOT) / mirror')
    patch(source / 'assets.py', "Path(__file__).resolve().parents[2]/'state'/'tb-problem-assets'",
          "Path(__import__('toolutil').REPO_ROOT)/'state'/'tb-problem-assets'")
    patch(source / 'judge.py', "self.compiler=shutil.which('g++')",
          "self.compiler=str(Path(__import__('toolutil').REPO_ROOT)/'compiler'/'ucrt64'/'bin'/'g++.exe')")
    patch(source / 'contestmeta.py', 'self.store=store;self.lock=threading.RLock();self.cache={};self.public={};self.by_url={}',
          'self.store=store;self.lock=threading.RLock();self.cache={};self.public={};self.by_url={}\n        seed=Path(toolutil.REPO_ROOT)/"public-contest-dates.json"\n        if seed.is_file():\n            try:self.public.update(json.loads(seed.read_text(encoding="utf-8")))\n            except (OSError,ValueError):pass')
    patch(source / 'launch.py', 'if __name__ == "__main__":\n    raise SystemExit(main())',
          'if __name__ == "__main__":\n    if len(sys.argv)==3 and sys.argv[1] in ("--package-check","--serve-check","--native-check"):\n        from release_probe import run\n        raise SystemExit(run(sys.argv[1],sys.argv[2]))\n    if len(sys.argv)==2 and sys.argv[1]=="--migrate-local":\n        from migration import migrate_legacy\n        outcome=migrate_legacy(APP_DIR)\n        raise SystemExit(0 if outcome.get("ok") else 1)\n    raise SystemExit(main())')
    write(stage / 'source-manifest.json', json.dumps({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('*.py')}, indent=2))
    if not args.compiler_source or not (args.compiler_source / 'ucrt64' / 'bin' / 'g++.exe').is_file():
        raise RuntimeError('--compiler-source must contain the complete compiler/ucrt64 tree')
    if not (stage / 'compiler').exists():
        shutil.copytree(args.compiler_source, stage / 'compiler')


def build(args):
    stage = args.stage
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
               '--name', NAME, '--distpath', str(stage / 'dist'), '--workpath', str(stage / 'build'),
               '--specpath', str(stage / 'spec'), '--paths', str(stage / 'src'), '--icon', str(stage / 'src' / 'tb.ico')]
    for module in MODULES + COMMON + ['webview', 'clr']:
        command += ['--hidden-import', module]
    subprocess.run(command + [str(stage / 'src' / 'launch.py')], cwd=APP, check=True)


def assemble(args):
    stage = args.stage
    package = stage / 'release' / PACKAGE
    if package.exists():
        raise RuntimeError('Use a new stage; never overwrite an assembled installation')
    if not args.data_root or not args.dictionary:
        raise RuntimeError('--data-root and --dictionary are required')
    data = args.data_root / '题解' if (args.data_root / '题解').is_dir() else args.data_root
    if not (data / 'TB.md').is_file():
        raise RuntimeError('Archive must contain TB.md')
    shutil.copytree(stage / 'dist' / NAME, package)
    shutil.copytree(APP / 'dist', package / 'dist')
    shutil.copytree(stage / 'compiler', package / 'compiler')
    copy(APP / 'tb.ico', package / 'tb.ico')
    copy(args.dictionary, package / 'knowledge' / '15-知识点词典.md')
    for resource in RESOURCES:
        copy(APP / resource, package / resource)
    shutil.copytree(APP / 'licenses', package / 'licenses')
    write(package / 'leaderboard.defaults.json', json.dumps({'endpoint': args.leaderboard_endpoint or ''}))
    write(package / 'config.json', json.dumps({'data_root': '.', 'backup_root': '备份', 'desktop_copy_dir': None}, ensure_ascii=False, indent=2))
    count = 0
    for base, dirs, names in os.walk(data):
        relative = Path(base).relative_to(data)
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'raw', '_待发OpenAI', '_收件箱', '.git')]
        for name in names:
            rel = relative / name
            if '_work' in rel.parts:
                keep = name in ('samples.py', '题单.md') or name.endswith('.txt') and '题面' in rel.parts
            else:
                keep = Path(name).suffix.lower() in ('.md', '.cpp', '.py', '.cmd', '.txt', '.png', '.jpg', '.svg', '.json')
            if keep:
                copy(Path(base) / name, package / '题解' / rel)
                count += 1
    # A library is a resource; distributed archive statuses never seed personal training.
    tb = package / '题解' / 'TB.md'
    lines = tb.read_text(encoding='utf-8-sig').splitlines()
    for index, line in enumerate(lines):
        cells = line.split('|')
        if len(cells) >= 9 and cells[1].strip().isdigit():
            cells[-3], cells[-2] = ' 未做 ', ' '
            lines[index] = '|'.join(cells)
    write(tb, '\n'.join(lines) + '\n')
    write(package / '使用说明.md', '# TB 0.5.0\n\n双击 TB新版.exe；安装版已包含 Python、C++ 工具链和离线 WebView2 安装组件。个人身份首次运行自动生成，设置里可改昵称。训练记录由实际加入和提交产生。\n\n每日任务奖励可在“成长与能力”领取；右上角奖杯查看成就。模拟赛支持综合、专项和随机单题，生成试卷与比赛期间隐藏考点。导航在设置里可排序、改名和组合。翻译支持自定义 Base URL、API Key 与模型。\n\n本地 AC 指通过已审核的本地测试，样例通过单独统计。排行榜统计已审核本地通过，需在设置中接入共享服务；本版未内置云服务账号或接口密钥。\n\n安装时可导入此电脑原 TB 的记录和配置；升级保留 state、cache、备份和现有题库。卸载保留个人记录，不会删除旧 DSH。分享请使用原始安装包，不转发使用后的目录。\n')
    copy(APP / 'README.md', package / '功能与键位.md')
    manifest = {str(p.relative_to(package)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}
    write(stage / 'release-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    write(stage / 'assembly.json', json.dumps({'package': str(package), 'archiveFilesCopied': count, 'files': len(manifest)}, indent=2))
    destination = stage / 'release' / (PACKAGE + '.zip')
    backup(destination)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                output.write(path, Path(PACKAGE) / path.relative_to(package))
    with zipfile.ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError('Corrupt archive entry: ' + bad)
    print(json.dumps({'package': str(package), 'zipBytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()}), flush=True)


def installer(args):
    if not args.inno or not args.webview2:
        raise RuntimeError('--inno ISCC.exe and --webview2 OFFLINE.exe are required')
    subprocess.run([str(args.inno), '/DPackageDir=' + str(args.stage / 'release' / PACKAGE),
                    '/DOutputDir=' + str(args.stage / 'release'), '/DWebViewInstaller=' + str(args.webview2),
                    '/DAppVersion=' + VERSION, str(APP / 'installer' / 'tb.iss')], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'build', 'assemble', 'installer'])
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--compiler-source', type=Path)
    parser.add_argument('--data-root', type=Path)
    parser.add_argument('--dictionary', type=Path)
    parser.add_argument('--inno', type=Path)
    parser.add_argument('--webview2', type=Path)
    parser.add_argument('--leaderboard-endpoint', default='')
    args = parser.parse_args()
    args.stage = args.stage.resolve()
    args.stage.mkdir(parents=True, exist_ok=True)
    globals()[args.action](args)


if __name__ == '__main__':
    main()
