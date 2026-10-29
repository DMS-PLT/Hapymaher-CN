#!/usr/bin/env python3
"""换字体前的度量对比（只读）。

排版宽度是引擎按 GetTextMetricsA 的返回值算的，所以换字体前必须先把这些数字
和「现在能正常显示的那一份」对齐。重点看：

  tmMaxCharWidth  —— 文档 §3.2 记的坑：charset 128 的 MS Gothic 是 79，
                     charset 134 那份是 40，差一倍，把 4 个 CreateFontA 调用点
                     全改就会让排版宽度算错。
  全角空格 A1A1 的步进 —— §3.3 的元凶字符，换字体后这个数字变了要当心。
  汉字 / ASCII 的步进 —— 直接决定折行位置。

字体参数完全照抄引擎：CreateFontA(-40, 0,0,0, 400, 0,0,0, charset, 0,0, 2, 0x30, face)。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from probe_music import (  # noqa: E402  复用已验过的 ctypes 封装
    DEFAULT_CHARSET, ENGINE_FACE_SJIS, GDI_ERROR, GLYPHMETRICS, MAT2, MAT2_IDENT,
    TEXTMETRICA, dc_metrics, glyph_w, gdi32,
)

sys.stdout.reconfigure(encoding="utf-8")


def make(face: bytes, charset: int, height: int = -40):
    font = gdi32.CreateFontA(height, 0, 0, 0, 400, False, False, False,
                             charset, 0, 0, 2, 0x30, face)
    dc = gdi32.CreateCompatibleDC(None)
    gdi32.SelectObject(dc, font)
    return dc


def report(label: str, face: bytes, charset: int, note: str = ""):
    dc = make(face, charset)
    buf = ctypes.create_string_buffer(64)
    gdi32.GetTextFaceA(dc, 64, buf)
    tm = dc_metrics(dc)
    adv_han, _ = glyph_w(dc, 0x90A3)     # 那
    adv_ascii, _ = glyph_w(dc, 0x0041)   # A
    adv_space, _ = glyph_w(dc, 0x3000)   # 全角空格
    adv_note, _ = glyph_w(dc, 0x266A)    # ♪

    def s(v):
        return f"{v:>4}" if v >= 0 else "  --"

    print(f"  {label}")
    print(f"      实际选中 : {buf.value.decode('gbk', errors='replace')}"
          f"   (原始字节 {buf.value.hex(' ').upper()})")
    print(f"      tmHeight={tm.tmHeight}  tmAscent={tm.tmAscent}  tmDescent={tm.tmDescent}"
          f"  tmAveCharWidth={tm.tmAveCharWidth}  tmMaxCharWidth={tm.tmMaxCharWidth}"
          f"  tmOverhang={tm.tmOverhang}  cs={tm.tmCharSet}")
    print(f"      步进: 那={s(adv_han)}  A={s(adv_ascii)}  全角空格={s(adv_space)}"
          f"  ♪={s(adv_note)}")
    if note:
        print(f"      {note}")
    print()


print("=" * 78)
print("① 现在游戏里实际用的（正文能正常显示的这一份）")
print("=" * 78)
report("ＭＳ ゴシック + charset=134  → 补丁后正文走这条",
       ENGINE_FACE_SJIS, 134, "★ 基准：换字体后这些数字要尽量和它一致")
report("ＭＳ ゴシック + charset=128  → 原版 / 另 3 个未改的调用点",
       ENGINE_FACE_SJIS, 128)

print("=" * 78)
print("② 黑体（候选）")
print("=" * 78)
report("黑体(SimHei) + charset=134", b"SimHei", 134,
       "GB2312 是 SimHei 的原生字符集")
report("黑体(SimHei) + charset=128", b"SimHei", 128,
       "若显示的不是黑体，说明 SJIS 字符集下选不中它")
report("黑体(SimHei) + charset=1(DEFAULT)", b"SimHei", DEFAULT_CHARSET)
report("黑体 中文名 → SimHei + charset=134", "黑体".encode("gbk"), 134,
       "直接给中文名能不能选中同一个字体")

print("=" * 78)
print("③ 其它候选")
print("=" * 78)
for name, face, cs in [
    ("宋体 SimSun", b"SimSun", 134),
    ("等线 DengXian", b"DengXian", 134),
    ("微软雅黑 Microsoft YaHei", b"Microsoft YaHei", 134),
    ("新宋体 NSimSun", b"NSimSun", 134),
]:
    report(f"{name} + charset={cs}", face, cs)
