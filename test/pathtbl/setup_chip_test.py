#!/usr/bin/env python3
"""界面图散装化测试：把 chip.cpz 路径改成目录，铺上全部 199 个 pb3。

背景：start.ps3 的路径表里图片走的是
    0x13E1  data\\pack\\chip.cpz
    0x1408  data\\pack\\chip.cpz   （同一路径出现两次）
和脚本一模一样的形式。既然 script.cpz -> script\\ 那条路已经验证可行，
这里照搬同样的改法。

用法：
    python setup_chip_test.py prepare    # 铺文件 + 改 start.ps3
    python setup_chip_test.py revert     # 只把 start.ps3 改回 chip.cpz
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\DMS\Desktop\Hapymaher")
CRYPTOR = ROOT / "tools" / "RxCMVS" / "PS3_Cryptor.exe"
GAME = ROOT / "ハピメア フルHD版"
START = GAME / "data" / "pack" / "start.ps3"
CHIP_SRC = ROOT / "UI界面" / "chip"
CHIP_DST = GAME / "data" / "pack" / "chip"
TMP = Path(__file__).parent

OLD = b"data\\pack\\chip.cpz"
NEW = b"data\\pack\\chip\\"


def decode_start(msg: str) -> bytearray:
    plain = TMP / "start_chip.plain"
    p = subprocess.run([str(CRYPTOR), "-mode", "decode", "-ps3", str(START), "-save", str(plain)],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"解密 start.ps3 失败: {p.stderr.decode('gbk', 'replace')}")
    print(f"  [{msg}] 解出 {plain.stat().st_size} 字节")
    return bytearray(plain.read_bytes())


def encode_start(d: bytearray) -> None:
    plain = TMP / "start_chip.plain"
    plain.write_bytes(bytes(d))
    p = subprocess.run([str(CRYPTOR), "-mode", "encode", "-ps3", str(plain), "-save", str(START)],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"加密 start.ps3 失败: {p.stderr.decode('gbk', 'replace')}")


def swap(d: bytearray, old: bytes, new: bytes, label: str) -> int:
    """把 old 换成 new，用 NUL 补足长度（这是连续字符串表，长度必须不变）"""
    assert len(new) <= len(old), f"{label}: 新串比旧串长，会撑坏字符串表"
    pad = b"\x00" * (len(old) - len(new))
    n = 0
    i = d.find(old)
    while i >= 0:
        d[i:i + len(old)] = new + pad
        print(f"    {label}: 0x{i:04X}  {old.decode()} -> {new.decode()}"
              f"  (+{len(old) - len(new)} NUL)")
        n += 1
        i = d.find(old, i + len(old))
    return n


def prepare() -> int:
    print("[1/3] 铺 chip 目录")
    CHIP_DST.mkdir(parents=True, exist_ok=True)
    srcs = sorted(CHIP_SRC.glob("*.pb3"))
    if not srcs:
        raise SystemExit(f"{CHIP_SRC} 里没有 pb3")
    total = 0
    for f in srcs:
        dst = CHIP_DST / f.name
        shutil.copy2(f, dst)
        total += dst.stat().st_size
    print(f"    拷入 {len(srcs)} 个文件，共 {total/1048576:.1f} MB -> {CHIP_DST}")

    print("[2/3] 重新生成带洋红标记的 title_chip.pb3")
    sys.path.insert(0, str(ROOT / "tools"))
    import pb3  # noqa: E402

    raw = (CHIP_SRC / "title_chip.pb3").read_bytes()
    meta = pb3.read_meta(raw)
    w, h, rgba = pb3.decode(raw)
    print(f"    解码 {w}x{h}  bpp={meta['bpp']} subtype={meta['subtype']:#x}")

    # 画一条横贯的洋红条，任何缩放都看得见
    bar = bytearray(rgba)
    y0, y1 = h // 2 - 90, h // 2 + 90
    for y in range(y0, y1):
        for x in range(w):
            o = (y * w + x) * 4
            bar[o:o + 4] = b"\xff\x00\xff\xff"

    enc = pb3.encode_pb3(bytes(bar), w, h, meta["bpp"], subtype=meta["subtype"])
    (CHIP_DST / "title_chip.pb3").write_bytes(enc)
    print(f"    编码 {len(enc)} 字节 (原始 {len(raw)})  -> 覆盖 {CHIP_DST/'title_chip.pb3'}")

    print("[3/3] 改 start.ps3 路径表")
    d = decode_start("prepare")
    if d.find(NEW) >= 0 and d.find(OLD) < 0:
        print("    已经是 chip\\ 形式，跳过")
    else:
        n = swap(d, OLD, NEW, "chip 路径")
        if n == 0:
            raise SystemExit("    找不到 data\\pack\\chip.cpz，路径表格式变了？")
        encode_start(d)
    print("    已写入", START)
    return 0


def pathonly() -> int:
    """只把 start.ps3 的 chip 路径改成目录形式，不动文件（文件已在磁盘上）"""
    d = decode_start("pathonly")
    if d.find(NEW) >= 0 and d.find(OLD) < 0:
        print("    已经是 chip\\ 形式了")
        return 0
    n = swap(d, OLD, NEW, "chip 路径")
    if n == 0:
        raise SystemExit("    找不到 data\\pack\\chip.cpz")
    encode_start(d)
    print("    已写入", START)
    return 0


def revert() -> int:
    """从原始备份重建 start.ps3（script 目录 + 标题补丁，chip 保持 chip.cpz）

    注意：不能在当前文件上原地改回去 —— NEW 比 OLD 短 3 字节，
    按 NEW 的长度去写 OLD 会**插入** 3 字节，把后面整个字符串表的偏移撑歪。
    所以直接从 test/backup/start.ps3.orig 重建。
    """
    orig = ROOT / "test" / "backup" / "start.ps3.orig"
    plain = TMP / "start_revert.plain"
    p = subprocess.run([str(CRYPTOR), "-mode", "decode", "-ps3", str(orig), "-save", str(plain)],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"解密备份失败: {p.stderr.decode('gbk', 'replace')}")
    d = bytearray(plain.read_bytes())
    n = swap(d, b"data\\pack\\script.cpz", b"data\\pack\\script\\", "script 路径")
    if n == 0:
        raise SystemExit("备份里找不到 script.cpz，备份不对？")
    # 标题：SJIS -> GBK 等长（和 build_encrypted.py 同一处理）
    for t in ("ハピメア RE.ver", "ハピメアFD RE.ver"):
        o = t.encode("cp932")
        j = d.find(o)
        if j >= 0 and d.find(o, j + 1) < 0:
            d[j:j + len(o)] = t.encode("gbk")
            print(f"    标题: 0x{j:04X}  SJIS -> GBK 等长")
    plain.write_bytes(bytes(d))
    p = subprocess.run([str(CRYPTOR), "-mode", "encode", "-ps3", str(plain), "-save", str(START)],
                       capture_output=True)
    if p.returncode != 0:
        raise SystemExit(f"加密失败: {p.stderr.decode('gbk', 'replace')}")
    print(f"    已从备份重建并写入 {START}")
    print("    [i] data/pack/chip/ 目录还在磁盘上，但它已不被引用，不影响游戏")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "prepare"
    sys.exit({"prepare": prepare, "revert": revert, "pathonly": pathonly}[cmd]())
