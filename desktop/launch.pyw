"""用 Python313/pythonw.exe 运行本文件，后台启动 TB，避免控制台闪现。"""

import ctypes
from pathlib import Path
import sys
import traceback


try:
    from launch import main
except Exception:
    detail = traceback.format_exc()
    log_file = Path(__file__).resolve().parents[2] / "logs" / "tb-web.log"
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8") as stream:
            stream.write(detail + "\n")
    except OSError:
        pass
    ctypes.windll.user32.MessageBoxW(
        None, f"TB 启动组件无法加载。\n\n详细记录：{log_file}", "TB 启动失败", 0x10,
    )
    raise SystemExit(1)


raise SystemExit(main())
