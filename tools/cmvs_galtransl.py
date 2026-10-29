#!/usr/bin/env python3
"""cmvs_galtransl.py — **清洗** `export_scripts.py` 导出的 JSON，并在 GalTransl 之间来回转。

形状对着 `Desktop/gal/tools/siglus_galtransl.py` 那套做：

    dump   : output/<game>/*.json  ->  gt_input/ + manifest.json + excluded.csv + name替换表.csv
    inject : gt_output/ + manifest.json  ->  output/<game>/translated/*.json

`export_scripts.py` 只负责把文本抠出来，**不清洗**；清洗在这里。

## ⭐ 先清洗，再送翻（别省这一步）

不洗的话，模型会白花 token 去「翻」`data\\pack\\bg.cpz`，而 `start.ps3` 整份
（路径表 + 窗口标题 `ハピメア RE.ver`）会被当台词翻，跟 §3.6 里单独打的那个标题补丁打架。

做法照 siglus 那套：**不可译的槽位根本不进 gt_input**，另出复核清单。
区别只是 siglus 有现成的 `kind=1/2/3` 列，CMVS 的导出没有，所以判据得自己定
（见下）。判据一律写进 `excluded.csv`，能逐条复核。

## 分类判据

| 槽位 | 处理 | 判据 |
|---|---|---|
| 台词 | 收 | `「…」` **或 `『…』`** 包起来的 |
| 说话人 | 收，挂成上一条的 `name` | **位置**：第 i 条是台词 ⇒ 第 i+1 条是它的说话人 |
| 旁白 / 地の文 | 收 | 有假名或汉字 |
| 章节标题 `- 第４話… -` | 收 | 同上 |
| 引擎规则串 | **不收** | 裸的、不带引号、且没有假名也没有汉字（`…―─`、`。、」』）！？”～ー♪`） |
| 资源路径 / 文件名 | **不收** | 含路径分隔符，或结尾像扩展名（`data\\pack\\bg.cpz`、`hapymaher_re.ico`） |
| 空槽 | **不收** | |

⚠ **`「…………」` 这种只有符号的台词必须收**（用户明确要求）——
它是对话的一部分，删了会断掉上下文连贯。所以规则里「没有假名也没有汉字」这一条
**只对不带引号的裸串生效**。

⚠ 判「有没有假名」时先把 `ー`（长音符，U+30FC）和 `・` 剔掉再查 ——
`。、」』）！？”～ー♪` 里的 `ー` 落在假名区，不剔的话这串会被误判成台词。
（GalTransl 自己的 skipNoJP 插件也是这么绕的。）

## 清洗

只洗**行首**的全角空格 `　`。实测 29,116 条是行首一个，但有 **4,157 条在句子中间**
（`事実ー！　事実だから…`），那是文意的一部分，动了就错。

## 用法

    uv run python tools/cmvs_galtransl.py dump   --game hapymaher --project test/galtransl/proj-hapymaher
    uv run python tools/cmvs_galtransl.py inject --game hapymaher --project test/galtransl/proj-hapymaher

详细说明见同目录的 README.md；整条流程见工作区根目录《汉化实施交接文档.md》§7.1。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent  # 项目根（不依赖开发机路径）
OUTPUT = ROOT / "output"
GALTRANSL = ROOT / "GalTransl-8.2.0"

MANIFEST_NAME = "manifest.json"
EXCLUDED_NAME = "excluded.csv"
NAME_TABLE_NAME = "name替换表.csv"          # GalTransl 固定读这个文件名
MANIFEST_VERSION = 1

# 台词引号。**两种都要认**：`「…」` 和 `『…』`。
# 引擎两种都用（『』多用于心声/引用），实测 209 句『』台词里有 203 句后面跟着说话人 ——
# 只认 `「」` 的话，这些台词说话人挂不上、纯符号的 `『―――――』` 还会被当引擎串剔掉。
# （GalTransl 的 analyse_dialogue 也是两种都剥，见 CSentense.py。）
QUOTE = re.compile(r"^「.*」$|^『.*』$", re.S)
KANA = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\uff66-\uff9f]")
KANJI = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# 结尾像扩展名：.cpz / .ico / .ver / .pb3 …（要求它不在 `「」` 里，见 exclude_reason）
EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,4}$")
BS = chr(92)
# 路径分隔符的反斜杠。**必须排掉 \n \r \t \\** —— 脚本里 `\n` 是换行码，
# 全语料就一条台词带它（`「――あら、強がっちゃって。\n素直に…」`），
# 不排的话这条真台词会被当成资源路径剔掉（真踩过）。
PATH_BS = re.compile(re.escape(BS) + r"(?![nrt" + re.escape(BS) + r"])")

STRIP_CHARS = "\u3000 \t\r\n"      # 和 build_encrypted.py 的 clean() 用同一套


# ─────────────────────────── 分类 ───────────────────────────

def is_dialogue_start(s: str) -> bool:
    """以 `「` / `『` 开头就算对白，**即使这一行没有闭合引号**。

    实测本体 14 行、FD 15 行对白只有开括号（引擎把后半句/闭括号放到了下一格，
    或者角色话没说完）。旧判据要求整行匹配 `^「.*」$`，这些行就认不出来，
    紧跟其后的说话人槽会被当成独立 message 送翻 —— 模型看到孤零零一个名字，
    于是报「疑似漏括号或错位的说话人标签」/「疑似角色名错位」。
    """
    return s.lstrip().startswith(("「", "『"))


def exclude_reason(s: str) -> str | None:
    """这条槽要不要送翻？返回 None = 要送；否则返回不送的理由（进复核清单）。"""
    if not s.strip():
        return "空槽"
    if PATH_BS.search(s):
        return "资源路径"
    if EXT_RE.search(s) and "「" not in s:
        return "资源文件名"
    if not is_dialogue_start(s):
        # 裸串：既没假名也没汉字 = 引擎规则串（`…―─`、禁则字符集）
        probe = s.replace("ー", "").replace("・", "")
        if not KANA.search(probe) and not KANJI.search(probe):
            return "非台词的符号串（引擎规则）"
    return None


NAME_MAX_LEN = 16


def looks_like_name(s: str) -> bool:
    """旁白 vs 说话人的形态判据，给下面「i+1 是说话人」的位置规则兜底。

    位置规则会误吞一种情况：台词后面紧跟的不是名字，而是旁白。实测 4 条：
        『翠京プラネタリウムへようこそ』 + '　その看板が丁度俺達の…立っていた。'
        『本当に、弥…』                         + '　それを俺は、試される事になった。'
    被吞掉的旁白会挂成 name，inject 时又强制写回原文 —— 等于**漏翻**。

    CMVS 的说话人槽都是短名字（最长 `黒髪の女性`、`アナウンサー` 这类，5 字），
    而误吞的旁白都以全角空格开头、带句读。`？？？`、`咲？` 是合法名字，所以
    这里不能一刀切禁问号，只禁句号/顿号 + 限长 + 禁行首缩进。
    """
    if len(s) > NAME_MAX_LEN:
        return False
    if s.startswith("　"):
        return False
    t = s.strip()
    if not t or "\n" in t or "。" in t or "、" in t:
        return False
    return True


def build_slots(entries: list[dict]):
    """把条目列表切成「送去翻译的单元」和「不送的」。

    返回 (units, excluded, taken)
        units   : [{"msg_idx": i, "name_idx": j 或 None}]
        excluded: [{"idx": i, "text": s, "why": r}]
        taken   : 已经作为别人的说话人收走了的下标
    """
    raw = [e.get("raw", "") for e in entries]

    # 说话人配对：位置决定 —— 第 i 条是台词 ⇒ 第 i+1 条是它的说话人。
    #
    # ⚠ 但**台词本身不可能是说话人**。有这种情形：电视/广播里的话用 `『』` 引用，
    # 引擎不给它说话人，它后面紧跟的就是下一句真台词：
    #     [189] '　『曇りのち雪。今年はホワイトクリスマス…』'   ← 无说话人
    #     [190] '「当たり前の予報じゃないですか」'              ← 台词
    #     [191] '景子'                                        ← 190 的说话人
    # 少了这个判据，190 会被当成 189 的说话人吞掉（实测本体 2 个文件、FD 0 个）。
    speaker_of: dict[int, int] = {}
    taken: set[int] = set()
    for i in range(len(raw) - 1):
        if i in taken or (i + 1) in taken:
            continue
        if (is_dialogue_start(raw[i]) and not is_dialogue_start(raw[i + 1])
                and looks_like_name(raw[i + 1])):
            speaker_of[i] = i + 1
            taken.add(i + 1)

    units, excluded = [], []
    for i, s in enumerate(raw):
        if i in taken:
            continue
        why = exclude_reason(s)
        if why:
            excluded.append({"idx": i, "text": s, "why": why})
            continue
        # name_idx 写在 msg_idx 前面 —— 只是让人读 manifest 时顺眼，
        # 取值一律按 key，顺序不影响任何逻辑。
        u = {"name_idx": speaker_of.get(i), "msg_idx": i}
        units.append(u)
    return units, excluded, taken


def clean_text(s: str) -> str:
    """只洗行首/行尾的 `　` 和空白；**句子中间的 `　` 保持不动**（那是文意）。"""
    return s.strip(STRIP_CHARS)


# ─────────────────────────── I/O ───────────────────────────

def load_entries(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_entries(path: Path, data: dict) -> None:
    # 保持和 PS3_TextEditor 一致：UTF-8 with BOM
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8-sig")


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────── dump ───────────────────────────

def cmd_dump(game: str, project: Path) -> int:
    src_dir = OUTPUT / game
    gt_input = project / "gt_input"
    gt_input.mkdir(parents=True, exist_ok=True)

    files = sorted(src_dir.glob("*.json"))
    if not files:
        print(f"错误：{src_dir} 下没有 json", file=sys.stderr)
        return 1

    manifest = {
        "version": MANIFEST_VERSION,
        "game": game,
        "source_dir": str(src_dir),
        "strip_chars": STRIP_CHARS,
        "files": {},
    }
    name_counter: Counter[str] = Counter()
    excluded_rows: list[list] = []
    n_entries = n_units = n_named = n_taken = n_quote = 0
    why_counter: Counter[str] = Counter()
    empty_files: list[str] = []

    for src in files:
        entries = load_entries(src)["Scenario"]
        n_entries += len(entries)
        units, excluded, taken = build_slots(entries)

        out = []
        for u in units:
            msg = clean_text(entries[u["msg_idx"]].get("raw", ""))
            # name 写在 message **前面**：JSON 的键顺序不影响读回（一律按 key 取），
            # 但写成 `{"message": …, "name": …}` 读起来像名字吊在句子后面，很别扭。
            item: dict = {}
            if u["name_idx"] is not None:
                nm = entries[u["name_idx"]].get("raw", "")
                item["name"] = nm
                name_counter[nm] += 1
                n_named += 1
            item["message"] = msg
            out.append(item)

        if not out:
            empty_files.append(src.name)
        else:
            _write_json(gt_input / src.name, out)

        for e in excluded:
            why_counter[e["why"]] += 1
            excluded_rows.append([src.name, e["idx"], e["text"], e["why"]])

        manifest["files"][src.name] = {
            "total": len(entries),
            "units": units,
        }
        n_units += len(units)
        n_taken += len(taken)

        # 「不漏台词」核对：本文件里所有「」台词都应该进了 units
        q = sum(1 for e in entries if is_dialogue_start(e.get("raw", "")))
        q_kept = sum(1 for u in units
                     if is_dialogue_start(entries[u["msg_idx"]].get("raw", "")))
        n_quote += q
        if q != q_kept:
            print(f"  ✗ {src.name}: 「」台词 {q} 句，只送进 {q_kept} 句 —— 有台词被误排除！")

    _write_json(project / MANIFEST_NAME, manifest)

    # 未纳入翻译的复核清单
    with io.open(project / EXCLUDED_NAME, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["file", "idx", "original", "why"])
        w.writerows(excluded_rows)

    # 说话人表（GalTransl 固定读这个名字；留空它自己也会生成）
    with io.open(project / NAME_TABLE_NAME, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(["SRC_Name", "DST_Name", "Count"])
        for nm, cnt in sorted(name_counter.items(), key=lambda x: (-x[1], x[0])):
            w.writerow([nm, "", cnt])

    print(f"=== dump 完成：{game} ===")
    print(f"  文件      : {len(files)} 个")
    print(f"  原文条目  : {n_entries}")
    print(f"  送入翻译  : {n_units} 条（其中带说话人 {n_named} 条）")
    print(f"  说话人槽  : {n_taken} 条（挂到上一条的 name 上，不单独占条目）")
    print(f"  不送翻译  : {len(excluded_rows)} 条")
    for why, cnt in why_counter.most_common():
        print(f"                {why:<26} {cnt}")
    print(f"  「」台词  : 源 {n_quote} 句 → 全部进入 gt_input"
          if n_quote else "  「」台词  : 无")
    if empty_files:
        print(f"  整个文件没东西可翻（未生成 gt_input）：{'、'.join(empty_files)}")
    print()
    print(f"产出：{gt_input}/*.json")
    print(f"      {project / MANIFEST_NAME}     槽位映射，inject 靠它")
    print(f"      {project / EXCLUDED_NAME}   未纳入的，**请扫一眼**")
    print(f"      {project / NAME_TABLE_NAME} 说话人表（填了 DST 就写回译名；留空保留原文）")
    return 0


# ─────────────────────────── inject ───────────────────────────

def cmd_inject(game: str, manifest_path: Path, gt_output: Path,
               out_dir: Path, allow_partial: bool) -> int:
    if not manifest_path.is_file():
        print(f"错误：找不到 {manifest_path}，请先跑 dump", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not gt_output.is_dir():
        print(f"错误：找不到 {gt_output}", file=sys.stderr)
        return 1

    # 原文目录：优先用本项目里的 output/<game>（由 export_scripts.py 生成），
    # 这样 manifest 里记录的开发机绝对路径不会绑死这个仓库；
    # 找不到才回退到 manifest 里的 source_dir（兼容旧 manifest）。
    src_dir = OUTPUT / game
    if not src_dir.is_dir():
        src_dir = Path(manifest["source_dir"])
        print(f"  注意：{OUTPUT / game} 不存在，回退到 manifest 记录的 {src_dir}")
        print("        如果也找不到，先跑 tools/export_scripts.py 导出原文")

    n_files = n_applied = n_kept = n_failed = n_nameinj = n_name_trans = 0
    miss, bad, unchanged_files = [], [], []
    failed_samples: list[str] = []
    nameinj_samples: list[str] = []

    for fname, info in manifest["files"].items():
        src = src_dir / fname
        jpath = gt_output / fname
        if not src.is_file():
            miss.append((fname, "原始 JSON 缺失"))
            continue
        if not jpath.is_file():
            # 没有译文的（`start.ps3` 这种整份是引擎配置的、`intcode.ps3` 空文件）
            # 也要原样写出来：构建读的是**整个目录**，缺文件就断了。
            data = load_entries(src)
            for e in data["Scenario"]:
                e["tra"] = e.get("raw", "")
            save_entries(out_dir / fname, data)
            unchanged_files.append(fname)
            n_files += 1
            continue

        trans = json.loads(jpath.read_text(encoding="utf-8"))
        units = info["units"]
        if not isinstance(trans, list) or len(trans) != len(units):
            got = len(trans) if isinstance(trans, list) else "非列表"
            bad.append((fname, f"条目数不符：gt_output {got} vs manifest {len(units)}"))
            if not allow_partial:
                continue

        data = load_entries(src)
        entries = data["Scenario"]
        for n, u in enumerate(units):
            if n >= len(trans):
                break
            item = trans[n]
            if not isinstance(item, dict) or "message" not in item:
                bad.append((fname, f"第 {n} 条缺 message 字段"))
                break
            i = u["msg_idx"]
            tra = item.get("message") or ""
            if KANA.search(tra.replace("ー", "")):
                n_failed += 1
                if len(failed_samples) < 8:
                    failed_samples.append(f"{fname}:{i} {tra[:36]!r}")
            # 防「说话人被写进对话」：网上旧补丁就栽在这 —— 对话槽里只剩
            # `「高原」`/`「彻」` 这种名字，原文其实是一整句台词。典型是导入时
            # 名字/台词错位，或者模型把 name 当成了 message。这里只报警，不改写。
            j = u.get("name_idx")
            nm_src = entries[j].get("raw", "") if j is not None else ""
            nm_dst = (item.get("name") or "").strip()
            if nm_src or nm_dst:
                name_forms = set()
                for nm in (nm_src, nm_dst):
                    if nm:
                        name_forms |= {nm, f"「{nm}」", f"『{nm}』"}
                if tra.strip() in name_forms and entries[i].get("raw", "").strip() not in name_forms:
                    n_nameinj += 1
                    if len(nameinj_samples) < 8:
                        nameinj_samples.append(f"{fname}:{i} {tra[:24]!r} ← 原句 {entries[i].get('raw','')[:28]!r}")
            entries[i]["tra"] = tra
            n_applied += 1
            # 说话人也写译文：GPP/GalTransl 的 name 字段已经按 NameTable 译好；
            # 没有就退回原文（用户要的是全汉化，包括说话人标签）。
            if j is not None:
                if nm_dst:
                    entries[j]["tra"] = nm_dst
                    n_name_trans += 1
                else:
                    entries[j]["tra"] = entries[j].get("raw", "")
                    n_kept += 1

        # 没进 units 的槽位（规则串、路径、空槽）一律写回原文
        unit_msgs = {u["msg_idx"] for u in units}
        unit_names = {u["name_idx"] for u in units if u.get("name_idx") is not None}
        for k, e in enumerate(entries):
            if k in unit_msgs or k in unit_names:
                continue
            e["tra"] = e.get("raw", "")
            n_kept += 1

        save_entries(out_dir / fname, data)
        n_files += 1

    print(f"=== inject 完成：{game} ===")
    print(f"  输出目录  : {out_dir}")
    print(f"  成功文件  : {n_files}")
    print(f"  写入槽位  : {n_applied}（说话人译名 {n_name_trans} 条；另 {n_kept} 个槽位写回原文）")
    if unchanged_files:
        print(f"  无译文原样写出：{'、'.join(unchanged_files)}")
    if n_failed:
        print(f"  ⚠ 译文里还残留假名 {n_failed} 条，样例：")
        for s in failed_samples:
            print(f"      {s}")
    if n_nameinj:
        print(f"  ⚠ 疑似把说话人写进了对话 {n_nameinj} 条（旧补丁的 bug 形态），样例：")
        for s in nameinj_samples:
            print(f"      {s}")
    for label, items in (("跳过", miss), ("异常", bad)):
        if not items:
            continue
        print(f"  !! {label} {len(items)} 个：")
        for f, why in items[:10]:
            print(f"      {f:<28} {why}")
    return 0 if not (miss or bad) else 2


# ─────────────────────────── CLI ───────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("dump", help="我们的 JSON -> gt_input + manifest + 复核清单")
    d.add_argument("--game", required=True, help="output 下的子目录名")
    d.add_argument("--project", required=True, type=Path)

    j = sub.add_parser("inject", help="gt_output + manifest -> 回写译文")
    j.add_argument("--game", required=True)
    j.add_argument("--project", type=Path, default=None,
                   help="GalTranslPP 工程目录（默认从它读 manifest.json 与 gt_output/）")
    j.add_argument("--manifest", type=Path, default=None,
                   help="manifest 路径（默认 <project>/manifest.json）")
    j.add_argument("--gt-output", type=Path, default=None,
                   help="译文目录（默认 <project>/gt_output）")
    j.add_argument("--out", type=Path, default=None,
                   help="译文写哪（默认 output/<game>/translated/，不动原始导出）")
    j.add_argument("--allow-partial", action="store_true",
                   help="条目数对不上时也按位置尽力对齐（默认跳过该文件）")

    a = ap.parse_args()
    if a.cmd == "dump":
        return cmd_dump(a.game, a.project)
    manifest = a.manifest or (a.project / MANIFEST_NAME if a.project else None)
    gt_output = a.gt_output or (a.project / "gt_output" if a.project else None)
    if manifest is None or gt_output is None:
        ap.error("inject 需要 --project，或同时给出 --manifest 与 --gt-output")
    out = a.out or (OUTPUT / a.game / "translated")
    out.mkdir(parents=True, exist_ok=True)
    return cmd_inject(a.game, manifest, gt_output, out, a.allow_partial)


if __name__ == "__main__":
    sys.exit(main())
