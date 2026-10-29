#!/usr/bin/env python3
"""构建中文补丁：JSON(GBK译文) → 明文 .ps3 → PS3_Cryptor 加密 → 游戏 data\\pack\\script\\

顺带做三件配套的事：
  · 把 start.ps3 的路径表从 data\\pack\\script.cpz 改指到散装目录 script\\
  · 把 start.ps3 的路径表从 data\\pack\\chip.cpz   改指到散装目录 chip\\
    （界面图改图后要能塞回去就得走这条；GARbro 解出来的 pb3 得先转 Form A，
      只补缺失文件，不会覆盖手改过的 —— 细节见 tools/pb3.py）
  · 把 start.ps3 里的窗口标题改成等长 GBK（修标题乱码）

initial.cfg **不动**，最后只做校验：FONT_SHIFT_JIS 必须还是装机值 1。
（早先以为改成 0 能走 ANSI 路径显示中文，实测是错的 —— charset=0 会让 GDI 回退到
Courier New，满屏问号；而且那个开关关联 11 处字体/排版逻辑。字符集交给 cnpatch.dll
在 CreateFontA 层强制 134。）

用法：python build_encrypted.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_test import TRANSLATIONS, clean  # 复用测试译文与清洗规则

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
TOOLS = ROOT / "tools" / "RxCMVS"
TEXTEDIT = TOOLS / "PS3_TextEditor.exe"
CRYPTOR = TOOLS / "PS3_Cryptor.exe"

SRC_JSON = ROOT / "output" / "hapymaher"
SRC_PS3 = ROOT / "ハピメア脚本" / "code"
GAME = ROOT / "ハピメア フルHD版"
DST = GAME / "data" / "pack" / "script"
TMP = Path(__file__).parent / "tmp"

START_ORIG = ROOT / "test" / "backup" / "start.ps3.orig"

# ── 窗口标题 ──
#
# start.ps3 里有一张 NUL 分隔的字符串表（图标路径、标题、ico 名、脚本名…），
# 标题那一条存的是 SJIS 的「ハピメア RE.ver」。游戏把它交给 SetWindowTextA，
# Windows 按系统码页(GBK)去解释这些字节 → 标题栏乱码。
# （同一句标题里还拼着脚本里的章节名，那是我们译的 GBK，所以「- 序章 -」看着是对的。）
#
# 改写成 GBK 假名即可正常显示，**一个字都不用译**：假名在 GB2312 里也有码位。
# 必须**等长**替换 —— 那是连续字符串表，长度一变后面所有条目的偏移都会挪位。
# 好在 SJIS 与 GBK 的假名都是 2 字节/字，所以同一串换个编码必然等长。
#
# 加新版本（FD 等）时往这里补一条即可，找不到就跳过。
TITLES: list[str] = [
    "ハピメア RE.ver",      # 本体（start.ps3 @ 0x14F9，15 字节）
    "ハピメアFD RE.ver",    # FD（start.ps3 @ 0x15DA，17 字节）
]
for _t in TITLES:
    if len(_t.encode("cp932")) != len(_t.encode("gbk")):
        raise SystemExit(f"标题必须等长替换，{_t!r} 不满足")

# ── 路径表里改成「目录形式」的封包 ──
#
# 改成目录后引擎就从散装文件读，不用重打包 cpz。两条都验证过可行。
# ⚠ chip.cpz 这条在表里**出现两次**（0x13E1 和 0x1408），两处都得改。
PATH_PAIRS: list[tuple[bytes, bytes]] = [
    (b"data\\pack\\script.cpz", b"data\\pack\\script\\"),
    (b"data\\pack\\chip.cpz",   b"data\\pack\\chip\\"),
]

# 界面图源目录（GARbro 从 chip.cpz 解出来的 pb3）与安装目标
CHIP_SRC = ROOT / "UI界面" / "chip"
CHIP_DST = GAME / "data" / "pack" / "chip"


def run(exe: Path, *args: str) -> bool:
    p = subprocess.run([str(exe), *args], capture_output=True)
    if p.returncode != 0:
        print("   ", p.stderr.decode("gbk", errors="replace").strip())
        return False
    return True


def build_encrypted(script: str, tmp: Path) -> bool:
    """JSON → 明文(936) → 加密 → 游戏目录"""
    js = SRC_JSON / f"{script}.json"
    if not js.exists():
        return False
    scenario = json.loads(js.read_text(encoding="utf-8-sig"))["Scenario"]
    override = TRANSLATIONS.get(script, {})
    for i, ent in enumerate(scenario):
        if i in override:
            ent["tra"] = clean(override[i])
        elif ent["raw"].isascii():
            # 纯 ASCII 的多半是标签、命令、文件名之类，不该动它，原样保留
            ent["tra"] = ent["raw"]
        else:
            # 其余未翻译的，不能沿用原文：日文假名编不进 GBK，工具会写成 '?'，
            # 满屏问号会让人分不清是编码问题还是渲染问题。换成明确的占位符。
            ent["tra"] = "（未译）"

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
    """start.ps3: 解密 → 改 script.cpz 路径 + 修窗口标题乱码 → 重新加密"""
    plain = tmp / "start.plain"
    if not run(CRYPTOR, "-mode", "decode", "-ps3", str(START_ORIG), "-save", str(plain)):
        return False
    d = bytearray(plain.read_bytes())

    # 路径表：把封包改成目录形式（等长替换，用 NUL 填充，见 PATH_PAIRS 说明）
    for old, new in PATH_PAIRS:
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

    # 窗口标题：SJIS -> GBK，等长（见文件头的说明）
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
    """铺界面图：UI界面/chip 的 pb3 → 转成 Form A → 游戏 data\\pack\\chip\\

    只补**缺的**文件，已存在的一律不碰 —— 免得把 PS 改过、再经 pb3.py encode
    出来的图覆盖掉。

    ⚠ 必须转 Form A：引擎读任何 pb3 都会先剥一层头部混淆，喂 GARbro 那个
    明文头成品进去会把宽高搅烂，建纹理时整数除零直接闪退。细节见 tools/pb3.py。
    """
    if not CHIP_SRC.is_dir():
        print(f"    ⚠ 找不到 {CHIP_SRC}，跳过（界面图会缺失，游戏可能崩）")
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
        pb3.encrypt_pb3(d)                       # Form B -> Form A
        dst.write_bytes(d)
        new += 1
    for extra in CHIP_SRC.glob("*.ogg"):         # chip.cpz 里还夹着音频
        dst = CHIP_DST / extra.name
        if not dst.exists():
            shutil.copy2(extra, dst)
            new += 1
    print(f"    新铺 {new} 个，保留已有 {kept} 个 → {CHIP_DST}")
    return True


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    DST.mkdir(parents=True, exist_ok=True)

    # 1. 脚本
    scripts = sorted(p.name[:-5] for p in SRC_JSON.glob("*.json"))
    ok = fail = 0
    for i, s in enumerate(scripts, 1):
        if build_encrypted(s, TMP):
            ok += 1
        else:
            fail += 1
            print(f"  [失败] {s}")
        if i % 50 == 0:
            print(f"  ... {i}/{len(scripts)}")
    # intcode.ps3 没有文本，直接加密原文件
    if run(CRYPTOR, "-mode", "encode", "-ps3", str(SRC_PS3 / "intcode.ps3"),
           "-save", str(DST / "intcode.ps3")):
        ok += 1
    print(f"\n[1/4] 加密脚本: 成功 {ok} 失败 {fail} → {DST}")
    print(f"      文件数 {len(list(DST.glob('*.ps3')))}")

    # 2. start.ps3
    print("\n[2/4] start.ps3:")
    if not patch_start_ps3(TMP):
        return 1
    print("      已写入", GAME / "data" / "pack" / "start.ps3")

    # 3. 界面图
    print("\n[3/4] 界面图 (chip):")
    install_chip()

    # 4. initial.cfg —— 保持装机值 1，不要动
    #
    # 早先以为改成 0 能让引擎走 ANSI 路径显示中文，实测是错的：charset=0 会让
    # GDI 回退到 Courier New（无汉字），显示一堆问号。而且这个开关还关联 11 处
    # 字体/排版逻辑，改了要连累缩进、数字排版等。
    # 正确做法是保持 1，字符集完全交给 cnpatch.dll 在 CreateFontA 层强制 134。
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
