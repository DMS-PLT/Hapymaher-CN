# -*- coding: utf-8 -*-
"""语料检索。所有字典核对结论都应基于这里的输出。

用法:
    python q.py つばさ 雀様              # 每个词：命中数 + 8 条样例
    python q.py @30 義妹                 # @N 控制样例条数
    python q.py -n 逆玉                  # 只打印命中次数（快速筛）
    python q.py -w 柚姫                  # 统计每个说话人用了多少次
    python q.py -c 柚姫 3 3 5            # 上下文：前3行 / 后3行 / 看5处
    python q.py -f 誅戮                  # 打印该词全部命中行（不截断）

选项:
    --corpus PATH   语料文件（默认 ./_dictwork/corpus.txt）
    --width N       单行截断宽度（默认 170）
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


def load(path):
    if not os.path.isfile(path):
        sys.exit('找不到语料文件: %s\n先跑 build_corpus.py 生成。' % path)
    return io.open(path, encoding='utf-8').read().split('\n')


def parse(line):
    m = HEAD.match(line)
    if not m:
        return None
    return {'file': m.group(1), 'idx': int(m.group(2)),
            'name': m.group(3), 'msg': m.group(4)}


def show_counts(lines, term, width, limit):
    hits = [l for l in lines if term in l]
    print('### %s —— %d 行' % (term, len(hits)))
    for l in hits[:limit]:
        print('   ' + l[:width])
    if len(hits) > limit:
        print('   …（还有 %d 行，用 @N 或 -f 看更多）' % (len(hits) - limit))
    print()


def show_full(lines, term, width):
    hits = [l for l in lines if term in l]
    print('### %s —— %d 行（全部）' % (term, len(hits)))
    for l in hits:
        print('   ' + l[:width])
    print()


def show_context(lines, term, before, after, limit, width):
    idx = [i for i, l in enumerate(lines) if term in l]
    print('### %s —— %d 行（上下文模式）' % (term, len(idx)))
    for n, h in enumerate(idx[:limit]):
        print('---- 第 %d 处 ----' % (n + 1))
        lo, hi = max(0, h - before), min(len(lines), h + after + 1)
        for j in range(lo, hi):
            print(('>>' if j == h else '  ') + lines[j][:width])
        print()
    if len(idx) > limit:
        print('（还有 %d 处未显示）\n' % (len(idx) - limit))


def show_speakers(lines, term):
    c = collections.Counter()
    for l in lines:
        p = parse(l)
        if p and term in p['msg']:
            c[p['name'] or '(旁白)'] += 1
    total = sum(c.values())
    print('### %s —— 共 %d 次，按说话人：' % (term, total))
    for k, v in c.most_common(12):
        print('   %-18s %d' % (k, v))
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('terms', nargs='+')
    ap.add_argument('--corpus', default=os.path.join('_dictwork', 'corpus.txt'))
    ap.add_argument('--width', type=int, default=170)
    ap.add_argument('-n', '--count', action='store_true')
    ap.add_argument('-w', '--who', action='store_true')
    ap.add_argument('-f', '--full', action='store_true')
    ap.add_argument('-c', '--context', nargs=3, metavar=('BEFORE', 'AFTER', 'LIMIT'))
    a = ap.parse_args()

    lines = load(a.corpus)

    limit = 8
    terms = []
    for t in a.terms:
        if t.startswith('@'):
            limit = int(t[1:])
        else:
            terms.append(t)

    if a.count:
        for t in terms:
            print('%-28s %d' % (t, sum(1 for l in lines if t in l)))
        return
    if a.who:
        for t in terms:
            show_speakers(lines, t)
        return
    if a.context:
        b, af, lim = (int(x) for x in a.context)
        for t in terms:
            show_context(lines, t, b, af, lim, a.width)
        return
    if a.full:
        for t in terms:
            show_full(lines, t, a.width)
        return
    for t in terms:
        show_counts(lines, t, a.width, limit)


if __name__ == '__main__':
    main()
