#!/usr/bin/env python3
"""把 exe 里的 UTF-16LE / SJIS 字符串挖出来（只读）。

用途：设置界面那个对话框的文字存在 exe 里，而且是 UTF-16（所以能正常显示日文）。
要汉化它，先得知道到底有哪些串、在哪、什么编码。

用法：
    python dump_exe_strings.py [exe 路径] [--min 3]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cmvs32.exe")
MIN_CHARS = 3


def _ok_char(c: str) -> bool:
    """像人写的字吗。收窄判据是为了滤掉 PE 头和代码被误当成 UTF-16 的噪声。"""
    o = ord(c)
    return (0x20 <= o <= 0x7E                     # ASCII 可见
            or 0x3000 <= o <= 0x30FF              # 假名 + 全角标点
            or 0x4E00 <= o <= 0x9FFF              # 汉字
            or 0xFF01 <= o <= 0xFF60              # 全角字符
            or 0x2010 <= o <= 0x203B              # 引号破折号省略号
            or 0x2190 <= o <= 0x21FF
            or 0x2460 <= o <= 0x24FF              # 带圈数字
            or 0x25A0 <= o <= 0x26FF              # 符号
            or 0x2160 <= o <= 0x217F
            or 0x00A0 <= o <= 0x00FF)


def _runs(d: bytes, ok, step: int, finalize):
    out, start = [], None
    i = 0
    while i + step <= len(d):
        if ok(d, i, step):
            if start is None:
                start = i
        else:
            if start is not None:
                finalize(out, d, start, i)
                start = None
        i += step
    if start is not None:
        finalize(out, d, start, len(d))
    return out


def _ok_utf16(d, i, step):
    lo, hi = d[i], d[i + 1]
    if hi == 0 and 0x20 <= lo < 0x7F:
        return True
    c = lo | (hi << 8)
    return _ok_char(chr(c))


def _ok_sjis(d, i, step):
    return False  # 占位，见 scan_sjis


def scan_utf16(d: bytes):
    def fin(out, d, a, b):
        raw = d[a:b]
        if len(raw) // 2 >= MIN_CHARS:
            out.append((a, raw))
    return _runs(d, _ok_utf16, 2, fin)


def scan_sjis(d: bytes):
    out, start, i = [], None, 0
    while i < len(d):
        b = d[i]
        ok, step = False, 1
        if 0x20 <= b < 0x7F:
            ok = True
        elif (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC):
            if i + 1 < len(d) and (0x40 <= d[i + 1] <= 0xFC and d[i + 1] != 0x7F):
                ok, step = True, 2
        if ok:
            if start is None:
                start = i
        else:
            if start is not None:
                out.append((start, d[start:i]))
                start = None
            step = 1
        i += step
    if start is not None:
        out.append((start, d[start:]))
    return out


def main() -> int:
    d = EXE.read_bytes()
    print(f"文件: {EXE.name}  {len(d):,} 字节\n")

    print("=" * 78)
    print(f"UTF-16LE 串（>= {MIN_CHARS} 字，且含非 ASCII）")
    print("=" * 78)
    for off, raw in scan_utf16(d):
        if len(raw) // 2 < MIN_CHARS:
            continue
        try:
            s = raw.decode("utf-16-le")
        except Exception:  # noqa: BLE001
            continue
        if not any(ord(c) > 0x2FFF for c in s):
            continue
        print(f"  0x{off:06X}  {len(s):3d} 字  {s!r}")

    print()
    print("=" * 78)
    print("SJIS 串（>= 4 字节，且含双字节）")
    print("=" * 78)
    for off, raw in scan_sjis(d):
        if len(raw) < 4 or not any(b >= 0x81 for b in raw):
            continue
        try:
            s = raw.decode("cp932")
        except Exception:  # noqa: BLE001
            continue
        print(f"  0x{off:06X}  {len(raw):3d} 字节  {s!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
