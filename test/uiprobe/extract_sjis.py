#!/usr/bin/env python3
"""从 exe 里捞出 SJIS 字面量，按用途筛。

对话框模板里的文字是「死」的（在资源里，解析出来就是），但**消息框的正文是活的** ——
游戏在运行时用 SetDlgItemTextA 塞进去（见 cnpatch.log 里 135 号对话框那条
`上記のデータをロードしますか？`）。那些正文是 exe 里的 SJIS 字面量，得从这儿捞。

字符串表是按 4 字节对齐的：每条 NUL 结尾，后面补 0 到 4 字节边界。
所以判据是「出现在 4 的倍数偏移上、且前面也是 0」。

用法：
    uv run python extract_sjis.py                # 全列
    uv run python extract_sjis.py --ui           # 只列像界面文字的（含 か？/ます/ください…）
    uv run python extract_sjis.py --at 0xD1150   # 看某个地址附近
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
EXE = ROOT / "ハピメア フルHD版" / "cmvs32.exe"

# 「像界面文字」的样子。消息框正文基本都落在这里面。
UI_HINTS = ("か？", "ます", "ください", "ません", "ですか", "します",
            "エラー", "失敗", "異常", "できません", "確認", "警告")


def is_sjis_pair(b0: int, b1: int) -> bool:
    """Shift-JIS 双字节判定（和引擎里那 9 处补丁同一条规则）。"""
    return (0x81 <= b0 <= 0x9F or 0xE0 <= b0 <= 0xFC) and 0x40 <= b1 <= 0xFC and b1 != 0x7F


def scan(data: bytes) -> list[tuple[int, str]]:
    """扫出 4 字节对齐、NUL 结尾、含日文的 SJIS 串。"""
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(data):
        if data[i] == 0:
            i += 1
            continue
        if i % 4 != 0:                      # 字符串表按 4 字节对齐
            i += 1
            continue
        if i and data[i - 1] != 0:          # 前面不是 NUL，说明落在一坨中间
            i += 1
            continue

        j, ok = i, True
        while j < len(data) and data[j] != 0:
            b = data[j]
            if 0x20 <= b < 0x7F:
                j += 1
            elif j + 1 < len(data) and is_sjis_pair(b, data[j + 1]):
                j += 2
            elif 0xA1 <= b <= 0xDF:
                j += 1                    # 单字节半角片假名（CTRL 菜单里满地都是）
            else:
                ok = False
                break
        if not ok or j == i:
            i += 1
            continue
        raw = data[i:j]
        if len(raw) >= 4 and any(x >= 0x81 for x in raw):
            try:
                s = raw.decode("cp932")
            except Exception:  # noqa: BLE001
                s = ""
            # 至少要有一个「正经」汉字/假名，否则半角片假名的单字节噪声会大量漏进来
            if s and any(ord(c) > 0x2FFF for c in s):
                out.append((i, s))
        i = j + 1
    return out


def main() -> int:
    data = EXE.read_bytes()
    strings = scan(data)

    if "--at" in sys.argv:
        lo = int(sys.argv[sys.argv.index("--at") + 1], 0)
        for off, s in strings:
            if abs(off - lo) < 0x400:
                print(f"  0x{off:06X}  {s!r}")
        return 0

    ui_only = "--ui" in sys.argv
    if ui_only:
        strings = [(o, s) for o, s in strings if any(h in s for h in UI_HINTS)]

    for off, s in strings:
        print(f"  0x{off:06X}  {s!r}")
    print(f"\n共 {len(strings)} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
