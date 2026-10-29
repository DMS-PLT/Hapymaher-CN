#!/usr/bin/env python3
"""dump start.plain 里的可打印串（含 NUL 分隔的字符串表）"""
import re
import sys

d = open(sys.argv[1] if len(sys.argv) > 1 else "start.plain", "rb").read()
print("size", len(d))

print("=== 可打印 ASCII 串（含 \\ . _）===")
for m in re.finditer(rb"[\x20-\x7E]{3,}", d):
    s = m.group().decode("ascii")
    if "\\" in s or "." in s or "_" in s:
        print(f"0x{m.start():04X}  {s!r}")

print()
print("=== 全部 NUL 分隔串（>=3 字节，原始）===")
for m in re.finditer(rb"[^\x00]{3,}", d):
    print(f"0x{m.start():04X}  {m.group()!r}")
