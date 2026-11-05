# -*- coding: utf-8 -*-
"""快速预览: python preview.py FD/eda 30 36  → 输出 30s~36s 的预览片段"""
import os
import subprocess
import sys

import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

target = sys.argv[1] if len(sys.argv) > 1 else "本体/eda"
t0 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
t1 = float(sys.argv[3]) if len(sys.argv) > 3 else t0 + 8.0
rel = dict(C.TARGETS)[target]
base = os.path.join(C.ROOT, rel)
out = f"preview_{target.replace('/', '_')}_{t0:g}-{t1:g}.mp4"

env = dict(os.environ, PREVIEW_T0=str(t0), PREVIEW_END=str(t1))
gen = subprocess.Popen([sys.executable, "gen.py", target], stdout=subprocess.PIPE, env=env)
ff = subprocess.Popen(
    ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
     "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{C.W}x{C.H}", "-r", str(C.FPS), "-i", "-",
     "-ss", str(t0), "-i", base,
     "-filter_complex", "[1:v][0:v]overlay=0:0:shortest=1",
     "-map", "1:a:0", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "128k", "-shortest", out],
    stdin=gen.stdout,
)
gen.stdout.close()
ff.wait()
gen.wait()
print("预览 ->", out)
