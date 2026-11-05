# -*- coding: utf-8 -*-
"""静态校对: python still.py FD/eda 7.2 30 60  → 生成叠加字幕的 PNG 到 _check/"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image

import config as C
from assparse import load_lines
from textline import build_layers

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

target, times = sys.argv[1], [float(x) for x in sys.argv[2:]] or [10.0]
rel = dict(C.TARGETS)[target]
base = os.path.join(C.ROOT, rel)
lines = load_lines(os.path.splitext(base)[0] + ".ass")

layers = build_layers(lines)

os.makedirs("_check", exist_ok=True)
for t in times:
    ov = Image.new("RGBA", (C.W, C.H), (0, 0, 0, 0))
    for layer in layers:
        layer.draw(ov, t)
    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", base, "-frames:v", "1",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    frame = Image.frombytes("RGB", (C.W, C.H), raw).convert("RGBA")
    frame.alpha_composite(ov)
    p = f"_check/{target.replace('/', '_')}_{t:g}.png"
    frame.convert("RGB").save(p)
    print(p)
