"""Import legacy educational files into a portable SQLite library."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend' / 'common'))
from library import LibraryDatabase
from archive_import import import_archive

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'library.sqlite3')
    args = parser.parse_args()
    database = LibraryDatabase(args.output)
    if database.rows():
        database.backup('before-import')
    print(json.dumps(import_archive(database, args.archive), ensure_ascii=False))
