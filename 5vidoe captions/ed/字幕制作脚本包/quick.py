# -*- coding: utf-8 -*-
"""快速看效果 —— 把所有歌词行的画面拼成一张总览图, 十几秒出结果, 不渲染整片。

用法:
    python quick.py                 # 默认 本体/eda, 3 列总览
    python quick.py FD/edb          # 换一支
    python quick.py FD/edb --cols 2 # 每格更大
    python quick.py FD/edb --band   # 1:1 字幕带视图 (左边中文 / 右边日文, 看版式细节用这个)
    python quick.py FD/edb 3 7 12   # 只看第 3/7/12 句 (行号从 0 开始, 同 ass 顺序)
输出: _check/<target>_总览.jpg 或 _check/<target>_字幕带.jpg
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import config as C
from assparse import load_lines
from textline import build_layers

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

argv = sys.argv[1:]
target, pick, cols, band = None, [], 3, False
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--cols":
        cols = int(argv[i + 1])
        i += 2
        continue
    if a.startswith("--cols="):
        cols = int(a.split("=", 1)[1])
    elif a == "--band":
        band = True
    elif a.isdigit():
        pick.append(int(a))
    elif target is None:
        target = a
    i += 1
target = target or "本体/eda"

rel = dict(C.TARGETS)[target]
base = os.path.join(C.ROOT, rel)
lines = load_lines(os.path.splitext(base)[0] + ".ass")
if pick:
    lines = [lines[i] for i in pick if 0 <= i < len(lines)]
layers = build_layers(lines)

os.makedirs("_check", exist_ok=True)
label_font = ImageFont.truetype(C.FONT_PATH, 26)


def grab(t):
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", base, "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    frame = Image.frombytes("RGB", (C.W, C.H), raw).convert("RGBA")
    ov = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    for layer in layers:
        layer.draw(ov, t)
    frame.alpha_composite(ov)
    return frame.convert("RGB")


def line_time(L):
    t = min(L.start + 0.75, (L.start + L.end) / 2)
    return max(t, L.start + 0.1)


if band:
    # 1:1 字幕带: 左边中文区域 / 右边日文区域, 逐句一行
    bw = 1120
    bh = 190
    row_h = bh + 6
    sheet = Image.new("RGB", (bw * 2 + 16, row_h * len(lines)), (14, 12, 16))
    for i, L in enumerate(lines):
        t = line_time(L)
        f = grab(t)
        cn = f.crop((0, C.H - bh, bw, C.H))
        jp = f.crop((C.W - bw, 0, C.W, bh))
        y = i * row_h
        sheet.paste(cn, (0, y))
        sheet.paste(jp, (bw + 16, y))
        d = ImageDraw.Draw(sheet)
        tag = f"#{i:02d} {int(t // 60)}:{t % 60:05.2f}"
        d.rectangle([0, y, 190, y + 26], fill=(0, 0, 0))
        d.text((5, y + 1), tag, font=label_font, fill=(255, 226, 190))
        d.line([0, y + row_h - 3, sheet.width, y + row_h - 3], fill=(70, 40, 44))
    path = f"_check/{target.replace('/', '_')}_字幕带.jpg"
    sheet.save(path, quality=94)
    print(f"{path}  ({len(lines)} 句, {sheet.width}x{sheet.height})")
    sys.exit(0)

cell_w = C.W // cols
cell_h = cell_w * 9 // 16
rows = (len(lines) + cols - 1) // cols
sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), (18, 16, 20))

for i, L in enumerate(lines):
    t = line_time(L)
    cell = grab(t).resize((cell_w, cell_h), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(cell)
    tag = f"#{i:02d}  {int(t // 60)}:{t % 60:05.2f}"
    d.rectangle([0, 0, 8 * len(tag) + 10, 34], fill=(0, 0, 0))
    d.text((6, 4), tag, font=label_font, fill=(255, 232, 200))
    sheet.paste(cell, ((i % cols) * cell_w, (i // cols) * cell_h))

path = f"_check/{target.replace('/', '_')}_总览.jpg"
sheet.save(path, quality=92)
print(f"{path}  ({len(lines)} 句, {sheet.width}x{sheet.height})")
