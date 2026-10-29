import json
import re
import sys
from collections import Counter, defaultdict

BASE = r"C:\Users\DMS\Desktop\Hapymaher\hapymaher-fd翻译\GPPGUI\Projects\hapimea_FD"
d = json.load(open(BASE + r"\ProblemOverview.json", encoding="utf-8"))

pat = re.compile(r"GPT字典 `(.+?)`->`(.+?)`")

MODE = sys.argv[1] if len(sys.argv) > 1 else "unused"
FILTER = sys.argv[2:] if len(sys.argv) > 2 else []

summary = defaultdict(list)
for e in d:
    for p in e["problems"]:
        m = pat.search(p)
        if not m:
            continue
        org, rep = m.group(1), m.group(2)
        inclusive = "但使用了" in p
        summary[(org, inclusive)].append(e)

if MODE == "summary":
    for (org, inc), v in sorted(summary.items(), key=lambda x: -len(x[1])):
        sp = Counter(x.get("name", "(旁白)") for x in v)
        print(f"{len(v):4d} {'包含' if inc else '独立'}  {org}->{rep}  {dict(sp)}")
elif MODE == "group":
    for (org, inc), v in sorted(summary.items(), key=lambda x: -len(x[1])):
        if FILTER and org not in FILTER:
            continue
        print("########", org, "包含" if inc else "独立", len(v))
        for e in v:
            print("---", e["filename"], e["index"], e.get("name", ""))
            print("JP:", e["original_text"])
            print("CN:", e["translated_view_text"])
