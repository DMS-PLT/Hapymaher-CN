# -*- coding: utf-8 -*-
"""1) FONT_SHIFT_JIS getter 的 11 个调用点上下文反汇编
2) CreateFontA ([0x4C8050]) 全部调用点
3) 0x41A421 / 0x41A3A0 / 0x41A610 是否被当作地址引用（函数指针）
4) font_enum_probe 唯一调用者 0x41EC8B 的上下文"""
import struct, sys, io
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\DMS\Desktop\Hapymaher"
data = open(BASE + r"\test\backup\cmvs32.exe.orig", "rb").read()

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", data, coff + 2)
opt_size, = struct.unpack_from("<H", data, coff + 16)
opt = coff + 20
image_base, = struct.unpack_from("<I", data, opt + 28)

secs = []
for i in range(nsec):
    o = opt + opt_size + i * 40
    name = data[o:o+8].rstrip(b"\0").decode()
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))

def va2off(va):
    rva = va - image_base
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    raise ValueError(hex(va))

md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

def disasm(va, back=0x30, fwd=0x10):
    """从 va-back 反汇编到 va+fwd，标注目标行"""
    start = va - back
    code = data[va2off(start):va2off(start) + back + fwd]
    lines = []
    for ins in md.disasm(code, start):
        mark = " <<<" if ins.address <= va < ins.address + ins.size else ""
        lines.append(f"  {hex(ins.address)}  {ins.mnemonic} {ins.op_str}{mark}")
    return "\n".join(lines)

print("========== 1. getter 11 个调用点上下文 ==========")
for va in (0x41CD8A, 0x461D1F, 0x461E73, 0x461EBF, 0x461F57,
           0x4770E5, 0x48A753, 0x4923D1, 0x4924C0, 0x493820):
    print(f"\n--- callsite {hex(va)} ---")
    print(disasm(va, back=0x28, fwd=0x28))

print("\n========== 2. call [0x4C8050] (CreateFontA) 调用点 ==========")
# FF 15 50 80 4C 00
pat = bytes([0xFF, 0x15]) + struct.pack("<I", 0x4C8050)
pos = 0
while True:
    pos = data.find(pat, pos)
    if pos < 0:
        break
    # 文件偏移 → VA
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= pos < rawptr + rawsize:
            va = image_base + vaddr + (pos - rawptr)
            print(f"  CreateFontA call @ {hex(va)} ({name})")
    pos += 1

print("\n========== 3. 地址引用（函数指针）扫描 ==========")
for tgt in (0x41A421, 0x41A3A0, 0x41A610, 0x41A7F0):
    pat = struct.pack("<I", tgt)
    hits = []
    pos = 0
    while True:
        pos = data.find(pat, pos)
        if pos < 0:
            break
        for name, vaddr, vsize, rawptr, rawsize in secs:
            if rawptr <= pos < rawptr + rawsize:
                hits.append(f"{hex(image_base + vaddr + (pos - rawptr))}({name})")
        pos += 1
    print(f"  {hex(tgt)}: {len(hits)} 处地址引用: {' '.join(hits[:12])}")

print("\n========== 4. font_enum_probe 调用者 0x41EC8B 上下文 ==========")
print(disasm(0x41EC8B, back=0x40, fwd=0x40))
