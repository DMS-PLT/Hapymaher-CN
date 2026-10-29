#!/usr/bin/env python3
"""核对译文表：把 cnpatch_ui.txt 的每一行原文，拿去和 exe 资源里的真实字符串比。

译文表是按「原文完全相等」匹配的，全角/半角差一个字符就静默失效 ——
所以改完词一定要跑一遍这个，别靠肉眼。

用法：
    uv run --with pefile python check_ui_table.py [exe] [译文表]
"""
from __future__ import annotations

import sys
from pathlib import Path

import pefile

sys.path.insert(0, str(Path(__file__).parent))
from extract_sjis import scan  # noqa: E402
from parse_dialog import parse  # noqa: E402
from parse_menu import parse as parse_menu  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ハピメア フルHD版" / "cmvs32.exe"
TABLE = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "test" / "hooklog" / "cnpatch_ui.txt"


def sjis_literals(data: bytes) -> dict[str, str]:
    """exe 里以 SJIS 存的字面量。

    窗口标题 `起動時の設定`、消息框正文 `上記のデータをロードしますか？` 这些都不在
    对话框资源里，而是这种 —— 游戏用 SetWindowTextA / SetDlgItemTextA 原样交给
    Windows，所以补丁是按「SJIS 字节」去查表的。

    用 extract_sjis 里的扫描器，别在这儿另写一份：那版认单字节半角片假名
    （`ﾋﾞｯﾄﾏｯﾌﾟﾌｧｲﾙ(*.bmp)` 开头就是 0xCD），漏了它这几条会被误报成「原文写错」。
    """
    return {s: "SJIS 字面量" for _off, s in scan(data)}


def exe_strings(pe) -> dict[str, str]:
    """收集 exe 里所有对话框控件的文字（原文 -> 资源 id），当校验用的真值表。"""
    out: dict[str, str] = {}
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id not in (4, 5):          # RT_MENU / RT_DIALOG
            continue
        for e in t.directory.entries:
            for lang in e.directory.entries:
                d = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                try:
                    if t.id == 4:
                        for _p, _f, _i, s in parse_menu(d):
                            if s:
                                out.setdefault(s, f"MENU {e.id}")
                        continue
                    info = parse(d)
                except Exception:  # noqa: BLE001
                    continue
                if info["title"]:
                    out.setdefault(info["title"], f"DIALOG {e.id} 标题")
                for it in info["items"]:
                    if it["title"]:
                        out.setdefault(it["title"], f"DIALOG {e.id} id={it['id']}")
    return out


def main() -> int:
    pe = pefile.PE(str(EXE), fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    known = exe_strings(pe)
    known.update(sjis_literals(EXE.read_bytes()))

    lines = TABLE.read_text(encoding="utf-8-sig").splitlines()
    ok = bad = skip = 0
    print(f"译文表: {TABLE}")
    print(f"对照源: {EXE.name}（对话框控件文字 {len(known)} 条）\n")

    for ln, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if "\t" not in s:
            print(f"  ✗ 第 {ln} 行：没有制表符，格式应为「原文<TAB>译文」")
            bad += 1
            continue
        jp, zh = s.split("\t", 1)
        jp, zh = jp.strip(), zh.strip()
        if not zh:
            print(f"  - 第 {ln} 行：译文为空，跳过 {jp!r}")
            skip += 1
            continue
        if jp.startswith("~"):                   # 片段替换：只要在某个已知串里出现过就行
            frag = jp[1:]
            host = next((k for k in known if frag in k), None)
            if host:
                print(f"  ✓ 第 {ln} 行  [片段] {frag!r}  ← 出现在 {host!r}")
                ok += 1
            else:
                print(f"  ✗ 第 {ln} 行  [片段] 在 exe 的任何字符串里都没出现过：{frag!r}")
                bad += 1
            continue
        if jp in known:
            print(f"  ✓ 第 {ln} 行  {jp!r}  ← {known[jp]}")
            ok += 1
        else:
            print(f"  ✗ 第 {ln} 行  在 exe 里找不到这个原文：{jp!r}")
            print(f"        逐字符: {' '.join(f'{c}(U+{ord(c):04X})' for c in jp)}")
            bad += 1

    print(f"\n对得上 {ok} 条，对不上 {bad} 条，空译文跳过 {skip} 条")
    if bad:
        print("\n对不上的原文，最可能是全角/半角或括号写错了 —— "
              "把上面『逐字符』那行和 exe 里的原串摆一起比对。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
