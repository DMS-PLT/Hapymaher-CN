#!/usr/bin/env python3
"""把游戏解包出来的 .ps3 脚本整理进 ハピメア脚本/code（export_scripts.py 的输入）。

用法：
    python tools/prepare_scripts.py <解包目录> [--game 本体|fd]

前置：先用 GARbro 把游戏里的 script.cpz 解开（GUI 手动，见 README）：
    GARbro → 打开 <游戏>\\data\\pack\\script.cpz → 全选 → 提取到 <解包目录>

⚠ 本作 script.cpz 解出来的 .ps3 大多是**明文**，不需要也不应该解密
  （对明文跑 PS3_Cryptor -mode decode：多数直接崩溃，少数「成功」但内容已毁）。
  本脚本对每个文件自动探测：

    1. 先试导出（PS3_TextEditor -mode export），能导出非空对白 = 明文 → 原样拷贝
    2. 导不出 = 密文/压缩态 → 先解密，解密后再导出验证；验证不过就不写出，
       按失败处理并给出提示（散装 start.ps3 这类压缩态文件走这条路）

判据是「导出的 JSON 里有非空对白」，不是工具的退出码——退出码骗过我们一次。
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRYPTOR = ROOT / "tools" / "RxCMVS" / "PS3_Cryptor.exe"
TEXTEDITOR = ROOT / "tools" / "RxCMVS" / "PS3_TextEditor.exe"

TARGETS = {
    "本体": ROOT / "ハピメア脚本" / "code",
    "fd": ROOT / "ハピメア Fragmentation Dream脚本" / "code",
}
ALIASES = {"hapymaher": "本体", "fragmentation-dream": "fd", "FD": "fd"}


def exports_dialogue(ps3: Path, tmpdir: Path) -> bool:
    """试导出，看 JSON 里有没有非空对白。导出成功且非空 = 明文。

    注意：RxCMVS 的工具对相对路径和正斜杠都挑剔，一律先 resolve 成
    绝对反斜杠路径再传。
    """
    ps3 = ps3.resolve()
    out = (tmpdir / f"{ps3.stem}.probe.json").resolve()
    try:
        out.unlink(missing_ok=True)
    except OSError:
        pass
    subprocess.run(
        [str(TEXTEDITOR), "-mode", "export", "-ps3", str(ps3),
         "-json", str(out), "-code", "932"],
        capture_output=True,
    )
    if not out.is_file():
        return False
    try:
        data = json.loads(out.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    return any(isinstance(v, list) and v for v in data.values())


def process_one(ps3: Path, dst: Path, tmpdir: Path) -> str:
    """处理单个文件，返回 'copy' / 'decrypt' / 'fail'。"""
    if exports_dialogue(ps3, tmpdir):
        shutil.copy2(ps3, dst / ps3.name)
        return "copy"

    decoded = (tmpdir / f"{ps3.stem}.dec.ps3").resolve()
    r = subprocess.run(
        [str(CRYPTOR), "-mode", "decode", "-ps3", str(ps3.resolve()),
         "-save", str(decoded)],
        capture_output=True,
    )
    if r.returncode != 0:
        return "fail"
    if not exports_dialogue(decoded, tmpdir):
        print(f"  [警告] {ps3.name} 解密工具报成功但导不出对白，"
              f"按失败处理（不写出可疑产物）")
        return "fail"
    shutil.copy2(decoded, dst / ps3.name)
    return "decrypt"


def main() -> int:
    ap = argparse.ArgumentParser(description="整理解包的 .ps3 脚本（自动识别明文/密文）")
    ap.add_argument("src", help="GARbro 解包得到的 .ps3 目录")
    ap.add_argument("--game", default="本体", help="本体 / fd（决定输出到哪个目录）")
    a = ap.parse_args()

    key = ALIASES.get(a.game, a.game)
    if key not in TARGETS:
        print(f"未知目标 {a.game!r}，可用：本体 / fd")
        return 2
    if not TEXTEDITOR.exists():
        print(f"缺少 {TEXTEDITOR}")
        return 1
    src = Path(a.src)
    if not src.is_dir():
        print(f"找不到输入目录 {src}")
        return 1

    files = sorted(src.glob("*.ps3"))
    if not files:
        print(f"{src} 里没有 .ps3 文件")
        return 1

    dst = TARGETS[key]
    dst.mkdir(parents=True, exist_ok=True)

    n_copy = n_dec = n_fail = 0
    failed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="prep_ps3_") as td:
        tmpdir = Path(td)
        for i, f in enumerate(files, 1):
            result = process_one(f, dst, tmpdir)
            if result == "copy":
                n_copy += 1
            elif result == "decrypt":
                n_dec += 1
            else:
                n_fail += 1
                failed.append(f.name)
            if i % 40 == 0:
                print(f"  ... {i}/{len(files)}")

    print(f"\n完成：明文直拷 {n_copy} / 解密 {n_dec} / 失败 {n_fail} → {dst}")
    if failed:
        print("失败清单：")
        for name in failed:
            print(f"  {name}")
        print("提示：解包目录里混入了非脚本的 .ps3（如 start.ps3 的部件），"
              "或文件本身已损坏；确认后可忽略。")
    print("下一步：python tools/export_scripts.py")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
