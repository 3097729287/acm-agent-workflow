"""Export the bundled SQLite library to text JSON, or rebuild it from that source.

`data/library.sqlite3` is a build artifact and is not tracked by git; the text
source under `data/library/` is. First startup and release assembly rebuild the
SQLite file automatically when it is missing.
"""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend' / 'common'))
from library import LibraryDatabase, source_fingerprint


def export(args):
    database = LibraryDatabase(args.input, readonly=True)
    directory = database.export_source(args.output)
    print(json.dumps({'exported': str(directory), 'fingerprint': source_fingerprint(directory)}, ensure_ascii=False))


def build(args):
    database = LibraryDatabase.from_source(args.source, args.output)
    print(json.dumps({'built': str(database.path), 'fingerprint': source_fingerprint(args.source),
                      'rows': database.check()}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Manage the public library text seed')
    sub = parser.add_subparsers(dest='action', required=True)
    export_parser = sub.add_parser('export', help='SQLite -> data/library/*.json')
    export_parser.add_argument('--input', type=Path, default=ROOT / 'data' / 'library.sqlite3')
    export_parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'library')
    export_parser.set_defaults(func=export)
    build_parser = sub.add_parser('build', help='data/library/*.json -> SQLite')
    build_parser.add_argument('--source', type=Path, default=ROOT / 'data' / 'library')
    build_parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'library.sqlite3')
    build_parser.set_defaults(func=build)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
