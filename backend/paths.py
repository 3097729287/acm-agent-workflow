"""Paths shared by API, desktop and release builds; never depend on the cwd."""
from pathlib import Path
import os
import sys

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
RESOURCES = ROOT / 'resources' if getattr(sys, 'frozen', False) else ROOT / 'backend' / 'resources'
STATE = Path(os.environ.get('TB_STATE_DIR') or ROOT / 'state').resolve()
FRONTEND = ROOT / 'frontend' / 'dist'
LIBRARY_SEED = ROOT / 'data' / 'library.sqlite3'

def resource(name):
    return RESOURCES / name
