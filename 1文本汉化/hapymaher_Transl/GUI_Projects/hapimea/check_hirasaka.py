import json

with open('pure_unused.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

for x in items:
    if x['problem'] == 'GPT字典 `平坂`->`平坂` 未使用':
        print(f"[{x['filename']} #{x['index']}] ({x['name']})")
        print('  Orig:', x['original_text'])
        print('  Tran:', x['translated_text'])
