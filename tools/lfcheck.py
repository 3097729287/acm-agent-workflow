# -*- coding: utf-8 -*-
"""核查一组文件的 CRLF / BOM / 体量：CRLF 必须为 0、BOM 必须为 False。"""
import io
import sys

for f in sys.argv[1:]:
    b = io.open(f, "rb").read()
    print("%-58s CRLF=%d  BOM=%s  bytes=%d  lines=%d"
          % (f, b.count(b"\r\n"), b.startswith(b"\xef\xbb\xbf"), len(b), b.count(b"\n") + 1))
