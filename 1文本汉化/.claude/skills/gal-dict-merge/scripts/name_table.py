# -*- coding: utf-8 -*-
"""生成 / 补全姓名替换表。

支持三种目标：

    gpp        GalTransl++ 的 NameTable.toml
               '原名' = [ '译名', 出现次数 ]
    galtransl  GalTransl 8.4.2 的 name替换表.csv
               SRC_Name,DST_Name,Count
    nyanya     天使喵喵（Angel-Nyanya）的 name替换表.csv
               JP_Name,CN_Name,Count

为什么姓名要单独一张表：
    - 喵喵的 GPT 字典只作用于正文，name 字段走 CSV；
    - GPP 的 GPT 字典虽然匹配 name，但同一份字典也参与提示词，泛称标签会污染正文；
    - 姓名表只改 name 字段，不进提示词，也不参与“字典未使用”检查。

用法:
    python name_table.py --target gpp --corpus _dictwork/corpus.txt \
        --dict 主字典.toml --table NameTable.toml

    python name_table.py --target galtransl --corpus _dictwork/corpus.txt \
        --dict 主字典.toml --table name替换表.csv

    python name_table.py --target nyanya --corpus _dictwork/corpus.txt \
        --dict 主字典.toml --table name替换表.csv

不带 --overwrite 时只填空行，已有译名保留。
表不存在时按语料统计新建。
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

HEAD = re.compile(r'^\[[^\]#]*#\d+\] ([^|]*)\| (.*)$')
SPLIT = re.compile(r'([/／])')
KANA = re.compile(r'[぀-ゟ゠-ヿ]')
# 纯标点 / ASCII / 数字 的片段不需要翻译，不算「未解决」
NEUTRAL = re.compile(r'^[0-9A-Za-zＡ-Ｚａ-ｚ０-９\s?？!！.。·・\-－_（）()／/＆&]*$')


def load_dict(path):
    """读取主字典（TOML 或 TSV），返回 {org: rep}。"""
    head = io.open(path, encoding='utf-8-sig').read(4096)
    if re.search(r'^\s*gptDict\s*=', head, re.M) or '{org' in head:
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
        return {x['org']: x.get('rep', '') for x in d[key]}
    m = {}
    for line in io.open(path, encoding='utf-8-sig'):
        if line.startswith('#') or not line.strip():
            continue
        c = line.rstrip('\r\n').replace('    ', '\t').split('\t')
        if len(c) < 2 or not c[0] or c[0] in ('日文原词',):
            continue
        m.setdefault(c[0], c[1])
    return m


def count_names(corpus):
    c = collections.Counter()
    for line in io.open(corpus, encoding='utf-8'):
        m = HEAD.match(line.rstrip('\n'))
        if m and m.group(1):
            c[m.group(1)] += 1
    return c


def translate(name, d):
    """把说话人标签翻成中文。

    '/' 与 '／' 两边分别查表。返回 (译文, 未能翻译的片段)。
    只要存在「含假名或汉字但查不到」的片段，调用方就应放弃写入，
    否则会把半中半日的标签灌进运行时表。
    """
    parts = SPLIT.split(name)
    out, unresolved = [], []
    for p in parts:
        if p in ('/', '／') or p == '':
            out.append(p)
            continue
        if p in d and d[p]:
            # 姓名字段不使用多译法：GPP 的 ||、GT 的 / 都只取第一个
            val = d[p].split('||')[0].strip()
            out.append(val)
            continue
        out.append(p)
        if not NEUTRAL.match(p):
            unresolved.append(p)
    return ''.join(out), unresolved


def _find_col(header, *names):
    for n in names:
        if n in header:
            return header.index(n)
    return None


def read_table(path):
    """读取已有姓名表（TOML 或 CSV），返回 (rows, order)。

    rows: name -> (cn, count)
    order: 表中出现顺序
    """
    rows, order = {}, []
    if not os.path.isfile(path):
        return rows, order

    if path.lower().endswith('.toml'):
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        for k, v in d.items():
            if isinstance(v, list):
                cn = v[0] if v and isinstance(v[0], str) else ''
                cnt = v[1] if len(v) > 1 and isinstance(v[1], int) else 0
            elif isinstance(v, str):
                cn, cnt = v, 0
            else:
                continue
            rows[k] = (cn, cnt)
            order.append(k)
        return rows, order

    with io.open(path, 'r', newline='', encoding='utf-8-sig') as f:
        rd = csv.reader(f)
        header = next(rd, None)
        if not header:
            return rows, order
        si = _find_col(header, 'JP_Name', 'SRC_Name')
        di = _find_col(header, 'CN_Name', 'DST_Name')
        if si is None or di is None:
            sys.exit('%s 缺少姓名列：需要 JP_Name/SRC_Name 和 CN_Name/DST_Name' % path)
        ci = _find_col(header, 'Count', '次数')
        for r in rd:
            if len(r) <= max(si, di):
                continue
            jp = r[si]
            if not jp:
                continue
            cn = r[di] if len(r) > di else ''
            cnt = 0
            if ci is not None and len(r) > ci:
                try:
                    cnt = int(r[ci])
                except ValueError:
                    cnt = 0
            rows[jp] = (cn, cnt)
            order.append(jp)
    return rows, order


def _toml_str(s):
    """TOML 字符串：优先用单引号 literal；含单引号/控制字符时用 basic string。"""
    if "'" not in s and '\n' not in s and '\t' not in s:
        return "'" + s + "'"
    return '"' + (s.replace('\\', '\\\\').replace('"', '\\"')
                  .replace('\n', '\\n').replace('\t', '\\t')) + '"'


def write_table(path, rows, order, target):
    order = sorted(set(order), key=lambda n: -rows[n][1])
    if target == 'gpp':
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write("# GalTransl++ NameTable.toml\n")
            f.write("# '原名' = [ '译名', 出现次数 ]\n")
            f.write("# 只负责替换 name 字段，不进入提示词。\n\n")
            for n in order:
                cn, cnt = rows[n]
                f.write('%s = [%s, %d]\n' % (_toml_str(n), _toml_str(cn), cnt))
        return

    header = ['JP_Name', 'CN_Name', 'Count'] if target == 'nyanya' \
        else ['SRC_Name', 'DST_Name', 'Count']
    with io.open(path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(header)
        for n in order:
            cn, cnt = rows[n]
            w.writerow([n, cn, cnt])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True)
    ap.add_argument('--dict', dest='dicts', nargs='+', required=True)
    ap.add_argument('--target', choices=['gpp', 'galtransl', 'nyanya'], default='gpp')
    ap.add_argument('--table', default=None,
                    help='默认：gpp=NameTable.toml，其它=name替换表.csv')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true',
                    help='连已填过的译名也一并覆盖（默认只填空行）')
    a = ap.parse_args()

    table = a.table
    if table is None:
        table = 'NameTable.toml' if a.target == 'gpp' else 'name替换表.csv'

    for p in [a.corpus] + a.dicts:
        if not os.path.isfile(p):
            sys.exit('找不到: %s' % p)

    mapping = {}
    for p in a.dicts:                       # 后面的字典不覆盖前面的（顺序即优先级）
        for k, v in load_dict(p).items():
            mapping.setdefault(k, v)

    counts = count_names(a.corpus)
    rows, order = read_table(table)

    filled, kept, partial = [], [], []

    def handle(name):
        cn, unresolved = translate(name, mapping)
        if unresolved:
            partial.append((name, cn, unresolved, counts.get(name, 0)))
            return None
        return cn

    # 表里已有的行
    for name in list(order):
        old_cn, old_cnt = rows[name]
        new_cnt = counts.get(name, old_cnt)
        cn = handle(name)
        if cn is None:
            rows[name] = (old_cn, new_cnt)
            continue
        if not old_cn.strip() or a.overwrite:
            if cn != old_cn:
                filled.append((name, old_cn, cn, new_cnt))
            rows[name] = (cn, new_cnt)
        else:
            rows[name] = (old_cn, new_cnt)
            kept.append(name)

    # 语料里新出现、表里没有的行
    for name, cnt in counts.items():
        if name in rows:
            continue
        order.append(name)
        cn = handle(name)
        rows[name] = (cn if cn is not None else '', cnt)
        if cn is not None:
            filled.append((name, '', cn, cnt))

    # 输出
    if filled:
        print('【已填 / 更新 %d 条】' % len(filled))
        for jp, old, cn, cnt in sorted(filled, key=lambda x: -x[3]):
            print('  %-26s %-14s → %-16s (%d 次)' % (jp, old or '(空)', cn, cnt))
    if kept:
        print('\n【保留原值 %d 条】(要覆盖加 --overwrite)' % len(kept))
    if partial:
        print('\n【⚠ 有片段译不出，已留空待人工 %d 条】' % len(partial))
        for jp, cn, miss, cnt in sorted(partial, key=lambda x: -x[3]):
            print('  %-26s %d 次   缺: %s' % (jp, cnt, ' / '.join(miss)))

    if a.dry_run:
        print('\n--dry-run，未写文件。')
        return

    write_table(table, rows, order, a.target)
    print('\n写出 %d 行 → %s（target=%s）' % (len(set(order)), table, a.target))


if __name__ == '__main__':
    main()
