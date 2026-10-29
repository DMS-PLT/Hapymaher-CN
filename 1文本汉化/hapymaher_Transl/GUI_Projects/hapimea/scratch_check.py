import json

with open('pure_unused_context_report.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect sections by category
categories = text.split("============================================================\nCATEGORY: ")
print(f"Categories count: {len(categories)-1}")

for cat in categories[1:]:
    lines = cat.split("\n")
    header = lines[0]
    print("--------------------------------------------------")
    print(header)
    # print up to 30 lines
    for line in lines[1:25]:
        print(line)
