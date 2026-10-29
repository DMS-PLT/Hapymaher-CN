import json

with open('pure_unused_context_report.txt', 'r', encoding='utf-8') as f:
    text = f.read()

cats = text.split('============================================================\nCATEGORY: ')
for c in cats:
    if not c.strip(): continue
    lines = c.strip().split('\n')
    header = lines[0]
    title = header.split(' (Total:')[0]
    # Check specific categories
    if any(k in title for k in ['咲', '平坂', 'ちゃん', '弥生・Ｂ', 'アリス', 'お嬢さん', '透']):
        print(f'*** {title} ***')
        for l in lines[1:]:
            if l.startswith('File:') or l.startswith('Original:') or l.startswith('Translated:'):
                print(l)
        print()
