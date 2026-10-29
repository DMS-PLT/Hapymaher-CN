#!/usr/bin/env python3
"""生成 / 更新译文表里的菜单段。

为什么要生成：菜单原文里有大量**半角片假名**（`ﾃﾞｰﾀ復元(&F)`、`ﾏｳｽｶｰｿﾙ…`），
手打十有八九打错，而译文表是按「原文完全相等」匹配的，错了就是静默失效。
所以键一律从 exe 里现取，人只提供译文 —— 按**解析顺序的下标**索引。

用法：
    uv run --with pefile python gen_ui_table.py --show      # 只列出来看看
    uv run --with pefile python gen_ui_table.py --write     # 写进 cnpatch_ui.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).parent))
from parse_menu import parse  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
EXE = ROOT / "ハピメア フルHD版" / "cmvs32.exe"
TABLE = ROOT / "test" / "hooklog" / "cnpatch_ui.txt"

BEGIN = "# ── 游戏内菜单（MENU 130）—— 下面这段由 gen_ui_table.py 生成，别手改 ──"
END = "# ── 菜单段结束 ──"

# 按解析下标给译文。槽位名（LOAD_001 / SAVE_001 那些）不译 ——
# 游戏会在运行时用 SetMenuItemInfoA 把它们换成真实存档信息，译了也是白译。
MENU_ZH: dict[int, str] = {
    0:   "基本项目",
    1:   "读取(&L)",
    12:  "存档(&S)",
    23:  "数据复原(&F)",
    24:  "上次存档无效(&R)",
    25:  "恢复读档前的状态(&L)",
    26:  "导入(&G)",
    27:  "剪贴板(&C)",
    28:  "保存到文件(&F)",
    29:  "系统相关(&X)",
    30:  "画面设置(&G)",
    31:  "窗口模式(640*480)",
    32:  "全屏模式(640*480)",
    33:  "不改变分辨率(&N)",
    34:  "对话框(&D)",
    35:  "读取确认(&L)",
    36:  "存档确认(&S)",
    37:  "同步时机(&T)",
    38:  "时间同步(&S)",
    39:  "帧同步(&G)",
    40:  "包文件检查(&P)",
    41:  "检查头部一致性(&H)",
    42:  "每次读取时检查数据段(&D)",
    43:  "画面特效(&E)",
    44:  "非活动时的行为(&A)",
    45:  "声音相关(&O)",
    46:  "播放(&P)",
    47:  "BGM(&M)",
    48:  "音效(&S)",
    49:  "语音(&V)",
    50:  "音量(&V)",
    51:  "基准(&B)",
    # 音量等级 / 显示速度等级：同一串在四条子菜单里各出现一次，译一处即可
    52:  "16 级[最大](&A)", 53: "15 级(&B)", 54: "14 级(&C)", 55: "13 级(&D)",
    56:  "12 级(&E)", 57: "11 级(&F)", 58: "10 级(&G)", 59: "09 级(&H)",
    60:  "08 级(&I)", 61: "07 级(&J)", 62: "06 级(&K)", 63: "05 级(&L)",
    64:  "04 级(&M)", 65: "03 级(&N)", 66: "02 级(&O)", 67: "01 级(&P)",
    68:  "00 级[最小](&Q)",
    69:  "BGM 音量(&M)",
    123: "动画(&A)",
    141: "音质(&Q)",
    142: "标准(&N)",
    143: "高音质(&H)",
    144: "语音播放时的 BGM 音量(&O)",
    145: "内存流播放(&M)",
    146: "消息相关(&T)",
    147: "字体(&F)",
    148: "文字加工(&C)",
    149: "描边[无](&0)",
    150: "描边[弱](&1)",
    151: "描边[强](&2)",
    152: "粗体(&B)",
    153: "轮廓修正(&A)",
    154: "显示速度(&W)",
    155: "00 级[瞬时](&N)",
    156: "01 级(&0)", 157: "02 级(&1)", 158: "03 级(&2)", 159: "04 级(&3)",
    160: "05 级(&4)", 161: "06 级(&5)", 162: "07 级(&6)", 163: "08 级(&7)",
    164: "09 级(&8)", 165: "10 级[低速](&9)",
    166: "文字显示特效(&E)",
    167: "普通(&N)",
    168: "透明(&T)",
    169: "逐字(&Z)",
    170: "特效[50ms](&0)", 171: "特效[200ms](&1)", 172: "特效[350ms](&2)",
    173: "特效[500ms](&3)", 174: "特效[650ms](&4)",
    175: "语音停止控制(&V)",
    176: "文字推进时停止语音(&C)",
    177: "直到下次语音播放前不停止(&N)",
    178: "文字推进时淡出(&F)",
    179: "自动推进设置(&T)",
    180: "未读文字时停止快进(&M)",
    181: "动画相关(&V)",
    182: "帧控制(&F)",
    183: "无效(&0)",
    185: "自动控制(&2)",
    186: "鼠标相关(&M)",
    187: "鼠标指针显示控制(&D)",
    188: "不自动隐藏鼠标指针(&N)",
    189: "5 秒后自动隐藏(&1)",
    190: "10 秒后自动隐藏(&2)",
    191: "15 秒后自动隐藏(&3)",
    192: "20 秒后自动隐藏(&4)",
    193: "信息(&I)",
    194: "返回标题画面(&R)",
    195: "退出(&E)",
}


def menu_items() -> list[str]:
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 4:
            continue
        for e in t.directory.entries:
            for lang in e.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                return [s for _p, _f, _i, s in parse(d) if s]
    return []


def main() -> int:
    items = menu_items()
    print(f"菜单里非空项 {len(items)} 条\n")

    lines, missing, unused = [], [], set(MENU_ZH)
    for i, s in enumerate(items):
        if i in MENU_ZH:
            lines.append(f"{s}\t{MENU_ZH[i]}")
            unused.discard(i)

    for i, s in enumerate(items):
        if i in MENU_ZH:
            print(f"  [{i:3d}] {s!r}\n        -> {MENU_ZH[i]}")
    for i in unused:
        print(f"  ⚠ 下标 {i} 在菜单里不存在（越界或算错了）")
    if missing:
        print("  未译:", missing)

    if "--write" not in sys.argv:
        print(f"\n（--show 模式，未写文件。共 {len(lines)} 条待写入）")
        return 1 if unused else 0

    text = TABLE.read_text(encoding="utf-8-sig")
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        _old, tail = rest.split(END, 1) if END in rest else ("", "")
        text = head + tail.lstrip("\n")
    block = f"{BEGIN}\n#\n" + "\n".join(lines) + f"\n{END}\n"
    TABLE.write_text(text.rstrip("\n") + "\n\n" + block, encoding="utf-8")
    print(f"\n已写入 {len(lines)} 条 -> {TABLE}")
    return 1 if unused else 0


if __name__ == "__main__":
    sys.exit(main())
