# -*- coding: utf-8 -*-
"""应用用户选定的 2-6、8-9、12 条译文修改。
同步 transl_cache 的 translated_raw_text / translated_view_text 与 gt_output 的 message。
修改前先备份到 test/fd_fix_backup/<timestamp>/。
"""
import json
import os
import shutil
from datetime import datetime

BASE = r"C:\Users\DMS\Desktop\Hapymaher\hapymaher-fd翻译\GPPGUI\Projects\hapimea_FD"
BACKUP_ROOT = r"C:\Users\DMS\Desktop\Hapymaher\test\fd_fix_backup"

CHANGES = [
    # (number, filename, index, old, new)
    (2, "s04d01.ps3.json", 374,
     "体内的异物抽出后，景子这次是真的浑身脱力，软绵绵地陷进了床铺里。",
     "肉棒从阴道内抽离后，景子这次是真的浑身脱力，软绵绵地陷进了床铺里。"),
    (3, "s01p07.ps3.json", 301,
     "「真的假的……。喂，透，这认真劲儿是怎么回事啊」",
     "「真的假的……。喂，透，这死正经的家伙是怎么回事啊」"),
    (4, "s05a01e.ps3.json", 50,
     "「……被以前的你推倒，任凭摆布之后直接做了，是吧？」",
     "「……被以前的有子推倒，任凭摆布之后直接做了，是吧？」"),
    (5, "sr0202.ps3.json", 76,
     "「是啊，因为我既不是什么好姐姐，也不是什么好欧尼酱。现在我要优先确保自己和咲的安心」",
     "「是啊，因为我既不是什么好姐姐，也不是什么好哥哥。现在我要优先确保自己和咲的安心」"),
    (6, "s04x04.ps3.json", 86,
     "「谁让我就是你这个狡猾家伙的欧尼酱呢」",
     "「谁让我就是你这个狡猾家伙的哥哥呢」"),
    (8, "sr0502.ps3.json", 70,
     "「毕竟你自尊心很高嘛。为什么欧尼酱是那副性子，却养出了这样的妹妹呢……」",
     "「毕竟你自尊心很高嘛。明明你哥哥是那副性子，怎么会养出你这样的妹妹呢……」"),
    (9, "s05b01b.ps3.json", 311,
     "「哈啊、哈啊……啊啊啊……小、透……」",
     "「哈啊、哈啊……啊啊啊……透、酱……」"),
    (12, "s05e99.ps3.json", 108,
     "「这种事不应该是欧尼酱的职责吗？」",
     "「这种事不应该是当哥哥的职责吗？」"),
]


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = os.path.join(BACKUP_ROOT, stamp)
    os.makedirs(backup_dir, exist_ok=True)

    # 1. 备份涉及的 16 个文件
    for _, fn, _, _, _ in CHANGES:
        for sub in ("transl_cache", "gt_output"):
            src = os.path.join(BASE, sub, fn)
            dst = os.path.join(backup_dir, sub, fn)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    print("backup:", backup_dir)

    # 2. 应用替换
    for num, fn, idx, old, new in CHANGES:
        cache_path = os.path.join(BASE, "transl_cache", fn)
        out_path = os.path.join(BASE, "gt_output", fn)

        # 先验证
        cache = json.load(open(cache_path, encoding="utf-8"))
        entry = [x for x in cache if x["index"] == idx]
        assert len(entry) == 1, (fn, idx, "index not unique")
        assert entry[0]["translated_raw_text"] == old, (fn, idx, "raw mismatch")
        assert entry[0]["translated_view_text"] == old, (fn, idx, "view mismatch")
        out = json.load(open(out_path, encoding="utf-8"))
        assert out[idx]["message"] == old, (fn, idx, "gt mismatch")

        raw = open(cache_path, encoding="utf-8", newline="").read()
        assert raw.count(old) == 2, (fn, idx, "cache occurrence", raw.count(old))
        raw = raw.replace(old, new)
        open(cache_path, "w", encoding="utf-8", newline="").write(raw)

        graw = open(out_path, encoding="utf-8", newline="").read()
        assert graw.count(old) == 1, (fn, idx, "gt occurrence", graw.count(old))
        graw = graw.replace(old, new)
        open(out_path, "w", encoding="utf-8", newline="").write(graw)

        print(f"applied #{num}: {fn}:{idx}")

    # 3. 校验
    for num, fn, idx, old, new in CHANGES:
        cache = json.load(open(os.path.join(BASE, "transl_cache", fn), encoding="utf-8"))
        e = [x for x in cache if x["index"] == idx][0]
        assert e["translated_raw_text"] == new and e["translated_view_text"] == new, (fn, idx)
        out = json.load(open(os.path.join(BASE, "gt_output", fn), encoding="utf-8"))
        assert out[idx]["message"] == new, (fn, idx)
    print("all %d changes verified" % len(CHANGES))


if __name__ == "__main__":
    main()
