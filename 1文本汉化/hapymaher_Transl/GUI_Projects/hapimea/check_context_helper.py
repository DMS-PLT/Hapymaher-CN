import json

with open(r'c:\Users\DMS\Desktop\Hapymaher\翻译\GPPGUI\Projects\hapimea\transl_cache\sky041.ps3.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for row in d:
    if 1018 <= row['index'] <= 1028:
        print(f"[{row['index']}] {row.get('name')}: {row['original_text']}")
        print(f"      -> {row.get('translated_view_text')}")
