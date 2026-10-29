# -*- coding: utf-8 -*-
"""为字典里的每个 org 生成一张证据表。

用法:
    python evidence.py --dict ProjGptDict.toml --corpus _dictwork/corpus.txt \
        --out evidence.tsv

    python evidence.py --dict ProjGptDict.toml --corpus _dictwork/corpus.txt \
        --org 平坂,声,センパイ

输出 TSV 列:
    org / rep / note
    body_hits   正文命中行数
    name_hits   name 字段命中次数
    flags       zero_hit / name_only / body_heavy / short_word
    speakers    正文命中行里的说话人（top 5）
    samples     最多 N 条证据行：[文件#序号] 说话人| 正文
"""
import argparse
import collections
import csv
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

HEAD = re.compile(r'^\[([^\]#]*)#(\d+)\] ([^|]*)\| (.*)$')


def load_dict(path):
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
        if len(c) >= 2 and c[0] and c[0] != '日文原词':
            rows.append((c[0], c[1], c[2] if len(c) > 2 else ''))
    return rows


def load_corpus(path):
    rows = []
    for line in io.open(path, encoding='utf-8'):
        m = HEAD.match(line.rstrip('\n'))
        if m:
            rows.append((m.group(1), int(m.group(2)), m.group(3), m.group(4)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dict', required=True)
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--out', default='evidence.tsv')
    ap.add_argument('--samples', type=int, default=3)
    ap.add_argument('--org', default=None, help='只查这些 org，逗号分隔')
    a = ap.parse_args()

    entries = load_dict(a.dict)
    corpus = load_corpus(a.corpus)
    wanted = set(a.org.split(',')) if a.org else None

    rows = []
    for org, rep, note in entries:
        if wanted and org not in wanted:
            continue
        body = [(fn, idx, nm, msg) for fn, idx, nm, msg in corpus if org in msg]
        name = [(fn, idx, nm, msg) for fn, idx, nm, msg in corpus if org in nm]
        flags = []
        if not body and not name:
            flags.append('zero_hit')
        if not body and name:
            flags.append('name_only')
        if body and len(body) >= 100 and len(name) < len(body) / 10:
            flags.append('body_heavy')
        if len(org) <= 2 and len(body) >= 50:
            flags.append('short_word')
        speakers = collections.Counter(nm for _, _, nm, _ in body if nm)
        spk = ', '.join('%s(%d)' % (k, v) for k, v in speakers.most_common(5))
        samples = ' || '.join('[%s#%d] %s| %s' % (fn, idx, nm, msg.replace('\n', ' '))
                              for fn, idx, nm, msg in body[:a.samples])
        rows.append((org, rep, note, len(body), len(name),
                     ','.join(flags), spk, samples))

    with io.open(a.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['org', 'rep', 'note', 'body_hits', 'name_hits',
                    'flags', 'speakers', 'samples'])
        for r in rows:
            w.writerow(r)

    print('输出 %d 条 → %s' % (len(rows), a.out))
    print('  zero_hit   %d' % sum(1 for r in rows if 'zero_hit' in r[5]))
    print('  name_only  %d' % sum(1 for r in rows if 'name_only' in r[5]))
    print('  body_heavy %d' % sum(1 for r in rows if 'body_heavy' in r[5]))
    print('  short_word %d' % sum(1 for r in rows if 'short_word' in r[5]))


if __name__ == '__main__':
    main()
