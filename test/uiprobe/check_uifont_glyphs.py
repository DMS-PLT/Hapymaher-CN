#!/usr/bin/env python3
"""查译文用到的字，在候选字体里到底有没有字形。

起因：对话框标题「复原功能」里的 **复** 显示不正常。
推断是模板自带的 ＭＳ Ｐゴシック（日文）里没有这个简体字，GDI 只好做字体链接
去别的字体借一个字形 —— 于是同一个词里「原/功/能」是 MS Gothic、「复」是借来的，
笔画和字面大小对不上。

这个脚本就验这条推断，顺带验换字体之后是不是真的都齐了。

判据用 `GetGlyphIndicesW` + `GGI_MARK_NONEXISTING_GLYPHS`：
字体里没有的码位直接返回 **0xFFFF**，比"看黑框宽度"干净 ——
那条路是当初查 ♪ 时踩出来的（GDI 缺字不报错，只给你一个豆腐块）。

用法：
    uv run python check_uifont_glyphs.py
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
TABLE = ROOT / "test" / "hooklog" / "cnpatch_ui.txt"

GDI32 = ctypes.WinDLL("gdi32")
USER32 = ctypes.WinDLL("user32")

GGI_MARK_NONEXISTING_GLYPHS = 0x0001
DEFAULT_CHARSET = 1

GDI32.CreateCompatibleDC.argtypes = [wintypes.HDC]
GDI32.CreateCompatibleDC.restype = wintypes.HDC
GDI32.CreateFontW.argtypes = [ctypes.c_int] * 5 + [wintypes.DWORD] * 4 + \
                             [wintypes.DWORD] * 4 + [wintypes.LPCWSTR]
GDI32.CreateFontW.restype = wintypes.HFONT
GDI32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
GDI32.SelectObject.restype = wintypes.HGDIOBJ
GDI32.GetGlyphIndicesW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int,
                                   ctypes.POINTER(wintypes.WORD), wintypes.DWORD]
GDI32.GetGlyphIndicesW.restype = wintypes.DWORD
GDI32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
GDI32.DeleteDC.argtypes = [wintypes.HDC]


def missing_in(face: str, charset: int, chars: list[str], pt: int = 9) -> list[str]:
    """返回这些字里，该字体**没有字形**的那些。"""
    hdc = GDI32.CreateCompatibleDC(None)
    # lfHeight 负数 = 字符高度（磅值 → 像素的大致换算是 96dpi 下 pt*4/3）
    h = GDI32.CreateFontW(-(pt * 96 // 72), 0, 0, 0, 400, 0, 0, 0,
                          charset, 0, 0, 0, 0, face)
    old = GDI32.SelectObject(hdc, h)

    out: list[str] = []
    for c in chars:
        gi = wintypes.WORD(0)
        n = GDI32.GetGlyphIndicesW(hdc, c, 1, ctypes.byref(gi), GGI_MARK_NONEXISTING_GLYPHS)
        if n == 0 or gi.value == 0xFFFF:
            out.append(c)

    GDI32.SelectObject(hdc, old)
    GDI32.DeleteObject(h)
    GDI32.DeleteDC(hdc)
    return out


def main() -> int:
    text = TABLE.read_text(encoding="utf-8-sig")
    chars: list[str] = []
    seen: set[str] = set()
    nline = 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "\t" not in s:
            continue
        zh = s.split("\t", 1)[1].strip()
        nline += 1
        for c in zh:
            if c not in seen:
                seen.add(c)
                chars.append(c)

    # 标点/ASCII 不参与 —— 哪个字体都有
    chars = [c for c in chars if ord(c) > 0x2000]
    print(f"译文表 {nline} 条，用到 {len(chars)} 个不同的非 ASCII 字\n")

    print("【病因核对】日文字体（对话框模板自带的那个）")
    for face, cs in (("ＭＳ Ｐゴシック", 128), ("MS PGothic", 128)):
        miss = missing_in(face, cs, chars)
        print(f"  {face:<16} charset=128  缺 {len(miss)} 个字：{''.join(miss[:60])}")
    print()

    print("【换字体后】候选中文字体")
    for face, cs in (("SimHei", 134), ("SimSun", 134), ("NSimSun", 134),
                     ("Microsoft YaHei", 134)):
        miss = missing_in(face, cs, chars)
        flag = "✅ 齐" if not miss else f"❌ 缺 {len(miss)} 个：{''.join(miss[:60])}"
        print(f"  {face:<16} charset={cs}  {flag}")

    print("\n注：只查字符**有没有字形**，不查字形好不好看 —— 好不好看要开游戏看。")

    if "--png" in sys.argv:
        render_compare()
    return 0


def render_compare() -> None:
    """把同一句话在三个候选字体里画出来存成 PNG，用来肉眼比对。

    这一步是"复"那个问题的定案手段：`ＭＳ Ｐゴシック` 里 **复 是有字形的**，
    所以 GetGlyphIndices 查不出来 —— 但它给的是**日文字形**，比周围几个字明显窄。
    字形「有没有」和字形「对不对」是两回事，后者只能画出来看。
    """
    from PIL import Image, ImageDraw, ImageFont   # noqa: PLC0415  (可选依赖)

    sample = "复原功能  要恢复到读取之前的状态吗？"
    rows = [
        ("Microsoft YaHei UI (系统标题栏用的)", r"C:\Windows\Fonts\msyh.ttc", "标题栏"),
        ("ＭＳ Ｐゴシック (对话框模板自带的)",  r"C:\Windows\Fonts\msgothic.ttc", "改之前"),
        ("SimHei (换过之后)",                   r"C:\Windows\Fonts\simhei.ttf", "改之后"),
    ]
    img = Image.new("RGB", (760, 62 * len(rows) + 12), "white")
    d = ImageDraw.Draw(img)
    small = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 15)
    for i, (name, path, note) in enumerate(rows):
        y = 12 + i * 62
        d.text((10, y + 4), f"{name}   [{note}]", fill=(120, 120, 120), font=small)
        try:
            d.text((330, y), sample, fill="black", font=ImageFont.truetype(path, 24))
        except OSError as exc:
            d.text((330, y), f"(打不开: {exc})", fill="red", font=small)
    out = ROOT / "test" / "uiprobe" / "font_compare.png"
    img.save(out)
    print(f"参考图已写到 {out}  —— 看 ＭＳ Ｐゴシック 那行的「复」和「读」")


if __name__ == "__main__":
    sys.exit(main())
