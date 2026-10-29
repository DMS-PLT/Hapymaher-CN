#!/usr/bin/env python3
"""把改过的 `gt_output/` 灌回游戏：校验 → 同步到项目 → inject（可选构建）。

只改 `message` / `name` 字段就行，但**条数和顺序不能动** —— inject 是按位置
对应的（gt_output 第 n 条 → manifest 第 n 个槽位），少一条就整份跳过。
这个脚本先检查这一点，再复制、注入，省得跑到一半才发现对不上。

检查项：
  · UTF-8 **无 BOM**（inject 用 encoding="utf-8" 读，带 BOM 会直接报错）
  · 每个文件的条数 == manifest 里该文件的 units 数
  · 有没有空 message
  · 有没有 GBK 编不了的字符（`♪` `・` 除外，构建时会换成哨兵/中点）

用法：
    python test/cntest/apply_gt_output.py            # 校验 + 注入
    python test/cntest/apply_gt_output.py --build    # 校验 + 注入 + 全量构建
    python test/cntest/apply_gt_output.py --check    # 只校验，不动任何文件
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
SRC = ROOT / "gt_output"                                  # 用户改的
PROJECT = ROOT / "galtransl" / "proj-hapymaher"
DST = PROJECT / "gt_output"
MANIFEST = PROJECT / "manifest.json"
INJECT = ROOT / "tools" / "cmvs_galtransl.py"
BUILD = ROOT / "test" / "cntest" / "build_full.py"

# 构建阶段会替换掉，校验时放行
ALLOWED_NON_GBK = {"♪", "・"}


def check() -> list[str]:
    problems: list[str] = []
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # 只检查有 units 的文件：start.ps3 / intcode.ps3 没有文本，inject 会原样写出
    units = {f: len(v["units"]) for f, v in manifest["files"].items() if v["units"]}

    files = sorted(SRC.glob("*.json"))
    if not files:
        return [f"找不到任何 JSON：{SRC}"]

    missing = [f for f in units if not (SRC / f).exists()]
    if missing:
        problems.append(f"gt_output 缺文件：{missing[:5]}{' …' if len(missing) > 5 else ''}")

    total = 0
    for p in files:
        raw = p.read_bytes()
        if raw[:3] == b"\xef\xbb\xbf":
            problems.append(f"{p.name}: 带 BOM，inject 读不了（请存成 UTF-8 无 BOM）")
            continue
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            problems.append(f"{p.name}: JSON 解析失败 —— {e}")
            continue

        n = units.get(p.name)
        if n is None:
            problems.append(f"{p.name}: manifest 里没有这个文件")
            continue
        if len(data) != n:
            problems.append(f"{p.name}: 条数 {len(data)} ≠ manifest {n}（增删条目会整份跳过）")
        total += len(data)

        for i, e in enumerate(data):
            msg = e.get("message")
            if not isinstance(msg, str) or not msg.strip():
                problems.append(f"{p.name}[{i}]: message 为空")
                break
            bad = {c for c in msg if c not in ALLOWED_NON_GBK and _bad_gbk(c)}
            if bad:
                problems.append(f"{p.name}[{i}]: GBK 编不了 {sorted(bad)!r} —— {msg[:30]!r}")
                break

    print(f"检查 {len(files)} 个文件，共 {total} 条")
    return problems


def _bad_gbk(ch: str) -> bool:
    try:
        ch.encode("gbk")
        return False
    except UnicodeEncodeError:
        return True


def main() -> int:
    build = "--build" in sys.argv
    only_check = "--check" in sys.argv

    problems = check()
    if problems:
        print("\n发现以下问题，先修好再注入：")
        for p in problems:
            print("  ✗", p)
        return 1
    print("校验通过。")
    if only_check:
        return 0

    DST.mkdir(parents=True, exist_ok=True)
    for p in sorted(SRC.glob("*.json")):
        shutil.copy2(p, DST / p.name)
    print(f"已同步到 {DST}")

    print("\n=== inject ===")
    r = subprocess.run([sys.executable, str(INJECT), "inject",
                        "--game", "hapymaher", "--project", str(PROJECT)])
    if r.returncode != 0:
        print("inject 失败，未构建")
        return r.returncode

    if build:
        print("\n=== build ===")
        r = subprocess.run([sys.executable, str(BUILD)])
        if r.returncode != 0:
            return r.returncode

    print("\n完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
