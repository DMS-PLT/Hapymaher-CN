#!/usr/bin/env python3
"""判断封包加密是「异或」还是「加法」，密钥是不是周期性的"""
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
CPZ = ROOT / "ハピメア フルHD版" / "data" / "pack" / "chip.cpz"
PLAIN = ROOT / "test" / "pathtbl" / "tc_plain.bin"
OFF = 0x88EEC3E

with CPZ.open("rb") as f:
    f.seek(OFF)
    C = f.read(4718377)
P = PLAIN.read_bytes()
n = len(C)


def periodic_score(derived, step, win=16384):
    """derived[i] == derived[i+step] 的比例（只看窗口内，够判定了）"""
    return sum(1 for i in range(win) if derived[i] == derived[i + step]) / win


variants = {
    "XOR (C^P)":  bytes(a ^ b for a, b in zip(C[:65536], P[:65536])),
    "ADD (C-P)":  bytes((a - b) & 0xFF for a, b in zip(C[:65536], P[:65536])),
    "SUB (P-C)":  bytes((b - a) & 0xFF for a, b in zip(C[:65536], P[:65536])),
}

print(f"样本 {n} 字节, 分析窗口 65536\n")
for name, d in variants.items():
    print(f"--- {name} ---")
    print("  前 16 字节:", " ".join(f"{b:02X}" for b in d[:16]))
    for step in (256, 512, 1024, 2048, 4096):
        s = periodic_score(d, step)
        flag = "  <<< 强周期!" if s > 0.9 else ("  <- 有结构" if s > 0.05 else "")
        print(f"    周期 {step:>5}: 匹配率 {s:.4f}{flag}")
    print()
