#!/usr/bin/env python3
"""从「明文 pb3 + chip.cpz 里的密文」反推封包加密的密钥流，看它是什么结构"""
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
CPZ = ROOT / "ハピメア フルHD版" / "data" / "pack" / "chip.cpz"
PLAIN = ROOT / "test" / "pathtbl" / "tc_plain.bin"
OFF = 0x88EEC3E

d = CPZ.open("rb")
d.seek(OFF)
C = d.read(4718377)
P = PLAIN.read_bytes()
assert len(C) == len(P), (len(C), len(P))

K = bytes(a ^ b for a, b in zip(C, P))
print(f"密钥流长度 {len(K)}")
print("前 64 字节:", " ".join(f"{b:02X}" for b in K[:64]))

# 周期性检查
def period_score(step, n=4096):
    return sum(1 for i in range(n) if K[i] == K[i + step])

print()
for step in (16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192, 16384, 65536):
    same = period_score(step)
    print(f"  步长 {step:>6}: 前 4096 字节里 K[i]==K[i+{step}] 的比例 = {same}/4096")

# 密钥流是不是「同一段重复」？看前 4096 字节里有没有重复块
print()
print("K[:4096] 里 1024 字节块的重复情况：")
b0 = K[:1024]
for j in range(1, 4):
    blk = K[j * 1024:(j + 1) * 1024]
    diffs = sum(1 for a, b in zip(b0, blk) if a != b)
    print(f"  第 {j} 块 vs 第 0 块: {diffs}/1024 字节不同")

# 保存密钥流，后面可能要用
(ROOT / "test" / "pathtbl" / "keystream.bin").write_bytes(K)
print()
print("已存 test/pathtbl/keystream.bin")
