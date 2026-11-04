# -*- coding: utf-8 -*-
"""把某个 ED 视频的双语字幕渲染成 RGBA 裸流写到 stdout (由 render.py 接 ffmpeg)。

用法: python gen.py FD/eda
"""
import os
import subprocess
import sys

from PIL import Image

import config as C
from assparse import load_lines
from textline import build_layers

TARGET = sys.argv[1] if len(sys.argv) > 1 else "本体/eda"
REL = dict(C.TARGETS).get(TARGET)
if REL is None:
    sys.exit(f"未知目标: {TARGET}，可选: {', '.join(k for k, _ in C.TARGETS)}")

BASE = os.path.join(C.ROOT, REL)
ASS = os.path.splitext(BASE)[0] + ".ass"
if not os.path.exists(BASE):
    sys.exit(f"找不到视频: {BASE}")
if not os.path.exists(ASS):
    sys.exit(f"找不到字幕: {ASS}")


def last_pts(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "packet=pts_time", "-of", "csv=p=0", path],
        text=True,
    )
    return max(float(x) for x in out.splitlines() if x.strip())


LINES = load_lines(ASS)
layers = build_layers(LINES)

N = int(round(last_pts(BASE) * C.FPS)) + 2
_T0 = float(os.environ.get("PREVIEW_T0", 0.0))
_T1 = float(os.environ.get("PREVIEW_END", N / C.FPS + 1.0))
fi0 = max(0, round(_T0 * C.FPS))
fi1 = min(N, round(_T1 * C.FPS))

out = sys.stdout.buffer
for fi in range(fi0, fi1):
    t = fi / C.FPS
    canvas = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    for layer in layers:
        layer.draw(canvas, t)
    out.write(canvas.tobytes())
    if (fi - fi0) % 240 == 0:
        print(f"[{TARGET}] frame {fi}/{fi1}  t={t:.1f}s", file=sys.stderr)

print(f"[{TARGET}] overlay done ({fi1 - fi0} 帧)", file=sys.stderr)
