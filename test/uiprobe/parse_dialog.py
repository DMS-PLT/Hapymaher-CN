#!/usr/bin/env python3
"""正经解析 PE 里的 DIALOG 资源，逐项列出（控件 id / 类名 / 文字）。

前一版是「扫 UTF-16 字节」，噪声大（二进制字段被误读成汉字）。
这里按 DLGTEMPLATE / DLGITEMTEMPLATE 的真实结构走，列出来的就是对话框里真实存在的文字。

⚠ 这个 exe 里**两种模板格式都有**，得分开认：

    扩展 DLGTEMPLATEEX   开头 01 00 FF FF            134/137/138/139/147
    标准 DLGTEMPLATE     开头直接就是 style(DWORD)   132/133/135/136

判据就是第 2、3 字节是不是 FF FF。两种的差别：

    ┌──────────────┬──────────────────────┬──────────────────────┐
    │              │ 扩展 DLGTEMPLATEEX   │ 标准 DLGTEMPLATE    │
    ├──────────────┼──────────────────────┼──────────────────────┤
    │ 控件 id       │ DWORD                │ WORD                 │
    │ 控件前         │ helpID(DWORD)        │ 无                   │
    │ DS_SHELLFONT │ weight+italic+cs     │ 同 DS_SETFONT        │
    └──────────────┴──────────────────────┴──────────────────────┘

**但两边的字符串都是 UTF-16** —— 这点很关键：标准模板里也是 UTF-16，
所以 132/133/135/136 的乱码成因和 139 是同一个（Unicode 模板被
DialogBoxParamA 按系统码页转），不是「SJIS 字节被当 GBK 读」。

字符串字段的编码：0x0000 = 空 / 0xFFFF+WORD = 序号 / 否则 UTF-16 NUL 结尾。
控件之间 DWORD 对齐。

用法：
    uv run --with pefile python parse_dialog.py <exe> [资源 id ...]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import pefile

sys.stdout.reconfigure(encoding="utf-8")

EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"C:\Users\DMS\Desktop\Hapymaher\ハピメア フルHD版\cmvs32.exe")
WANT = [int(a) for a in sys.argv[2:]]

DS_SETFONT = 0x40
DS_SHELLFONT = 0x48


class Reader:
    def __init__(self, b: bytes):
        self.b, self.i = b, 0

    def u16(self) -> int:
        v = struct.unpack_from("<H", self.b, self.i)[0]; self.i += 2; return v

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.b, self.i)[0]; self.i += 4; return v

    def align4(self) -> None:
        self.i = (self.i + 3) & ~3

    def string(self) -> str:
        """模板里的字符串字段：0x0000 = 空 / 0xFFFF+序号 / UTF-16 NUL 结尾。"""
        v = self.u16()
        if v == 0x0000:
            return ""
        if v == 0xFFFF:
            return f"<ordinal {self.u16()}>"
        self.i -= 2
        start = self.i
        while True:
            c = self.u16()
            if c == 0:
                break
        return self.b[start:self.i - 2].decode("utf-16-le", errors="replace")


def parse(d: bytes) -> dict:
    """解析 DIALOG 模板，自动分辨扩展 / 标准两种格式。

    判据：第 2、3 字节是 FF FF 就是扩展（dlgVer=1 + signature=0xFFFF）。
    两种格式的字符串**都是 UTF-16**，所以调用方不用关心走的是哪条路。
    """
    ext = len(d) >= 4 and d[2:4] == b"\xff\xff"
    return _parse_ex(d) if ext else _parse_std(d)


def _parse_ex(d: bytes) -> dict:
    r = Reader(d)
    r.u16()                                   # dlgVer(=1)
    r.u16()                                   # signature(=0xFFFF)
    r.u32()                                   # helpID
    ex, style = r.u32(), r.u32()
    cdit = r.u16()
    x, y, cx, cy = r.u16(), r.u16(), r.u16(), r.u16()
    out = {"ver": 1, "style": style, "count": cdit, "rect": (x, y, cx, cy),
           "menu": r.string(), "class": r.string(), "title": r.string(),
           "font": "", "items": []}

    if style & DS_SETFONT:
        pt = r.u16()
        weight = r.u16()
        italic = self_byte(r)
        charset = self_byte(r)
        face = r.string()
        out["font"] = f"{face}  {pt}pt  weight={weight} italic={italic} charset={charset}"

    for _ in range(cdit):
        r.align4()
        r.u32()                               # 控件 helpID
        i_ex, i_style = r.u32(), r.u32()
        ix, iy, icx, icy = r.u16(), r.u16(), r.u16(), r.u16()
        cid = r.u32()                         # 扩展格式里 id 是 DWORD
        cls = r.string()
        title = r.string()
        extra = r.u16()
        out["items"].append({"id": cid, "class": cls, "title": title,
                             "style": i_style, "rect": (ix, iy, icx, icy)})
        if extra:                       # 创建数据：一个 WORD 长度 + 数据，跳过去
            cb = r.u16()
            r.i += cb
    return out


def _parse_std(d: bytes) -> dict:
    """标准 DLGTEMPLATE：id 是 WORD，控件前没有 helpID，也没有 charset 那三字节。"""
    r = Reader(d)
    style, ex = r.u32(), r.u32()
    cdit = r.u16()
    x, y, cx, cy = r.u16(), r.u16(), r.u16(), r.u16()
    out = {"ver": 0, "style": style, "count": cdit, "rect": (x, y, cx, cy),
           "menu": r.string(), "class": r.string(), "title": r.string(),
           "font": "", "items": []}

    if style & DS_SETFONT:
        pt = r.u16()
        out["font"] = f"{r.string()}  {pt}pt"

    for _ in range(cdit):
        r.align4()
        i_ex, i_style = r.u32(), r.u32()
        ix, iy, icx, icy = r.u16(), r.u16(), r.u16(), r.u16()
        cid = r.u16()                         # ← 标准格式里是 WORD
        cls = r.string()
        title = r.string()
        extra = r.u16()
        out["items"].append({"id": cid, "class": cls, "title": title,
                             "style": i_style, "rect": (ix, iy, icx, icy)})
        if extra:
            cb = r.u16()
            r.i += cb
    return out


def self_byte(r: Reader) -> int:
    v = r.b[r.i]; r.i += 1; return v


def main() -> int:
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    print(f"文件: {EXE.name}\n")

    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 5:
            continue
        for e in t.directory.entries:
            if WANT and e.id not in WANT:
                continue
            for lang in e.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                try:
                    info = parse(d)
                except Exception as exc:  # noqa: BLE001
                    print(f"=== DIALOG {e.id}  解析失败: {exc}")
                    continue
                print("=" * 78)
                print(f"DIALOG {e.id}  ({len(d)} 字节)  "
                      f"{'扩展' if info['ver'] else '标准'}模板  "
                      f"style=0x{info['style']:08X}  "
                      f"控件 {info['count']} 个  字体 {info['font']}")
                print(f"  标题   : {info['title']!r}")
                print(f"  类名   : {info['class']!r}   菜单: {info['menu']!r}")
                print("-" * 78)
                for it in info["items"]:
                    if it["title"] or it["class"]:
                        print(f"  id={it['id']:<5} {it['class']:<8} {it['title']!r}")
                print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
