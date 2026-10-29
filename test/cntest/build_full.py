#!/usr/bin/env python3
"""全量中文补丁构建：output\\hapymaher\\translated → 加密 .ps3 → 游戏

与 build_encrypted.py 的区别只有数据源：那个读原始导出 + `build_test.TRANSLATIONS`
里的测试译文，未覆盖的一律写「（未译）」—— 只适合试跑几个脚本。全量注入后译文
已经躺在 `output\\hapymaher\\translated\\` 里（由 `tools/cmvs_galtransl.py inject`
写入），这里直接拿它构建。

清洗规则必须在出库时再做一遍（inject 只负责回填 tra）：
  · 去首尾全角空格 `　` —— GBK A1A1 会让引擎把文本框宽度算成 0（交接文档 §3.3）
  · `♪`（U+266A）GBK 没有码位，换哨兵 U+E4C6，游戏里由 cnpatch.dll 换回字形
  · `・`（U+30FB）GBK 也没有码位，换中点 `·`（U+00B7 / GBK A1A4）

其余步骤（start.ps3 路径表 + 标题、chip 界面图、initial.cfg 校验）照搬
build_encrypted.py，那边写得够细，不再重复。

用法：
    python test/cntest/build_full.py            # 构建全部
    python test/cntest/build_full.py sky01      # 只构建一个（调试用）
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # 项目根（test/cntest 往上两级）
TOOLS = ROOT / "tools" / "RxCMVS"
TEXTEDIT = TOOLS / "PS3_TextEditor.exe"
CRYPTOR = TOOLS / "PS3_Cryptor.exe"

SRC_JSON = ROOT / "output" / "hapymaher" / "translated"
SRC_PS3 = ROOT / "ハピメア脚本" / "code"
# 游戏安装目录：可用环境变量 HAPYMAHER_GAME 指定，默认放在项目根目录下
GAME = Path(os.environ.get("HAPYMAHER_GAME") or (ROOT / "ハピメア フルHD版"))
DST = GAME / "data" / "pack" / "script"
TMP = Path(__file__).parent / "tmp"

START_ORIG = ROOT / "test" / "backup" / "start.ps3.orig"

NOTE_SENTINEL = "\ue4c6"

TITLES: list[str] = [
    "ハピメア RE.ver",
    "ハピメアFD RE.ver",
]
for _t in TITLES:
    if len(_t.encode("cp932")) != len(_t.encode("gbk")):
        raise SystemExit(f"标题必须等长替换，{_t!r} 不满足")

PATH_PAIRS: list[tuple[bytes, bytes]] = [
    (b"data\\pack\\script.cpz", b"data\\pack\\script\\"),
    (b"data\\pack\\chip.cpz",   b"data\\pack\\chip\\"),
]

CHIP_SRC = ROOT / "3UI源文件" / "UI界面" / "chip"
CHIP_DST = GAME / "data" / "pack" / "chip"


def clean(t: str) -> str:
    """出库清洗：见文件头。"""
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
    # 原版 start.ps3 属于游戏文件，不随仓库分发（版权）。第一次构建前自备一份：
    #   从游戏安装包 / 镜像里取 data\pack\start.ps3，放到 test\backup\start.ps3.orig
    if not START_ORIG.exists():
        print(f"    !! 缺少原版 {START_ORIG}")
        print("       请从正版游戏的 data\\pack\\start.ps3 复制一份到上面这个路径")
        print("       （补丁只改路径表和标题，必须基于原版重建，不能拿改过的文件当输入）")
        return False
    if not run(CRYPTOR, "-mode", "decode", "-ps3", str(START_ORIG), "-save", str(plain)):
        return False
    d = bytearray(plain.read_bytes())

    # 没有界面图源时不要把 chip 路径改成散装目录 —— 那样引擎会去找
    # 不存在的 data\pack\chip\，一进游戏就弹「ファイルをオープンできませんでした」。
    # 保留 chip.cpz 读取，界面图维持日文原版，至少能玩。
    pairs = PATH_PAIRS
    if not CHIP_SRC.is_dir():
        pairs = [p for p in PATH_PAIRS if b"chip" not in p[0]]
        print("    没有界面图源：chip.cpz 保持原样（界面图为日文原版）")

    for old, new in pairs:
        if len(new) > len(old):
            raise SystemExit(f"路径 {new!r} 比 {old!r} 长，会撑坏字符串表")
        pad = b"\x00" * (len(old) - len(new))
        n, i = 0, d.find(old)
        while i >= 0:
            d[i:i + len(old)] = new + pad
            print(f"    路径表: 0x{i:X}  {old.decode()} -> {new.decode()}"
                  f"  (+{len(old)-len(new)} 字节填充)")
            n += 1
            i = d.find(old, i + len(old))
        if n == 0:
            print(f"    ⚠ 找不到 {old.decode()}，路径表可能已经改过")

    hit = 0
    for t in TITLES:
        old = t.encode("cp932")
        j = d.find(old)
        if j < 0:
            continue
        if d.find(old, j + 1) >= 0:
            print(f"    ⚠ 标题串 {t!r} 出现多次，为免误伤跳过，标题栏仍会乱码")
            continue
        d[j:j + len(old)] = t.encode("gbk")
        hit += 1
        print(f"    窗口标题: 0x{j:X}  SJIS {t!r} -> GBK 同串"
              f"（{len(old)} 字节等长，只修编码不译名）")
    if not hit:
        print("    ⚠ 没找到已知标题串，标题栏仍会乱码（要加的版本见 TITLES）")

    plain.write_bytes(bytes(d))
    return run(CRYPTOR, "-mode", "encode", "-ps3", str(plain),
               "-save", str(GAME / "data" / "pack" / "start.ps3"))


def install_chip() -> bool:
    if not CHIP_SRC.is_dir():
        print(f"    ⚠ 找不到 {CHIP_SRC}，跳过 —— 界面图保持日文原版（chip.cpz 未被改动，不影响运行）")
        print("       想要中文界面图：把 UI 素材包解压到 3UI源文件/UI界面/chip/ 后重跑")
        return False
    sys.path.insert(0, str(ROOT / "tools"))
    import pb3  # noqa: PLC0415

    CHIP_DST.mkdir(parents=True, exist_ok=True)
    new = kept = 0
    for f in sorted(CHIP_SRC.glob("*.pb3")):
        dst = CHIP_DST / f.name
        if dst.exists():
            kept += 1
            continue
        d = bytearray(f.read_bytes())
        pb3.encrypt_pb3(d)
        dst.write_bytes(d)
        new += 1
    for extra in CHIP_SRC.glob("*.ogg"):
        dst = CHIP_DST / extra.name
        if not dst.exists():
            shutil.copy2(extra, dst)
            new += 1
    print(f"    新铺 {new} 个，保留已有 {kept} 个 → {CHIP_DST}")
    return True


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only and not only.endswith(".ps3"):
        only += ".ps3"
    TMP.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)

    if not SRC_JSON.is_dir():
        print(f"错误：找不到 {SRC_JSON}，请先跑 tools/cmvs_galtransl.py inject",
              file=sys.stderr)
        return 1

    # 1. 脚本
    scripts = sorted(p.name[:-5] for p in SRC_JSON.glob("*.json"))
    if only:
        scripts = [s for s in scripts if s == only]
        if not scripts:
            print(f"错误：{SRC_JSON} 里没有 {only}.json", file=sys.stderr)
            return 1
    ok = fail = 0
    for i, s in enumerate(scripts, 1):
        if s == "intcode.ps3":
            continue          # 纯代码文件，没有文本，下面单独加密原样复制
        if build_encrypted(s, TMP):
            ok += 1
        else:
            fail += 1
            print(f"  [失败] {s}")
        if i % 50 == 0:
            print(f"  ... {i}/{len(scripts)}")

    # intcode.ps3 没有文本（Scenario 为空），重新 import 会产出坏文件 —— 直接把解密版重新加密
    if (SRC_PS3 / "intcode.ps3").exists():
        if run(CRYPTOR, "-mode", "encode", "-ps3", str(SRC_PS3 / "intcode.ps3"),
               "-save", str(DST / "intcode.ps3")):
            ok += 1
        else:
            fail += 1
            print("  [失败] intcode.ps3")

    print(f"\n[1/4] 加密脚本: 成功 {ok} 失败 {fail} → {DST}")
    print(f"      文件数 {len(list(DST.glob('*.ps3')))}")

    if only:
        print("\n只构建了一个，跳过后面的 start/chip/cfg 步骤")
        return 0 if fail == 0 else 1

    # 2. start.ps3
    print("\n[2/4] start.ps3:")
    if not patch_start_ps3(TMP):
        return 1
    print("      已写入", GAME / "data" / "pack" / "start.ps3")

    # 3. 界面图
    print("\n[3/4] 界面图 (chip):")
    install_chip()

    # 4. initial.cfg
    print("\n[4/4] initial.cfg:")
    cfg = GAME / "initial.cfg"
    if not cfg.exists():
        print("      ⚠ 找不到 initial.cfg")
        return 1
    text = cfg.read_text(encoding="cp932")
    if "FONT_SHIFT_JIS=1" in text:
        print("      FONT_SHIFT_JIS=1（装机值，保持不变）—— 正确")
    else:
        print("      ⚠ FONT_SHIFT_JIS 不是 1，请先跑 test/restore_game.py 还原")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
