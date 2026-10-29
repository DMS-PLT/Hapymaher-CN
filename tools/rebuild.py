#!/usr/bin/env python3
"""一条命令：2文本汉化输出 -> 注入 -> 构建 -> 游戏。

翻译工程（1文本汉化\\...\\GUI_Projects）只读，不碰。译文以 2文本汉化输出 为准。

用法：
    python tools/rebuild.py 本体            # 注入 + 全量构建
    python tools/rebuild.py fd             # 同上（FD）
    python tools/rebuild.py 本体 --inject-only   # 只注入，不构建
    python tools/rebuild.py 本体 --build-only    # 只构建（用上次注入的结果）
    python tools/rebuild.py 本体 sky01      # 只构建单个脚本（调试）

流程：
    1. cmvs_galtransl.inject：2文本汉化输出\\<游戏>_gt_output + <游戏>_manifest.json
                             -> output\\<game>\\translated\\
    2. test\\cntest\\build_full.py / build_fd.py：
       clean() -> PS3_TextEditor 写 GBK 明文 -> PS3_Cryptor 加密 -> 游戏 data\\pack\\script
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
OUT_DIR = ROOT / "2文本汉化输出"

sys.path.insert(0, str(ROOT / "tools"))
import cmvs_galtransl  # noqa: E402

GAMES = {
    "本体": {
        "game": "hapymaher",
        "manifest": OUT_DIR / "本体_manifest.json",
        "gt_output": OUT_DIR / "本体_gt_output",
        "build": ROOT / "test" / "cntest" / "build_full.py",
    },
    "fd": {
        "game": "fragmentation-dream",
        "manifest": OUT_DIR / "FD_manifest.json",
        "gt_output": OUT_DIR / "FD_gt_output",
        "build": ROOT / "test" / "cntest" / "build_fd.py",
    },
}

ALIASES = {
    "hapymaher": "本体",
    "fragmentation-dream": "fd",
    "FD": "fd",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="译文副本 -> 注入 -> 构建 -> 游戏")
    ap.add_argument("target", help="本体 / fd（也认 hapymaher / fragmentation-dream）")
    ap.add_argument("--inject-only", action="store_true", help="只注入，不构建")
    ap.add_argument("--build-only", action="store_true", help="只构建，用上次注入的结果")
    ap.add_argument("scripts", nargs="*", help="只构建这些脚本（调试用，如 sky01）")
    a = ap.parse_args()

    key = ALIASES.get(a.target, a.target)
    if key not in GAMES:
        ap.error(f"不认识 {a.target!r}，可用：{', '.join(GAMES)}")
    g = GAMES[key]

    if not a.build_only:
        for label, p in (("manifest", g["manifest"]), ("译文目录", g["gt_output"])):
            if not p.exists():
                print(f"错误：找不到{label} {p}", file=sys.stderr)
                return 1
        out_dir = ROOT / "output" / g["game"] / "translated"
        out_dir.mkdir(parents=True, exist_ok=True)
        rc = cmvs_galtransl.cmd_inject(
            g["game"], g["manifest"], g["gt_output"], out_dir, False)
        if rc != 0:
            return rc

    if a.inject_only:
        return 0

    return subprocess.call([sys.executable, str(g["build"]), *a.scripts])


if __name__ == "__main__":
    sys.exit(main())
