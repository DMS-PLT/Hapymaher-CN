# -*- coding: utf-8 -*-
"""整片合成: python render.py [目标...]   (不带参数则渲染全部 5 支)

沿用已修好的 VFR 管线: overlay=shortest=1 + fps_mode passthrough + 音轨原样复制,
渲染完成后按帧数校验, 不一致直接报错。
"""
import os
import subprocess
import sys

import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)


def frame_count(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        text=True,
    )
    return int(out.strip())


def render_one(target):
    rel = dict(C.TARGETS)[target]
    base = os.path.join(C.ROOT, rel)
    out_path = os.path.splitext(base)[0] + C.OUT_SUFFIX
    if os.path.abspath(out_path) == os.path.abspath(base):
        sys.exit("输出不能覆盖基底视频")

    print(f"\n=== {target} -> {out_path}", flush=True)
    gen = subprocess.Popen([sys.executable, "gen.py", target],
                           stdout=subprocess.PIPE, cwd=HERE)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stats",
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{C.W}x{C.H}",
         "-r", str(C.FPS), "-i", "-",
         "-i", base,
         "-filter_complex", "[1:v][0:v]overlay=0:0:shortest=1",
         "-map", "1:a:0",
         "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-fps_mode", "passthrough",
         "-c:a", "copy",
         out_path],
        stdin=gen.stdout, cwd=HERE,
    )
    gen.stdout.close()
    ff.wait()
    gen.wait()
    if gen.returncode != 0:
        sys.exit(f"{target}: gen.py 失败 ({gen.returncode})")
    if ff.returncode != 0:
        sys.exit(f"{target}: ffmpeg 失败 ({ff.returncode})")

    nb_base, nb_out = frame_count(base), frame_count(out_path)
    if nb_base != nb_out:
        sys.exit(f"{target}: 帧数校验失败 基底 {nb_base} / 输出 {nb_out}")
    print(f"[OK] {target}: {nb_out}/{nb_base} 帧", flush=True)


targets = sys.argv[1:] or [k for k, _ in C.TARGETS]
unknown = [t for t in targets if t not in dict(C.TARGETS)]
if unknown:
    sys.exit(f"未知目标: {unknown}")

for t in targets:
    render_one(t)

print("\n全部完成。")
