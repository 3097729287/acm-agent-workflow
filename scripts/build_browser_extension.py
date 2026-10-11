"""Bundle the same tested OJ adapters for Edge/Chrome, without remote code."""
from pathlib import Path
import argparse
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'desktop'))
from official_bridge import page_source


def build(destination):
    destination = Path(destination).resolve()
    source = ROOT / 'desktop' / 'browser_extension'
    if destination == source or destination.is_relative_to(source):
        raise ValueError('Use a separate output directory')
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, destination / path.name)
    (destination / 'official.js').write_text(page_source(), encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    print(build(parser.parse_args().destination))
