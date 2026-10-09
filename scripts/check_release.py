"""Windows setup/upgrade checks in a new disposable directory and registry identity.

The production installer and users' installations are never run or edited here.
Validation installers use the same files/rules with an isolated AppId.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler
import uuid

ROOT = Path(__file__).resolve().parent.parent
NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
CODE = '#include <bits/stdc++.h>\nusing namespace std; int main(){int n;cin>>n;long long one[61]={1},two[61]={0};for(int i=1;i<=n;++i){one[i]=one[i-1]+two[i-1];if(i>=2)two[i]=one[i-2];}cout<<one[n]+two[n]<<"\\n";}\n'
OPENER = build_opener(ProxyHandler({}))


def run(command, log, env=None, timeout=300, cwd=None):
    with Path(log).open('w', encoding='utf-8') as output:
        subprocess.run([str(x) for x in command], stdout=output, stderr=subprocess.STDOUT,
                       env=env, timeout=timeout, cwd=cwd or ROOT, check=True,
                       creationflags=NO_WINDOW)


def environment(app):
    state = app / 'state'
    return dict(os.environ, TB_OFFLINE='1', TB_PACKAGE_NO_SYNC='1', TB_PACKAGE_PORT='0',
                TB_STATE_DIR=str(state), TB_LIBRARY_DB=str(state / 'tb-library.sqlite3'),
                TB_ARCHIVE_ROOT=str(state / 'imports'), TB_BACKUP_DIR=str(state / 'backups'),
                AGENT_CP_CONFIG=str(app / 'config.json'), DSH_HOME=str(state / 'absent'),
                DEEPSEEK_API_KEY='', HUOSHAN_API_KEY='', TB_TRANSLATION_API_KEY='')


class API:
    def __init__(self, base):
        self.base, self.token = base, None
        self.catalog = self.get('data')
        self.token = self.catalog['token']

    def get(self, path):
        with OPENER.open(self.base + '/api/' + path, timeout=60) as response:
            return json.load(response)

    def post(self, path, body):
        request = Request(self.base + '/api/' + path,
                          data=json.dumps(body).encode('utf-8'),
                          headers={'Content-Type': 'application/json', 'X-TB-Token': self.token,
                                   'Origin': self.base})
        with OPENER.open(request, timeout=60) as response:
            return json.load(response)


@contextmanager
def serving(app, report):
    report.unlink(missing_ok=True)
    stop = report.with_suffix('.stop')
    stop.unlink(missing_ok=True)
    process = subprocess.Popen([str(app / 'TB新版.exe'), '--serve-check', str(report)],
                               env=environment(app), cwd=app, creationflags=NO_WINDOW)
    try:
        deadline = time.monotonic() + 60
        while not report.is_file():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('Packaged API startup failed; see ' + str(report))
            time.sleep(.1)
        value = json.loads(report.read_text(encoding='utf-8'))
        assert value['ok'], value
        yield API(value['baseUrl'])
    finally:
        stop.touch()
        try:
            process.wait(30)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(10)


def install(setup, app, log):
    assert app.is_relative_to(ROOT / 'build') and 'release-check-' in str(app)
    run([setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/NOICONS',
         '/MERGETASKS=!desktopicon,!importlegacy', '/DIR=' + str(app), '/LOG=' + str(log)],
        log.with_suffix('.process.log'), timeout=300)
    assert (app / 'TB新版.exe').is_file()


def state_hashes(app):
    return {p.relative_to(app).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (app / 'state').rglob('*') if p.is_file()}


def legacy_mock(api, problem):
    row = next(row for row in api.catalog['rows'] if row['id'] == problem)
    plan = api.post('contests/preview', {'strategy': 'single', 'count': 1, 'duration': 60,
                    'min': row['difficulty'], 'max': row['difficulty'], 'platform': row['platform'],
                    'reviewedOnly': True, 'excludeSolved': False})['plan']
    ids = [slot['id'] for slot in plan['slots']]
    assert len(ids) == 1 and ids[0] in {row['id'] for row in api.catalog['rows']}
    mock_problem = ids[0]
    contest = api.post('contests/start', {'ids': ids, 'duration': plan['duration'], 'previewId': plan['previewId']})['contest']['id']
    api.post('draft', {'id': mock_problem, 'code': '// preserved contest draft\nint main(){}\n', 'contestId': contest})
    api.post('contests/finish', {'contestId': contest})
    return contest, mock_problem


def snapshot(api, problem, contest=None, mock_problem=None):
    workspace, profile = api.get('workspace'), api.get('profile')
    result = {
        'userId': profile['profile']['userId'], 'nickname': profile['profile']['nickname'],
        'summary': {key: workspace['summary'][key] for key in ['total', 'accepted', 'attempts']},
        'draft': api.get('problem?' + urlencode({'id': problem}))['draft'],
        'xp': api.get('insights')['growth']['totalXp'],
        'submissions': [{key: row.get(key) for key in ['id', 'problemId', 'code', 'mode', 'verdict', 'scope', 'submittedAt']}
                        for row in api.get('submissions')['submissions']],
        'contests': [{key: row.get(key) for key in ['id', 'status', 'accepted', 'total']}
                     for row in workspace['contests']],
    }
    if contest:
        result['contestDraft'] = api.get('problem?' + urlencode({'id': mock_problem or problem, 'contestId': contest}))['draft']
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--legacy-package', type=Path, required=True)
    parser.add_argument('--legacy-iss', type=Path, required=True)
    parser.add_argument('--inno', type=Path, required=True)
    parser.add_argument('--webview2', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('Windows installer checks require Windows')
    work = ROOT / 'build' / ('release-check-' + uuid.uuid4().hex[:10])
    work.mkdir(parents=True, exist_ok=False)
    identity = 'TB.Validation.' + work.name
    result = {'ok': False, 'work': str(work), 'validationAppId': identity, 'phase': 'compile'}
    print('Disposable release validation: ' + str(work), flush=True)
    try:
        version = (ROOT / 'VERSION').read_text().strip()
        package = args.stage.resolve() / 'release' / ('TB-' + version + '-win64')
        new_output, old_output = work / 'setup-new', work / 'setup-old'
        new_output.mkdir(); old_output.mkdir()
        run([args.inno, '/DAppId=' + identity, '/DPackageDir=' + str(package),
             '/DOutputDir=' + str(new_output), '/DWebViewInstaller=' + str(args.webview2),
             '/DAppVersion=' + version, ROOT / 'packaging/installer/tb.iss'], work / 'compile-new.log')
        old_source = args.legacy_iss.read_text(encoding='utf-8-sig')
        original_id = 'AppId={{0F82D178-AC2B-4696-96C1-1A210F72B509}'
        assert original_id in old_source
        old_iss = old_output / 'legacy.iss'
        old_iss.write_text(old_source.replace(original_id, 'AppId=' + identity), encoding='utf-8')
        shutil.copy2(args.legacy_iss.parent / 'ChineseSimplified.isl', old_output)
        run([args.inno, '/DPackageDir=' + str(args.legacy_package), '/DOutputDir=' + str(old_output),
             '/DWebViewInstaller=' + str(args.webview2), '/DAppVersion=0.5.0', old_iss], work / 'compile-old.log')
        new_setup = new_output / ('TB-Setup-' + version + '-win64.exe')
        old_setup = old_output / 'TB-Setup-0.5.0-win64.exe'

        result['phase'] = 'fresh install'
        fresh = work / 'fresh'
        install(new_setup, fresh, work / 'fresh-install.log')
        assert not (fresh / 'state').exists(), 'Installer must not distribute or implicitly migrate personal state'
        with serving(fresh, work / 'fresh-api.json') as api:
            env = dict(environment(fresh), BASE_URL=api.base, SCREENSHOT_DIR=str(work / 'screenshots'))
            run(['node', 'tests/package.mjs'], work / 'fresh-browser.log', env=env,
                timeout=300, cwd=ROOT / 'frontend')
            result['fresh'] = {'problems': len(api.catalog['rows']), 'solutions': sum(bool(r['solutionAvailable']) for r in api.catalog['rows']),
                               'localAccepted': api.get('workspace')['summary']['accepted'],
                               'submissions': api.get('submissions')['total']}
        hashes = state_hashes(fresh)
        run([fresh / 'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], work / 'fresh-uninstall.log')
        assert hashes == state_hashes(fresh), 'Uninstall changed generated user data'
        result['uninstallPreservesState'] = True

        result['phase'] = 'legacy fixture'
        upgrade = work / 'upgrade'
        install(old_setup, upgrade, work / 'old-install.log')
        with serving(upgrade, work / 'old-api.json') as api:
            assert api.get('workspace')['summary']['total'] == 0
            problem = next(r['id'] for r in api.catalog['rows'] if r['contest'] == '入门赛 49' and r['problem'] == 'D')
            api.post('profile', {'nickname': '升级保留验证', 'endpoint': ''})
            api.post('draft', {'id': problem, 'code': CODE})
            submitted = api.post('submissions', {'id': problem, 'code': CODE, 'mode': 'submit'})['submission']
            deadline = time.monotonic() + 60
            while True:
                finished = next(r for r in api.get('submissions')['submissions'] if r['id'] == submitted['id'])
                if finished.get('finishedAt'): break
                assert time.monotonic() < deadline, 'Old packaged compiler did not finish'
                time.sleep(.1)
            assert finished['verdict'] == 'AC' and finished['scope'] == 'local', finished['verdict']
            tasks = api.get('daily-tasks')
            reward = next(t for t in tasks['tasks'] if t['completed'] and not t['claimed'])
            api.post('daily-tasks/claim', {'id': reward['id'], 'date': tasks['date']})
            contest, mock_problem = legacy_mock(api, problem)
            api.post('hub/configure', {'autoSync': False, 'intervalHours': 12, 'minDifficulty': 1000, 'maxDifficulty': 1800})
            api.post('translation/settings', {'provider': 'deepseek', 'model': 'deepseek-chat', 'apiKey': 'upgrade-proof-credential-00000000'})
            before = snapshot(api, problem, contest, mock_problem)
            assert before['xp'] > 0 and before['contests'] and before['submissions']
        settings = {p.name: p.read_bytes() for p in (upgrade / 'state').glob('*.json')}
        original_personal = hashlib.sha256((upgrade / 'state/tb-personal.sqlite3').read_bytes()).hexdigest()
        result['phase'] = 'upgrade install'
        install(new_setup, upgrade, work / 'upgrade-install.log')
        assert hashlib.sha256((upgrade / 'state/tb-personal.sqlite3').read_bytes()).hexdigest() == original_personal
        with serving(upgrade, work / 'upgraded-api.json') as api:
            assert snapshot(api, problem, contest, mock_problem) == before, 'Upgrade altered identity, code, history, missions or XP'
            assert len(api.catalog['rows']) == 607 and all(r['solutionAvailable'] for r in api.catalog['rows'])
            assert api.get('translation/settings')['configured']
            assert api.get('hub')['settings']['intervalHours'] == 12
            assert all((upgrade / 'state' / name).read_bytes() == raw for name, raw in settings.items())
        with sqlite3.connect(upgrade / 'state/tb-documents.sqlite3') as db:
            rows = dict(db.execute('SELECT key,value FROM documents'))
            assert json.loads(rows['translation-settings.json'])['protectedKey'] == json.loads(settings['translation-settings.json'])['protectedKey']
            assert json.loads(rows['integrations.json'])['settings']['intervalHours'] == 12
        hashes = state_hashes(upgrade)
        result['phase'] = 'upgrade uninstall'
        run([upgrade / 'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'], work / 'upgrade-uninstall.log')
        assert hashes == state_hashes(upgrade)
        result.update(ok=True, phase='complete', upgrade={'identityPreserved': True, 'codeAndDraftsPreserved': True,
                      'mockPreserved': True, 'xpPreserved': True, 'protectedSettingsMigrated': True,
                      'originalSettingsUnchanged': True, 'solutions': 607})
    except Exception as error:
        result.update(error=str(error))
        raise
    finally:
        (work / 'report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
