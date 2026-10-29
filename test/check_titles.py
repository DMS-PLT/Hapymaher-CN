import glob
import json
import re
import os

# 匹配包含 -...- 的标题
pattern = re.compile(r'-\s*(.*?)\s*-')

results = []
files = glob.glob('output/hapymaher/translated/*.ps3.json')
files.sort()

for fpath in files:
    with open(fpath, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    for idx, item in enumerate(data.get('Scenario', [])):
        raw = item.get('raw', '')
        tra = item.get('tra', '')
        if pattern.search(raw.strip()):
            results.append({
                'file': os.path.basename(fpath),
                'idx': idx,
                'raw': raw,
                'tra': tra
            })

out_path = 'test/matched_titles.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f"Total matched: {len(results)}\n")
    f.write("=" * 80 + "\n")
    for r in results:
        f.write(f"{r['file']:<25} [#{r['idx']:<3}] {r['raw']:<35} -> {r['tra']}\n")

print(f"Done. Written {len(results)} items to {out_path}")
