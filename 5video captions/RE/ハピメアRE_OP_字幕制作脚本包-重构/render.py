# -*- coding: utf-8 -*-
"""整条 OP 渲染 + 合成成片。
用法:
    python render.py              # 输出 op_out.mkv
    python render.py myfilm.mkv   # 自定义文件名

原理: 用 subprocess 把 gen.py 和 ffmpeg 连成管道, 不落中间文件。
      Python 的 subprocess 管道是二进制安全的, 不需要 20GB 的临时裸流。
"""
import sys
import subprocess
import os

OUT = sys.argv[1] if len(sys.argv) > 1 else "op_out.mkv"

script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

import config as C

if os.path.abspath(OUT) == os.path.abspath(C.BASE_VIDEO):
    sys.exit("输出文件不能覆盖基底视频，请换一个输出名")


def frame_count(path):
    result = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-count_frames",
            "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        text=True,
    )
    return int(result.strip())


gen = subprocess.Popen(
    [sys.executable, "gen.py"],
    stdout=subprocess.PIPE,
    stderr=sys.stderr,
    cwd=script_dir,
)

ffmpeg = subprocess.Popen(
    [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{C.W}x{C.H}", "-r", str(C.FPS), "-i", "-",
        "-i", C.BASE_VIDEO,
        "-filter_complex", "[1:v][0:v]overlay=0:0:shortest=1", "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p",
        "-fps_mode", "passthrough",
        "-c:a", "copy",
        OUT,
    ],
    stdin=gen.stdout,
    cwd=script_dir,
)

gen.stdout.close()   # 让 gen 的 SIGPIPE 能正常传播
ffmpeg.wait()
gen.wait()

if gen.returncode != 0:
    sys.exit(f"gen.py 失败 (exit {gen.returncode})")
if ffmpeg.returncode != 0:
    sys.exit(f"ffmpeg 失败 (exit {ffmpeg.returncode})")

expected_frames = frame_count(C.BASE_VIDEO)
actual_frames = frame_count(OUT)
if actual_frames != expected_frames:
    sys.exit(f"帧数校验失败：基底 {expected_frames} 帧，输出 {actual_frames} 帧；请勿回写游戏")

print(f"完成 -> {OUT}（{actual_frames} 帧，保留基底可变时间轴）")
