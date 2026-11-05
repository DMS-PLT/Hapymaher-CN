#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FD OP 单句/多句/任意区间高精度快速预览工具。

用法:
    python preview_line.py 0 1 2         # 预览序幕 (L00~L02)
    python preview_line.py --span 24 31  # 预览 0:25 走廊原生题记区间
"""
import os
import sys
import subprocess

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

import config as C
from assparse import load_lines

OFF_PRE = 1.0
OFF_POST = 1.2


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
            spans.append((max(0.0, L.start - OFF_PRE), L.end + OFF_POST))
        spans.sort()
        merged = []
        for s, e in spans:
            if merged and s <= merged[-1][1] + 1.0:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        spans = merged

    for si, (a, b) in enumerate(spans):
        dur = b - a
        outname = f"preview_{si}_{a:.1f}-{b:.1f}.mp4"
        env = dict(os.environ, PREVIEW_T0=f"{a:.3f}", PREVIEW_END=f"{b:.3f}")
        raw = subprocess.Popen(
            [sys.executable, "gen.py"],
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            env=env,
            cwd=script_dir,
        )
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{C.W}x{C.H}",
            "-r", str(C.FPS), "-i", "-",
            "-i", C.BASE_VIDEO,
            "-filter_complex",
            f"[1:v]trim=start={a:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS[base];"
            f"[base][0:v]overlay=0:0[v];"
            f"[1:a]atrim=start={a:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            outname,
        ]
        subprocess.run(cmd, stdin=raw.stdout, cwd=script_dir, check=True)
        raw.wait()
        if raw.returncode != 0:
            sys.exit(f"gen.py 渲染失败 (exit {raw.returncode})")
        print(f"完成预览 -> {outname}  ({a:.2f}s ~ {b:.2f}s)")


if __name__ == "__main__":
    main()
