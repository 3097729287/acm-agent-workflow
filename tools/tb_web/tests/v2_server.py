"""GUI integration server with temporary personal data and a read-only real library."""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import create_server

with tempfile.TemporaryDirectory(prefix='tb-v2-ui-') as directory:
    temporary = Path(directory)
    server = create_server(port=18766, training_file=temporary/'personal.sqlite3',
                           history_file=temporary/'history.jsonl', backup_dir=temporary/'backups')
    print('TB v2 isolated UI server http://127.0.0.1:18766', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
