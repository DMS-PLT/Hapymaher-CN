#!/usr/bin/env python3
"""生成 / 更新译文表里的「其它对话框 + 运行时文字」两段。

为什么不手写：原文里有 `スタティック`、`ﾍｯﾀﾞ部のﾁｪｯｸ` 这种半角片假名，
还有 `送り時間　＝　基準値＋…` 里夹着全角空格 —— 手打必错，
而译文表是按「原文完全相等」匹配的，错一个字符就是**静默失效**。
所以键一律从 exe 现取，人只出译文：

  · 对话框控件文字 —— 按 (对话框号, 该对话框内非空文字的下标) 索引。
    用下标而不是控件 id，是因为很多控件 id 是 -1（静态框），撞成一片。
  · 消息框正文   —— 那些是运行时用 SetDlgItemTextA 塞进去的 SJIS 字面量，
    按它在 exe 里的**文件偏移**索引（extract_sjis.py 扫出来的地址）。

用法：
    uv run --with pefile python gen_dialog_table.py            # 只核对，不写
    uv run --with pefile python gen_dialog_table.py --write    # 写进 cnpatch_ui.txt
"""
from __future__ import annotations

import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).parent))
from extract_sjis import scan  # noqa: E402
from parse_dialog import parse  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
EXE = ROOT / "ハピメア フルHD版" / "cmvs32.exe"
TABLE = ROOT / "test" / "hooklog" / "cnpatch_ui.txt"

BEGIN = "# ── 其它对话框 + 运行时文字 —— 由 gen_dialog_table.py 生成，别手改 ──"
END = "# ── 对话框段结束 ──"

# ── 对话框：标题 + 控件文字（下标 = 该对话框里「非空文字」的顺序号）──
# `items` 里没提到的下标＝不译（Static 占位框、公司名、URL、版本号、单选框的
# `Radio1`.. 那些运行时会被游戏自己填掉，译了也是白译）。
DIALOG_ZH: dict[int, dict] = {
    132: {"title": "消息对话框", "items": {
        0: "是(&Y)",
        1: "否(&N)",
    }},
    133: {"title": "对话框", "items": {
        1: "确定(&S)",
    }},
    134: {"title": None, "items": {          # 关于框：公司名/URL/版权不动
        0: "确定(&Y)",
    }},
    135: {"title": "确认对话框", "items": {
        0: "是(&Y)",
        1: "否(&N)",
    }},
    136: {"title": "字体选择", "items": {
        0: "确定(&Y)",
        1: "取消(&N)",
    }},
    137: {"title": "语音播放时的 BGM 音量设置", "items": {
        0: "取消(&S)",
        1: "设定音量",
        2: "淡出时间",
        3: "语音的淡出期间也算作播放中。",
        4: "静态", 5: "静态",                # id 1012 / 1013
        6: "确定(&R)",
        7: "语音结束等待",
        8: "静态",                           # id 1014
        9: "设定音量为 [100%] 时该功能停止。",
    }},
    138: {"title": "自动推进设置", "items": {
        0: "取消(&S)",
        1: "基准值",
        2: "每字增量",
        3: "推进时间　＝　基准值＋每字增量×字数－总衰减时间",
        4: "执行自动推进",
        5: "与语音同步的设置",
        6: "静态", 7: "静态",                # id 1020 / 1021
        8: "确定(&R)",
        9: "衰减值",
        10: "静态",                          # id 1023
        11: "（衰减值：每个字的基础衰减时间）",
        12: "语音等待",
        13: "静态",                          # id 1034
    }},
    147: {"title": "文本调试", "items": {     # 调试窗，正常玩看不到，顺手译了
        0: "【编号】",
        1: "【文件】",
        2: "【语音】",
        3: "【名字＆文本】",
        4: "【备注】",
        5: "确定(&R)",
        6: "取消(&S)",
        7: "调试种类",
        8: "名字＆文本",
        9: "未设定", 10: "未设定",           # id 1053 / 1054，下拉框默认项
        11: "其他",
        12: "撤销(&U)",
    }},
}

# ── 消息框正文 / 标题：运行时 SetDlgItemTextA / SetWindowTextA 传进来的 SJIS 串 ──
# 键是 extract_sjis.py 扫出的**文件偏移**。这些串是「活」的，不在对话框资源里，
# 所以只能按地址钉住；换个版本的 exe 地址会变，脚本会把对不上的报出来。
RUNTIME_ZH: dict[int, str] = {
    # 存档 / 读档
    0x0D1174: "存档确认",
    0x0D1184: "要覆盖上面的数据吗？",
    0x0D11A4: "读取确认",
    0x0D11B4: "要读取上面的数据吗？",
    # 退出 / 回标题
    0x0D0418: "退出游戏的确认",
    0x0D042C: "要退出游戏吗？",
    0x0D0448: "返回标题的确认",
    0x0D045C: "要返回标题画面吗？",
    # 复原功能
    0x0D0480: "系统信息",
    0x0D0490: "复原功能",
    0x0D049C: "要取消上一次的存档吗？",
    0x0D04C0: "要恢复到读取之前的状态吗？",
    0x0D04E4: "保存图像",
    # 设置类
    0x0D04F0: "头部检查【设置需要重启才能生效】",
    0x0D051C: "要更改设置吗？",
    0x0D0534: "数据段检查【设置需要重启才能生效】",
    0x0D0560: "音质更改[设置从下次启动起生效]",
    0x0D0590: "要将音质设为『标准』吗？",
    0x0D05BC: "要将音质设为『高音质』吗？",
    # 声音
    0x0D03C0: "声音警告",
    0x0D03D0: "播放设备已更改。",
    0x0CFE50: "声音类初始化异常",
    0x0CFE6C: "声音类创建失败。",
    # 报错（正常玩看不到，但既然能查到就一并译了）
    0x0C68C0: "异常",
    0x0C68C8: "数据解压失败。",
    0x0C696C: "包文件异常",
    0x0C6980: "包文件格式异常。",
    0x0C69A4: "包文件已损坏，即将退出。",
    0x0C6B98: "文本检查",
    0x0C6BAC: "包含半角字符。",
    0x0C6BC8: "注释中包含半角 [,]。",
    0x0CF2F0: "未知",
    0x0CFDD8: "初始化异常",
    0x0CFDE4: "设备初始化失败。",
    0x0D0404: "内部脚本异常",
    0x0D0720: "文件异常",
    0x0D07BC: "贴图异常",
    0x0D07D0: "贴图创建失败。",
    0x0D07F4: "内部文件未找到",
    0x0D080C: "找不到指定的名称。",
    0x0D0834: "空贴图创建失败。",
    0x0D0EF0: "注音异常",
    0x0D0EFC: "注音字符总数超限",
    0x0D11DC: "中断定义异常",
    0x0D11F0: "中断注册失败。",
    # 杂项
    0x0CF770: "位图文件(*.bmp)",
    0x0D14EC: "语音播放时的 BGM 淡出设置",
    0x0D1538: "示例对话框",
    0x0D1640: "无标题 - 记事本",
}

# 同一串在对话框和运行时表里都出现的，以先出现的为准（翻译一样，不必重复写）
_SAME = {"未設定", "テキストデバッグ"}


def dialog_items() -> dict[int, dict]:
    """{对话框号: {"title":..., "texts": [非空控件文字...]}}"""
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    out: dict[int, dict] = {}
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 5:
            continue
        for e in t.directory.entries:
            for lang in e.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                try:
                    info = parse(d)
                except Exception:  # noqa: BLE001
                    continue
                out[e.id] = {"title": info["title"],
                             "texts": [it["title"] for it in info["items"] if it["title"]]}
    return out


def main() -> int:
    items = dialog_items()
    runtime = dict(scan(EXE.read_bytes()))

    rows: list[tuple[str, str, str]] = []      # (键, 值, 出处) —— 出处只用于打印
    bad = 0

    for dlg, spec in sorted(DIALOG_ZH.items()):
        info = items.get(dlg)
        if not info:
            print(f"  ✗ DIALOG {dlg} 在 exe 里不存在")
            bad += 1
            continue
        zh = spec.get("title")
        if zh:
            rows.append((info["title"], zh, f"DIALOG {dlg} 标题"))
            print(f"  ✓ DIALOG {dlg} 标题  {info['title']!r} -> {zh!r}")
        for idx, z in sorted(spec.get("items", {}).items()):
            if idx >= len(info["texts"]):
                print(f"  ✗ DIALOG {dlg} 下标 {idx} 越界（只有 {len(info['texts'])} 条非空文字）")
                bad += 1
                continue
            jp = info["texts"][idx]
            rows.append((jp, z, f"DIALOG {dlg} #{idx}"))
            print(f"  ✓ DIALOG {dlg} #{idx:<2} {jp!r}\n        -> {z!r}")

    print()
    for off, z in sorted(RUNTIME_ZH.items()):
        jp = runtime.get(off)
        if jp is None:
            print(f"  ✗ 偏移 0x{off:06X} 处不是一条已知的 SJIS 串（exe 版本变了？）")
            bad += 1
            continue
        if jp in _SAME:                        # 对话框段已经写过同一条
            print(f"  - 0x{off:06X}  {jp!r} 与对话框段重复，跳过")
            continue
        rows.append((jp, z, f"0x{off:06X}"))
        print(f"  ✓ 0x{off:06X}  {jp!r}\n        -> {z!r}")

    # 去重：同一原文只留第一条（表是顺序查的，重复没意义还容易改漏）
    seen, uniq = set(), []
    for jp, z, src in rows:
        if jp in seen:
            print(f"  - 原文 {jp!r} 重复，只留先出现的那条")
            continue
        seen.add(jp)
        uniq.append((jp, z))

    print(f"\n共 {len(uniq)} 条待写入；对不上 {bad} 条")

    if "--write" not in sys.argv:
        print("（没有 --write，未写文件）")
        return 1 if bad else 0

    text = TABLE.read_text(encoding="utf-8-sig")
    if BEGIN in text:
        head, rest = text.split(BEGIN, 1)
        _old, tail = rest.split(END, 1) if END in rest else ("", "")
        text = head + tail.lstrip("\n")
    body = "\n".join(f"{jp}\t{z}" for jp, z in uniq)
    TABLE.write_text(text.rstrip("\n") + "\n\n" + f"{BEGIN}\n#\n{body}\n{END}\n",
                     encoding="utf-8")
    print(f"已写入 {len(uniq)} 条 -> {TABLE}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
