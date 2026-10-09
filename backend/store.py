"""Application catalog backed exclusively by SQLite after one-time migration."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import threading
from errors import APIError
from insights import canonical_url
from library import LibraryDatabase
from paths import LIBRARY_SEED, STATE
import toolutil
import knowledge_dict as KD
import status_report as SR

class Store:
    def __init__(self, data_file=None, data_root=None, history_file=None, library_file=None):
        self.lock = threading.RLock()
        self.token = __import__('secrets').token_urlsafe(32)
        self.data_root = str(Path(data_root or os.environ.get('TB_ARCHIVE_ROOT') or STATE / 'imports').resolve())
        self.extensions = None
        self.data_file = Path(data_file or Path(self.data_root) / '题解' / 'TB.md').resolve()
        state = Path(history_file).parent if history_file else self.data_file.parent if data_file else STATE
        target = Path(library_file or os.environ.get('TB_LIBRARY_DB') or state / 'tb-library.sqlite3').resolve()
        self.library = LibraryDatabase(target)
        if data_file is None and LIBRARY_SEED.is_file() and target != LIBRARY_SEED.resolve():
            self.library.merge_seed(LIBRARY_SEED)
        if not self.library.rows() and self.data_file.is_file():
            from archive_import import import_archive
            import_archive(self.library, self.data_root, self.data_file)
        if data_file is None and not self.library.rows():
            raise APIError(503, '内置题库缺失或为空，请重新完整安装 TB')
        self.history_file = Path(history_file or STATE / 'history.jsonl')
        from contestmeta import ContestDates
        self.contest_dates = ContestDates(self)

    def raw_rows(self):
        return self.library.rows(raw=True)

    def row(self, identity):
        found = self.library.find(identity)
        if found:
            return found['raw']
        remote = self.extensions.row(identity) if self.extensions else None
        if remote:
            return remote
        raise APIError(404, '没有找到这道题，请刷新列表')

    def contest_metadata(self, row, url=None):
        method = getattr(self.extensions, 'contest_metadata', None)
        return method(row, url) if callable(method) else self.contest_dates.for_row(row, url)

    def _enrich_knowledge(self, row):
        from knowledge import enrich_row
        cache = getattr(self, 'knowledge_analysis', None)
        return cache.apply(row) if cache else enrich_row(row)

    def encode_row(self, row, today=None):
        identity = row.get('_id') or row['场次'] + '::' + row['题号']
        found = self.library.find(identity)
        available, url = self._archive_info(row)
        return self._encode_record(row, found, available, url)

    def _encode_record(self, row, found, available, url):
        identity = row.get('_id') or row['场次'] + '::' + row['题号']
        if found:
            value = dict(found['encoded'])
        else:
            value = {'id': identity, 'contest': row['场次'], 'problem': row['题号'], 'title': row['题名'],
                     'knowledge': row['知识点'], 'tags': KD.split_names(row['知识点']), 'difficulty': SR.difficulty_num(str(row['难度'])),
                     'platform': row.get('_platform', '其他'), 'series': row.get('_series', '其他'), 'url': row.get('_url'),
                     'source': 'remote', 'status': '未做', 'date': '', 'queue': None, 'solutionAvailable': False, 'solutionState': 'missing'}
        value.update(solutionAvailable=available, solutionState='available' if available else 'missing')
        if url:
            value['url'] = url
        metadata = getattr(self.extensions, 'problem_metadata', None)
        if callable(metadata):
            value.update(metadata(row, value.get('url')))
        dated_row = dict(row, _library_metadata=found['encoded']) if found else row
        value.update(self.contest_metadata(dated_row, value.get('url')))
        return self._enrich_knowledge(value)

    def _archive_info(self, row):
        found = self.library.find(row.get('_id') or row['场次'] + '::' + row['题号'], canonical_url(row.get('_url')))
        return (bool(self.library.solution(found['id'])), found['url']) if found else (False, row.get('_url'))

    def data(self):
        with self.lock:
            records = self.library.catalog()
            by_id = {record['id']: record for record in records}
            by_url = {}
            for record in records:
                key = canonical_url(record['url'])
                if key:
                    by_url.setdefault(key, record)
            encoded = [self._encode_record(record['raw'], record, bool(record['available']), record['url'])
                       for record in records]
            seen_urls = {canonical_url(row.get('url')) for row in encoded if row.get('url')}
            seen_ids = {row['id'] for row in encoded}
            for row in self.extensions.rows() if self.extensions else []:
                key = canonical_url(row.get('url'))
                if row['id'] in seen_ids or key and key in seen_urls:
                    continue
                source = by_id.get(row['id']) or by_url.get(key)
                encoded.append(self._encode_record(self.extensions.row(row['id']), by_id.get(row['id']),
                                                   bool(source and source['available']), source['url'] if source else row.get('url')))
                seen_ids.add(row['id'])
                if key:
                    seen_urls.add(key)
            revision = hashlib.sha256(json.dumps(encoded, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            return {'rows': encoded, 'statuses': list(SR.STATES), 'categories': self.categories(),
                    'revision': revision, 'today': dt.date.today().isoformat(), 'token': self.token}

    def solution(self, identity):
        row = self.row(identity)
        found = self.library.find(identity, canonical_url(row.get('_url')))
        value = self.library.solution(found['id']) if found else None
        if not value:
            raise APIError(404, '这道题尚未收录题解')
        return {**value, 'title': found['encoded']['title'], 'url': found['url']}

    def update(self, body):
        raise APIError(410, '训练进度由提交记录产生，请使用运行或提交')

    def inbox(self, action=None):
        from archive_import import inbox
        return inbox(self, action)

    def categories(self):
        from knowledge import dictionary
        catalog = dictionary()
        groups, standards = catalog['groups'], set(catalog['names'])
        children = {child for parent, kids in groups.items() for child in kids if child != parent}
        def branch(name, ancestry=()):
            if name in ancestry:
                return {'name': name, 'children': [], 'tags': [name] if name in standards else []}
            nodes = [({'name': child, 'children': [], 'tags': [child] if child in standards else []} if child == name
                      else branch(child, ancestry + (name,))) for child in groups.get(name, [])]
            tags = ([name] if name in standards else []) + [tag for node in nodes for tag in node['tags']]
            return {'name': name, 'children': nodes, 'tags': list(dict.fromkeys(tags))}
        roots = [name for name in groups if name not in children]
        represented = set(groups) | children
        roots += [name for name in catalog['names'] if name not in represented]
        return [branch(name) for name in roots]
