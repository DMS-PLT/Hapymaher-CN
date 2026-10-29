# -*- coding: utf-8 -*-
"""把游戏原文 json 目录压成可检索语料。

用法:
    python build_corpus.py <input目录> [-o 输出路径] [--ext .json] [--quiet]

输出每行一条:
    [文件名#序号] 说话人| 正文
（无说话人时 "|" 前为空）

兼容结构:
    A. [{"name": "要", "message": "「おう」"}, ...]      喵喵 / GalTransl
    B. {"0": {"message": ...}, "1": {...}}
    C. 任意嵌套 —— 递归找文本字段，同级有 name/speaker 就当说话人
"""
import argparse
import io
import json
import os
import sys
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

TEXT_KEYS = ('message', 'text', 'jp', 'src', 'original', 'source', 'content')
NAME_KEYS = ('name', 'speaker', 'chara', 'character', 'who')
# 排除纯控制/元数据字段
SKIP_KEYS = ('id', 'index', 'voice', 'voiced', 'file', 'line', 'type', 'flag')


def walk(node, out, speaker=None, depth=0):
    """递归收集文本。"""
    if depth > 12:
        return
    if isinstance(node, str):
        return
    if isinstance(node, list):
        for x in node:
            walk(x, out, speaker, depth + 1)
        return
    if not isinstance(node, dict):
        return

    # 同级的说话人字段
    spk = speaker
    for k in NAME_KEYS:
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            spk = v.strip()
            break

    hit = False
    for k in TEXT_KEYS:
        v = node.get(k)
        if isinstance(v, str) and v.strip():
            out.append((spk or '', v))
            hit = True
    if hit:
        return

    for k, v in node.items():
        if k in NAME_KEYS or k in SKIP_KEYS:
            continue
        walk(v, out, spk, depth + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--ext', default='.json', help='文件后缀，默认 .json')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    src = os.path.abspath(a.input)
    if not os.path.isdir(src):
        sys.exit('不是目录: %s' % src)
    out_path = a.out or os.path.join(os.getcwd(), '_dictwork', 'corpus.txt')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    files = sorted(glob.glob(os.path.join(src, '*' + a.ext)))
    if not files:
        sys.exit('目录里没有 %s 文件: %s' % (a.ext, src))

    buf = io.StringIO()
    total = 0
    for p in files:
        stem = os.path.splitext(os.path.basename(p))[0]
        try:
            data = json.load(open(p, encoding='utf-8-sig'))
        except Exception as e:
            print('[跳过] %s : %s' % (stem, e), file=sys.stderr)
            continue
        rows = []
        walk(data, rows)
        for i, (spk, txt) in enumerate(rows):
            txt = txt.replace('\r', '').replace('\n', '\\n')
            buf.write('[%s#%d] %s| %s\n' % (stem, i, spk, txt))
            total += 1

    io.open(out_path, 'w', encoding='utf-8').write(buf.getvalue())
    if not a.quiet:
        print('文件 %d 个，语料 %d 行' % (len(files), total))
        print('输出: %s' % out_path)


if __name__ == '__main__':
    main()
