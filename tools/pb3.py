#!/usr/bin/env python3
r"""pb3.py — CMVS 的 PB3B 图片 **解码成 PNG / 从 PNG 编回去**（改 UI 用）。

## 这格式是什么

`data\\pack\\chip.cpz` 里那 198 个 `.pb3` 就是界面的图（顶部菜单栏、对话框底图…）。
头 4 字节是 `PB3B`，不是改名的 PNG，得解。

布局（来自 GARbro 的 `ArcFormats/Cmvs/ImagePB3.cs`）：

| 偏移 | 字段 | 说明 |
|---|---|---|
| 0x00 | 魔数 | `PB3B` |
| 0x04 | input_size | 压缩流长度 |
| 0x18 | SubType | 见下 |
| 0x1C | Type (u16) | 1 = UnpackV1（本作是这种） |
| 0x1E | width (u16) | |
| 0x20 | height (u16) | |
| 0x22 | bpp (u16) | 24 / 32 |
| 0x2C | data1 | 通道表 1 的偏移 |
| 0x30 | data2 | 通道表 2 的偏移 |

Type=1 且 SubType=0x10 时走 `UnpackV1`，三个通道（B/G/R，32bpp 还有 A）各自：
1. 用 **LZSS** 解出一段「平面」数据
2. 再按 **16×16 块**铺开 —— 每个块一位：该位为 1 表示整块是同一个颜色值
   （从另一条流里读一个字节），为 0 才从上面那个平面里取像素

> GARbro 只能**读**不能写（`Pb3Format.Write` 直接抛 `NotImplementedException`），
> 所以编码这一半是自己写的 —— 布局从 `ci01a.pb3` 实测反推，见下面「编码」一节。

## 用法

    # 解出 PNG 给 Photoshop 改
    uv run python tools/pb3.py decode --in "UI界面/chip" --out "UI界面/chip_png"
    uv run python tools/pb3.py info   --in "UI界面/chip/ci01a.pb3"

    # 改完编回 pb3（--tpl 是原始 pb3 目录，尺寸/bpp 照它来）
    uv run --with pillow python tools/pb3.py encode \
        --in "UI界面/chip_png" --tpl "UI界面/chip" --out "UI界面/chip_new"

    # 编出来的直接就是游戏能吃的形态，拷进 游戏目录\data\pack\chip\ 即可
    copy "UI界面\chip_new\*.pb3" "ハピメア フルHD版\data\pack\chip\"

decode 是纯标准库（PNG 自己拼）；encode 要读 PNG，用 Pillow —— 因为 PS 存出来的
PNG 变体太多（RGB/RGBA、隔行…），自己写读取器不划算。

`encode` 默认会套上 **Form A** 那层混淆（下面「编码是怎么写的」末尾有说明）；
只想要明文头做往返测试就加 `--plain`。`decode` 两种形态都收。

## ⚠ 两层形态：Form A 和 Form B

GARbro 从 `chip.cpz` 解出来的是 **Form B**（头部明文，本工具 `read_meta`/`decode` 直接吃）。
但**游戏要的是 Form A** —— 头部第 8~0x33 字节被一层浅混淆盖住（算法见 `encrypt_pb3`，
就是 GARbro `ArcCPZ.DecryptPb3` 的逆）。

原因是引擎读**任何** pb3 都会先跑一次那层解混淆：喂 Form B 进去，它会把宽高字段
一起搅烂，然后建纹理时整数除零，黑屏闪退（实测 `0xC0000094`，出错点 `0x42FFA8` 的
`idiv ebx`）。所以 `encode` 默认输出 Form A，`decode` 两种都能认。

> 走 `chip.cpz` 那条老路时这层是封包解密顺带做的，看不出来；只有把封包换成散装目录
> （`data\pack\chip\`）时才会暴露。

## 编码是怎么写的

`encode` 是 `decode` 的严格逆过程，三件事：

1. **逐 16×16 块扫每个通道**。整块同色的走「常量色流」（256 字节压成 1 字节，
   透明区和纯色区靠这个）；否则像素按**块内顺序**进平面。
   ⚠ 平面不是行优先 —— 宽高不是 16 的倍数时两者不同。
2. **平面用 LZSS 压**：哈希链贪心匹配，长度 3–34、距离 ≤2047。注意解码端
   `frame_offset` 从 `0x7DE` 起步、回引里存的是**环形下标**而不是「往前多少」，
   所以 offset = `(0x7DE + 匹配起点) & 0x7FF`。
3. **两张表拼装**：`data1` 放各通道的块记录 + 块位图 + 常量色 + LZSS **位流**；
   `data2` 放 LZSS **数据流**。两处表头的 DWORD 是各通道块大小。

自检：`0x34 + 4×通道数 + Σ(size1) == data2 偏移`，
`data2 + 4×通道数 + Σ(size2) == 文件长度`。

**实测**（原图 → 编码）：`ci01a` 1.03x、`dialog_chip` 1.11x、`title_chip` **0.90x**
（比原文件还小）。三个都做到**逐像素往返一致**（含 32bpp 的 alpha）。
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

SIG = b"PB3B"
FRAME_SIZE = 0x800


# ────────────── pb3 自己的那层头部混淆 ──────────────
#
# ⚠ 这是 2026-10-06 才搞明白的关键一层，之前漏了会直接让游戏崩。
#
# 引擎（和 GARbro）读**任何** pb3 时都会先跑一遍这个（GARbro 的
# `ArcCPZ.DecryptPb3`）。它只动头部**第 8 ~ 0x33 字节** —— 正好是
# SubType / Type / 宽 / 高 / bpp / data1 / data2 这些字段，密钥取自文件末尾两个字节。
#
# 所以：
#   · GARbro 从 chip.cpz 解出来的是**已经解过这一层**的成品（Form B）
#   · 塞进 data\pack\chip\ 的必须是**没过这一层**的形态（Form A）= encrypt_pb3(Form B)
#
# 喂成品（Form B）进去，引擎会再解一次，把宽高搅成乱值 → 建纹理时整数除零，
# 黑屏闪退（实测 0xC0000094，出错点 0x42FFA8 的 `idiv ebx`）。
#
# 脚本那边不需要这步：`.ps3` 用 PS3_Cryptor 编出来的形态**本来就是**引擎期望的那层。
def decrypt_pb3(d: bytearray) -> None:
    """Form A（引擎形态）→ Form B（明文头），就地修改"""
    k1, k2 = d[-3], d[-2]
    src = len(d) - 0x2F
    for i in range(8, 0x34, 2):
        d[i] = ((d[i] ^ k1) - d[src]) & 0xFF
        d[i + 1] = ((d[i + 1] ^ k2) - d[src + 1]) & 0xFF
        src += 2


def encrypt_pb3(d: bytearray) -> None:
    """Form B（明文头）→ Form A（引擎形态），就地修改。decrypt_pb3 的逆运算。"""
    k1, k2 = d[-3], d[-2]
    src = len(d) - 0x2F
    for i in range(8, 0x34, 2):
        d[i] = ((d[i] + d[src]) ^ k1) & 0xFF
        d[i + 1] = ((d[i + 1] + d[src + 1]) ^ k2) & 0xFF
        src += 2


def looks_plain(d: bytes) -> bool:
    """头部看着像没混淆过的 Form B 吗（用来判断手里的文件是哪一层）

    混淆只动 [8, 0x34)，所以拿它盖住的几个字段去卡：机型上是
    type ∈ {1,3,5}、宽高在合理区间、bpp ∈ {8,16,24,32}；
    撞上 Form A 时这些字段是乱的，基本不会同时成立。
    """
    if len(d) < 0x40 or d[:4] != SIG:
        return False
    m = read_meta(d)
    return m["type"] in (1, 3, 5) and 0 < m["width"] <= 8192 \
        and 0 < m["height"] <= 8192 and m["bpp"] in (8, 16, 24, 32)


# ─────────────────────────── LZSS ───────────────────────────

def lzss_unpack(src: bytes, bit_src: int, data_src: int,
                out_size: int) -> bytes:
    """GARbro `PbReaderBase.LzssUnpack` 的直译。

    环形字典 0x800 字节，起始游标在 0x7DE，重置时前 0x7DE 清零。
    一位控制：1 = 回引（2 字节：低 5 位是长度-3，高位是偏移），0 = 字面量。
    """
    out = bytearray(out_size)
    frame = bytearray(FRAME_SIZE)          # 前 0x7DE 本来就是 0

    dst = 0
    bit_mask = 0x80
    frame_offset = 0x7DE
    while dst < out_size:
        if bit_mask == 0:
            bit_mask = 0x80
            bit_src += 1
        if src[bit_src] & bit_mask:
            v = src[data_src] | (src[data_src + 1] << 8)
            data_src += 2
            count = (v & 0x1F) + 3
            offset = v >> 5
            for i in range(count):
                if dst >= out_size:
                    break
                b = frame[(i + offset) & 0x7FF]
                out[dst] = b
                dst += 1
                frame[frame_offset] = b
                frame_offset = (frame_offset + 1) & 0x7FF
        else:
            b = src[data_src]
            data_src += 1
            out[dst] = b
            dst += 1
            frame[frame_offset] = b
            frame_offset = (frame_offset + 1) & 0x7FF
        bit_mask >>= 1
    return bytes(out)


# ─────────────────────────── 解码 ───────────────────────────

def read_meta(d: bytes) -> dict:
    return {
        "input_size": struct.unpack_from("<i", d, 4)[0],
        "subtype":    struct.unpack_from("<i", d, 0x18)[0],
        "type":       struct.unpack_from("<H", d, 0x1C)[0],
        "width":      struct.unpack_from("<H", d, 0x1E)[0],
        "height":     struct.unpack_from("<H", d, 0x20)[0],
        "bpp":        struct.unpack_from("<H", d, 0x22)[0],
        "data1":      struct.unpack_from("<i", d, 0x2C)[0],
        "data2":      struct.unpack_from("<i", d, 0x30)[0],
    }


def _u32(d: bytes, off: int) -> int:
    return struct.unpack_from("<I", d, off)[0]


def unpack_v1(d: bytes, m: dict) -> bytearray:
    """`Pb3Reader.UnpackV1` 的直译。输出是 BGRA，stride = 4*width。"""
    width, height, bpp = m["width"], m["height"], m["bpp"]
    data1, data2 = m["data1"], m["data2"]

    channels = bpp // 8
    stride = 4 * width
    out = bytearray(stride * height)

    x_blocks = (width + 15) // 16
    y_blocks = (height + 15) // 16
    plane_size = width * height

    for channel in range(channels):
        # 通道表：4*通道数 字节的表头，然后每通道一项
        off1 = 4 * channels + sum(_u32(d, data1 + 4 * i) for i in range(channel))
        v21 = data1 + off1
        bit_src = v21 + 12 + _u32(d, v21) + _u32(d, v21 + 4)
        channel_size = _u32(d, v21 + 8)

        off2 = 4 * channels + sum(_u32(d, data2 + 4 * i) for i in range(channel))
        data_src = data2 + off2

        plane = lzss_unpack(d, bit_src, data_src, channel_size)

        if x_blocks == 0 or y_blocks == 0:
            continue

        # 块铺开
        plane_src = 0
        bsrc = v21 + 12                     # 块位图流
        bit_mask = 128
        dsrc = bsrc + _u32(d, v21)          # 常量色流
        v68 = 16
        for y in range(y_blocks):
            row = 16 * y
            v66 = 16
            dst_origin = stride * row + channel
            for _x in range(x_blocks):
                dst = dst_origin
                block_w = 16 if v66 <= width else width - 16 * _x
                block_h = 16 if v68 <= height else height - row
                if bit_mask == 0:
                    bsrc += 1
                    bit_mask = 128
                if bit_mask & d[bsrc]:
                    b = d[dsrc]
                    dsrc += 1
                    for _j in range(block_h):
                        p = dst
                        for _i in range(block_w):
                            out[p] = b
                            p += 4
                        dst += stride
                else:
                    for _j in range(block_h):
                        p = dst
                        for _i in range(block_w):
                            out[p] = plane[plane_src]
                            plane_src += 1
                            p += 4
                        dst += stride
                bit_mask >>= 1
                v66 += 16
                dst_origin += 64
            v68 += 16
    return out


def decode(d: bytes) -> tuple[int, int, bytes]:
    """pb3 字节 → (width, height, RGBA bytes)。"""
    m = read_meta(d)
    if d[:4] != SIG:
        raise ValueError("不是 PB3B 文件")
    if m["type"] != 1:
        raise NotImplementedError(f"只实现了 Type=1，这个是 Type={m['type']}")
    if m["subtype"] != 0x10:
        raise NotImplementedError(f"Type=1 只支持 SubType=0x10，这个是 {m['subtype']:#x}")

    bgra = unpack_v1(d, m)
    w, h = m["width"], m["height"]
    rgba = bytearray(w * h * 4)
    for i in range(w * h):
        rgba[i * 4 + 0] = bgra[i * 4 + 2]      # R ← B 通道位置
        rgba[i * 4 + 1] = bgra[i * 4 + 1]      # G
        rgba[i * 4 + 2] = bgra[i * 4 + 0]      # B
        # 24bpp 时第 4 个通道是垃圾（GARbro 那边也不算 alpha），24bpp 一律不透明
        rgba[i * 4 + 3] = bgra[i * 4 + 3] if m["bpp"] == 32 else 255
    return w, h, bytes(rgba)


# ─────────────────────────── 编码 ───────────────────────────
#
# 布局（从 ci01a.pb3 实测反推，和 GARbro 的解码器完全对得上）：
#
#   PB3 头 (0x34 字节)
#   data1 @ 0x2C:
#     u32 各通道 data1 块大小 × 通道数
#     每通道一个块:
#       u32 a         块位图流长度（每 16x16 块一位，MSB 优先）
#       u32 b         常量色流长度
#       u32 plane_len 平面长度（LZSS 输出字节数）
#       a 字节        块位图
#       b 字节        常量色
#       其余          **LZSS 的位流**（1 位 = 回引，0 位 = 字面量）
#   data2 @ 0x30:
#     u32 各通道 data2 块大小 × 通道数
#     每通道 size2 字节：**LZSS 的数据流**（字面量 1 字节 / 回引 2 字节）
#
# 自检：0x34 + 4*通道数 + Σ(size1) == data2 偏移；data2 + 4*通道数 + Σ(size2) == 文件长度。
#
# 编码器只用「块全部来自平面」这一种情形（块位图全 0），常量色流长度 0 ——
# 这是最直白的一条路，解码器那边走 else 分支，严格正确。

def channel_streams(pixels: bytes, w: int, h: int, channel: int):
    """逐 16x16 块扫一个通道 → (块位图, 常量色流, 平面)。

    解码端两种块：
      · 位图该位 = 1 → 整块同一个值，从常量色流读 **1 个字节**（256 字节压成 1 字节）
      · 位图该位 = 0 → 块内像素按顺序从平面取

    ⚠ 平面是「逐块、块内逐行」的顺序，**不是行优先** —— 宽高不是 16 的倍数时
    两者不一样。而且常量块**不占平面**，所以平面长度 = 非常量块的像素总数，
    正好就是记录里那个 plane_len。
    """
    bits, const, plane = [], bytearray(), bytearray()
    for by in range((h + 15) // 16):
        row = 16 * by
        bh = 16 if row + 16 <= h else h - row
        for bx in range((w + 15) // 16):
            col = 16 * bx
            bw = 16 if col + 16 <= w else w - col
            vals = bytearray()
            for j in range(bh):
                base = ((row + j) * w + col) * 4 + channel
                for i in range(bw):
                    vals.append(pixels[base + 4 * i])
            first = vals[0]
            if all(v == first for v in vals):
                bits.append(1)
                const.append(first)
            else:
                bits.append(0)
                plane += vals

    mask = bytearray((len(bits) + 7) // 8)
    for k, b in enumerate(bits):
        if b:
            mask[k // 8] |= 0x80 >> (k % 8)       # MSB 优先，和解码端一致
    return bytes(mask), bytes(const), bytes(plane)


def lzss_compress(plane: bytes, chain: int = 8) -> tuple[bytes, bytes]:
    """把平面压成 LZSS。返回 (位流, 数据流)。

    解码端是个 0x800 的环形字典，`frame_offset` 从 0x7DE 起步、每写一字节 +1，
    回引里存的 offset 是**环形下标**而不是「往前多少」。所以：
        输出位置 p 的字节 → 环下标 (0x7DE + p) & 0x7FF
    要复制从输出位置 j 开始的 L 个字节，就填 offset = (0x7DE + j) & 0x7FF、count = L。
    这样也天然避开了环里 0x7DE..0x7FF 那 34 个「复位时没清零」的字节 ——
    因为我们只会引用**本通道已经写过的**位置。
    """
    n = len(plane)
    bits, data = bytearray(), bytearray()
    bitbuf = bitcnt = 0

    def push_bit(b: int) -> None:
        nonlocal bitbuf, bitcnt
        bitbuf = (bitbuf << 1) | b
        bitcnt += 1
        if bitcnt == 8:
            bits.append(bitbuf)
            bitbuf = bitcnt = 0

    head: dict[bytes, int] = {}
    prev = [-1] * n

    def insert(k: int) -> None:
        if k + 3 <= n:
            key = plane[k:k + 3]
            prev[k] = head.get(key, -1)
            head[key] = k

    i = 0
    while i < n:
        best_len, best_pos = 0, -1
        if i + 3 <= n:
            j = head.get(plane[i:i + 3], -1)
            depth = 0
            maxl = min(34, n - i)
            while j >= 0 and depth < chain:
                if i - j > 2047:
                    break                       # 链是按位置从新到旧排的
                l = 3
                while l < maxl and plane[j + l] == plane[i + l]:
                    l += 1
                if l > best_len:
                    best_len, best_pos = l, j
                    if l == maxl:
                        break
                j = prev[j]
                depth += 1

        if best_len >= 3:
            push_bit(1)
            v = (((0x7DE + best_pos) & 0x7FF) << 5) | (best_len - 3)
            data += v.to_bytes(2, "little")
            for k in range(i, i + best_len):
                insert(k)
            i += best_len
        else:
            push_bit(0)
            data.append(plane[i])
            insert(i)
            i += 1

    if bitcnt:
        bits.append(bitbuf << (8 - bitcnt))
    return bytes(bits), bytes(data)


def encode_pb3(pixels: bytes, w: int, h: int, bpp: int, subtype: int = 0x10) -> bytes:
    """RGBA 像素 → pb3 字节。

    ⚠ **通道顺序的坑**：像素流里通道 0 是 **B**、1 是 G、2 是 R（解码端
    `unpack_v1` 出的是 BGRA，`decode()` 再把它转成 RGBA 给人看）。
    所以编码时要按 `2 - c` 去 RGBA 里取，**不能直接拿通道号当偏移** ——
    写反了图能正常解出来、看着也"对"，但游戏里红蓝对调（整屏发蓝）。
    这个 bug 被「自己编、自己解」的往返测试盖住了（两边同时反，往返照样一致）。

    alpha（32bpp 的通道 3）在两种顺序里都在第 4 字节，不用换。
    """
    channels = bpp // 8

    blk_sizes, data_sizes, blocks, datas = [], [], [], []
    for c in range(channels):
        off = 3 if c == 3 else 2 - c          # 流通道 -> RGBA 内的字节偏移
        mask, const, plane = channel_streams(pixels, w, h, off)
        bit_stream, data_stream = lzss_compress(plane)
        blk = (struct.pack("<III", len(mask), len(const), len(plane))
               + mask + const + bit_stream)
        blocks.append(blk)
        datas.append(data_stream)
        blk_sizes.append(len(blk))
        data_sizes.append(len(data_stream))

    data1 = struct.pack(f"<{channels}I", *blk_sizes) + b"".join(blocks)
    data2 = struct.pack(f"<{channels}I", *data_sizes) + b"".join(datas)

    head = bytearray(0x34)
    head[0:4] = SIG
    struct.pack_into("<I", head, 0x08, 1)
    struct.pack_into("<I", head, 0x18, subtype)
    struct.pack_into("<H", head, 0x1C, 1)        # Type
    struct.pack_into("<H", head, 0x1E, w)
    struct.pack_into("<H", head, 0x20, h)
    struct.pack_into("<H", head, 0x22, bpp)
    struct.pack_into("<I", head, 0x2C, 0x34)                  # data1 偏移
    struct.pack_into("<I", head, 0x30, 0x34 + len(data1))     # data2 偏移

    out = bytes(head) + data1 + data2
    # input_size = 整个文件长度（解码端拿它给读缓冲定长，必须 >= 用到的最大偏移）
    return out[:4] + struct.pack("<I", len(out)) + out[8:]


# ─────────────────────────── PNG ───────────────────────────

def write_png(path: Path, w: int, h: int, rgba: bytes) -> None:
    """自己拼 PNG，省得依赖 Pillow。"""
    raw = bytearray()
    for y in range(h):
        raw.append(0)                                   # filter type 0
        raw += rgba[y * w * 4:(y + 1) * w * 4]

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + \
               struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


# ─────────────────────────── CLI ───────────────────────────

def cmd_encode(args) -> int:
    """PNG → pb3。

    必须给一份**原始 pb3 目录**当模板：尺寸和 bpp 照它来（游戏是按原样读的），
    PNG 只负责换像素。这样也顺手挡住「图存错尺寸」这类事故。
    """
    try:
        from PIL import Image
    except ImportError:
        print("需要 Pillow：uv run --with pillow python tools/pb3.py encode ...",
              file=sys.stderr)
        return 1

    src, tpl_dir, out = Path(args.src), Path(args.tpl), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pngs = sorted(src.glob("*.png")) if src.is_dir() else [src]
    ok = 0
    for png in pngs:
        tpl = tpl_dir / (png.stem + ".pb3")
        if not tpl.is_file():
            print(f"  ✗ {png.name}: 找不到模板 {tpl.name}")
            continue
        m = read_meta(tpl.read_bytes())
        if m["type"] != 1 or m["subtype"] != 0x10:
            print(f"  ✗ {png.name}: 模板是 Type={m['type']} Sub={m['subtype']:#x}，暂不支持")
            continue
        im = Image.open(png).convert("RGBA")
        if im.size != (m["width"], m["height"]):
            print(f"  ✗ {png.name}: 尺寸 {im.size} 与模板 "
                  f"({m['width']}, {m['height']}) 不符 —— 改图时别动画布尺寸")
            continue
        blob = bytearray(encode_pb3(im.tobytes(), m["width"], m["height"], m["bpp"]))
        if not args.plain:
            encrypt_pb3(blob)          # 转成引擎直接吃的形态，见文件开头说明
        (out / (png.stem + ".pb3")).write_bytes(blob)
        ratio = len(blob) / tpl.stat().st_size
        print(f"  ✓ {png.stem+'.pb3':<24} {m['width']}x{m['height']} {m['bpp']}bpp  "
              f"{len(blob):>9,} 字节（原 {tpl.stat().st_size:,}，{ratio:.1f}x）")
        ok += 1
    kind = "Form B（明文头，调试用）" if args.plain else "Form A（可直接塞回游戏）"
    print(f"\n编出 {ok} / {len(pngs)} 个 → {out}   [{kind}]")
    if not args.plain:
        print("  塞进 游戏目录\\data\\pack\\chip\\ 即可（路径表已指向该目录，见交接文档）")
    return 0 if ok == len(pngs) else 1


def cmd_info(args) -> int:
    for p in sorted(Path(args.src).glob("*.pb3"))[:args.limit]:
        d = p.read_bytes()
        m = read_meta(d)
        print(f"{p.name:<26} {m['width']:>5} x {m['height']:<5} {m['bpp']}bpp  "
              f"Type={m['type']} Sub={m['subtype']:#x}  {len(d):>9,} 字节")
    return 0


def cmd_decode(args) -> int:
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("*.pb3")) if src.is_dir() else [src]
    ok = 0
    for p in files:
        try:
            raw = bytearray(p.read_bytes())
            if not looks_plain(bytes(raw)):
                decrypt_pb3(raw)        # 拿到的是 Form A 就先剥掉那层，能直接解
            w, h, rgba = decode(bytes(raw))
        except Exception as exc:                        # noqa: BLE001
            print(f"  ✗ {p.name}: {exc}")
            continue
        write_png(out / (p.stem + ".png"), w, h, rgba)
        ok += 1
    print(f"解出 {ok} / {len(files)} 个 → {out}")
    return 0 if ok == len(files) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode", help="pb3 → png")
    d.add_argument("--in", dest="src", required=True, help="pb3 文件或目录")
    d.add_argument("--out", dest="out", required=True, help="PNG 输出目录")
    e = sub.add_parser("encode", help="png → pb3（改完塞回游戏用）")
    e.add_argument("--in", dest="src", required=True, help="PNG 文件或目录")
    e.add_argument("--tpl", required=True, help="原始 pb3 目录（当尺寸/bpp 模板）")
    e.add_argument("--out", required=True, help="pb3 输出目录")
    e.add_argument("--plain", action="store_true",
                   help="不套 Form A 那层混淆，输出明文头的 Form B（只做往返测试时用）")
    i = sub.add_parser("info", help="只打印尺寸/类型，不解码")
    i.add_argument("--in", dest="src", required=True)
    i.add_argument("--limit", type=int, default=20)
    a = ap.parse_args()
    if a.cmd == "decode":
        return cmd_decode(a)
    if a.cmd == "encode":
        return cmd_encode(a)
    return cmd_info(a)


if __name__ == "__main__":
    sys.exit(main())
