# 按 mgv 帧索引表重建视频时间轴，再用 mkvmerge 封装
# 背景：ogv 内部的 granulepos 时间戳带 12.6s 假偏移（游戏不读它），
#       游戏真正的时间线 = mgv 头部的槽位表：第 i 槽 = 第 i/24 秒
# 用法：python test/rebuild_mgv_video.py <mgv文件> <ogv文件> <ogg文件> <输出mkv>
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

FPS = 24
# 优先环境变量，其次 PATH，最后常见安装路径
MKVMERGE = (os.environ.get("MKVMERGE") or shutil.which("mkvmerge")
            or r"C:\Program Files\MKVToolNix\mkvmerge.exe")


def slots_from_mgv(mgv: Path) -> list[int]:
    b = mgv.read_bytes()
    idxcount = struct.unpack_from("<I", b, 16)[0]
    vals = struct.unpack_from(f"<{idxcount}I", b, 32)
    return [v >> 16 for v in vals]  # 高16位 = 帧号


def count_ogv_frames(ogv: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(ogv)],
        capture_output=True, text=True, check=True,
    )
    return len([x for x in r.stdout.splitlines() if x.strip()])


def main() -> int:
    mgv, ogv, ogg, out = map(Path, sys.argv[1:5])
    frames = slots_from_mgv(mgv)
    distinct = []
    seen = set()
    for slot, fno in enumerate(frames):
        if fno not in seen:
            seen.add(fno)
            distinct.append((fno, slot))
        elif fno != distinct[-1][0]:
            sys.exit(f"错误：帧号乱序，槽 {slot} 出现 {fno}")
    # 帧号必须连续 0..N-1
    order = [f for f, _ in distinct]
    if order != list(range(len(order))):
        sys.exit(f"错误：帧号不连续，得到 {order[:10]}...")
    n_video = count_ogv_frames(ogv)
    if n_video != len(distinct):
        sys.exit(f"错误：ogv {n_video} 帧 ≠ 索引 {len(distinct)} 帧")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     newline="\n", encoding="utf-8") as fp:
        ts = Path(fp.name)
        fp.write("# timestamp format v2\n")
        for _, slot in distinct:
            fp.write(f"{round(slot * 1000 / FPS)}\n")

    try:
        r = subprocess.run([MKVMERGE, "--timestamps", f"0:{ts}", "-o", str(out),
                            str(ogv), str(ogg)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
    finally:
        ts.unlink(missing_ok=True)
    if r.returncode not in (0, 1):
        sys.exit(f"mkvmerge 失败：{r.stdout[-500:]} {r.stderr[-500:]}")
    print(f"ok {out.name}: {len(distinct)} 帧, {len(frames)} 槽位 "
          f"({len(frames)/FPS:.2f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
