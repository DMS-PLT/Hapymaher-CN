# -*- coding: utf-8 -*-
"""把 ProjGptDict.toml + NameTable.toml 合并导出成 GalTransl 8.4.2 用的 TSV。

格式（与之前那份 项目GPT字典-GalTransl.txt 一致）：
    # 注释头 4 行
    ----------↓分节名↓----------
    日文原词<TAB>中文翻译<TAB>备注

- 分节名取自 ProjGptDict.toml 里的 `# ═══ 分节名 ═══` 注释
- rep 里的 `A||B` 只取 A（GalTransl 8.4.2 不认这个语法）
- NameTable.toml 里 ProjGptDict 没收录的说话人标签，按 NameTable 顺序补在最后一段；
  译名和备注取自旧版 248 条字典（Hapymaher_Transl/project/ProjGptDict.toml）

用法：
    python gen_galtransl_tsv.py --dict ProjGptDict.toml --nametable NameTable.toml \
        --old Hapymaher_Transl/project/ProjGptDict.toml -o 项目GPT字典-GalTransl.txt
"""
import argparse
import io
import re
import tomllib

SECTION_RE = re.compile(r'#\s*═══\s*(.+?)\s*═══')


def load_sections(path):
    """返回 [(分节名, [entry, ...]), ...]，按 TOML 中的顺序。"""
    text = io.open(path, encoding='utf-8').read()
    data = tomllib.loads(text)['gptDict']

    # 逐行确认条目顺序与 section 归属
    order = [l for l in text.split('\n') if l.lstrip().startswith('{org = ')]
    if len(order) != len(data):
        raise SystemExit('条目数与 TOML 解析结果不一致: %d vs %d' % (len(order), len(data)))

    idx = 0
    sections = []
    cur = None
    for line in text.split('\n'):
        m = SECTION_RE.search(line)
        if m:
            cur = [m.group(1), []]
            sections.append(cur)
            continue
        if line.lstrip().startswith('{org = '):
            if cur is None:
                cur = ['未分节', []]
                sections.append(cur)
            cur[1].append(data[idx])
            idx += 1
    return sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dict', required=True)
    ap.add_argument('--nametable', required=True)
    ap.add_argument('--old', required=True, help='旧版 248 条字典，用于补说话人标签的备注')
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()

    sections = load_sections(a.dict)
    entries = [e for _, es in sections for e in es]

    names = tomllib.load(open(a.nametable, 'rb'))
    old = tomllib.load(open(a.old, 'rb'))['gptDict']
    old_by = {e['org']: e for e in old}
    seen = {e['org'] for e in entries}

    extras = []
    for org, (rep, _count) in names.items():
        if org in seen:
            continue
        src = old_by.get(org)
        if src:
            extras.append({'org': org, 'rep': src['rep'], 'note': src.get('note', '')})
        else:
            extras.append({'org': org, 'rep': rep, 'note': ''})

    total = len(entries) + len(extras)

    buf = io.StringIO()
    buf.write('# Hapymaher 项目 GPT 字典（GalTransl 8.4.2 / TAB 分隔 TSV）\n')
    buf.write('# 格式为日文[Tab]中文[Tab]解释(可不写)\n')
    buf.write('# 由 ProjGptDict.toml + NameTable.toml 合并；共 %d 条。\n' % total)
    buf.write('# GPP 专用的 A||B 多译法在 TSV 里取第一个。\n')

    def emit(name, rows):
        buf.write('\n----------↓%s↓----------\n' % name)
        for x in rows:
            rep = (x.get('rep') or '').split('||')[0]
            note = (x.get('note') or '').replace('\t', ' ').replace('\n', ' ')
            buf.write('%s\t%s\t%s\n' % (x['org'], rep, note))

    for name, rows in sections:
        if rows:
            emit(name, rows)
    if extras:
        emit('说话人标签（GalTransl 无 NameTable，补回）', extras)
    buf.write('\n')

    with io.open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(buf.getvalue())
    print('写出 %d 条（字典 %d + 说话人标签 %d）→ %s'
          % (total, len(entries), len(extras), a.out))


if __name__ == '__main__':
    main()
