# -*- coding: utf-8 -*-
"""在 .text 中扫描 E8/E9 rel32 直接调用，统计四个关键函数的调用点：
0x41A3A0(判定#1) 0x41A421(比较,含判定#2) 0x41A610(查找/计数,含判定#3) 0x419F70(字体探测) 0x419DB0(getter)
只读。"""
import struct, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\DMS\Desktop\Hapymaher"
data = open(BASE + r"\test\backup\cmvs32.exe.orig", "rb").read()

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", data, coff + 2)
opt_size, = struct.unpack_from("<H", data, coff + 16)
opt = coff + 20
image_base, = struct.unpack_from("<I", data, opt + 28)

targets = {0x41A3A0: "is_sjis_lead (29B函数)", 0x41A421: "dbcs_strcmp(判定#2)",
           0x41A610: "dbcs_find(判定#3)", 0x419F70: "font_enum_probe",
           0x419DB0: "FONT_SHIFT_JIS getter"}
found = {t: [] for t in targets}

for i in range(nsec):
    o = opt + opt_size + i * 40
    name = data[o:o+8].rstrip(b"\0").decode()
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    if name != ".text":
        continue
    for off in range(rawptr, rawptr + rawsize - 5):
        op = data[off]
        if op in (0xE8, 0xE9):
            disp, = struct.unpack_from("<i", data, off + 1)
            va = image_base + vaddr + (off - rawptr)
            tgt = va + 5 + disp
            if tgt in targets:
                found[tgt].append((va, "call" if op == 0xE8 else "jmp"))

for t in targets:
    print(f"\n[{hex(t)} {targets[t]}] 直接调用 {len(found[t])} 处:")
    print("  " + " ".join(hex(v) for v, _ in found[t][:60]))
