import os

RULES = [
    (
        "sky07100.ps3.json",
        [
            ("— 第7话【最后的胜地】 —", "— 第7话【最后的避风港】 —"),
            ("- 第7话【最后的胜地】 -", "- 第7话【最后的避风港】 -"),
        ]
    ),
    (
        "szal10.ps3.json",
        [
            ("— 演职员表 —", "— 制作人员名单 —"),
            ("- 演职员表 -", "- 制作人员名单 -"),
        ]
    ),
    (
        "szke15.ps3.json",
        [
            ("— 演职员表 —", "— 制作人员名单 —"),
            ("- 演职员表 -", "- 制作人员名单 -"),
        ]
    ),
    (
        "szya13.ps3.json",
        [
            ("— 演职员表 —", "— 制作人员名单 —"),
            ("- 演职员表 -", "- 制作人员名单 -"),
        ]
    ),
    (
        "szsa16.ps3.json",
        [
            ("— 片尾字幕 —", "— 制作人员名单 —"),
            ("- 片尾字幕 -", "- 制作人员名单 -"),
        ]
    ),
    (
        "szya07.ps3.json",
        [
            ("— 正在执行回想模式 —", "— 回想模式运行中 —"),
            ("- 正在执行回想模式 -", "- 回想模式运行中 -"),
        ]
    ),
    (
        "sky041.ps3.json",
        [
            ("— 第4话【截然相反的2人】 —", "— 第4话【截然相反的两人】 —"),
            ("- 第4话【截然相反的2人】 -", "- 第4话【截然相反的两人】 -"),
        ]
    ),
    (
        "szsaep.ps3.json",
        [
            ("— 尾声【在阳光洒入的森林中】 —", "— 尾声【阳光洒落的森林中】 —"),
            ("- 尾声【在阳光洒入的森林中】 -", "- 尾声【阳光洒落的森林中】 -"),
        ]
    ),
    (
        "sky031.ps3.json",
        [
            ("— 第3话【Getting　entangled】 —", "— 第3话【Getting entangled】 —"),
            ("- 第3话【Getting　entangled】 -", "- 第3话【Getting entangled】 -"),
        ]
    ),
    (
        "szal01.ps3.json",
        [
            ("— 第8话【dream　sick　diseased】 —", "— 第8话【dream sick diseased】 —"),
            ("- 第8话【dream　sick　diseased】 -", "- 第8话【dream sick diseased】 -"),
        ]
    ),
]

DIRS = [
    "output/hapymaher/translated",
    "gt_output",
    "翻译/GPPGUI/Projects/hapimea/transl_cache"
]

total_files_changed = 0
total_replacements = 0

for fname, pair_list in RULES:
    print(f"\nProcessing {fname}...")
    for d in DIRS:
        filepath = os.path.join(d, fname)
        if not os.path.exists(filepath):
            print(f"  [SKIP] Not found in {d}")
            continue

        with open(filepath, 'rb') as f:
            raw_bytes = f.read()

        has_bom = raw_bytes.startswith(b'\xef\xbb\xbf')
        # Decode using utf-8-sig to handle bom transparently
        text = raw_bytes.decode('utf-8-sig')

        new_text = text
        file_replaced = 0
        for old_str, new_str in pair_list:
            if old_str in new_text:
                count = new_text.count(old_str)
                new_text = new_text.replace(old_str, new_str)
                file_replaced += count
                print(f"  [{d}] Replaced '{old_str}' -> '{new_str}' ({count} times)")

        if file_replaced > 0:
            encoded_bytes = (b'\xef\xbb\xbf' if has_bom else b'') + new_text.encode('utf-8')
            with open(filepath, 'wb') as f:
                f.write(encoded_bytes)
            total_files_changed += 1
            total_replacements += file_replaced
        else:
            print(f"  [{d}] No patterns matched")

print("\n" + "=" * 50)
print(f"DONE. Total files modified: {total_files_changed}, Total replacements: {total_replacements}")
