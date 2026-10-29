#!/usr/bin/env python3
"""FD（Fragmentation Dream）全量中文补丁构建。

和 build_full.py（本体）同一条链路，差别只在目录和 start.ps3 的现状：

  · FD 的 data\\pack\\start.ps3 之前被改过：chip.cpz 已经是 chip\\ 目录形式，
    但 script.cpz 还是封包、窗口标题还是 SJIS。这里**在当前文件上补这两处**
    （都是等长替换，可重复执行；已经改过的会跳过）。
  · FD 的 data\\pack\\script\\ 目录原本不存在，构建时创建。
  · FD 没有单独的界面图补丁，chip 目录保持原样，不碰。

用法：
    python test/cntest/build_fd.py            # 构建全部
    python test/cntest/build_fd.py sr0503     # 只构建一个（调试用）
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 项目根（test/cntest 往上两级）
TOOLS = ROOT / "tools" / "RxCMVS"
TEXTEDIT = TOOLS / "PS3_TextEditor.exe"
CRYPTOR = TOOLS / "PS3_Cryptor.exe"

SRC_JSON = ROOT / "output" / "fragmentation-dream" / "translated"
SRC_PS3 = ROOT / "ハピメア Fragmentation Dream脚本" / "code"
# 游戏安装目录：可用环境变量 HAPYMAHER_FD_GAME 指定，默认放在项目根目录下
GAME = Path(os.environ.get("HAPYMAHER_FD_GAME") or (ROOT / "ハピメア Fragmentation Dream フルHD版"))
DST = GAME / "data" / "pack" / "script"
START = GAME / "data" / "pack" / "start.ps3"
TMP = Path(__file__).parent / "tmp_fd"

NOTE_SENTINEL = "\ue4c6"

# FD 的标题（start.ps3 @0x15DA，17 字节）
TITLES = ["ハピメアFD RE.ver"]
for _t in TITLES:
    if len(_t.encode("cp932")) != len(_t.encode("gbk")):
        raise SystemExit(f"标题必须等长替换，{_t!r} 不满足")

BS = chr(92).encode()
PATH_PAIRS = [
    (b"data" + BS + b"pack" + BS + b"script.cpz", b"data" + BS + b"pack" + BS + b"script" + BS),
    (b"data" + BS + b"pack" + BS + b"chip.cpz",   b"data" + BS + b"pack" + BS + b"chip" + BS),
]


def clean(t: str) -> str:
    return (t.strip("　 \t\r\n")
             .replace("♪", NOTE_SENTINEL)
             .replace("・", "·"))


def run(exe: Path, *args: str) -> bool:
    p = subprocess.run([str(exe), *args], capture_output=True)
    if p.returncode != 0:
        print("   ", p.stderr.decode("gbk", errors="replace").strip())
        return False
    return True


def build_encrypted(script: str, tmp: Path) -> bool:
    js = SRC_JSON / f"{script}.json"
    if not js.exists():
        return False
    scenario = json.loads(js.read_text(encoding="utf-8-sig"))["Scenario"]
    for ent in scenario:
        ent["tra"] = clean(ent.get("tra") or ent.get("raw") or "")

    tmp_json = tmp / f"{script}.json"
    tmp_json.write_text(json.dumps({"Scenario": scenario}, ensure_ascii=False),
                        encoding="utf-8-sig")

    plain = tmp / f"{script}.plain"
    if not run(TEXTEDIT, "-mode", "import", "-ps3", str(SRC_PS3 / script),
               "-json", str(tmp_json), "-save", str(plain), "-code", "936"):
        return False
    return run(CRYPTOR, "-mode", "encode", "-ps3", str(plain),
               "-save", str(DST / script))


def patch_start_ps3(tmp: Path) -> bool:
    plain = tmp / "start.plain"
    if not run(CRYPTOR, "-mode", "decode", "-ps3", str(START), "-save", str(plain)):
        return False
    d = bytearray(plain.read_bytes())

    # 和 build_full 一样：没有 data\pack\chip 目录时不要把路径改成散装形式，
    # 否则引擎找不到文件会一路弹「ファイルをオープンできませんでした」。
    pairs = PATH_PAIRS
    if not (GAME / "data" / "pack" / "chip").is_dir():
        pairs = [p for p in PATH_PAIRS if b"chip" not in p[0]]
        print("    没有 data/pack/chip 目录：chip.cpz 保持原样（界面图为日文原版）")

    for old, new in pairs:
        if len(new) > len(old):
            raise SystemExit(f"路径 {new!r} 比 {old!r} 长，会撑坏字符串表")
        pad = b"\x00" * (len(old) - len(new))
        n, i = 0, d.find(old)
        while i >= 0:
            d[i:i + len(old)] = new + pad
            print(f"    路径表: 0x{i:X}  {old.decode()} -> {new.decode()}")
            n += 1
            i = d.find(old, i + len(old))
        if n == 0:
            print(f"    路径表: {old.decode()} 已是目录形式，跳过")

    hit = 0
    for t in TITLES:
        old = t.encode("cp932")
        j = d.find(old)
        if j < 0:
            continue
        if d.find(old, j + 1) >= 0:
            print(f"    ⚠ 标题串 {t!r} 出现多次，跳过")
            continue
        d[j:j + len(old)] = t.encode("gbk")
        hit += 1
        print(f"    窗口标题: 0x{j:X}  SJIS -> GBK（{len(old)} 字节等长）")
    if not hit:
        print("    窗口标题: 没找到 SJIS 原文（可能已改过）")

    plain.write_bytes(bytes(d))
    return run(CRYPTOR, "-mode", "encode", "-ps3", str(plain), "-save", str(START))


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only and not only.endswith(".ps3"):
        only += ".ps3"
    TMP.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)

    if not SRC_JSON.is_dir():
        print(f"错误：找不到 {SRC_JSON}，请先跑 inject", file=sys.stderr)
        return 1

    scripts = sorted(p.name[:-5] for p in SRC_JSON.glob("*.json"))
    if only:
        scripts = [s for s in scripts if s == only]
        if not scripts:
            print(f"错误：{SRC_JSON} 里没有 {only}.json", file=sys.stderr)
            return 1

    ok = fail = 0
    for i, s in enumerate(scripts, 1):
        if s == "intcode.ps3":
            continue          # 没有文本，下面单独原样加密（与 build_full.py 一致）
        if build_encrypted(s, TMP):
            ok += 1
        else:
            fail += 1
            print(f"  [失败] {s}")
        if i % 40 == 0:
            print(f"  ... {i}/{len(scripts)}")
    # intcode.ps3 没有文本，直接加密原文件
    if run(CRYPTOR, "-mode", "encode", "-ps3", str(SRC_PS3 / "intcode.ps3"),
           "-save", str(DST / "intcode.ps3")):
        ok += 1
    print(f"\n[1/3] 加密脚本: 成功 {ok} 失败 {fail} → {DST}")
    print(f"      文件数 {len(list(DST.glob('*.ps3')))}")

    if only:
        print("只构建了一个，跳过 start.ps3 / cfg 步骤")
        return 0 if fail == 0 else 1

    print("\n[2/3] start.ps3:")
    if not patch_start_ps3(TMP):
        return 1
    print("      已写入", START)

    print("\n[3/3] initial.cfg:")
    cfg = GAME / "initial.cfg"
    if not cfg.exists():
        print("      ⚠ 找不到 initial.cfg")
        return 1
    text = cfg.read_text(encoding="cp932")
    if "FONT_SHIFT_JIS=1" in text:
        print("      FONT_SHIFT_JIS=1（装机值，保持不变）—— 正确")
    else:
        print("      ⚠ FONT_SHIFT_JIS 不是 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
