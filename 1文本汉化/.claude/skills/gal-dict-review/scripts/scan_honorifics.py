# -*- coding: utf-8 -*-
"""扫描「已知名字 + 敬称」在原文里的出现次数，找出字典可能漏收的称呼。

与「懒懒检测工具合集.py」的区别：
    那个工具用 1～5 字前缀去猜名字，噪声很大（た様 / は兄さん / した様）。
    审查场景里名字其实是已知的：gt_input 的 name 字段、NameTable、
    以及字典里已有的名字。直接用这些名字 + 后缀去数，精确得多。

用法:
    python scan_honorifics.py --input gt_input --dict ProjGptDict.toml \
        --name-table NameTable.toml --only-missing --out missing_honorifics.tsv

输入:
    --input       原文 json 目录
    --dict        主字典（TOML 或 TSV）
    --name-table  可选，GPP 的 NameTable.toml 或 CSV
    --suffixes    后缀规则，默认同目录 suffixes.txt
    --exclude     可选，排除词（后缀<TAB>完整词），默认同目录 exclude.txt
    --extra-names 可选，额外的名字名单，一行一个
    --min-count   只保留出现次数 >= N 的组合（默认 3）
    --only-missing 只输出字典 / 姓名表都没覆盖的候选

输出 TSV 列:
    suffix / name / combined / count / in_dict / in_name_table / status
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TEXT_KEYS = ('message', 'text', 'jp', 'src', 'original', 'source', 'content')
NAME_KEYS = ('name', 'names', 'speaker', 'chara', 'character', 'who')


def load_suffixes(path):
    rules = []
    for line in io.open(path, encoding='utf-8-sig'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if parts[0]:
            rules.append(parts[0])
    return rules


def load_dict_orgs(path):
    head = io.open(path, encoding='utf-8-sig').read(4096)
    if re.search(r'^\s*gptDict\s*=', head, re.M) or '{org' in head:
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
        return {x['org'] for x in d[key]}
    orgs = set()
    for line in io.open(path, encoding='utf-8-sig'):
        if line.startswith('#') or not line.strip():
            continue
        c = line.rstrip('\r\n').replace('    ', '\t').split('\t')
        if len(c) >= 2 and c[0] and c[0] != '日文原词':
            orgs.add(c[0])
    return orgs


def load_name_table(path):
    if not path or not os.path.isfile(path):
        return set()
    if path.lower().endswith('.toml'):
        import tomllib
        return set(tomllib.load(open(path, 'rb')).keys())
    keys = set()
    with io.open(path, 'r', newline='', encoding='utf-8-sig') as f:
        rd = csv.reader(f)
        header = next(rd, None)
        if not header:
            return keys
        si = header.index('JP_Name') if 'JP_Name' in header else (
            header.index('SRC_Name') if 'SRC_Name' in header else None)
        if si is None:
            return keys
        for r in rd:
            if len(r) > si and r[si]:
                keys.add(r[si])
    return keys


def load_extra(path):
    if not path or not os.path.isfile(path):
        return set()
    return {l.strip() for l in io.open(path, encoding='utf-8-sig')
            if l.strip() and not l.startswith('#')}


def load_excludes(path):
    by_suffix = collections.defaultdict(set)
    if not path or not os.path.isfile(path):
        return by_suffix
    for line in io.open(path, encoding='utf-8-sig'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            by_suffix[parts[0]].add(parts[1])
    return by_suffix


def collect(path):
    """返回 (messages, speaker_names)。"""
    messages = []
    names = set()

    def walk(node, depth=0):
        if depth > 12:
            return
        if isinstance(node, str):
            return
        if isinstance(node, list):
            for x in node:
                walk(x, depth + 1)
            return
        if not isinstance(node, dict):
            return

        for k in NAME_KEYS:
            v = node.get(k)
            if isinstance(v, str) and v.strip():
                names.add(v.strip())
            elif isinstance(v, list):
                for x in v:
                    if isinstance(x, str) and x.strip():
                        names.add(x.strip())

        for k in TEXT_KEYS:
            v = node.get(k)
            if isinstance(v, str) and v.strip():
                messages.append(v)

        for k, v in node.items():
            if k not in TEXT_KEYS and k not in NAME_KEYS:
                walk(v, depth + 1)

    if os.path.isdir(path):
        files = sorted(glob.glob(os.path.join(path, '**', '*.json'), recursive=True))
        for p in files:
            try:
                walk(json.load(io.open(p, encoding='utf-8-sig')))
            except Exception as e:
                print('[跳过] %s: %s' % (p, e), file=sys.stderr)
    else:
        walk(json.load(io.open(path, encoding='utf-8-sig')))
    return messages, names


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--dict', required=True)
    ap.add_argument('--name-table', default=None)
    ap.add_argument('--suffixes', default=os.path.join(here, 'suffixes.txt'))
    ap.add_argument('--exclude', default=os.path.join(here, 'exclude.txt'))
    ap.add_argument('--extra-names', default=None)
    ap.add_argument('--out', default='missing_honorifics.tsv')
    ap.add_argument('--min-count', type=int, default=3)
    ap.add_argument('--only-missing', action='store_true')
    a = ap.parse_args()

    suffixes = load_suffixes(a.suffixes)
    excludes = load_excludes(a.exclude)
    dict_orgs = load_dict_orgs(a.dict)
    table_keys = load_name_table(a.name_table)
    extra = load_extra(a.extra_names)
    messages, speakers = collect(a.input)

    # 已知名字：说话人 + 姓名表 + 字典里出现的名字 + 额外名单
    names = set(speakers) | set(table_keys) | set(extra)
    # 字典里的 org 也可以当名字候选；太长的（术语）跳过
    for o in dict_orgs:
        if len(o) <= 10 and not re.search(r'[。、！？「」『』]', o):
            names.add(o)

    print('message %d 条，已知名字 %d 个，后缀 %d 个'
          % (len(messages), len(names), len(suffixes)))

    all_rows = []
    for name in names:
        for suffix in suffixes:
            combined = name + suffix
            if combined in excludes.get(suffix, ()):
                continue
            count = sum(msg.count(combined) for msg in messages)
            if count < a.min_count:
                continue
            in_dict = combined in dict_orgs or name in dict_orgs
            in_table = name in table_keys or combined in table_keys
            status = '已覆盖' if (in_dict or in_table) else '候选'
            all_rows.append((suffix, name, combined, count,
                             'yes' if in_dict else 'no',
                             'yes' if in_table else 'no', status))

    all_rows.sort(key=lambda x: (x[6] != '候选', -x[3], x[0], x[1]))
    rows = [r for r in all_rows if not (a.only_missing and r[6] == '已覆盖')]
    with io.open(a.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['suffix', 'name', 'combined', 'count',
                    'in_dict', 'in_name_table', 'status'])
        for r in rows:
            w.writerow(r)

    missing = [r for r in all_rows if r[6] == '候选']
    print('候选 %d 条，已覆盖 %d 条' % (len(missing), len(all_rows) - len(missing)))
    print('输出: %s' % a.out)
    if missing:
        print('\n出现次数最高的候选:')
        for r in missing[:30]:
            print('  %-24s %6d 次' % (r[2], r[3]))


if __name__ == '__main__':
    main()
