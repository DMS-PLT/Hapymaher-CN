#!/usr/bin/env python3
"""解析 PE 里的 MENU 资源，列出每一项（层级、flags、原文）。

菜单模板是顺序结构，不是「扫 UTF-16 字节」—— 那样会从半个字符处开始读，
扫出一堆前面带怪字的假串（`翠LOAD_001` 那种）。按结构逐项走才干净：

    MENUHEADER:  WORD wVersion(0)  WORD cbHeaderSize(0)
    然后一串 MENUITEMTEMPLATE，每项：
        WORD mtOption      标志位（0x10=MF_POPUP，0x800=MF_END 表示本层结束）
        WORD mtID          POPUP 项这项另有含义，普通项是命令 id
        WCHAR mtString[]   UTF-16，NUL 结尾

用法：
    uv run --with pefile python parse_menu.py [exe] [资源 id ...]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pefile

sys.stdout.reconfigure(encoding="utf-8")

EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cmvs32.exe")
WANT = [int(a, 0) for a in sys.argv[2:]]

MF_POPUP = 0x0010
MF_END = 0x0080          # 本层最后一项（模板里的名字是 MF_END）


def parse(d: bytes) -> list[tuple[bool, int, int, str]]:
    """返回 [(是否 POPUP, flags, id, 原文)]。

    实测出来的格式（看字节定的，不是照文档猜的）：

        menuitem := WORD mtOption
                    [WORD mtID]        ← **只有普通项才有；POPUP 项没有这个字段**
                    WCHAR string[]     ← UTF-16，NUL 结尾
        （每项之后 DWORD 对齐）

    照「POPUP 也有 mtID」写会多读 2 字节，症状是字符串开头少一个字，
    并且 POPUP 项会读出一个假 id（`LOAD(&L)` 的 'L' 被当成 id=76）。
    """
    ver, hdr = struct.unpack_from("<HH", d, 0)
    if ver != 0:
        raise ValueError(f"不是经典菜单模板（wVersion={ver}）")
    # 项从 4 + cbHeaderSize 开始：MENUHEADER 本身占 4 字节，cbHeaderSize 是
    # 「头部额外部分」的大小（普通菜单是 0）。写成 i = cbHeaderSize 就会从 0 开始，
    # 把 MENUHEADER 的四个 0 字节当成第一项的 flags/id。
    out: list[tuple[bool, int, int, str]] = []
    i = 4 + hdr
    while i + 2 <= len(d):
        flags = struct.unpack_from("<H", d, i)[0]
        i += 2
        popup = bool(flags & MF_POPUP)
        mid = 0
        if not popup:
            if i + 2 > len(d):
                break
            mid = struct.unpack_from("<H", d, i)[0]
            i += 2
        start = i
        while i + 1 < len(d):
            c = struct.unpack_from("<H", d, i)[0]
            i += 2
            if c == 0:
                break
        s = d[start:i - 2].decode("utf-16-le", errors="replace")
        out.append((popup, flags, mid, s))
    return out


def main() -> int:
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 4:                     # RT_MENU
            continue
        for e in t.directory.entries:
            if WANT and e.id not in WANT:
                continue
            for lang in e.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                items = parse(d)
                print(f"MENU {e.id}  ({len(d)} 字节，{len(items)} 项)")
                print("（POPUP 项模板里没有 id 字段，id 显示为 -）\n")
                for popup, flags, mid, s in items:
                    kind = "POPUP" if popup else "ITEM "
                    ids = "   -  " if popup else f"{mid:<6}"
                    print(f"  {kind} id={ids} flags=0x{flags:04X}  {s!r}")
                print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
