#!/usr/bin/env python3
"""把游戏解包出来的 .ps3 脚本批量解密，放到 ハピメア脚本/code（export_scripts.py 的输入）。

用法：
    python tools/prepare_scripts.py <解包目录> [--game 本体|fd]

前置：先用 GARbro 把游戏里的 script.cpz 解开（GUI 手动，见 README）：
    GARbro → 打开 <游戏>\\data\\pack\\script.cpz → 全选 → 提取到 <解包目录>
解出来的 .ps3 是加密的，这个脚本调 RxCMVS 的 PS3_Cryptor 逐个解密。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRYPTOR = ROOT / "tools" / "RxCMVS" / "PS3_Cryptor.exe"

TARGETS = {
    "本体": ROOT / "ハピメア脚本" / "code",
    "fd": ROOT / "ハピメア Fragmentation Dream脚本" / "code",
}
ALIASES = {"hapymaher": "本体", "fragmentation-dream": "fd", "FD": "fd"}


def main() -> int:
    ap = argparse.ArgumentParser(description="批量解密 .ps3 脚本")
    ap.add_argument("src", help="GARbro 解包得到的 .ps3 目录")
    ap.add_argument("--game", default="本体", help="本体 / fd（决定输出到哪个目录）")
    a = ap.parse_args()

    key = ALIASES.get(a.game, a.game)
    if key not in TARGETS:
        print(f"未知目标 {a.game!r}，可用：本体 / fd")
        return 2
    src = Path(a.src)
    dst = TARGETS[key]
    if not CRYPTOR.exists():
        print(f"缺少 {CRYPTOR}")
        return 1
    if not src.is_dir():
        print(f"找不到输入目录 {src}")
        return 1

    files = sorted(src.glob("*.ps3"))
    if not files:
        print(f"{src} 里没有 .ps3 文件")
        return 1

    dst.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for i, f in enumerate(files, 1):
        r = subprocess.run([str(CRYPTOR), "-mode", "decode",
                            "-ps3", str(f), "-save", str(dst / f.name)],
                           capture_output=True)
        if r.returncode == 0:
            ok += 1
        else:
            fail += 1
            print(f"  [失败] {f.name}")
        if i % 40 == 0:
            print(f"  ... {i}/{len(files)}")

    print(f"\n解密完成：成功 {ok} 失败 {fail} → {dst}")
    print("下一步：python tools/export_scripts.py")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
