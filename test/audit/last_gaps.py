# -*- coding: utf-8 -*-
"""收尾疑点：
1) cmvs32.exe 是否有导出表（解释 0x41A421 无静态引用之谜）
2) 0x41CD8A / 0x4770E5 调用点上下文（从调用点向后反汇编）
3) 关键字符串：0x4D2DD4/0x4D2DD8, 0x4D3178/0x4D3184, 0x4D1C08/0x4D1C30
4) 0x41A421 是否被 JMP rel16/其它形式引用（全文件扫 rel32 jmp/call 已做过，这里扫 push imm32 变体已含；
   改扫 'mov reg, imm32' 中的 imm32 == 0x41A421，前面已覆盖。故这里只查导出表 + int3 前函数边界确认）"""
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
export_rva, export_size = struct.unpack_from("<II", data, opt + 96)

secs = []
for i in range(nsec):
    o = opt + opt_size + i * 40
    name = data[o:o+8].rstrip(b"\0").decode()
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))

def rva2off(rva):
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    return None

def read_cstr_va(va):
    o = rva2off(va - image_base)
    if o is None:
        return None
    return data[o:].split(b"\0")[0]

md = Cs(CS_ARCH_X86, CS_MODE_32)

print("========== 1. 导出表 ==========")
print(f"export dir rva={hex(export_rva)} size={hex(export_size)}")
if export_rva:
    o = rva2off(export_rva)
    chars, ts, mj, mn, name_rva, base, nfunc, nnames, afn, anm, aord = struct.unpack_from("<IIHHIIIIIII", data, o)
    print(f"  函数数={nfunc} 名称数={nnames} dll={read_cstr_va(image_base+name_rva)!r}")
    names_off = rva2off(anm)
    funcs_off = rva2off(afn)
    ords_off = rva2off(aord)
    for i in range(min(nnames, 40)):
        fnrva, = struct.unpack_from("<I", data, names_off + i*4)
        name = read_cstr_va(image_base + fnrva)
        ordinal, = struct.unpack_from("<H", data, ords_off + i*2)
        frva, = struct.unpack_from("<I", data, funcs_off + ordinal*4)
        print(f"  [{ordinal+base}] {name.decode(errors='replace')} @ {hex(image_base+frva)}")
else:
    print("  无导出表")

print("\n========== 2. 0x41CD8A 调用点向后 0x60 ==========")
o = rva2off(0x41CD8A - image_base)
code = data[o:o+0x60]
for ins in md.disasm(code, 0x41CD8A):
    print(f"  {hex(ins.address)}  {ins.mnemonic} {ins.op_str}")

print("\n========== 3. 0x4770E5 调用点向后 0x40 ==========")
o = rva2off(0x4770E5 - image_base)
code = data[o:o+0x40]
for ins in md.disasm(code, 0x4770E5):
    print(f"  {hex(ins.address)}  {ins.mnemonic} {ins.op_str}")

print("\n========== 4. 关键字符串 ==========")
for va in (0x4D2DD4, 0x4D2DD8, 0x4D3178, 0x4D3184, 0x4D1C08, 0x4D1C30, 0x4EA7B0, 0x41A7F0):
    s = read_cstr_va(va)
    if s:
        for enc in ("shift-jis", "gbk"):
            try:
                print(f"  {hex(va)} ({enc}): {s.decode(enc)!r}")
                break
            except Exception:
                continue
        else:
            print(f"  {hex(va)}: {s[:40]!r}")
