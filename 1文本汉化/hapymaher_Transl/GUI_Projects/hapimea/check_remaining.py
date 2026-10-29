import json

with open('pure_unused.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

target_probs = [
    'GPT字典 `ちゃん`->`酱` 未使用',
    'GPT字典 `アリス`->`有栖` 未使用',
    'GPT字典 `お嬢さん`->`小姐` 未使用',
    'GPT字典 `透`->`透` 未使用',
    'GPT字典 `トール`->`透` 未使用',
    'GPT字典 `責め`->`责难||折磨||拷问||惩罚` 未使用',
    'GPT字典 `弥生`->`弥生` 未使用',
    'GPT字典 `バイブ`->`振动棒` 未使用',
    'GPT字典 `膣`->`阴道` 未使用',
]

for prob in target_probs:
    sub = [x for x in items if x['problem'] == prob]
    print(f"=== {prob} ({len(sub)}) ===")
    for x in sub:
        print(f"[{x['filename']} #{x['index']}] ({x['name']})")
        print("  Orig:", x['original_text'])
        print("  Tran:", x['translated_text'])
