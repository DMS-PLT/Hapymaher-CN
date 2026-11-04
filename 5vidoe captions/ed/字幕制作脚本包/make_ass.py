# -*- coding: utf-8 -*-
"""生成可在 Aegisub 里继续编辑的双语 .ass (与烧录成片版式一致: 日文右上 / 中文左下)。

用法: python make_ass.py          # 全部目标
      python make_ass.py FD/eda
"""
import os
import sys

import config as C
from assparse import load_lines

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

HEAD = """[Script Info]
; 中日双语 ED 字幕 —— 日文右上 / 中文左下
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {w}
PlayResY: {h}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: JP,TW-Kai,{jp_size},&H00FFFFFF,&H00FFFFFF,&H00120C10,&H64000000,0,0,0,0,100,100,{jp_sp},0,1,2.4,1.4,9,{jp_mr},40,{jp_top},1
Style: CN,TW-Kai,{cn_size},&H00FCF8FF,&H00FCF8FF,&H00120C10,&H64000000,0,0,0,0,100,100,{cn_sp},0,1,2.4,1.4,1,{cn_left},40,{cn_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build(target):
    rel = dict(C.TARGETS)[target]
    base = os.path.join(C.ROOT, rel)
    lines = load_lines(os.path.splitext(base)[0] + ".ass")
    out = os.path.splitext(base)[0] + "_中日.ass"
    body = [HEAD.format(w=C.W, h=C.H, jp_size=C.FONT_SIZE_JP, cn_size=C.FONT_SIZE_CN,
                        jp_sp=C.JP_SPACING, cn_sp=C.CN_SPACING,
                        jp_mr=C.JP_RIGHT, jp_top=C.JP_TOP,
                        cn_left=C.CN_LEFT, cn_bottom=C.CN_BOTTOM)]
    for L in lines:
        body.append(f"Dialogue: 0,{_ts(L.start)},{_ts(L.end)},JP,,0,0,0,,{L.jp}\n")
        if L.cn:
            body.append(f"Dialogue: 1,{_ts(L.start)},{_ts(L.end)},CN,,0,0,0,,{L.cn}\n")
    open(out, "w", encoding="utf-8-sig").write("".join(body))
    print("写入", out, f"({len(lines)} 条)")


for t in (sys.argv[1:] or [k for k, _ in C.TARGETS]):
    build(t)
