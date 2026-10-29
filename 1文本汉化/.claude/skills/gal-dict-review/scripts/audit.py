# -*- coding: utf-8 -*-
"""风险分层：把字典条目分成 P0/P1/P2，决定哪些必须逐条审。

用法:
    python audit.py --dict ProjGptDict.toml --corpus _dictwork/corpus.txt \
        --out risk_entries.tsv

    python audit.py --dict ProjGptDict.toml --corpus _dictwork/corpus.txt \
        --characters characters.txt --coined coined.txt

判定:
    P0  必须逐条审：zero_hit / 主要角色 / 自造词
    P1  强烈建议审：name_only / body_heavy / short_word / 敬称 / 撞名
    P2  抽样审：低频 / 派生不一致 / 同 rep 多 org

输出 TSV 列:
    priority / org / rep / body_hits / name_hits / flags / reason
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

HEAD = re.compile(r'^\[([^\]#]*)#(\d+)\] ([^|]*)\| (.*)$')
DEFAULT_SUFFIXES = ('さん', 'ちゃん', 'くん', '君', '様', '先輩', '先生', '殿', 'お嬢様')


def load_dict(path):
    head = io.open(path, encoding='utf-8-sig').read(4096)
    if re.search(r'^\s*gptDict\s*=', head, re.M) or '{org' in head:
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
        return [(x['org'], x.get('rep', '')) for x in d[key]]
    rows = []
    for line in io.open(path, encoding='utf-8-sig'):
        if line.startswith('#') or not line.strip():
            continue
        c = line.rstrip('\r\n').replace('    ', '\t').split('\t')
        if len(c) >= 2 and c[0] and c[0] != '日文原词':
            rows.append((c[0], c[1]))
    return rows


def load_corpus(path):
    rows = []
    for line in io.open(path, encoding='utf-8'):
        m = HEAD.match(line.rstrip('\n'))
        if m:
            rows.append((m.group(3), m.group(4)))
    return rows


def load_list(path):
    if not path or not os.path.isfile(path):
        return set()
    return {l.strip() for l in io.open(path, encoding='utf-8-sig')
            if l.strip() and not l.startswith('#')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dict', required=True)
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--out', default='risk_entries.tsv')
    ap.add_argument('--characters', default=None, help='主要角色名单，一行一个')
    ap.add_argument('--coined', default=None, help='作品自造词名单，一行一个')
    a = ap.parse_args()

    entries = load_dict(a.dict)
    corpus = load_corpus(a.corpus)
    characters = load_list(a.characters)
    coined = load_list(a.coined)

    body_hit = {o: sum(1 for _, msg in corpus if o in msg) for o, _ in entries}
    name_hit = {o: sum(1 for nm, _ in corpus if o in nm) for o, _ in entries}

    # 撞名
    byrep = collections.defaultdict(list)
    for o, r in entries:
        byrep[r].append(o)
    collision = {o for o, r in entries if len(byrep[r]) > 1}

    # 派生不一致
    deriv = set()
    for o, r in entries:
        for o2, r2 in entries:
            if o == o2 or o not in o2:
                continue
            if r and r not in r2:
                deriv.add(o)

    rows = []
    for o, r in entries:
        b, n = body_hit[o], name_hit[o]
        flags, reasons = [], []
        priority = None

        def add(p, flag, reason):
            nonlocal priority
            flags.append(flag)
            reasons.append(reason)
            order = {'P0': 0, 'P1': 1, 'P2': 2}
            if priority is None or order[p] < order[priority]:
                priority = p

        if b == 0 and n == 0:
            add('P0', 'zero_hit', '语料 0 命中，确认是否写法差异或假词条')
        if o in characters or n >= 100:
            add('P0', 'main_character', '主要角色/高频说话人，必须逐条核对')
        if o in coined:
            add('P0', 'coined', '作品自造词，必须逐条核对')
        if b == 0 and n > 0:
            add('P1', 'name_only', '只在 name 字段出现，建议移入姓名表')
        if b >= 100 and n < b / 10:
            add('P1', 'body_heavy', '正文高频、name 很少，检查是否污染提示词')
        if len(o) <= 2 and b >= 50 and not (o in characters or n >= 100):
            add('P1', 'short_word', '短词正文高频，检查子串污染')
        if any(o.endswith(s) for s in DEFAULT_SUFFIXES):
            add('P1', 'honorific', '敬称/称谓，检查译法是否跨条目一致')
        if o in collision:
            add('P2', 'same_rep', '与其他 org 共用同一 rep，确认是否同一人物')
        if o in deriv:
            add('P2', 'derived_inconsistent', '短词译文不是长词译文的子串')
        if b + n <= 2:
            add('P2', 'low_freq', '低频，抽样确认是否自造词')

        if priority is None:
            continue
        rows.append((priority, o, r, b, n, ','.join(flags), '；'.join(reasons)))

    order = {'P0': 0, 'P1': 1, 'P2': 2}
    rows.sort(key=lambda x: (order[x[0]], -(x[3] + x[4]), x[1]))

    with io.open(a.out, 'w', encoding='utf-8', newline='') as f:
        f.write('priority\torg\trep\tbody_hits\tname_hits\tflags\treason\n')
        for r in rows:
            f.write('\t'.join(str(x).replace('\t', ' ').replace('\n', ' ')
                              for x in r) + '\n')

    print('条目 %d，需审 %d → %s' % (len(entries), len(rows), a.out))
    for p in ('P0', 'P1', 'P2'):
        print('  %s: %d' % (p, sum(1 for r in rows if r[0] == p)))
    print('\nP0 条目:')
    for r in [x for x in rows if x[0] == 'P0'][:40]:
        print('  %-24s body %-5d name %-5d %s' % (r[1], r[3], r[4], r[5]))


if __name__ == '__main__':
    main()
