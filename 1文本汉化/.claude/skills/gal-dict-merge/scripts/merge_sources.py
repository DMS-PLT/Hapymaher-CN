# -*- coding: utf-8 -*-
"""多来源字典合并分析。

用法:
    python merge_sources.py --base 基准字典.txt 来源1.txt 来源2.txt \
        [--corpus _dictwork/corpus.txt] [--out 报告.txt]

输出四块:
    A 概览     各来源条目数 / org 并集 / 两两重叠
    B 待补     基准里没有、其他来源有的 org —— 标注是「正文词」还是「仅 name 字段」
    C 冲突     同一个 org 在不同来源里 rep 不一致 —— 需要人工拍板
    D 来源问题 某来源内部 org 重复 / rep 为空

「仅 name 字段」的条目不要塞进 GPT 字典，交给 name_table.py 去填姓名表：
GalTransl++ 用 NameTable.toml，喵喵 / GalTransl 8.4.2 用 name替换表.csv。
（GPP 的 gptDict 虽然也匹配 name，但泛称标签会同时污染正文提示词。）
"""
import argparse
import collections
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HEAD = re.compile(r'^\[[^\]#]*#\d+\] ([^|]*)\| (.*)$')


def load(path):
    """按内容判断 TOML / TSV，返回 [(org, rep, note), ...]。"""
    head = io.open(path, encoding='utf-8-sig').read(4096)
    if re.search(r'^\s*gptDict\s*=', head, re.M) or '{org' in head:
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
        return [(x['org'], x.get('rep', ''), x.get('note', '')) for x in d[key]]
    rows = []
    for line in io.open(path, encoding='utf-8-sig'):
        if line.startswith('#') or not line.strip():
            continue
        c = line.rstrip('\r\n').replace('    ', '\t').split('\t')
        if len(c) < 2 or not c[0] or c[0] in ('日文原词',) or c[0].startswith('【'):
            continue
        rows.append((c[0], c[1], c[2] if len(c) > 2 else ''))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sources', nargs='+', help='除基准外的来源字典')
    ap.add_argument('--base', required=True, help='基准字典（要整合进的那份）')
    ap.add_argument('--corpus', default=None)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    paths = [os.path.abspath(p) for p in [a.base] + a.sources]
    # 同名文件（很常见：各工具都叫 项目GPT字典-生成.txt）用「父目录/文件名」区分
    names, seen = [], collections.Counter(os.path.basename(p) for p in paths)
    for p in paths:
        b = os.path.basename(p)
        label = b if seen[b] == 1 else '%s/%s' % (os.path.basename(os.path.dirname(p)), b)
        while label in names:
            label = '_' + label
        names.append(label)
    data = {}
    for p, n in zip(paths, names):
        if not os.path.isfile(p):
            sys.exit('找不到: %s' % p)
        data[n] = load(p)

    buf = io.StringIO()

    def w(s=''):
        buf.write(s + '\n')

    # ---- A 概览 ----
    w('=' * 78)
    w('多来源字典合并分析')
    w('=' * 78)
    for n, rows in data.items():
        w('  %-28s %4d 条' % (n, len(rows)))
    sets = {n: {r[0] for r in rows} for n, rows in data.items()}
    union = set().union(*sets.values())
    w('')
    w('  org 并集: %d' % len(union))
    w('  两两重叠:')
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            w('    %-24s ∩ %-24s %d' % (n1, n2, len(sets[n1] & sets[n2])))
    w('')

    # ---- 语料：区分「正文词」和「仅 name 字段」----
    body_hit, name_hit = {}, {}
    if a.corpus and os.path.isfile(a.corpus):
        parsed = []
        for line in io.open(a.corpus, encoding='utf-8'):
            m = HEAD.match(line.rstrip('\n'))
            if m:
                parsed.append((m.group(1), m.group(2)))
        targets = union
        for t in targets:
            body_hit[t] = sum(1 for nm, msg in parsed if t in msg)
            name_hit[t] = sum(1 for nm, msg in parsed if t in nm)

    def classify(o):
        if not body_hit:
            return '（未给语料，无法判断）'
        b, n = body_hit.get(o, 0), name_hit.get(o, 0)
        if b and n:
            return '正文 %d 行 / name %d 次' % (b, n)
        if b:
            return '正文 %d 行' % b
        if n:
            return '仅 name 字段 %d 次 ← 建议放进姓名表（GPP NameTable.toml / CSV）' % n
        return '语料 0 命中 ← 考虑不收'

    base_set = sets[names[0]]

    # ---- B 待补 ----
    w('-' * 78)
    w('【B】基准「%s」缺失、其他来源有的 org —— 新增候选' % names[0])
    w('-' * 78)
    cand = collections.OrderedDict()
    for n in names[1:]:
        for o, r, note in data[n]:
            if o in base_set:
                continue
            cand.setdefault(o, []).append((n, r))
    if not cand:
        w('  （无）')
    for o, srcs in cand.items():
        reps = ' / '.join('%s:%s' % (n, r) for n, r in srcs)
        w('  %-26s %-38s %s' % (o, reps[:38], classify(o)))
    w('')

    # ---- C 冲突 ----
    w('-' * 78)
    w('【C】同 org 不同 rep 的冲突 —— 需要人工拍板')
    w('-' * 78)
    repmap = collections.defaultdict(dict)
    for n, rows in data.items():
        for o, r, _ in rows:
            repmap[o].setdefault(r, []).append(n)
    nconf = 0
    for o, reps in repmap.items():
        if len(reps) > 1:
            nconf += 1
            w('  %s   （%s）' % (o, classify(o)))
            for r, ns in reps.items():
                w('      %-22s ← %s' % (r, ', '.join(ns)))
    if not nconf:
        w('  （无）')
    w('')

    # ---- D 来源自身问题 ----
    w('-' * 78)
    w('【D】来源自身的问题')
    w('-' * 78)
    for n, rows in data.items():
        orgs = [r[0] for r in rows]
        dup = [o for o, c in collections.Counter(orgs).items() if c > 1]
        empty = [o for o, r, _ in rows if not r]
        if dup or empty:
            w('  %s: 重复 %d，空 rep %d' % (n, len(dup), len(empty)))
            if dup:
                w('      重复: %s' % dup[:10])
            if empty:
                w('      空 rep: %s' % empty[:10])
        else:
            w('  %s: 无' % n)
    w('')
    w('=' * 78)

    text = buf.getvalue()
    if a.out:
        io.open(a.out, 'w', encoding='utf-8').write(text)
        print('报告已写出 → %s' % a.out)
        print('（%d 个来源，org 并集 %d，冲突 %d 组，新增候选 %d 条）'
              % (len(paths), len(union), nconf, len(cand)))
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
