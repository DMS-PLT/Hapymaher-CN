#!/usr/bin/env python3
"""在 cmvs32.exe 里找与封包/扩展名有关的 ASCII 串"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r"ハピメア フルHD版\cmvs32.exe"
d = open(path, "rb").read()
print("exe 大小", len(d))

pats = [b".cpz", b"cpz", b"CPZ", b".pb3", b"pb3", b".ps3", b"ps3",
        b"data\\pack", b"data\\", b"pack"]

for pat in pats:
    hits = [m.start() for m in re.finditer(re.escape(pat), d)]
    print(f"{pat!r:14} {len(hits):4} 处  {[hex(h) for h in hits[:10]]}")

# 把含 pack 的可打印串整条列出来
print("\n=== 含 pack / cpz 的可打印串 ===")
seen = set()
for m in re.finditer(rb"[ -~]{4,}", d):
    s = m.group()
    if b"pack" in s.lower() or b"cpz" in s.lower():
        if s not in seen:
            seen.add(s)
            print(f"0x{m.start():06X}  {s.decode('ascii')!r}")
