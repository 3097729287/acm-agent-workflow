"""Real TB assets with an isolated disposable personal database for UI probes."""
import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from backend import create_server
import status_report as SR
import toolutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--lifetime", type=int, default=900)
    args = parser.parse_args()
    if args.port == 18765:
        parser.error("The normal personal server port is prohibited.")
    with tempfile.TemporaryDirectory(prefix="tb-v5-real-ui-") as directory:
        root = Path(directory)
        os.environ["DSH_HOME"] = str(root / "empty-home")
        for reference in ("DEEPSEEK_API_KEY", "HUOSHAN_API_KEY", "TB_TRANSLATION_API_KEY", "TB_LEADERBOARD_URL"):
            os.environ.pop(reference, None)
        # Keep the entire source archive read-only. Even accidental status edits
        # from the probe would only affect this disposable copy of the table.
        data_file = root / "library.md"
        shutil.copyfile(SR.DEFAULT_FILE, data_file)
        server = create_server(
            port=args.port,
            data_file=data_file,
            data_root=toolutil.DATA_ROOT,
            training_file=root / "personal.sqlite3",
            history_file=root / "history.jsonl",
            backup_dir=root / "backups",
            integration_state_dir=root,
            integration_auto_start=False,
            dist_dir=APP / "dist",
        )
        timer = threading.Timer(args.lifetime, server.shutdown)
        timer.daemon = True
        timer.start()

        def stop_from_input():
            for line in sys.stdin:
                if line.strip() == "stop":
                    server.shutdown()
                    return

        threading.Thread(target=stop_from_input, daemon=True).start()
        print(json.dumps({"url": "http://127.0.0.1:%d" % server.server_address[1], "isolated": True, "pid": os.getpid()}), flush=True)
        try:
            server.serve_forever()
        finally:
            timer.cancel()
            server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
