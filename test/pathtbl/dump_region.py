#!/usr/bin/env python3
"""dump exe 里一段区域的可打印串（ASCII 与 SJIS 都试）"""
import re
import sys

path = sys.argv[1]
lo = int(sys.argv[2], 0)
hi = int(sys.argv[3], 0)

d = open(path, "rb").read()[lo:hi]

# 收集所有以 NUL 结尾的可打印串
i = 0
while i < len(d):
    j = d.find(b"\x00", i)
    if j < 0:
        j = len(d)
    chunk = d[i:j]
    if len(chunk) >= 2 and all(32 <= b < 127 for b in chunk):
        print(f"{lo+i:06X}  {chunk.decode('ascii')!r}")
        i = j + 1
        continue
    if len(chunk) >= 2 and all(b in (9, 10, 13) or 32 <= b < 127 or b >= 0x81 or b == 0x5C for b in chunk):
        try:
            dec = chunk.decode("cp932")
            if any(c >= "\u0080" for c in dec) or " " in dec:
                print(f"{lo+i:06X}  SJIS {dec!r}")
                i = j + 1
                continue
        except UnicodeDecodeError:
            pass
    i += 1
