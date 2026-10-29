# -*- coding: utf-8 -*-
import json, os, sys, io, struct
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\DMS\Desktop\Hapymaher"

# 1) 含 ♪ / ・ 的条目数（raw 字段 = 真实条数）
for label, p in [("本体", BASE + r"\output\hapymaher"),
                 ("FD", BASE + r"\output\fragmentation-dream")]:
    e_m, e_dot, occ_m, occ_dot = 0, 0, 0, 0
    for fn in os.listdir(p):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(p, fn), encoding="utf-8-sig"))
        for it in d["Scenario"]:
            r = it["raw"]
            if "♪" in r:
                e_m += 1
                occ_m += r.count("♪")
            if "・" in r:
                e_dot += 1
                occ_dot += r.count("・")
    print(f"{label}: 含♪条目={e_m}(出现{occ_m}次)  含・条目={e_dot}(出现{occ_dot}次)")

# 2) raw 里含反斜杠的条目样例
print()
n = 0
for fn in sorted(os.listdir(BASE + r"\output\hapymaher")):
    if not fn.endswith(".json") or n >= 10:
        continue
    d = json.load(open(os.path.join(BASE, "output", "hapymaher", fn), encoding="utf-8-sig"))
    for it in d["Scenario"]:
        if "\\" in it["raw"] and n < 10:
            print(f"  {fn}: {it['raw'][:60]!r}")
            n += 1

# 3) start.ps3 头字段核对
h = open(BASE + r"\test\backup\start.ps3.orig", "rb").read(48)
u = struct.unpack("<12I", h)
print()
print("orig start.ps3 头字段:", " ".join(f"{x:08X}" for x in u))
print(f"  签名={h[:4]!r} 头大小={u[1]} 密钥={u[3]:#x} 文本数={u[4]} Code={u[5]:#x} Un={u[6]:#x} Text={u[7]:#x} 压缩后={u[10]} 解压后={u[11]}")

# 4) 引擎文本控制字符全谱（本体 raw 里所有 ASCII 标点出现频率，找潜在标记）
import collections
cnt = collections.Counter()
for fn in os.listdir(BASE + r"\output\hapymaher"):
    if not fn.endswith(".json"):
        continue
    d = json.load(open(os.path.join(BASE, "output", "hapymaher", fn), encoding="utf-8-sig"))
    for it in d["Scenario"]:
        for ch in it["raw"]:
            if ord(ch) < 0x80 and not ch.isalnum():
                cnt[ch] += 1
print()
print("本体 raw 中 ASCII 标点频率:", dict(cnt.most_common(25)))
