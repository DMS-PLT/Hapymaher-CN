#!/usr/bin/env python3
"""中文补丁测试构建：JSON → GBK 编码的 .ps3 → 游戏 data\\pack\\script\\

流程：读 output\\hapymaher\\*.json → 替换 GBK 装不下的符号 → （可选填入测试译文）
      → PS3_TextEditor import -code 936 → 输出到游戏散装脚本目录

用法：
    python build_test.py sir0200        # 只做 sir0200.ps3
    python build_test.py                # 全部 158 个
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
TOOL = ROOT / "tools" / "RxCMVS" / "PS3_TextEditor.exe"
SRC_JSON = ROOT / "output" / "hapymaher"          # 导出的原文 JSON
SRC_PS3 = ROOT / "ハピメア脚本" / "code"           # 原始明文脚本
DST = ROOT / "ハピメア フルHD版" / "data" / "pack" / "script"   # 游戏散装脚本目录

# ♪ 的哨兵字符。
#
# ♪（U+266A）在 GBK 里没有码位，而且不是「变成问号」——PS3_TextEditor 会直接
# 报 RxCvt::ToMBCS Error! 让整个脚本构建失败。所以译文里用 U+E4C6 占位，
# CP936 把它编成字节对 0xA1 0x40（GBK 用户区，任何输入法都产不出）。
# 游戏里由 cnpatch.dll hook GetGlyphOutlineA 换成真的 ♪ 字形。
#
# 注意：Python 的 gbk 编解码器不认 U+E4C6，但真正做编码的是 PS3_TextEditor
# （走系统 CP936），它能编。别在这里试着 .encode("gbk") 验证，会误判。
NOTE_SENTINEL = ""

# GBK 装不下 / 需要换成等义符号的字符
SUB = str.maketrans({"♪": NOTE_SENTINEL, "・": "·"})


def clean(t: str) -> str:
    """译文出库前的清洗。

    一定要去掉开头的全角空格 　（U+3000）。日文原文每段都以它开头做缩进，
    但 GBK 里 　 是 A1A1，引擎的「可变文本框」在算宽度时碰到它会算出接近 0 的
    结果，于是框退化成一个小方块、正文全部溢出框外。
    AI 汉化补丁的译文里一个 　 都没有 —— 这正是它能正常显示的原因。

    ♪ 在这里统一换成哨兵：必须全量替换（包括那些行首禁则字符集配置串里的 ♪），
    否则同样的字符在台词里和配置串里变成两种东西，折行判定会不一致。
    """
    return t.strip("　 \t\r\n").replace("♪", NOTE_SENTINEL)

# 测试译文（脚本名 → {条目序号: 中文}）；其余条目保持原文
TRANSLATIONS: dict[str, dict[int, str]] = {
    # 序章，开局立刻可见
    "sky01.ps3": {
        4:  "- 序章 -",
        5:  "　那是一个奢华的房间。",
        6:  "　正中央摆着一张宽大结实的大桌子。",
        7:  "　桌上摆着冒着热气的水壶和五颜六色的点心。",
        8:  "　为来客准备的松软沙发，铺在地上的手工编织地毯，全都是为了造访此地的客人。",
        9:  "　在这里，茶会的准备随时都万无一失。",
        # ↓ 单变量对照：第 10 条和第 11 条文字完全相同，只差开头一个全角空格。
        #   原文日文是以 　 开头的，但 SJIS 的 　 是 0x8140，GBK 的是 0xA1A1。
        #   哪一条框正常，就说明 　 是不是元凶。
        10: "　那个仿佛只存在于童话中的房间，看上去简直像是一个恶作剧。",
        11: "　那是它的配色。黑、白、红、紫、粉、蓝。映入眼帘的尽是鲜艳的色彩。房间被点缀得宛如蝴蝶般斑斓。",
        # 12: 开头故意又加一个全角空格（源里本来就有），验证 clean() 确实去掉了
        12: "　　双重全角空格开头，应当被清洗掉两个。",
        # 13: GBK 里尾字节恰好是 0x5C 的汉字。文本标记扫描补丁失效的话会凭空断行
        13: "尾字节 5C 测试：運淺誠賊錦黒乗衆籠襖。若这一行换行错乱，说明补丁没生效。",
        # 14: 符号。♪ 现在保留 —— 构建时换成哨兵，游戏里由 cnpatch.dll 还原成真 ♪。
        #     ・ 换成 ·（GBK 里 ・ 有码位，纯粹是排版习惯）
        14: "符号测试：波浪线～、间隔号·、省略号…、破折号——、引号“”‘’、音符♪。",
        # 15: 长句，看折行与是否超出
        15: "折行测试：这一行特意写得长一些，用来观察中文字符在文本框里的换行位置，以及是否会超出右侧边界。",
        # 16: ♪ 的位置测试 —— 句尾、句中、连续多个，另外夹一个全角空格看会不会互相干扰
        #     （全角空格会被 clean() 去掉，这里故意放在中间，看它是否只去首尾）
        16: "♪ 句首的♪、句中♪的音符、连续♪♪♪三个，还有「带引号的♪」和收尾♪",
    },
    "sir0200.ps3": {
        4:  "- 幕间 1 -",
        5:  "「——那种答案，就算听了也没有意义吧」",
        6:  "透",
        7:  "　我推开那扇梦之门，踏进了舞亚所在的这个房间。",
        8:  "　舞亚依旧咯咯地笑着，可在这昏暗的房间里，那笑声让我有些发毛。",
        9:  "　于是我打了个响指，把灯打开。",
        10: "　随着一声“啪”响，房间里一下子亮了起来。",
        11: "「晚上好，今晚也是个好夜晚呢」",
        12: "舞亚",
        13: "　我明明是突然来的，舞亚却一点也不惊讶。",
        14: "「这算什么好夜晚」",
        15: "透",
        16: "「哎呀，你为什么会这么说呢？」",
        17: "舞亚",
        18: "　舞亚依旧咯咯笑着，歪了歪头。",
        19: "「舞亚突然冒出来，又被有栖搭救，还落得去偷窥咲的梦境这种地步」",
        20: "透",
        21: "「要是厚脸皮到能把这种事说成有趣，我活得也能轻松些吧」",
        22: "透",
        23: "「原来如此原来如此，哥哥确实没法享受这个梦呢，呵呵」",
        24: "舞亚",
        25: "「那么不够厚脸皮的哥哥，究竟有何贵干呢？难道是来看我的？」",
    },
}


def build_one(name: str) -> tuple[bool, str]:
    ps3 = SRC_PS3 / name
    js = SRC_JSON / f"{name}.json"
    if not ps3.exists() or not js.exists():
        return False, "源文件不存在"

    scenario = json.loads(js.read_text(encoding="utf-8-sig"))["Scenario"]
    override = TRANSLATIONS.get(name, {})
    n_tr = 0
    for i, ent in enumerate(scenario):
        if i in override:
            ent["tra"] = override[i]
            n_tr += 1
        else:
            ent["tra"] = ent["raw"].translate(SUB)

    DST.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp_json = Path(td) / "t.json"
        tmp_json.write_text(
            json.dumps({"Scenario": scenario}, ensure_ascii=False, indent=1),
            encoding="utf-8-sig",
        )
        proc = subprocess.run(
            [str(TOOL), "-mode", "import", "-ps3", str(ps3),
             "-json", str(tmp_json), "-save", str(DST / name), "-code", "936"],
            capture_output=True,
        )
    if proc.returncode != 0 or not (DST / name).exists():
        return False, proc.stderr.decode("gbk", errors="replace").strip() or "导入失败"
    return True, f"{len(scenario)} 条（译 {n_tr} 条）"


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    # names 里存的是脚本文件名，如 "sir0200.ps3"
    names = ([only if only.endswith(".ps3") else f"{only}.ps3"] if only
             else sorted(p.name[:-5] for p in SRC_JSON.glob("*.json")))
    ok = fail = 0
    for i, js in enumerate(names, 1):
        good, msg = build_one(js)
        if good:
            ok += 1
            if only:
                print(f"  [OK] {js}  {msg}")
        else:
            fail += 1
            print(f"  [失败] {js} — {msg}")
        if not only and i % 40 == 0:
            print(f"  ... {i}/{len(names)}")
    print(f"\n完成：成功 {ok} 个，失败 {fail} 个 → {DST}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
