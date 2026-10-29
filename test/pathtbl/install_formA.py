#!/usr/bin/env python3
"""把 UI界面/chip 的 pb3 全部转成「引擎形态」(Form A) 铺进游戏目录。

Form A = encrypt_pb3(GARbro 解出来的成品)。原因见 tools/pb3.py 里的长注释。
title_chip 换成带洋红横条的版本，用来在标题画面上肉眼验证。
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
sys.path.insert(0, str(ROOT / "tools"))
import pb3  # noqa: E402

SRC = ROOT / "UI界面" / "chip"
DST = ROOT / "ハピメア フルHD版" / "data" / "pack" / "chip"


def marked_title_chip() -> bytes:
    """解码 title_chip，画一条洋红横条，再编回 pb3（Form B）"""
    raw = (SRC / "title_chip.pb3").read_bytes()
    meta = pb3.read_meta(raw)
    w, h, rgba = pb3.decode(raw)
    print(f"    title_chip {w}x{h} bpp={meta['bpp']} subtype={meta['subtype']:#x}")

    bar = bytearray(rgba)
    y0, y1 = h // 2 - 90, h // 2 + 90
    for y in range(y0, y1):
        row = (y * w) * 4
        bar[row:row + w * 4] = b"\xff\x00\xff\xff" * w
    return pb3.encode_pb3(bytes(bar), w, h, meta["bpp"], subtype=meta["subtype"])


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    srcs = sorted(SRC.glob("*.pb3"))
    total = 0
    for f in srcs:
        d = bytearray(f.read_bytes())
        if not pb3.looks_plain(bytes(d)):
            raise SystemExit(f"{f.name} 头部不像 Form B，别乱转")
        pb3.encrypt_pb3(d)
        (DST / f.name).write_bytes(d)
        total += len(d)
    print(f"  铺入 {len(srcs)} 个 pb3（Form A），共 {total/1048576:.1f} MB")

    # 标题图：换成带标记的
    m = bytearray(marked_title_chip())
    pb3.encrypt_pb3(m)
    (DST / "title_chip.pb3").write_bytes(m)
    print(f"  title_chip.pb3 换成带洋红横条的版本（{len(m)} 字节）")

    # chip.cpz 里还有一个 ogg，一并放进去
    ogg = SRC / "se020d.ogg"
    if ogg.exists():
        shutil.copy2(ogg, DST / ogg.name)
        print(f"  附带拷贝 {ogg.name}")

    print(f"  → {DST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
