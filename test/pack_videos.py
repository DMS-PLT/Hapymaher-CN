# 字幕成片批量回写游戏：成片 -> Theora ogv -> MGV_Editor replace -> 换入
# 每步失败即停，已换入的文件不受影响；原始 mgv 全部备份到 test/backup/video/
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # 项目根（test 往上两级）
CAP = ROOT / "5video captions"
WORK = ROOT / "test" / "video_work"
BACKUP = ROOT / "test" / "backup" / "video"
MGV_EDITOR = ROOT / "tools" / "RxCMVS" / "MGV_Editor.exe"
# 游戏安装目录：可用环境变量指定，默认放在项目根目录下
MAIN_GAME = Path(os.environ.get("HAPYMAHER_GAME") or (ROOT / "ハピメア フルHD版"))
FD_GAME = Path(os.environ.get("HAPYMAHER_FD_GAME") or (ROOT / "ハピメア Fragmentation Dream フルHD版"))
MAIN = MAIN_GAME / "data" / "video"
FD = FD_GAME / "data" / "video"

# (成片, 目标 mgv, 期望帧数, 备份名)
JOBS = [
    (CAP / "FD" / "FDop_字幕成片.mkv", FD / "op.mgv", 3089, "FD_op"),
    (CAP / "RE" / "REop_字幕成片.mkv", FD / "opre.mgv", 2427, "FD_opre"),
    (CAP / "ed" / "本体" / "eda_中日字幕成片.mkv", MAIN / "eda.mgv", 3270, "本体_eda"),
    (CAP / "ed" / "FD" / "eda_中日字幕成片.mkv", FD / "eda.mgv", 2928, "FD_eda"),
    (CAP / "ed" / "FD" / "edb_中日字幕成片.mkv", FD / "edb.mgv", 4796, "FD_edb"),
    (CAP / "ed" / "FD" / "edc_中日字幕成片.mkv", FD / "edc.mgv", 2693, "FD_edc"),
    (CAP / "ed" / "FD" / "edd_中日字幕成片.mkv", FD / "edd.mgv", 4062, "FD_edd"),
]


def frame_count(ogv: Path) -> int:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(ogv)],
        capture_output=True, text=True, check=True,
    )
    return len([x for x in r.stdout.splitlines() if x.strip()])


def verify_and_swap(newmgv: Path, target: Path, backup: Path, ogv: Path) -> None:
    old = backup.read_bytes()
    new = newmgv.read_bytes()
    ho = struct.unpack_from("<4sIIIIIHHII", old, 0)
    hn = struct.unpack_from("<4sIIIIIHHII", new, 0)
    idx = ho[4] * 4
    if hn[2] != ogv.stat().st_size:
        sys.exit(f"  视频大小字段不符: {hn[2]} != {ogv.stat().st_size}")
    if old[32:32 + idx] != new[32:32 + idx]:
        sys.exit("  索引段与原文件不一致")
    if old[32 + idx:32 + idx + ho[3]] != new[32 + idx:32 + idx + hn[3]]:
        sys.exit("  音频段与原文件不一致")
    if hn[0] != ho[0] or hn[1] != ho[1] or hn[5:] != ho[5:]:
        sys.exit("  头部其余字段与原文件不一致")
    expect = 32 + idx + hn[3] + hn[2]
    if len(new) != expect:
        sys.exit(f"  文件总大小不符: {len(new)} != {expect}")
    newmgv.replace(target)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    BACKUP.mkdir(parents=True, exist_ok=True)
    for i, (src, target, expect, label) in enumerate(JOBS, 1):
        t0 = time.time()
        ogv = WORK / f"{label}.ogv"
        backup = BACKUP / f"{label}.mgv.orig"
        print(f"[{i}/{len(JOBS)}] {label}", flush=True)
        if not src.is_file():
            sys.exit(f"  找不到成片 {src}")
        if not target.is_file():
            sys.exit(f"  找不到目标 {target}")
        if not backup.exists():
            shutil.copy2(target, backup)
            print("  已备份原始 mgv", flush=True)

        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(src),
             "-map", "0:v", "-c:v", "libtheora", "-q:v", "8",
             "-pix_fmt", "yuv420p", "-fps_mode", "passthrough", str(ogv)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            sys.exit(f"  编码失败: {r.stderr[-800:]}")
        n = frame_count(ogv)
        if n != expect:
            sys.exit(f"  帧数不符: {n} != {expect}")
        print(f"  编码完成 {n} 帧, {ogv.stat().st_size/1048576:.1f} MiB", flush=True)

        r = subprocess.run(
            [str(MGV_EDITOR), "-mode", "replace",
             "-mgv", str(target), "-ogv", str(ogv)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        newmgv = Path(str(target) + ".new")
        if not newmgv.is_file():
            sys.exit(f"  替换失败: {r.stdout[-400:]} {r.stderr[-400:]}")
        verify_and_swap(newmgv, target, backup, ogv)
        print(f"  已换入 ({time.time()-t0:.0f}s)", flush=True)

    print("全部完成", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
