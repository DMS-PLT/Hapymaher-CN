# -*- coding: utf-8 -*-
"""复核《汉化技术分析.md》中所有 exe 层面的论断。只读，不改动任何文件。"""
import struct, sys, hashlib, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\DMS\Desktop\Hapymaher"
ORIG = BASE + r"\test\backup\cmvs32.exe.orig"
FD   = BASE + r"\ハピメア Fragmentation Dream フルHD版\cmvs32.exe"
MAIN = BASE + r"\ハピメア フルHD版\cmvs32.exe"

data = open(ORIG, "rb").read()
print(f"[size] orig = {len(data)}  (报告称 1060864: {len(data)==1060864})")

# ---------- PE 解析 ----------
assert data[:2] == b"MZ"
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
assert data[e_lfanew:e_lfanew+4] == b"PE\0\0"
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", data, coff + 2)
opt_size, = struct.unpack_from("<H", data, coff + 16)
opt = coff + 20
magic, = struct.unpack_from("<H", data, opt)
assert magic == 0x10B, hex(magic)  # PE32
image_base, = struct.unpack_from("<I", data, opt + 28)
print(f"[pe] sections={nsec} image_base={hex(image_base)}")

secs = []
sec_off = opt + opt_size
for i in range(nsec):
    o = sec_off + i * 40
    name = data[o:o+8].rstrip(b"\0").decode()
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    secs.append((name, vaddr, vsize, rawptr, rawsize))
    print(f"  sec {name:8s} VA={hex(image_base+vaddr)} vsize={hex(vsize)} raw={hex(rawptr)} rawsz={hex(rawsize)}")

def va2off(va):
    rva = va - image_base
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    raise ValueError(hex(va))

# ---------- 1. 六个补丁位点的字节值 ----------
print("\n[patch-sites] 报告表：offset 原 改")
claims = [
    (0x0197AB, 0x9F, 0xFE, "双字节判定#1 cmp al,0x9F 的操作数 (VA 0x41A3AB)"),
    (0x019836, 0x9F, 0xFE, "双字节判定#2 (字符串版)"),
    (0x019A2B, 0x9F, 0xFE, "双字节判定#3"),
    (0x0611AA, 0x80, 0x86, "CreateFontA charset 128→134 (push 0x80 的操作数)"),
    (0x06C581, 0x74, 0xEB, "Script_Xor 强制跳过解密 (VA 0x46D181)"),
    (0x06C5AD, 0x74, 0xEB, "Script_Com 强制跳过解压 (VA 0x46D1AD)"),
]
for off, orig, patched, desc in claims:
    b = data[off]
    va = None
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= off < rawptr + rawsize:
            va = image_base + vaddr + (off - rawptr)
    ok = "OK" if b == orig else f"MISMATCH(实际={b:02X})"
    print(f"  {off:#08x} {orig:02X}->{patched:02X}  实际={b:02X}  VA={hex(va)}  {ok}  {desc}")

# ---------- 2. 0x41A3A0 函数完整字节 ----------
print("\n[func@0x41A3A0] 完整 40 字节 hexdump（报告称 29 字节函数）:")
o = va2off(0x41A3A0)
blob = data[o:o+40]
for i in range(0, 40, 16):
    print("  " + hex(0x41A3A0+i) + "  " + " ".join(f"{b:02X}" for b in blob[i:i+16]))

# ---------- 3. 另外两处 9F 位点的上下文 ----------
print("\n[site2/site3 context] 另两处补丁点前后各 48 字节:")
for off, tag in [(0x019836, "site2"), (0x019A2B, "site3")]:
    va = image_base + va2off(0x41A3A0)  # dummy
    # 直接换算
    rva = None
    for name, vaddr, vsize, rawptr, rawsize in secs:
        if rawptr <= off < rawptr + rawsize:
            rva = vaddr + (off - rawptr)
    va = image_base + rva
    start = off - 0x30
    print(f"  {tag}: 文件 {off:#x} → VA {hex(va)}")
    blob = data[start:start+0x60]
    for i in range(0, len(blob), 16):
        print(f"    {hex(va-0x30+i)}  " + " ".join(f"{b:02X}" for b in blob[i:i+16]))
    print()

# ---------- 4. LOGFONT 第二读取点上下文 (VA 0x419F97) ----------
print("[LOGFONT@0x419F97] 前 16 后 80 字节:")
o = va2off(0x419F60)
blob = data[o:o+0xA0]
for i in range(0, len(blob), 16):
    print(f"  {hex(0x419F60+i)}  " + " ".join(f"{b:02X}" for b in blob[i:i+16]))

# ---------- 5. charset 分支 (VA 0x461D91-0x461DD0) ----------
print("\n[charset-branch@0x461D91]:")
o = va2off(0x461D80)
blob = data[o:o+0x60]
for i in range(0, len(blob), 16):
    print(f"  {hex(0x461D80+i)}  " + " ".join(f"{b:02X}" for b in blob[i:i+16]))

# ---------- 6. 导入表：GDI/user32 文本绘制 API ----------
print("\n[imports] 在整个文件中搜索关键 API 名字符串（区分导入表 vs 普通字符串）:")
for api in [b"CreateFontA", b"CreateFontIndirectA", b"CreateFontIndirectW",
            b"GetGlyphOutlineA", b"GetGlyphOutlineW", b"GetTextMetricsA",
            b"TextOutA", b"TextOutW", b"ExtTextOutA", b"DrawTextA",
            b"GetTextExtentPoint32A", b"GetTextExtentPoint32W", b"GetCharacterPlacementA"]:
    pos = data.find(api)
    cnt = data.count(api)
    print(f"  {api.decode():28s} 出现 {cnt} 次" + (f"，首次 @ {pos:#x}" if pos>=0 else ""))

# ---------- 7. FD 与本体 exe 对比 ----------
def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()
print("\n[hash]")
print(f"  backup/orig      {md5(ORIG)}")
print(f"  本体/cmvs32.exe  {md5(MAIN)}")
print(f"  FD/cmvs32.exe    {md5(FD)}")
fd_data = open(FD, "rb").read()
print(f"  FD size = {len(fd_data)}，与本体 orig 逐字节相同: {fd_data == data}")
