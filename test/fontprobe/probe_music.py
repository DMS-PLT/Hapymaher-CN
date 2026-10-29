#!/usr/bin/env python3
"""♪ 保留可行性探头（只读，不碰游戏文件）

回答三个问题：
  A. 引擎那条字体链（CreateFontA(-40, charset=134, "ＭＳ ゴシック", q=2, family=0x30)）
     实际选中哪个字体？它对 U+266A（♪）有没有字形？
  B. 常见中文字体里哪些有 ♪（备选私用字体用）
  C. CP936 全码表扫描：有没有哪个双字节码位能解到 U+266A？
     以及哪些码位是「未映射 / 用户区」——那是哨兵字节对的候选。
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

sys.stdout.reconfigure(encoding="utf-8")

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

GDI_ERROR = 0xFFFFFFFF
GGO_METRICS = 0
DEFAULT_CHARSET = 1
TRANSPARENT = 1
FW_NORMAL = 400

# 引擎在 CreateFontA 里的实参（从反汇编 + 日志得到）
ENGINE_LFHEIGHT = -40
ENGINE_QUALITY = 2       # PROOF
ENGINE_PITCHFAMILY = 0x30
ENGINE_FACE_SJIS = b"\x82\x6C\x82\x72\x20\x83\x53\x83\x56\x83\x62\x83\x4E"  # ＭＳ ゴシック


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class GLYPHMETRICS(ctypes.Structure):
    _fields_ = [
        ("gmBlackBoxX", wintypes.UINT),
        ("gmBlackBoxY", wintypes.UINT),
        ("gmptGlyphOrigin", POINT),
        ("gmCellIncX", ctypes.c_short),
        ("gmCellIncY", ctypes.c_short),
    ]


class FIXED(ctypes.Structure):
    _fields_ = [("fract", wintypes.WORD), ("value", ctypes.c_short)]


class MAT2(ctypes.Structure):
    _fields_ = [("eM11", FIXED), ("eM12", FIXED), ("eM21", FIXED), ("eM22", FIXED)]


class TEXTMETRICA(ctypes.Structure):
    _fields_ = [
        ("tmHeight", wintypes.LONG), ("tmAscent", wintypes.LONG),
        ("tmDescent", wintypes.LONG), ("tmInternalLeading", wintypes.LONG),
        ("tmExternalLeading", wintypes.LONG), ("tmAveCharWidth", wintypes.LONG),
        ("tmMaxCharWidth", wintypes.LONG), ("tmWeight", wintypes.LONG),
        ("tmOverhang", wintypes.LONG), ("tmDigitizedAspectX", wintypes.LONG),
        ("tmDigitizedAspectY", wintypes.LONG),
        ("tmFirstChar", ctypes.c_byte), ("tmLastChar", ctypes.c_byte),
        ("tmDefaultChar", ctypes.c_byte), ("tmBreakChar", ctypes.c_byte),
        ("tmItalic", ctypes.c_byte), ("tmUnderlined", ctypes.c_byte),
        ("tmStruckOut", ctypes.c_byte), ("tmPitchAndFamily", ctypes.c_byte),
        ("tmCharSet", ctypes.c_byte),
    ]


MAT2_IDENT = MAT2(FIXED(0, 1), FIXED(0, 0), FIXED(0, 0), FIXED(0, 1))

_P = ctypes.c_void_p
gdi32.CreateFontA.restype = _P
gdi32.CreateFontA.argtypes = [_P] * 0 + [
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
    wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_char_p,
]
gdi32.CreateCompatibleDC.restype = _P
gdi32.CreateCompatibleDC.argtypes = [_P]
gdi32.SelectObject.restype = _P
gdi32.SelectObject.argtypes = [_P, _P]
gdi32.DeleteDC.argtypes = [_P]
gdi32.DeleteObject.argtypes = [_P]
gdi32.GetTextFaceA.argtypes = [_P, ctypes.c_int, ctypes.c_char_p]
gdi32.GetTextMetricsA.argtypes = [_P, ctypes.POINTER(TEXTMETRICA)]
gdi32.GetGlyphOutlineW.restype = wintypes.DWORD
gdi32.GetGlyphOutlineW.argtypes = [_P, wintypes.UINT, wintypes.UINT,
                                   ctypes.POINTER(GLYPHMETRICS), wintypes.DWORD,
                                   _P, ctypes.POINTER(MAT2)]
gdi32.GetGlyphOutlineA.restype = wintypes.DWORD
gdi32.GetGlyphOutlineA.argtypes = [_P, wintypes.UINT, wintypes.UINT,
                                   ctypes.POINTER(GLYPHMETRICS), wintypes.DWORD,
                                   _P, ctypes.POINTER(MAT2)]


def make_dc(face_bytes: bytes, charset: int, height: int = ENGINE_LFHEIGHT,
            quality: int = ENGINE_QUALITY, family: int = ENGINE_PITCHFAMILY) -> ctypes.c_void_p:
    """完全复刻引擎的 CreateFontA 调用（face 传原始字节，绕过 Python 编码）。"""
    font = gdi32.CreateFontA(
        height, 0, 0, 0, FW_NORMAL, False, False, False,
        charset, 0, 0, quality, family, face_bytes,
    )
    dc = gdi32.CreateCompatibleDC(None)
    gdi32.SelectObject(dc, font)
    return dc


def dc_face(dc) -> tuple[str, int]:
    buf = ctypes.create_string_buffer(64)
    gdi32.GetTextFaceA(dc, 64, buf)
    tm = TEXTMETRICA()
    gdi32.GetTextMetricsA(dc, ctypes.byref(tm))
    return buf.value.decode("mbcs", errors="replace"), tm.tmCharSet


def dc_metrics(dc) -> TEXTMETRICA:
    tm = TEXTMETRICA()
    gdi32.GetTextMetricsA(dc, ctypes.byref(tm))
    return tm


def glyph_w(dc, cp: int) -> tuple[int, int]:
    """返回 (gmCellIncX, gmCellIncY)；无字形返回 (-1, -1)。"""
    gm = GLYPHMETRICS()
    n = gdi32.GetGlyphOutlineW(dc, cp, GGO_METRICS, ctypes.byref(gm), 0, None, ctypes.byref(MAT2_IDENT))
    if n == GDI_ERROR:
        return -1, -1
    return gm.gmCellIncX, gm.gmCellIncY


def glyph_a_raw(dc, word: int) -> int:
    """按 GetGlyphOutlineA 传一个 WORD（DBCS 码），返回 gmCellIncX 或 -1。"""
    gm = GLYPHMETRICS()
    n = gdi32.GetGlyphOutlineA(dc, word, GGO_METRICS, ctypes.byref(gm), 0, None, ctypes.byref(MAT2_IDENT))
    if n == GDI_ERROR:
        return -1
    return gm.gmCellIncX


print("=" * 72)
print("A. 引擎字体链实际选中什么字体，有没有 ♪")
print("=" * 72)
for label, charset in [("charset=134 (补丁后, GB2312)", 134),
                       ("charset=128 (原版, ShiftJIS)", 128)]:
    dc = make_dc(ENGINE_FACE_SJIS, charset)
    face, cs = dc_face(dc)
    tm = dc_metrics(dc)
    adv_note, _ = glyph_w(dc, 0x266A)
    adv_han, _ = glyph_w(dc, 0x90A3)   # 那
    adv_A, _ = glyph_w(dc, 0x0041)
    print(f"\n{label}")
    print(f"  实际选中字体      : {face}   (tmCharSet={cs})")
    print(f"  tmHeight={tm.tmHeight} tmAveCharWidth={tm.tmAveCharWidth} "
          f"tmMaxCharWidth={tm.tmMaxCharWidth}")
    print(f"  汉字「那」步进    : {adv_han}")
    print(f"  ASCII 'A' 步进    : {adv_A}")
    print(f"  ♪ U+266A 字形     : {'有, 步进=' + str(adv_note) if adv_note >= 0 else '*** 没有 ***'}")

print()
print("=" * 72)
print("B. 常见字体在引擎参数下的 ♪ 覆盖")
print("=" * 72)
candidates = [
    ("ＭＳ ゴシック", ENGINE_FACE_SJIS, 128),
    ("ＭＳ ゴシック", ENGINE_FACE_SJIS, 134),
    ("SimSun", b"SimSun", DEFAULT_CHARSET),
    ("SimHei", b"SimHei", DEFAULT_CHARSET),
    ("Microsoft YaHei", b"Microsoft YaHei", DEFAULT_CHARSET),
    ("DengXian", b"DengXian", DEFAULT_CHARSET),
    ("MS Gothic (ASCII 名)", b"MS Gothic", DEFAULT_CHARSET),
    ("Arial Unicode MS", b"Arial Unicode MS", DEFAULT_CHARSET),
]
for label, face_bytes, charset in candidates:
    try:
        dc = make_dc(face_bytes, charset)
        face, _ = dc_face(dc)
        adv_note, _ = glyph_w(dc, 0x266A)
        adv_five, _ = glyph_w(dc, 0x266B)   # ♫
        adv_note2, _ = glyph_w(dc, 0x2669)  # ♩
        mark = "有" if adv_note >= 0 else "无"
        print(f"  {label:24s} -> 实际 {face:24s} ♪={mark}({adv_note:>3}) "
              f"♫={'有' if adv_five >= 0 else '无'}({adv_five:>3}) "
              f"♩={'有' if adv_note2 >= 0 else '无'}({adv_note2:>3})")
    except Exception as exc:  # noqa: BLE001
        print(f"  {label:24s} -> 失败: {exc}")

print()
print("=" * 72)
print("C. CP936 码表扫描")
print("=" * 72)

MultiByteToWideChar = ctypes.WinDLL("kernel32", use_last_error=True).MultiByteToWideChar
MultiByteToWideChar.restype = ctypes.c_int
CP_ACP, MB_ERR_INVALID_CHARS = 0, 0x00000008

mapped = {}      # (b1,b2) -> unicode
unmapped = []    # 未映射的双字节码位
pua = {}         # PUA 映射
for b1 in range(0x81, 0xFF):
    for b2 in list(range(0x40, 0x7F)) + list(range(0x80, 0xFF)):
        buf = bytes([b1, b2])
        out = ctypes.create_unicode_buffer(2)
        n = MultiByteToWideChar(CP_ACP, MB_ERR_INVALID_CHARS, buf, 2, out, 2)
        if n == 1:
            mapped[(b1, b2)] = out[0]
            if 0xE000 <= ord(out[0]) <= 0xF8FF:
                pua[(b1, b2)] = out[0]
        else:
            unmapped.append((b1, b2))

print(f"  可解码双字节码位 : {len(mapped):,}")
print(f"  未映射（空）码位 : {len(unmapped):,}")
print(f"  映射到 PUA 的码位: {len(pua):,}")

note_pairs = [f"0x{b1:02X}{b2:02X}" for (b1, b2), u in mapped.items() if u == "♪"]
print(f"\n  能解到 U+266A(♪) 的码位: {note_pairs if note_pairs else '*** 一个都没有 ***'}")
for sym in "♩♪♫♬♭♮♯":
    hits = [f"0x{b1:02X}{b2:02X}" for (b1, b2), u in mapped.items() if u == sym]
    print(f"    U+{ord(sym):04X} {sym} -> {hits if hits else '无'}")

if unmapped:
    print(f"\n  未映射码位（哨兵候选）前 20 个:")
    print("   ", " ".join(f"0x{b1:02X}{b2:02X}" for b1, b2 in unmapped[:20]))
    b1s = sorted({b1 for b1, _ in unmapped})
    print(f"    涉及的 lead byte: {', '.join(f'0x{b:02X}' for b in b1s)}")

if pua:
    print(f"\n  PUA 码位（哨兵候选）前 20 个:")
    for (b1, b2), u in list(pua.items())[:20]:
        print(f"    0x{b1:02X}{b2:02X} -> U+{ord(u):04X}")

print()
print("=" * 72)
print("D. GetGlyphOutlineA 的 WORD 字节序（确认引擎请求的形态）")
print("=" * 72)
dc = make_dc(ENGINE_FACE_SJIS, 134)
for label, word in [("那 0xC4C7 (lead 在低字节)", 0xC7C4),
                    ("那 0xC7C4 (lead 在高字节)", 0xC4C7)]:
    print(f"  uChar=0x{word:04X}  {label:26s} -> gmCellIncX={glyph_a_raw(dc, word)}")
