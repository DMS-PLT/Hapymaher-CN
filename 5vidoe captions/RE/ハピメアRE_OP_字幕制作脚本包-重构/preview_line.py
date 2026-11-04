#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单句快速预览: 只渲染指定句 (含前后各 2 秒) 并与 opre.mkv 合成, 几秒出片。

用法:
    python preview_line.py 2            # 预览第 2 句 (0~17)
    python preview_line.py 14 15        # 多句 (自动合并相邻区间)
    python preview_line.py --span 55 58 # 任意时间段

依赖: numpy, pillow, ffmpeg; 基底 ../opre.mkv (唯一事实来源)。
输出: preview_*.mp4
"""
import os
import sys
import subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import config as C
from assparse import load_lines

OFF_PRE = OFF_POST = 2.0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    spans = []
    if args[0] == "--span":
        spans.append((float(args[1]), float(args[2])))
    else:
        lines = {L.li: L for L in load_lines()}
        for a in args:
            L = lines[int(a)]
            spans.append((L.start, L.end))
        spans.sort()
        merged = []
        for s, e in spans:
            if merged and s <= merged[-1][1] + 1.0:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        spans = merged

    for si, (s, e) in enumerate(spans):
        a = max(0.0, s - OFF_PRE)
        b = e + OFF_POST
        dur = b - a
        outname = f"preview_{si}_{a:.1f}-{b:.1f}.mp4"

        env = dict(os.environ, PREVIEW_T0=f"{a:.3f}", PREVIEW_END=f"{b:.3f}")
        raw = subprocess.Popen([sys.executable, "gen.py"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=env)
        cmd = ["ffmpeg", "-y", "-v", "error",
               "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{C.W}x{C.H}",
               "-r", str(C.FPS), "-i", "-",
               "-ss", f"{a:.3f}", "-t", f"{dur:.3f}", "-i", C.BASE_VIDEO,
               "-filter_complex", "[1:v][0:v]overlay=0:0", "-map", "1:a",
               "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
               "-c:a", "aac", outname]
        subprocess.run(cmd, stdin=raw.stdout)
        raw.wait()
        print(f"-> {outname}  ({a:.2f}s ~ {b:.2f}s)")


if __name__ == "__main__":
    main()
