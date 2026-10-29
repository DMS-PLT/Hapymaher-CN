#!/usr/bin/env python3
"""一键生成发布包：已经构建好的游戏目录 -> 发布包\\<包名>\\

用法：
    python tools/make_release.py 本体     # 只做本体
    python tools/make_release.py fd       # 只做 FD
    python tools/make_release.py          # 两个都做

前置条件（这一步不管，它只负责打包）：
    译文改动 -> 在 GalTranslPP 里 Rebuild -> 复制 gt_output 到 2文本汉化输出/
             -> python tools/rebuild.py 本体   （FD 用 fd）
    界面图改动 -> PSD 改完导出到 ps修改/cs -> 复制到 chip_png -> pb3 encode 到 chip_new
             -> 同上跑 rebuild.py（build_full.py 会把 chip_new 铺进游戏目录）

发布包内容（和玩家实际覆盖的顺序一致）：
    cmvs32_cn.exe / cmvs32_cn_FD.exe   启动器（launch_gui*.exe 改名，带图标）
    cnpatch.dll + cnpatch_ui.txt       补丁 DLL 与界面译文表
    TW-Kai-98_1.ttf                    随包字体（私有加载）
    data/pack/start.ps3                路径表已改成读散装目录
    data/pack/script/*.ps3             **全部**脚本
    data/pack/chip/*                   **全部**界面图（含没改过的原版，缺一张游戏就报错）
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "test" / "hooklog"
OUT = ROOT / "发布包"

GAMES = {
    "本体": {
        "game": ROOT / "ハピメア フルHD版",
        "exe": "launch_gui.exe",
        "pkg": "ハピメア RE.ver 修图+gemini-4-argon翻译补丁v1.0",
        "cn": "cmvs32_cn.exe",
        # 卸载还原用的加密原版 start.ps3（构建时从它解密再打补丁的，逐字节就是装机原版）
        "orig_start": ROOT / "test" / "backup" / "start.ps3.orig",
        "readme": "release_readme_main.txt",
    },
    "fd": {
        "game": ROOT / "ハピメア Fragmentation Dream フルHD版",
        "exe": "launch_gui_fd.exe",
        "pkg": "ハピメア FD RE.ver 修图+gemini-4-argon翻译补丁v1.0",
        "cn": "cmvs32_cn_FD.exe",
        "orig_start": ROOT / "test" / "backup" / "fd_start.ps3.orig",
        "readme": "release_readme_fd.txt",
    },
}
ALIASES = {"hapymaher": "本体", "fragmentation-dream": "fd", "FD": "fd"}


def fresh_dir(d: Path) -> None:
    """目标目录已存在就先挪进 .trash（工作区约定：不直接永久删除）。"""
    if d.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        trash = ROOT / ".trash" / stamp / "发布包" / d.name
        trash.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(trash))
    d.mkdir(parents=True)


def build_one(key: str) -> int:
    g = GAMES[key]
    game: Path = g["game"]
    pkg = OUT / g["pkg"]

    # 1. 先确认游戏目录是完整构建过的，别把半成品打进包
    script = game / "data" / "pack" / "script"
    chip = game / "data" / "pack" / "chip"
    if not script.is_dir() or not chip.is_dir():
        print(f"  !! {game.name} 没有散装 script/chip 目录，先在游戏目录跑 rebuild.py")
        return 1
    n_script = len(list(script.glob("*.ps3")))
    n_chip = len([f for f in chip.iterdir() if f.is_file()])
    if n_chip < 100:
        print(f"  !! chip 只有 {n_chip} 个文件，像是只铺了改过的图 —— 会缺文件让游戏报错")
        return 1

    # 2. 重建目录
    fresh_dir(pkg)
    (pkg / "data" / "pack" / "script").mkdir(parents=True)
    (pkg / "data" / "pack" / "chip").mkdir(parents=True)

    # 3. 启动器与补丁
    shutil.copy2(HOOK / g["exe"], pkg / g["cn"])
    for f in ("cnpatch.dll", "cnpatch_ui.txt", "TW-Kai-98_1.ttf"):
        shutil.copy2(HOOK / f, pkg / f)

    # 4. 数据：start.ps3 + 全部脚本 + 全部界面图
    shutil.copy2(game / "data" / "pack" / "start.ps3", pkg / "data" / "pack" / "start.ps3")
    for f in script.glob("*.ps3"):
        shutil.copy2(f, pkg / "data" / "pack" / "script" / f.name)
    for f in chip.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / "data" / "pack" / "chip" / f.name)

    # 5. 卸载还原用的原版 start.ps3 + 读我
    #    原版文件是游戏资源，不进仓库；第一次出包前自备（见 build_full.py 里的说明）
    if not g["orig_start"].exists():
        print(f"  !! 缺少原版 {g['orig_start']}，无法生成「还原用/start.ps3」")
        print("     从正版游戏的 data\\pack\\start.ps3 复制一份到该路径后再跑")
        return 1
    restore = pkg / "还原用"
    restore.mkdir()
    shutil.copy2(g["orig_start"], restore / "start.ps3")
    shutil.copy2(HOOK / g["readme"], pkg / "读我.txt")

    size = sum(f.stat().st_size for f in pkg.rglob("*") if f.is_file())
    print(f"  {g['pkg']}: script {n_script}, chip {n_chip}, 共 {size / 1024 / 1024:.0f} MB")
    return 0


def main() -> int:
    targets = sys.argv[1:] or ["本体", "fd"]
    targets = [ALIASES.get(t, t) for t in targets]
    bad = 0
    for t in targets:
        if t not in GAMES:
            print(f"未知目标 {t!r}，可用：本体 / fd")
            return 2
        bad += build_one(t)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
