#!/usr/bin/env python3
"""把游戏目录还原到装机原始状态。

校验依据不是记忆，而是游戏自带的 cmvsCheck.cfg —— 里面逐文件记录了装机时的 MD5。
凡是它列出的文件都能比对，比「我记得原版是什么样」可靠。

做四件事：
  1. initial.cfg 的 FONT_SHIFT_JIS 恢复成装机值 1
  2. data\\pack\\start.ps3 用 test\\backup\\start.ps3.orig 覆盖
  3. data\\pack\\script\\ （散装脚本实验残留）整体移走，不删除
  4. 游戏根目录里探头留下的 hooklog.txt 移走

用法：
    python test/restore_game.py          # 还原
    python test/restore_game.py --check  # 只看现状，不改动
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import Path

# 控制台默认是 cp936，直接 print 中文会花屏
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
BACKUP = ROOT / "test" / "backup"
RESIDUE = ROOT / "test" / "cntest" / "tmp" / "residue"

GAMES = {
    "hapymaher": ROOT / "ハピメア フルHD版",
    "fragmentation-dream": ROOT / "ハピメア Fragmentation Dream フルHD版",
}

# 装机默认值（FD 那份未被动过的 initial.cfg 可佐证）
FONT_SHIFT_JIS_DEFAULT = 1

# cmvsCheck.cfg 里挑几个便宜且能说明问题的来核对；
# 其余条目是几百 MB 的音频/视频，逐个体检不划算。
CHECK_KEYS = ["cmvs32.exe", r"data\pack\start.ps3", r"data\pack\script.cpz"]

# 注入 DLL 会写进游戏目录、需要在还原时清出去的日志
STRAY_LOGS = ["hooklog.txt", "cnpatch.log"]


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_install_hashes(game: Path) -> dict[str, str]:
    """从 cmvsCheck.cfg 读出装机 MD5 表（路径统一成小写反斜杠形式）。"""
    cfg = game / "cmvsCheck.cfg"
    if not cfg.exists():
        return {}
    text = cfg.read_bytes().decode("cp932", errors="replace")
    out: dict[str, str] = {}
    for m in re.finditer(r"^FILE\d+=([^:\r\n]+):([0-9a-fA-F]{32})", text, re.M):
        out[m.group(1).lower()] = m.group(2).lower()
    return out


def check(game: Path, label: str) -> list[str]:
    """核对现状，返回问题描述列表。"""
    problems: list[str] = []
    hashes = load_install_hashes(game)

    for key in CHECK_KEYS:
        cur = game / key
        if not cur.exists():
            if key.endswith("script.cpz"):
                problems.append(f"{key} 不存在")
            continue
        want = hashes.get(key.lower())
        got = md5(cur)
        if want and got != want:
            problems.append(f"{key} 与装机 MD5 不符 ({got[:8]}… 应为 {want[:8]}…)")

    cfg = game / "initial.cfg"
    if cfg.exists():
        m = re.search(rb"FONT_SHIFT_JIS=(\d)", cfg.read_bytes())
        if m and int(m.group(1)) != FONT_SHIFT_JIS_DEFAULT:
            problems.append(f"initial.cfg FONT_SHIFT_JIS={m.group(1).decode()}（应为 {FONT_SHIFT_JIS_DEFAULT}）")

    if (game / "data" / "pack" / "script").is_dir():
        n = len(list((game / "data" / "pack" / "script").glob("*")))
        problems.append(f"data\\pack\\script\\ 存在（{n} 个文件，散装脚本实验残留）")

    for name in STRAY_LOGS:
        if (game / name).exists():
            problems.append(f"游戏根目录有 {name}（注入 DLL 的日志）")

    print(f"[{label}] " + ("已还原" if not problems else f"{len(problems)} 处待处理"))
    for p in problems:
        print(f"    - {p}")
    return problems


def move_aside(src: Path, dst_dir: Path) -> Path:
    """移动到 dst_dir 下；重名时自动加序号，绝不覆盖也绝不删除。"""
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    n = 2
    while dst.exists():
        dst = dst_dir / f"{src.name}.{n}"
        n += 1
    shutil.move(str(src), str(dst))
    return dst


def restore(game: Path, label: str) -> None:
    # 1. initial.cfg
    cfg = game / "initial.cfg"
    if cfg.exists():
        b = cfg.read_bytes()
        new = re.sub(rb"FONT_SHIFT_JIS=\d",
                     f"FONT_SHIFT_JIS={FONT_SHIFT_JIS_DEFAULT}".encode(), b)
        if new != b:
            cfg.write_bytes(new)
            print(f"[{label}] initial.cfg: FONT_SHIFT_JIS → {FONT_SHIFT_JIS_DEFAULT}")

    # 2. start.ps3
    # 备份是三份游戏共用的名字，但本体和 FD 的 start.ps3 内容不同（标题串、图标名不一样）。
    # 所以必须先用该机自己的 cmvsCheck.cfg 核对备份的 MD5 —— 对不上就说明这份备份不是它的，绝不能覆盖。
    bak = BACKUP / "start.ps3.orig"
    cur = game / "data" / "pack" / "start.ps3"
    install_md5 = load_install_hashes(game).get(r"data\pack\start.ps3")
    if not bak.exists():
        print(f"[{label}] ⚠ 没有 start.ps3 备份，若与装机 MD5 不符请手动处理")
    elif install_md5 and md5(bak) != install_md5:
        print(f"[{label}] 跳过 start.ps3：备份 MD5 {md5(bak)[:8]}… 与该机装机值 {install_md5[:8]}… 不符")
        print(f"{' ' * (len(label) + 2)}  （这份备份属于别的游戏，覆盖会损坏此机文件）")
    elif not cur.exists() or md5(cur) != install_md5:
        shutil.copy2(bak, cur)
        print(f"[{label}] start.ps3 已用备份覆盖（{cur.stat().st_size} 字节，MD5 {install_md5[:8]}…）")

    # 3. 散装脚本目录
    sc = game / "data" / "pack" / "script"
    if sc.is_dir():
        dst = move_aside(sc, RESIDUE / label)
        print(f"[{label}] data\\pack\\script\\ → {dst.relative_to(ROOT)}")

    # 4. 注入 DLL 留下的日志
    for name in STRAY_LOGS:
        log = game / name
        if log.exists():
            dst = move_aside(log, ROOT / "test" / "hooklog" / "stray")
            print(f"[{label}] {name} → {dst.relative_to(ROOT)}")


def main() -> int:
    check_only = "--check" in sys.argv
    bad = 0
    for label, game in GAMES.items():
        if not game.is_dir():
            print(f"[{label}] 目录不存在，跳过")
            continue
        if check_only:
            bad += len(check(game, label))
        else:
            restore(game, label)
            print()
            bad += len(check(game, label))
        print()
    if check_only:
        print("（--check 模式，未做任何改动）")
    print("全部干净" if bad == 0 else f"仍有 {bad} 处不符，请看上面")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
