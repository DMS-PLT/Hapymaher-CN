import json
import os

items = [
    ("sky07100.ps3.json", "- 第７話【ラストリゾート】 -", "— 第7话【最后的避风港】 —", "- 第7话【最后的避风港】 -"),
    ("szal10.ps3.json", "- エンドロール -", "— 制作人员名单 —", "- 制作人员名单 -"),
    ("szke15.ps3.json", "- エンドロール -", "— 制作人员名单 —", "- 制作人员名单 -"),
    ("szya13.ps3.json", "- エンドロール -", "— 制作人员名单 —", "- 制作人员名单 -"),
    ("szsa16.ps3.json", "- エンドロール -", "— 制作人员名单 —", "- 制作人员名单 -"),
    ("szya07.ps3.json", "- 回想モード実行中 -", "— 回想模式运行中 —", "- 回想模式运行中 -"),
    ("sky041.ps3.json", "- 第４話【正反対の２人】 -", "— 第4话【截然相反的两人】 —", "- 第4话【截然相反的两人】 -"),
    ("szsaep.ps3.json", "- エピローグ【光差す森の中で】 -", "— 尾声【阳光洒落的森林中】 —", "- 尾声【阳光洒落的森林中】 -"),
    ("sky031.ps3.json", "- 第３話【Ｇｅｔｔｉｎｇ　ｅｎｔａｎｇｌｅｄ】 -", "— 第3话【Getting entangled】 —", "- 第3话【Getting entangled】 -"),
    ("szal01.ps3.json", "- 第８話【ｄｒｅａｍ　ｓｉｃｋ　ｄｉｓｅａｓｅｄ】 -", "— 第8话【dream sick diseased】 —", "- 第8话【dream sick diseased】 -")
]

dirs = [
    "output/hapymaher/translated",
    "gt_output",
    "翻译/GPPGUI/Projects/hapimea/transl_cache"
]

print("=== DRY RUN INSPECTION ===")
for fname, raw_target, new_view, new_raw in items:
    print(f"\n--- Target: {fname} [{raw_target}] -> {new_view} ---")
    for d in dirs:
        p = os.path.join(d, fname)
        if not os.path.exists(p):
            print(f"  [{d}]: NOT FOUND")
            continue
        with open(p, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)

        # Scenario list (output/hapymaher/translated)
        if isinstance(data, dict) and 'Scenario' in data:
            found = False
            for idx, sc in enumerate(data['Scenario']):
                if sc.get('raw', '').strip() == raw_target:
                    print(f"  [{d}] #{idx}: current tra = '{sc.get('tra')}'")
                    found = True
                    break
            if not found:
                print(f"  [{d}]: raw_target '{raw_target}' not found in Scenario")
        # transl_cache list
        elif isinstance(data, list):
            found = False
            for idx, entry in enumerate(data):
                if entry.get('original_text', '').strip() == raw_target:
                    print(f"  [{d}] #{idx}: current view = '{entry.get('translated_view_text')}', raw = '{entry.get('translated_raw_text')}'")
                    found = True
                    break
                elif 'message' in entry: # gt_output format
                    pass
            # for gt_output format
            if not found and len(data) > 0 and 'message' in data[0]:
                print(f"  [{d}]: gt_output format with {len(data)} entries")
