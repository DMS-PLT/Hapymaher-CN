# -*- coding: utf-8 -*-
"""字典体检。整合完字典、交付之前必跑。

用法:
    python check_dict.py 新字典.toml --corpus _dictwork/corpus.txt --target gpp
    python check_dict.py 项目GPT字典.txt --corpus _dictwork/corpus.txt --target galtransl

检查项:
    [1] 结构    TOML/TSV 可解析 / org 重复 / org|rep 缺失
    [2] 格式    目标工具的 TSV 表头、# 注释、Tab/换行
    [3] 覆盖率  旧字典里的 org 是否都还在（--old）
    [4] 译名用字 rep 里混进假名 / 繁体字 / 日式和字
    [5] 多译法  是否符合目标工具（GPP: || / GT: / / 喵喵: 不支持）
    [6] 备注    超长 / 自指 / Tab 或换行
    [7] 派生一致 A 是 B 的子串时，rep A 是否也是 rep B 的子串
    [8] 语料命中 每条 org 在正文/name 的命中次数
    [9] 命中密度 每批送进提示词的条目数（mean/p90/p99/max）
    [10] 姓名单   仅出现在 name、正文 0 命中的条目（建议放姓名表）

--target:
    gpp         GalTransl++（TOML）
    galtransl   GalTransl 8.4.2（TSV，无表头，# 不是注释）
    nyanya      天使喵喵（TSV，带表头）
    auto        按扩展名推断：.toml→gpp，.txt→galtransl

退出码：有 ERROR 时返回 1。
"""
import argparse
import collections
import io
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 片假名区里 U+30A0(゠) 和 U+30FB(・) 是标点不是假名，中文里也照用，排除掉
KANA = re.compile(r'[぀-ゟ゠-ヿ]')
KANA_OK = {'゠', '・'}

# 繁体字 / 日本新字体 —— 出现在简体译文里即为错误。
TRAD = (
    '鳳雲譯價質變經龍讓關開們個這說時會來東車長門馬鳥魚點齒縣藥醫護讀語課記註證識議讚響髮鬥齊龜'
    '壓學實圖團圍國圓場壞奧寶將專對導屆島嶺帥帶廣廳彈歸當盡監盤眾矯礙礦禮萬稱穩竊筆筍糾紀約紅'
    '紋納純紙級細紳紹終組結給統繪絕絹繼續綴締編緩練緣縛縫縮績纖織繕繭繰覺觀親單嚴營產鐵銀錢錯'
    '鐘鏡陣隊際隨隱難雖雜雙雞離靈靜韓頁頂項順須預領頭頸頻題顏願類顧顯風飛飯飲養餘駕騎驗體鬆灣'
    '沒設訴評詞誌認誰調談請論誼諷謝譜豐豬貝負財責貴買貸費賀資賊賓賜賞賠賢賣賤賬購賽贈贊贏'
    '覽豔曬甦礙閃閉問間聞闆陽階陳陸霧韻顫驕驚驅騷驟鬧魯鮮鳴鴨鵝鷹麗麥黃黨'
)
TRAD_SET = set(TRAD)

CORPUS_HEAD = re.compile(r'^\[([^\]#]*)#(\d+)\] ([^|]*)\| (.*)$')


def die(msg):
    print(msg)
    sys.exit(1)


def resolve_target(path, target):
    if target != 'auto':
        return target
    return 'gpp' if path.lower().endswith('.toml') else 'galtransl'


def load_dict(path, target):
    """按内容判断格式：含 gptDict 或 {org 就当 TOML，否则按 TAB 分隔 TSV。"""
    head = io.open(path, encoding='utf-8-sig').read(4096)
    if re.search(r'^\s*gptDict\s*=', head, re.M) or '{org' in head:
        import tomllib
        d = tomllib.load(open(path, 'rb'))
        key = 'gptDict' if 'gptDict' in d else list(d.keys())[0]
        return [(x['org'], x.get('rep', ''), x.get('note', '')) for x in d[key]]

    rows = []
    for line in io.open(path, encoding='utf-8-sig'):
        if line.startswith('\n') or line.startswith('#'):
            continue
        c = line.rstrip('\r\n').replace('    ', '\t').split('\t')
        if len(c) < 2 or not c[0]:
            continue
        if c[0].startswith('日文原词'):
            continue
        rows.append((c[0], c[1], c[2] if len(c) > 2 else ''))
    return rows


def load_corpus(path):
    """返回 [(name, message), ...]；不是 corpus 格式时返回 None。"""
    rows = []
    for line in io.open(path, encoding='utf-8'):
        m = CORPUS_HEAD.match(line.rstrip('\n'))
        if m:
            rows.append((m.group(3), m.group(4)))
    return rows or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dict')
    ap.add_argument('--old', default=None, help='旧字典（TSV 或 TOML），用于覆盖率对比')
    ap.add_argument('--corpus', default=None)
    ap.add_argument('--target', choices=['gpp', 'galtransl', 'nyanya', 'auto'],
                    default='auto', help='目标工具，默认按扩展名推断')
    ap.add_argument('--batch-size', type=int, default=16,
                    help='模拟每批句数，用于命中密度检查（默认 16）')
    ap.add_argument('--max-note', type=int, default=60)
    a = ap.parse_args()

    if not os.path.isfile(a.dict):
        die('找不到字典: %s' % a.dict)

    target = resolve_target(a.dict, a.target)
    try:
        rows = load_dict(a.dict, target)
    except Exception as e:
        die('解析失败: %s' % e)

    errors, warns, infos = [], [], []
    orgs = [r[0] for r in rows]

    # [1] 结构
    dup = [o for o, c in collections.Counter(orgs).items() if c > 1]
    if dup:
        errors.append('org 重复 %d 条: %s' % (len(dup), dup[:10]))
    for o, r, n in rows:
        if not o or not r:
            errors.append('空 org 或 rep: %r' % (o,))
        if not n:
            warns.append('空备注: %s' % o)

    # [2] 目标格式
    if not a.dict.lower().endswith('.toml'):
        if target == 'galtransl':
            first_content = None
            for i, line in enumerate(io.open(a.dict, encoding='utf-8-sig'), 1):
                if not line.strip():
                    continue
                if first_content is None:
                    first_content = line.rstrip('\r\n')
                if line.startswith('#'):
                    errors.append(
                        '第 %d 行以 # 开头：GalTransl 的 GPT 字典会把 # 换成 Tab，'
                        '产生空 org 伪词条；请改用 // 或删除' % i)
            if first_content and first_content.startswith('日文原词'):
                errors.append(
                    'TSV 含表头「日文原词…」：GalTransl 8.4.2 会把它当成一条真实词条；'
                    '请用 toml2tsv.py --target galtransl 生成无表头版本')
        elif target == 'nyanya':
            pass  # 喵喵的生成文件本来就带表头

    # [3] 译名用字
    for o, r, n in rows:
        kana = [c for c in KANA.findall(r) if c not in KANA_OK]
        if kana:
            errors.append('rep 含假名: %s → %s  (%s)' % (o, r, ''.join(sorted(set(kana)))))
        bad = sorted(set(r) & TRAD_SET)
        if bad:
            errors.append('rep 含繁体/和字: %s → %s  (%s)' % (o, r, ''.join(bad)))

    # [4] 多译法
    for o, r, n in rows:
        has_slash = bool(re.search(r'[^/]/[^/]', r)) or ('／' in r)
        has_pipe = '||' in r
        if target == 'gpp':
            if has_slash and not has_pipe:
                warns.append('GPP 多译法应使用 ||：%s → %s' % (o, r))
            if has_pipe and has_slash:
                warns.append('rep 同时含 / 和 ||，容易混淆：%s → %s' % (o, r))
        elif target == 'galtransl':
            if has_pipe:
                warns.append('GalTransl 多译法应使用 /，|| 会原样输出：%s → %s' % (o, r))
            if '／' in r:
                warns.append('GalTransl 多译法请用半角 /：%s → %s' % (o, r))
        else:  # nyanya
            if has_pipe or has_slash:
                warns.append('喵喵不支持多译法，只能选一个：%s → %s' % (o, r))

    # [5] 备注
    SELFREF = re.compile(r'同上|同「|同『|见「|见『|见上|前述|前条|如上|上述|上文|参见|同下|该团体|此团体')
    for o, r, n in rows:
        if '\t' in n or '\n' in n:
            errors.append('备注含 Tab/换行（会破坏 TSV/提示词表格）: %s' % o)
        if len(n) > a.max_note:
            warns.append('备注 %d 字（上限 %d）: %s' % (len(n), a.max_note, o))
        if SELFREF.search(n):
            errors.append('备注自指（被引用的词条不保证一起送进提示词）: %s → %s' % (o, n))
        if [c for c in KANA.findall(n) if c not in KANA_OK]:
            cn = len(re.findall(r'[一-鿿]', n))
            if cn < 4:
                warns.append('备注几乎全为日文，缺中文提示: %s → %s' % (o, n))

    # [6] 语料
    corpus_rows = None
    if a.corpus and os.path.isfile(a.corpus):
        corpus_rows = load_corpus(a.corpus)
        if corpus_rows is None:
            infos.append('语料不是 [文件#序号] 说话人| 正文 格式，跳过命中检查')

    body_hit, name_hit = {}, {}
    if corpus_rows is not None:
        for o in orgs:
            body_hit[o] = sum(1 for nm, msg in corpus_rows if o in msg)
            name_hit[o] = sum(1 for nm, msg in corpus_rows if o in nm)

    # [7] 派生一致性
    deriv = []
    for x in rows:
        for y in rows:
            if x[0] == y[0] or x[0] not in y[0]:
                continue
            if x[1] and x[1] not in y[1]:
                deriv.append((x[0], x[1], y[0], y[1]))
    if deriv:
        infos.append('派生不一致 %d 组（短词译文不是长词译文的子串）' % len(deriv))
        for short, srep, long, lrep in deriv[:20]:
            if target == 'gpp':
                # GPP 不消耗子串，长短两条都会送；不是“永远不命中”
                warns.append('派生不一致（GPP 会把两条一起送出）：%s → %s   但   %s → %s'
                             % (short, srep, long, lrep))
            else:
                warns.append('派生不一致（吞词工具可能让短词永远用不上）：%s → %s   但   %s → %s'
                             % (short, srep, long, lrep))

    # [8] 同 rep 多 org
    byrep = collections.defaultdict(list)
    for o, r, n in rows:
        byrep[r].append(o)
    multi = {r: os_ for r, os_ in byrep.items() if len(os_) > 1}
    if multi:
        infos.append('同 rep 多 org %d 组（同一人物的不同写法属正常，不同人物则是撞名）' % len(multi))
        for r, os_ in list(multi.items())[:15]:
            infos.append('    %s ← %s' % (r, ' / '.join(os_)))

    # [9] 语料命中 + [10] 姓名单
    if corpus_rows is not None:
        zero = [o for o in orgs if body_hit[o] == 0 and name_hit[o] == 0]
        if zero:
            infos.append('语料中 0 命中的 org %d 条: %s' % (len(zero), zero[:20]))
        name_only = [(o, name_hit[o]) for o in orgs
                     if body_hit[o] == 0 and name_hit[o] > 0]
        if name_only:
            infos.append('仅 name 字段出现、正文 0 命中的 org %d 条（建议放姓名表）' % len(name_only))
            for o, c in name_only[:30]:
                infos.append('    %s  (name %d 次)' % (o, c))

        # 命中密度
        batch_texts = []
        for i in range(0, len(corpus_rows), a.batch_size):
            chunk = corpus_rows[i:i + a.batch_size]
            if target == 'gpp':
                texts = (nm + ':::::' + msg for nm, msg in chunk)
            elif target == 'galtransl':
                texts = (nm + ':' + msg for nm, msg in chunk)
            else:
                texts = (msg for nm, msg in chunk)
            batch_texts.append('\n'.join(texts))
        per = [sum(1 for o in orgs if o in t) for t in batch_texts]
        per.sort()
        if per:
            mean = statistics.mean(per)
            median = statistics.median(per)
            p90 = per[min(len(per) - 1, int(len(per) * 0.90))]
            p99 = per[min(len(per) - 1, int(len(per) * 0.99))]
            mx = max(per)
            infos.append('每批命中密度（%d 句/批）：mean %.2f / median %s / p90 %d / p99 %d / max %d'
                         % (a.batch_size, mean, median, p90, p99, mx))
            if p99 > 15 or mx > 20:
                warns.append('每批命中偏多（p99 %d / max %d）；建议检查短词和泛称标签' % (p99, mx))

    # [11] 覆盖率
    if a.old:
        if not os.path.isfile(a.old):
            die('找不到旧字典: %s' % a.old)
        old = load_dict(a.old, resolve_target(a.old, 'auto'))
        oldorg = [o for o, _, _ in old]
        gone = [o for o in oldorg if o not in set(orgs)]
        infos.append('旧字典 %d 条 → 新字典 %d 条；消失的 org %d 条' % (len(oldorg), len(rows), len(gone)))
        for o in gone:
            warns.append('原条目消失: %s  （确认是有意删除/移出）' % o)

    # 输出
    print('=' * 78)
    print('字典体检: %s  (target=%s)' % (a.dict, target))
    print('=' * 78)
    print('条目数 %d | 错误 %d | 警告 %d' % (len(rows), len(errors), len(warns)))
    print()
    for label, items, mark in (('ERROR', errors, '✗'), ('WARN', warns, '!'), ('INFO', infos, '·')):
        if not items:
            continue
        print('【%s】' % label)
        for it in items:
            print('  %s %s' % (mark, it))
        print()
    print('=' * 78)
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
