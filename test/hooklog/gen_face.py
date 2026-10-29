#!/usr/bin/env python3
"""从 cnpatch.log 里抠出引擎请求的字体名的原始字节，生成 fontmetrics.c 需要的 C 字面量。

引擎传的是 ANSI 串（这里就是 Shift-JIS 字节），不能靠手写字面量猜，
直接从日志里取实际值最保险。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

LOG = Path(r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cnpatch.log")

b = LOG.read_bytes()
m = re.search(rb"face=([\x20-\xff]+?)\s+-> charset", b)
if not m:
    sys.exit("日志里找不到 face= 字段")

face = m.group(1)
print("原始字节:", face.hex(" "))
print("长度:", len(face), "字节 →", len(face) // 2, "个双字节字符")
print("按 cp932:", face.decode("cp932", errors="replace"))
print()
print("C 字面量:")
print('    static const char kEngineFace[] = "' + "".join(f"\\x{c:02X}" for c in face) + '";')
