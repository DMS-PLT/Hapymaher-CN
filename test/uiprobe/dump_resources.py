#!/usr/bin/env python3
"""列出 exe 的 PE 资源，并把对话框/字符串表里的文本吐出来（只读）。

设置界面是个标准 Win32 对话框，它的文字大概率在 DIALOG 资源里。
直接全文件扫字节噪声太大（代码段撞出来的「汉字」一大片），按资源走才干净。

用法：
    uv run --with pefile python dump_resources.py [exe 路径]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pefile

sys.stdout.reconfigure(encoding="utf-8")

EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cmvs32.exe")

RT = {1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG", 6: "STRING",
      7: "FONTDIR", 8: "FONT", 9: "ACCELERATOR", 10: "RCDATA", 11: "MESSAGETABLE",
      12: "GROUP_CURSOR", 14: "GROUP_ICON", 16: "VERSION", 24: "MANIFEST"}


def ok_char(c: str) -> bool:
    o = ord(c)
    return (0x20 <= o <= 0x7E or 0x3000 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF
            or 0xFF01 <= o <= 0xFF60 or 0x2010 <= o <= 0x203B
            or 0x2460 <= o <= 0x24FF or 0x25A0 <= o <= 0x26FF)


def utf16_runs(b: bytes, min_chars: int = 2):
    out, start, i = [], None, 0
    while i + 1 < len(b):
        c = b[i] | (b[i + 1] << 8)
        if (b[i + 1] == 0 and 0x20 <= b[i] < 0x7F) or (c >= 0x3000 and ok_char(chr(c))):
            if start is None:
                start = i
        else:
            if start is not None and i - start >= min_chars * 2:
                out.append((start, b[start:i]))
            start = None
        i += 2
    if start is not None and len(b) - start >= min_chars * 2:
        out.append((start, b[start:]))
    return out


def main() -> int:
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    print(f"文件: {EXE.name}\n")

    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        print("没有资源目录")
        return 1

    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        name = RT.get(t.id, t.name) if t.id is not None else t.name
        n = len(t.directory.entries)
        print("=" * 78)
        print(f"资源类型 {t.id} ({name})  共 {n} 项")
        print("=" * 78)
        for e in t.directory.entries:
            for lang in e.directory.entries:
                data = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                print(f"  --- id={e.id} lang=0x{lang.id:04X}  {len(data)} 字节 ---")
                if t.id in (5, 4, 6, 10):     # DIALOG / MENU / STRING / RCDATA
                    for off, raw in utf16_runs(data):
                        try:
                            s = raw.decode("utf-16-le")
                        except Exception:  # noqa: BLE001
                            continue
                        if any(ord(c) > 0x2FFF for c in s):
                            print(f"      +0x{off:04X}  {s!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
