# -*- coding: utf-8 -*-
"""追查 0x419F70 函数（含 LOGFONT 构造）调用的 API；解析导入表 IAT→名称映射。
另核对当前游戏目录的 start.ps3 / initial.cfg 与备份的差异。"""
import struct, sys, io, hashlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\DMS\Desktop\Hapymaher"
data = open(BASE + r"\test\backup\cmvs32.exe.orig", "rb").read()

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
coff = e_lfanew + 4
nsec, = struct.unpack_from("<H", data, coff + 2)
opt_size, = struct.unpack_from("<H", data, coff + 16)
opt = coff + 20
image_base, = struct.unpack_from("<I", data, opt + 28)
import_rva, import_size = struct.unpack_from("<II", data, opt + 96 + 8)  # data dir[1]

secs = []
for i in range(nsec):
    o = opt + opt_size + i * 40
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
    secs.append((vaddr, vsize, rawptr, rawsize))

def rva2off(rva):
    for vaddr, vsize, rawptr, rawsize in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsize):
            return rawptr + (rva - vaddr)
    raise ValueError(hex(rva))

# 解析导入表：建立 IAT VA -> "dll!func" 映射
iat_map = {}
o = rva2off(import_rva)
while True:
    oft, ts, fc, name_rva, iat = struct.unpack_from("<IIIII", data, o)
    if oft == 0 and iat == 0:
        break
    dll = data[rva2off(name_rva):].split(b"\0")[0].decode()
    thunk = oft if oft else iat
    t = rva2off(thunk)
    idx = 0
    while True:
        val, = struct.unpack_from("<I", data, t + idx*4)
        if val == 0:
            break
        if val & 0x80000000:
            iat_map[image_base + iat + idx*4] = f"{dll}!ordinal{val & 0xFFFF}"
        else:
            fn = data[rva2off(val)+2:].split(b"\0")[0].decode()
            iat_map[image_base + iat + idx*4] = f"{dll}!{fn}"
        idx += 1
    o += 20

print("[iat] 关键 IAT 项：")
for va in (0x4C8360, 0x4C80A0, 0x4C8068, 0x4C835C, 0x4C8050, 0x4C8050):
    if va in iat_map and va != 0x4C8050:
        print(f"  {hex(va)} -> {iat_map[va]}")
print(f"  0x4C8050 -> {iat_map.get(0x4C8050)}")

# 0x41A7F0 处的字符串（EnumFontFamiliesExA 的回调地址）
print("\n[0x41A7F0] 回调函数前 0x100 字节 + 尝试解读:")
off = rva2off(0x41A7F0 - image_base)
blob = data[off:off+0x100]
for i in range(0, len(blob), 16):
    print(f"  {hex(0x41A7F0+i)}  " + " ".join(f"{b:02X}" for b in blob[i:i+16]))

# 该函数附近是否有字体名字符串？搜 .rdata 里的 "ＭＳ" 等
print("\n[rdata] 0x41A700-0x41A900 区域内可打印字符串:")
region_off = rva2off(0x41A700 - image_base)
region = data[region_off:region_off+0x200]
cur, start = b"", None
for i, b in enumerate(region):
    if 0x20 <= b < 0x7F or b >= 0x81:
        if not cur:
            start = i
        cur += bytes([b])
    else:
        if len(cur) >= 4:
            try:
                s = cur.decode("shift-jis")
                print(f"  {hex(0x41A700+start)}: {s!r}")
            except Exception:
                pass
        cur = b""

# 当前游戏目录状态核对
print("\n[state] 当前游戏目录 vs 备份：")
def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()
pairs = [
    (r"\test\backup\start.ps3.orig", r"\ハピメア フルHD版\data\pack\start.ps3", "start.ps3"),
    (r"\test\backup\initial.cfg.orig", r"\ハピメア フルHD版\initial.cfg", "initial.cfg"),
]
for b, g, name in pairs:
    try:
        hb, hg = md5(BASE+b), md5(BASE+g)
        print(f"  {name}: 备份={hb[:12]} 当前={hg[:12]} {'相同' if hb==hg else '不同(实验态)'}")
    except FileNotFoundError as e:
        print(f"  {name}: 缺文件 {e.filename}")

# start.ps3 若不同，diff 看差异落点
try:
    b = open(BASE + r"\test\backup\start.ps3.orig", "rb").read()
    g = open(BASE + r"\ハピメア フルHD版\data\pack\start.ps3", "rb").read()
    if b != g:
        print(f"  start.ps3 尺寸: 备份={len(b)} 当前={len(g)}")
        n = min(len(b), len(g))
        diffs = [i for i in range(n) if b[i] != g[i]]
        print(f"  差异字节数(公共部分)={len(diffs)}，范围 {hex(diffs[0])}..{hex(diffs[-1])}" if diffs else "  公共部分无差异(仅追加)")
except FileNotFoundError:
    pass
