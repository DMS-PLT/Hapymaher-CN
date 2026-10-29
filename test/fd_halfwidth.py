# -*- coding: utf-8 -*-
"""把 transl_cache / gt_output 译文中的全角英文、数字、・ 转成半角。

转换范围：
- 全角大写/小写字母 Ａ-Ｚ ａ-ｚ -> A-Z a-z
- 全角数字 ０-９ -> 0-9
- ・（U+30FB）/ ･（U+FF65）-> ·（U+00B7，与现有译文和字典一致）
- 数字之间的全角斜杠 ／ -> /、全角句点 ． -> .
- 英文字母/数字之间的全角空格 -> 半角空格（只影响英文短语内部）

只改 translated_raw_text / translated_view_text 与 gt_output 的 message，
不动 original_text / pre_processed_text / problems。
修改前备份到 test/fd_fix_backup/<timestamp>_halfwidth/。
"""
import json
import glob
import os
import re
import shutil
from datetime import datetime

BASE = r"C:\Users\DMS\Desktop\Hapymaher\hapymaher-fd翻译\GPPGUI\Projects\hapimea_FD"
BACKUP_ROOT = r"C:\Users\DMS\Desktop\Hapymaher\test\fd_fix_backup"


def convert(s: str) -> str:
    out = []
    for i, ch in enumerate(s):
        o = ord(ch)
        if 0xFF21 <= o <= 0xFF3A or 0xFF41 <= o <= 0xFF5A or 0xFF10 <= o <= 0xFF19:
            out.append(chr(o - 0xFEE0))
        elif ch in ("・", "･"):
            out.append("·")
        elif ch == "／" and 0 < i < len(s) - 1 and s[i - 1].isdigit() and s[i + 1].isdigit():
            out.append("/")
        elif ch == "．" and 0 < i < len(s) - 1 and s[i - 1].isdigit() and s[i + 1].isdigit():
            out.append(".")
        else:
            out.append(ch)
    s = "".join(out)
    # 英文短语内部的全角空格（只处理左右都是 ASCII 字母/数字的情况）
    s = re.sub(r"(?<=[A-Za-z0-9])\u3000(?=[A-Za-z0-9])", " ", s)
    return s


def main():
    targets = []  # (filename, [indices])
    for f in glob.glob(os.path.join(BASE, "transl_cache", "*.json")):
        fn = os.path.basename(f)
        cache = json.load(open(f, encoding="utf-8"))
        indices = []
        for e in cache:
            if convert(e.get("translated_raw_text", "")) != e.get("translated_raw_text", "") or \
               convert(e.get("translated_view_text", "")) != e.get("translated_view_text", ""):
                indices.append(e["index"])
        if indices:
            targets.append((fn, indices))

    print("files:", len(targets), "entries:", sum(len(x[1]) for x in targets))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S") + "_halfwidth"
    backup_dir = os.path.join(BACKUP_ROOT, stamp)
    os.makedirs(backup_dir, exist_ok=True)

    for fn, indices in targets:
        for sub in ("transl_cache", "gt_output"):
            src = os.path.join(BASE, sub, fn)
            dst = os.path.join(backup_dir, sub, fn)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    total_changed = 0
    for fn, indices in targets:
        cache_path = os.path.join(BASE, "transl_cache", fn)
        out_path = os.path.join(BASE, "gt_output", fn)
        cache = json.load(open(cache_path, encoding="utf-8"))
        out = json.load(open(out_path, encoding="utf-8"))
        idx_set = set(indices)
        for e in cache:
            if e["index"] not in idx_set:
                continue
            old_raw = e.get("translated_raw_text", "")
            old_view = e.get("translated_view_text", "")
            new_raw = convert(old_raw)
            new_view = convert(old_view)
            if out[e["index"]].get("message") == old_view:
                out[e["index"]]["message"] = new_view
            else:
                raise AssertionError((fn, e["index"], "gt_output != view before change"))
            e["translated_raw_text"] = new_raw
            e["translated_view_text"] = new_view
            total_changed += 1
        with open(cache_path, "w", encoding="utf-8", newline="") as f:
            f.write(json.dumps(cache, ensure_ascii=False, indent=2))
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(json.dumps(out, ensure_ascii=False, indent=2))

    print("changed entries:", total_changed)
    print("backup:", backup_dir)


if __name__ == "__main__":
    main()
