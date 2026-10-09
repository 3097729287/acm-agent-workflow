"""TB archive and submission-derived personal training HTTP service."""
from __future__ import annotations

import argparse
import io
import datetime as dt
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import parse_qs, unquote, urlsplit

TOOLS = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
COMMON = Path(__file__).resolve().parent / 'common'
sys.path.insert(0, str(COMMON if COMMON.is_dir() else TOOLS))
import knowledge_dict as KD
import status_report as SR
import toolutil
from training import TrainingService, ServiceError
from insights import canonical_url


class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)


def _gui():
    return SimpleNamespace(StatusGui=SimpleNamespace(parse_problem_url=parse_problem_url))


def parse_problem_url(self, row):
        """v12 立、v79 改：Alt+Enter 的解析链（**只读**：不改任何文件、不产生备份）。

        场次（如 `周赛 164` / `Div.2 1124`）→ 读该场题解 md（`toolutil.contest_paths`，
        就是本 GUI 回车打开的那份），取里面的比赛链接 → 拼单题页 URL：
          · 牛客 `ac.nowcoder.com/acm/contest/<cid>` → `…/<cid>/<字母>`
          · AtCoder `atcoder.jp/contests/<id>` → `…/tasks/<id>_<字母小写>`
          · CF `codeforces.com/contest/<id>` → `…/problem/<字母>`
          · 洛谷题面页按 pid——先从 `_work\题单.md` 找，找不到就报提示
        返回 (url, None)；失败 (None, 原因)：「这场还没接」（场次不认）/
        「没找到这场比赛的原题链接」（题解文件不在 / 里面没有链接行）。
        """
        name, num = toolutil.parse_contest(row["场次"])
        if name is None:
            return None, "这场还没接"
        rdir, sol = toolutil.contest_paths(self.data_root, name, num)
        try:
            with io.open(sol, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return None, "没找到这场比赛的原题链接"
        plat = toolutil.SERIES[name]["plat"]
        lt = row["题号"]
        if plat == "nowcoder":
            m = re.search(r"ac\.nowcoder\.com/acm/contest/(\d+)", text)
            if m:
                return "https://ac.nowcoder.com/acm/contest/%s/%s" % (m.group(1), lt), None
        elif plat == "atcoder":
            m = re.search(r"atcoder\.jp/contests/([A-Za-z0-9_-]+)", text)
            if m:
                cid = m.group(1)
                return "https://atcoder.jp/contests/%s/tasks/%s_%s" % (cid, cid, lt.lower()), None
        elif plat == "codeforces":
            m = re.search(r"codeforces\.com/contest/(\d+)", text)
            if m:
                return "https://codeforces.com/contest/%s/problem/%s" % (m.group(1), lt), None
        else:                            # luogu：题面页按 pid——先从 _work\题单.md 找
            p = os.path.join(rdir, "_work", "题单.md")
            if os.path.exists(p):
                try:
                    with io.open(p, "r", encoding="utf-8", errors="replace") as f:
                        for ln in f.read().split("\n"):
                            c = toolutil.split_cells(ln)
                            if c and len(c) >= 3 and c[0] == lt \
                                    and re.fullmatch(r"[A-Za-z]+\d+", c[2]):
                                return ("https://www.luogu.com.cn/problem/%s" % c[2]), None
                except OSError:
                    pass
            return None, "洛谷按题号 pid 打开（_work\\题单.md 不在，订不到链接）"
        return None, "没找到这场比赛的原题链接"



def _revision(raw):
    return hashlib.sha256(raw).hexdigest()


def _atomic_bytes(path, raw):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class LegacyStore:
    def __init__(self, data_file=None, data_root=None, history_file=None):
        self.data_file = Path(data_file or SR.DEFAULT_FILE).resolve()
        self.data_root = str(Path(data_root or toolutil.DATA_ROOT).resolve())
        self.history_file = Path(history_file or (TOOLS.parent / "logs" / "tb-web-history.jsonl"))
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.dictionary = KD.load()
        self.extensions = None
        self._catalog_cache = {}
        from contestmeta import ContestDates
        self.contest_dates = ContestDates(self)

    def contest_metadata(self, row, url=None):
        method = getattr(self.extensions, "contest_metadata", None)
        return method(row, url) if callable(method) else self.contest_dates.for_row(row, url)

    def raw_rows(self):
        try:
            return SR.parse_table(str(self.data_file))
        except SystemExit as error:
            raise APIError(422, str(error)) from error

    def row(self, identity):
        hits = [r for r in self.raw_rows() if r["场次"] + "::" + r["题号"] == identity]
        if not hits:
            remote = self.extensions.row(identity) if self.extensions is not None else None
            if remote:
                return remote
            raise APIError(404, "没有找到这道题，请刷新列表")
        if len(hits) != 1:
            raise APIError(409, "这道题存在重复记录，已停止操作")
        return hits[0]

    def categories(self):
        from knowledge import dictionary
        catalog = dictionary()
        groups = catalog["groups"]
        standards = set(catalog["names"])
        children = {child for parent, kids in groups.items() for child in kids if child != parent}

        def branch(name, ancestry=()):
            if name in ancestry:
                return {"name": name, "children": [], "tags": [name] if name in standards else []}
            nodes = []
            for child in groups.get(name, []):
                if child == name:
                    nodes.append({"name": child, "children": [], "tags": [child] if child in standards else []})
                else:
                    nodes.append(branch(child, ancestry + (name,)))
            tags = ([name] if name in standards else []) + [tag for node in nodes for tag in node["tags"]]
            return {"name": name, "children": nodes, "tags": list(dict.fromkeys(tags))}

        roots = [name for name in groups if name not in children]
        represented = set(groups) | children
        roots += [name for name in catalog["names"] if name not in represented]
        return [branch(name) for name in roots]

    def _enrich_knowledge(self, row):
        from knowledge import enrich_row
        cache = getattr(self, "knowledge_analysis", None)
        if cache is not None:
            with cache.lock:
                previous = cache.state.get(row.get("id"))
                if previous:
                    row = {**row, "knowledgeAnalysis": previous}
        return enrich_row(row)

    def encode_row(self, row, today):
        if row.get("_remote"):
            return self._enrich_knowledge({"id": row["_id"], "contest": row["场次"], "problem": row["题号"], "title": row["题名"], "knowledge": row["知识点"], "tags": KD.split_names(row["知识点"]), "difficulty": SR.difficulty_num(str(row["难度"])), "status": "未做", "date": "", "platform": row.get("_platform", "其他"), "series": row.get("_series", "其他"), "queue": None, "url": row.get("_url"), "source": "remote", "solutionAvailable": False, "solutionState": "missing", **self.contest_metadata(row, row.get("_url"))})
        series, _ = toolutil.parse_contest(row["场次"])
        platform = toolutil.SERIES.get(series, {}).get("dir", ("其他",))[0]
        date = SR.parse_date(row["日期"]) if row["日期"] else None
        age = (today - date).days if date else None
        state = row["状态"]
        queue = None
        if state == SR.TODO_HARD:
            queue = "rewrite"
        elif state in SR.TODO_FILL:
            queue = "fill"
        elif state in SR.REVIEW and age is not None and age >= 7:
            queue = "review"
        elif state == SR.KEEP and age is not None and age >= SR.KEEP_DAYS:
            queue = "check"
        tags = [self.dictionary.canonical(name) or name for name in KD.split_names(row["知识点"])]
        available, url = self._archive_info(row)
        metadata = getattr(self.extensions, "problem_metadata", None)
        latest = metadata(row, url) if callable(metadata) else {}
        return self._enrich_knowledge({"id": row["场次"] + "::" + row["题号"], "contest": row["场次"],
                "problem": row["题号"], "title": row["题名"], "knowledge": row["知识点"],
                "tags": list(dict.fromkeys(tags)), "difficulty": SR.difficulty_num(row["难度"]),
                "status": state, "date": row["日期"], "platform": platform,
                "series": series or "其他", "queue": queue, "source": "archive",
                "url": url, "solutionAvailable": available, "solutionState": "available" if available else "missing", **self.contest_metadata(row, url), **latest})

    def _archive_info(self, row):
        series, number = toolutil.parse_contest(row["场次"])
        if series is None:
            return False, None
        directory, source = toolutil.contest_paths(self.data_root, series, number)
        if not source:
            return False, None
        path = Path(source)
        listing = Path(directory) / "_work" / "题单.md"
        try:
            signatures = tuple((str(item), item.stat().st_mtime_ns, item.stat().st_size) if item.exists() else (str(item), None, None) for item in (path, listing))
        except OSError:
            return False, None
        key = str(path)
        cached = self._catalog_cache.get(key)
        if cached is None or cached[0] != signatures:
            catalog = toolutil.parse_catalog(str(path)) if path.is_file() else {}
            urls = {}
            for letter in catalog:
                probe = dict(row, 题号=letter)
                urls[letter], _ = _gui().StatusGui.parse_problem_url(SimpleNamespace(data_root=self.data_root), probe)
            cached = self._catalog_cache[key] = (signatures, catalog, urls)
        return row["题号"] in cached[1], cached[2].get(row["题号"])

    def data(self):
        with self.lock:
            today = dt.date.today()
            before = self.data_file.read_bytes()
            rows = self.raw_rows()
            after = self.data_file.read_bytes()
            if before != after:
                raise APIError(409, "数据刚被其他程序修改，请刷新")
            encoded = [self.encode_row(row, today) for row in rows]
            seen_urls = {canonical_url(row.get("url")) for row in encoded if canonical_url(row.get("url"))}
            seen_ids = {row["id"] for row in encoded}
            remote = self.extensions.rows() if self.extensions is not None else []
            for row in remote:
                key = canonical_url(row.get("url"))
                if row["id"] in seen_ids or key and key in seen_urls:
                    continue
                encoded.append(self._enrich_knowledge(row))
                seen_ids.add(row["id"])
                if key:
                    seen_urls.add(key)
            revision = _revision(after) if not remote else _revision(after + json.dumps(remote, sort_keys=True, ensure_ascii=False).encode())
            return {"rows": encoded, "statuses": list(SR.STATES),
                    "categories": self.categories(), "revision": revision,
                    "today": today.isoformat(), "token": self.token}

    def solution(self, identity):
        row = self.row(identity)
        if row.get("_remote"):
            key = canonical_url(row.get("_url"))
            row = next((candidate for candidate in self.raw_rows() if key and canonical_url(self._archive_info(candidate)[1]) == key), None)
            if row is None:
                raise APIError(404, "题解未生成")
        series, number = toolutil.parse_contest(row["场次"])
        if series is None:
            raise APIError(404, "没有找到这场比赛的题解")
        _, path = toolutil.contest_paths(self.data_root, series, number)
        if not path or not Path(path).is_file():
            raise APIError(404, "没有找到这场比赛的题解")
        text = Path(path).read_text(encoding="utf-8-sig")
        catalog = toolutil.parse_catalog(path)
        letter = row["题号"]
        if letter not in catalog:
            raise APIError(404, "题解目录中没有这道题")
        lines = text.splitlines(keepends=True)
        masked = toolutil.fence_mask(lines, tilde=True)
        headings, candidates = [], []
        for i, line in enumerate(lines):
            if masked[i]:
                continue
            heading = re.match(r"^##(?!#)\s+(.+?)\s*$", line)
            if not heading:
                continue
            headings.append(i)
            match = re.match(r"^" + re.escape(letter) + r"(?:[.．、:：]\s*|\s+)(.+)$", heading.group(1))
            if match:
                candidates.append((i, toolutil.norm_title(match.group(1)) == toolutil.norm_title(catalog[letter][0])))
        exact = [i for i, matches_title in candidates if matches_title]
        # Math/HTML escaping may differ between a directory cell and its heading.
        # A unique problem-code heading remains authoritative once catalog membership is confirmed.
        if len(exact) == 1:
            start = exact[0]
        elif len(candidates) == 1:
            start = candidates[0][0]
        else:
            raise APIError(404, "没有找到这道题对应的题解章节")
        end = next((i for i in headings if i > start), len(lines))
        url, _ = _gui().StatusGui.parse_problem_url(SimpleNamespace(data_root=self.data_root), row)
        return {"markdown": "".join(lines[start:end]).rstrip(), "path": path,
                "url": url, "title": row["题名"]}


def import_archive(database, root, data_file=None):
    """Read a legacy archive once. Never migrate its personal status into a library."""
    from archive_assets import LegacyAssetLibrary
    from lecture_library import LectureLibrary, portable_markdown
    root = Path(root).resolve()
    if root.name == '题解':
        root = root.parent
    data_file = Path(data_file or root / '题解' / 'TB.md')
    store = LegacyStore(data_file, root)
    assets = LegacyAssetLibrary(store)
    lectures = LectureLibrary(store)
    lectures._refresh()
    entries = {item['id']: item for item in lectures.export()['lectures']}
    records, references = [], {}
    for raw in store.raw_rows():
        raw = dict(raw, 状态='未做', 日期='')
        encoded = store.encode_row(raw, dt.date.today())
        identity = encoded['id']
        encoded.update(status='未做', date='', queue=None)
        solution = None
        if encoded['solutionAvailable']:
            solution = store.solution(identity)
            source = Path(solution['path'])
            original = solution['markdown']
            solution['images'] = lectures._images(original, source)
            solution['markdown'] = portable_markdown(original)[0]
            solution['path'] = source.relative_to(root).as_posix()
        statement = dict(assets._cached(identity))
        if statement.get('markdown'):
            statement['markdown'] = portable_markdown(statement['markdown'])[0]
        records.append((raw, encoded, solution, statement))
        own = [i for i, e in entries.items() if identity in e.get('sourceProblemIds', [])]
        links = [(i, 'own') for i in own]
        # Cross-problem lessons require a reference in the same prose line.
        # Sharing a DP/number-theory tag is never proof of using a lesson.
        if solution:
            lines = solution['markdown'].splitlines(keepends=True)
            mask = toolutil.fence_mask(lines, tilde=True)
            pointers = [line for line, fenced in zip(lines, mask) if not fenced and re.search(r'详见|参见|从零讲|已讲过|见《', line)]
            seen_concepts = {entries[i].get('knowledgeName') for i in own}
            for i, entry in entries.items():
                if i in own or entry.get('knowledgeName') in seen_concepts:
                    continue
                for pointer in pointers:
                    contest = entry.get('sourceContest', '')
                    if contest and re.search(re.escape(contest)+r'(?!\d)',pointer) and any(name and name in pointer for name in (entry.get('originalConcept'), entry.get('knowledgeName'))):
                        links.append((i, 'explicit'))
                        seen_concepts.add(entry.get('knowledgeName'))
                        break
        references[identity] = links
    # Retain the deterministic portable corpus when the legacy archive is small.
    if not entries:
        saved = json.loads(__import__('paths').resource('curated_lectures.json').read_text(encoding='utf-8'))
        entries = {e['id']: e for e in saved.get('lectures', []) if e.get('markdown')}
    database.import_records(records, entries, references, {'sourceKind': 'legacy-import', 'lectureAudit': json.dumps(lectures.audit, ensure_ascii=False)})
    return database.check()


def inbox(store, action=None):
    """Preview interchange files, then commit content/lesson relations as one transaction."""
    from lecture_library import portable_markdown
    import lecture_curation as C
    from knowledge import normalize_tags
    directory = Path(store.data_root) / '题解' / '_收件箱'
    files = sorted(directory.glob('*.md')) if directory.is_dir() else []
    summary = {'pending': 0, 'conflicts': [], 'errors': [], 'adds': [], 'files': [p.name for p in files], 'path': str(directory)}
    if action is not None and action not in ('import', 'skip', 'overwrite'):
        raise APIError(400, '收件箱操作无效')
    records, entries, references = [], {}, {}
    for path in files:
        try:
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError('题解文件超过 8 MB')
            text = path.read_text(encoding='utf-8-sig')
            parsed = C.parse_document(text)
            first = next((line for line in parsed['lines'] if line.startswith('# ')), '')
            match = re.search(r'(周赛|小白月赛|练习赛|挑战赛|入门赛|基础赛|月赛|ABC|ARC|AGC|Div\.[234])\s*#?\s*(\d+)', first)
            if not match:
                raise ValueError('首行缺少场次名')
            contest = match[1] + ' ' + match[2]
            for letter, (title, tags, difficulty, *_) in parsed['catalog'].items():
                identity = contest + '::' + letter
                summary['pending'] += 1
                existing = store.library.find(identity)
                summary['conflicts' if existing else 'adds'].append({'file': path.name, 'id': identity, 'title': title})
                markdown = parsed['problems'].get(letter)
                if not markdown:
                    raise ValueError('缺少完整题目章节 ' + letter)
                if existing and action == 'skip':
                    continue
                markdown = portable_markdown(markdown)[0]
                normalized = normalize_tags(KD.split_names(tags))['tags']
                series, _ = toolutil.parse_contest(contest)
                raw = {'场次': contest, '题号': letter, '题名': title, '知识点': tags, '难度': str(difficulty), '状态': '未做', '日期': ''}
                urls = re.findall(r'https?://(?:codeforces\.com|atcoder\.jp|ac\.nowcoder\.com|www\.luogu\.com\.cn)/[^\s<>`]+',markdown)
                url = urls[0] if urls and canonical_url(urls[0]) else existing['url'] if existing else None
                encoded = {'id': identity, 'contest': contest, 'problem': letter, 'title': title, 'knowledge': tags, 'tags': normalized,
                           'difficulty': SR.difficulty_num(str(difficulty)), 'platform': toolutil.SERIES.get(series, {}).get('dir', ['其他'])[0], 'series': series,
                           'source': 'import', 'status': '未做', 'date': '', 'queue': None, 'url': url, 'solutionAvailable': True}
                records.append((raw, encoded, {'markdown': markdown, 'path': path.name}, None))
                links = []
                problem = C.parse_document(markdown)
                for heading in problem['headings']:
                    if heading['level'] < 3 or not re.search(r'从零讲', heading['title']):
                        continue
                    body = heading['body']
                    if len(body) < 90 or len(body) < 300 and re.search(r'详见|参见|已讲过|见《',body):
                        continue
                    lecture_id = 'import:' + hashlib.sha256((identity + heading['title'] + body).encode()).hexdigest()[:24]
                    source = '# ' + heading['title'] + '\n\n' + body
                    entry = {'id': lecture_id, 'title': heading['title'], 'tags': normalized,
                             'sourceContest': contest, 'sourceProblem': letter, 'sourceTitle': title,
                             'sourceProblemIds': [identity], 'sourcePath': path.name, 'available': True, 'images': {}}
                    entries[lecture_id] = C.curate(entry, source, markdown)
                    links.append((lecture_id, 'own'))
                references[identity] = links
        except (OSError, UnicodeError, ValueError) as error:
            summary['errors'].append({'file': path.name, 'message': str(error)})
    if action is None:
        return summary
    if summary['errors']:
        return dict(summary, needsChoice=False)
    if summary['conflicts'] and action == 'import':
        return dict(summary, needsChoice=True)
    if records:
        store.library.backup('before-import')
        store.library.import_records(records, entries, references)
    archive = directory / '_已导入'
    if files:
        archive.mkdir(exist_ok=True)
    for path in files:
        destination = archive / (dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + path.name)
        path.rename(destination)
    updated = sum(bool(store.library.find(row[1]['id'])) and row[1]['id'] in {item['id'] for item in summary['conflicts']} for row in records)
    return dict(summary, pending=0, result={'added': len(records)-updated, 'updated': updated}, needsChoice=False)
