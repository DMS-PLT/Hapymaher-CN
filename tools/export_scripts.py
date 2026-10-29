#!/usr/bin/env python3
"""Hapymaher 脚本批量导出 —— 把 .ps3 脚本里的文本导成 JSON（翻译流程的第一步）。

用法（详细说明见同目录的 README.md）：
    python tools/export_scripts.py                    # 导出全部，落 output\
    python tools/export_scripts.py --only hapymaher   # 只导本体，不导 FD
    python tools/export_scripts.py --out D:\\某个目录   # 换输出目录

它只是把 `tools/RxCMVS/PS3_TextEditor.exe` 的 export 模式循环跑一遍 ——
导出逻辑全在那个 exe 里，这里只负责批量、命名、汇总和自检。

JSON 文件名 = 原脚本名 + .json（logo.ps3 → logo.ps3.json），方便一一对回去。
**别手改这些 JSON**：下游 `tools/cmvs_galtransl.py` 按数组下标跟 .ps3
的槽位一一对应，删一条就全体错位。

产出之后：
    1) tools/cmvs_galtransl.py dump   —— 清洗 + 转成 GalTransl 的 gt_input
    2) GalTransl 翻译
    3) tools/cmvs_galtransl.py inject —— 把译文写回 tra
    4) test/cntest/build_encrypted.py          —— 构建成游戏能读的 .ps3
全流程见工作区根目录的《汉化实施交接文档.md》§7.1。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 项目根（不依赖开发机路径）
TOOL = ROOT / "tools" / "RxCMVS" / "PS3_TextEditor.exe"
CODE_PAGE = "932"  # Shift-JIS

# (源脚本目录, 输出子目录名)
TARGETS = {
    "hapymaher": ROOT / "ハピメア脚本" / "code",
    "fragmentation-dream": ROOT / "ハピメア Fragmentation Dream脚本" / "code",
}


def export_one(ps3: Path, out_json: Path) -> str | None:
    """导出单个脚本。成功返回 None，失败返回错误说明。"""
    proc = subprocess.run(
        [str(TOOL), "-mode", "export", "-ps3", str(ps3),
         "-json", str(out_json), "-code", CODE_PAGE],
        capture_output=True,
    )
    if proc.returncode != 0 or not out_json.exists():
        err = proc.stderr.decode("gbk", errors="replace").strip() or "未知错误"
        return err.splitlines()[0] if err else "未知错误"
    return None


def count_entries(out_dir: Path) -> tuple[int, int]:
    """返回 (条目总数, 读取失败的文件数)。"""
    total = 0
    bad = 0
    for jp in out_dir.rglob("*.json"):
        try:
            with jp.open(encoding="utf-8-sig") as fp:
                total += len(json.load(fp)["Scenario"])
        except Exception:
            bad += 1
    return total, bad


def main() -> int:
    ap = argparse.ArgumentParser(description="批量导出 CMVS .ps3 脚本文本")
    ap.add_argument("--out", type=Path, default=ROOT / "output", help="输出根目录")
    ap.add_argument("--only", choices=sorted(TARGETS), help="只导出其中一个游戏")
    args = ap.parse_args()

    if not TOOL.exists():
        print(f"[错误] 找不到工具：{TOOL}", file=sys.stderr)
        return 1

    targets = {args.only: TARGETS[args.only]} if args.only else TARGETS

    ok = 0
    failures: list[tuple[str, str]] = []
    for name, src_dir in targets.items():
        if not src_dir.is_dir():
            print(f"[跳过] 目录不存在：{src_dir}")
            continue
        dst_dir = args.out / name
        dst_dir.mkdir(parents=True, exist_ok=True)
        scripts = sorted(src_dir.glob("*.ps3"))
        print(f"\n=== {name}  ({len(scripts)} 个)  →  {dst_dir}")
        for i, ps3 in enumerate(scripts, 1):
            err = export_one(ps3, dst_dir / f"{ps3.name}.json")
            if err:
                failures.append((ps3.name, err))
                print(f"  [{i}/{len(scripts)}] 失败 {ps3.name} — {err}")
            else:
                ok += 1

    print(f"\n[导出完成] 成功 {ok} 个，失败 {len(failures)} 个")

    total, bad = count_entries(args.out)
    print(f"[自检] 输出目录共 {total:,} 条目，读取失败 {bad} 个文件")
    if bad:
        print("       ↑ 有 JSON 损坏，请检查磁盘或重新导出")

    return 1 if (failures or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
