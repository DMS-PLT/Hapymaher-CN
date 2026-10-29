#!/usr/bin/env python3
"""分析 hooklog.txt：统计字体/字形请求，并判断引擎实际在用什么编码。

用法：python analyze.py [hooklog.txt]
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("hooklog.txt"))
if not path.exists():
    sys.exit(f"找不到 {path}")

fonts: list[str] = []
metrics: list[str] = []
codes: list[int] = []
hooks: list[str] = []

for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
    f = line.split("\t")
    if f[0] == "font":
        fonts.append(line)
    elif f[0] == "metrics":
        metrics.append(line)
    elif f[0] == "hook":
        hooks.append(line)
    elif f[0] == "glyph" and len(f) >= 2:
        codes.append(int(f[1], 16))

print(f"文件: {path}  ({path.stat().st_size:,} 字节)")
print(f"hook 成功: {len(hooks)} 个")
for h in hooks:
    print("   ", h.replace("\t", " "))
print(f"\n创建字体 {len(fonts)} 次:")
for x in collections.Counter(fonts).most_common(8):
    n, s = x[1], x[0].replace("\t", " ")
    print(f"   {n:6d}× {s}")
print(f"\n字体度量变化 {len(set(metrics))} 种:")
for s in sorted(set(metrics))[:8]:
    print("   ", s.replace("\t", " "))
print(f"\n字形请求共 {len(codes):,} 次，不同字符码 {len(set(codes)):,} 个")

if not codes:
    print("\n没有字形记录——游戏可能还没走到画文字的地方。")
    sys.exit(0)


def score(text: str) -> float:
    """可读性打分：假名/汉字/常用标点占比"""
    if not text:
        return 0.0
    good = sum(1 for c in text
               if "぀" <= c <= "ヿ"          # 假名
               or "一" <= c <= "鿿"          # 汉字
               or c in "、。「」！？…―ー～♪　0123456789")
    return good / len(text)


print("\n=== 字形码流按两种字节序 × 两种编码试解 ===")
for order_name, tobytes in [
    ("低字节在前(lead=低8位)", lambda c: bytes([c & 0xFF, (c >> 8) & 0xFF])),
    ("高字节在前(lead=高8位)", lambda c: bytes([(c >> 8) & 0xFF, c & 0xFF])),
]:
    buf = b"".join(tobytes(c)[:2] if c > 0xFF else bytes([c & 0xFF]) for c in codes)
    for enc in ("shift_jis", "gbk"):
        try:
            t = buf.decode(enc, errors="replace")
        except Exception:
            continue
        print(f"  {order_name} + {enc:<10} 可读率 {score(t):5.1%}   样例: {t[:46]!r}")

print("\n=== 出现最多的字符码 ===")
for code, n in collections.Counter(codes).most_common(20):
    ch = ""
    for enc in ("gbk", "shift_jis"):
        try:
            b = bytes([code & 0xFF, (code >> 8) & 0xFF]) if code > 0xFF else bytes([code & 0xFF])
            ch = b.decode(enc)
            break
        except Exception:
            ch = "?"
    print(f"   0x{code:04X}  {n:6d} 次")
