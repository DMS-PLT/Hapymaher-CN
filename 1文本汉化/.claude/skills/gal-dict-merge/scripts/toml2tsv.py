# -*- coding: utf-8 -*-
"""把 TOML 字典转成 TAB 分隔的 TSV。

用法:
    python toml2tsv.py 字典.toml --target nyanya -o 项目GPT字典.txt
    python toml2tsv.py 字典.toml --target galtransl -o 项目GPT字典.txt

目标工具:
    nyanya     天使喵喵（Angel-Nyanya）：带表头
               日文原词<TAB>中文翻译<TAB>备注
    galtransl  GalTransl 8.4.2：不带表头。
               注意：GT 的 GPT 字典里 `#` 不是注释，会被替换成 Tab，
               产生空 org 伪词条。所以这里不输出任何注释。

--no-header 仍保留，等价于强制不输出表头。
"""
import argparse
import io
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dict')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--target', choices=['nyanya', 'galtransl'], default='nyanya',
                    help='nyanya=带表头；galtransl=无表头（默认 nyanya）')
    ap.add_argument('--no-header', action='store_true',
                    help='强制不输出表头（galtransl 总是无表头）')
    a = ap.parse_args()

    import tomllib
    d = tomllib.load(open(a.dict, 'rb'))
    key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
    entries = d[key]

    buf = io.StringIO()
    header = (a.target == 'nyanya') and not a.no_header
    if header:
        buf.write('日文原词\t中文翻译\t备注\n')

    for x in entries:
        org = x['org']
        rep = x.get('rep', '')
        note = (x.get('note', '') or '').replace('\t', ' ').replace('\n', ' ')
        # org / rep 里的 Tab 或换行会直接破坏 TSV，必须显式报错
        if '\t' in org or '\n' in org or '\t' in rep or '\n' in rep:
            sys.exit('词条含 Tab/换行，无法导出 TSV: %r -> %r' % (org, rep))
        buf.write('%s\t%s\t%s\n' % (org, rep, note))

    text = buf.getvalue()
    if a.out:
        io.open(a.out, 'w', encoding='utf-8').write(text)
        print('写出 %d 条 → %s（target=%s，%s表头）'
              % (len(entries), a.out, a.target, '带' if header else '无'))
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    main()
