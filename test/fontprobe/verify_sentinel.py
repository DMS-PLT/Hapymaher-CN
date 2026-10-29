#!/usr/bin/env python3
"""验证哨兵字符能不能穿过 PS3_TextEditor 变成 0xA1 0x40 两个字节。

Python 的 gbk 编解码器不认 U+E4C6，但 Windows 的 CP936 认（0xA140 <-> U+E4C6，
两个方向都验过）。真正做编码的是 PS3_TextEditor，所以只要 JSON 里放对字符就行。

注意：必须按 build_encrypted.py 的规则，把所有未翻译的非 ASCII 条目换成（未译），
否则满篇日文假名先编不过 GBK —— 那是另一回事，会掩盖真正要验的东西。

只读 sky01.ps3，产物写 test/ 里，不碰游戏目录。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
TOOL = ROOT / "tools" / "RxCMVS" / "PS3_TextEditor.exe"
SRC_PS3 = ROOT / "ハピメア脚本" / "code" / "sky01.ps3"
SRC_JSON = ROOT / "output" / "hapymaher" / "sky01.ps3.json"
OUT = Path(__file__).parent / "out"

SENTINEL = "\ue4c6"          # CP936 0xA140
NOTE = "\u266a"              # ♪
PLACEHOLDER = "（未译）"

OUT.mkdir(parents=True, exist_ok=True)


def build(label: str, index: int, text: str) -> bytes:
    """按 build_encrypted.py 的规则构建一个脚本，返回明文 .ps3 字节。"""
    scenario = json.loads(SRC_JSON.read_text(encoding="utf-8-sig"))["Scenario"]
    for ent in scenario:
        if ent["raw"].isascii():
            ent["tra"] = ent["raw"]          # 纯 ASCII 原样（标签/命令）
        else:
            ent["tra"] = PLACEHOLDER
    scenario[index]["tra"] = text

    tmp_json = OUT / f"{label}.json"
    tmp_json.write_text(json.dumps({"Scenario": scenario}, ensure_ascii=False),
                        encoding="utf-8-sig")
    plain = OUT / f"{label}.plain"
    p = subprocess.run([str(TOOL), "-mode", "import", "-ps3", str(SRC_PS3),
                        "-json", str(tmp_json), "-save", str(plain), "-code", "936"],
                       capture_output=True)
    print(f"\n--- {label} ---")
    print(f"    条目 #{index} 译文 : {text!r}")
    if p.returncode != 0:
        print("    工具返回非 0:", p.returncode)
    err = p.stderr.decode("gbk", errors="replace").strip()
    if err:
        print("    stderr:", err[:200])
    if not plain.exists():
        print("    *** 产物没生成 ***")
        return b""
    return plain.read_bytes()


def report(data: bytes, want: bytes, what: str) -> None:
    i = data.find(want)
    print(f"    {what}: {'找到，偏移 0x%X' % i if i >= 0 else '*** 没找到 ***'}")
    if i >= 0:
        print(f"    上下文 : {data[i-8:i+10].hex(' ')}")
        print(f"    可读   : {data[i-8:i+10].decode('gbk', errors='replace')!r}")


# 1. 哨兵：期望原样变成 A1 40
data = build("sentinel", 14, f"前{SENTINEL}后")
if data:
    report(data, b"\xa1\x40", "找 A1 40（哨兵）")
    report(data, b"?", "找 '?' 0x3F")

# 2. 对照：直接塞 ♪，期望变成 '?'
data2 = build("raw_note", 14, f"前{NOTE}后")
if data2:
    report(data2, b"?", "找 '?' 0x3F（♪ 的替代）")
    report(data2, b"\x81\xf4", "找 81 F4（♪ 的 SJIS 字节）")

# 3. 真台词场景：句子里的 ♪
data3 = build("inline", 14, f"来玩吧{SENTINEL}真开心")
if data3:
    report(data3, b"\xa1\x40", "找 A1 40（句中哨兵）")
