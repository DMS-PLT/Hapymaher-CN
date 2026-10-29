# -*- coding: utf-8 -*-
"""文本数据论断复核：
1) 条目总数（本体 158 文件 64,888 / 全部 282 文件 107,142）
2) 不可 GBK 编码的字符及次数（报告称仅 ♪ 982 次、・ 22 次）
3) 文本中出现的控制字符/引擎标记（评估 GBK 尾字节碰撞风险）
4) 0x41A421 的 RVA 形式引用扫描（补查）
"""
import json, os, sys, io, struct, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\DMS\Desktop\Hapymaher"

# ---- 0x41A421 RVA 引用补查 ----
data = open(BASE + r"\test\backup\cmvs32.exe.orig", "rb").read()
rva_pat = struct.pack("<I", 0x41A421 - 0x400000)
print(f"[0x41A421] RVA(0x1A421) 形式引用: {data.count(rva_pat)} 处")

# ---- JSON 统计 ----
def collect(d):
    """递归收集 JSON 里的字符串值，返回 (条目文本列表)"""
    texts = []
    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str):
            texts.append(o)
    walk(d)
    return texts

def stats(dirpath):
    files = [f for f in os.listdir(dirpath) if f.endswith(".json")]
    total_entries = 0
    bad_chars = collections.Counter()
    ctrl_chars = collections.Counter()
    field_names = collections.Counter()
    for fn in sorted(files):
        with open(os.path.join(dirpath, fn), encoding="utf-8-sig") as f:
            d = json.load(f)
        if isinstance(d, dict):
            field_names.update(d.keys())
        texts = collect(d)
        total_entries += len(texts)
        for t in texts:
            for ch in t:
                try:
                    ch.encode("gbk")
                except UnicodeEncodeError:
                    bad_chars[ch] += 1
                if ord(ch) < 0x20 and ch not in "\n\r\t":
                    ctrl_chars[ch] += 1
    return files, total_entries, bad_chars, ctrl_chars, field_names

for label, p in [("本体", BASE + r"\output\hapymaher"),
                 ("FD", BASE + r"\output\fragmentation-dream")]:
    files, n, bad, ctrl, fields = stats(p)
    print(f"\n[{label}] 文件数={len(files)} 条目数={n}")
    print(f"  顶层字段: {dict(fields)}")
    print(f"  不可GBK字符: {dict([(hex(ord(c)), f'{c} x{n}') for c, n in bad.most_common()])}")
    print(f"  控制字符: {dict([(hex(ord(c)), n) for c, n in ctrl.most_common()])}")

# ---- 抽样看一条完整条目结构 ----
with open(BASE + r"\output\hapymaher\autodemo.ps3.json", encoding="utf-8-sig") as f:
    d = json.load(f)
print("\n[条目样例] autodemo.ps3.json 前 2 条:")
sc = d["Scenario"]
items = sc if isinstance(sc, list) else list(sc.items())[:2]
for it in (items[:2] if isinstance(items, list) else items):
    print("  " + json.dumps(it, ensure_ascii=False)[:300])

# ---- 文本中的引擎标记字符统计（整个本体）----
marker = collections.Counter()
mdir = BASE + r"\output\hapymaher"
for fn in os.listdir(mdir):
    if not fn.endswith(".json"):
        continue
    with open(os.path.join(mdir, fn), encoding="utf-8-sig") as f:
        for t in collect(json.load(f)):
            for ch in t:
                if ch in "@\\/_^$#|~":
                    marker[ch] += 1
print(f"\n[标记字符出现次数(本体全部文本)] {dict(marker)}")

# ---- GBK 尾字节 0x5C 的字符清单（风险演示）----
print("\n[GBK 尾字节=0x5C 的常用字示例] (前 30 个):")
hits = []
for lead in range(0x81, 0xFF):
    b = bytes([lead, 0x5C])
    try:
        ch = b.decode("gbk")
        hits.append(ch)
    except Exception:
        pass
print(f"  共 {len(hits)} 个: {''.join(hits[:30])}")
