# -*- coding: utf-8 -*-
"""解析 FDop.ass 的非空卡拉OK句轴、\\k 音节 (含空 \\k 休止拍与全角空格气口) 及 `; CN:` 中译。"""
import os
import re
from dataclasses import dataclass, field
import config as C


@dataclass
class Syl:
    start: float
    end: float
    dur: float
    text: str


@dataclass
class AssLine:
    li: int
    start: float
    end: float
    jp: str
    cn: str
    syls: list = field(default_factory=list)


def _ts(s: str) -> float:
    h, m, sec = s.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


_K_RE = re.compile(r"\{\\k(\d+)\}([^{]*)")


def _norm_spaces(txt: str) -> str:
    # 将全角空格 \u3000 统一规范为半角空格 ' ' (作为句中气口留白标记)
    return txt.replace("\u3000", " ")


def load_lines(ass_path: str = None) -> list[AssLine]:
    if ass_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        ass_path = os.path.normpath(os.path.join(here, C.ASS_FILE))

    with open(ass_path, "r", encoding="utf-8-sig") as f:
        raw_lines = [ln.rstrip("\r\n") for ln in f]

    out = []
    i = 0
    while i < len(raw_lines):
        ln = raw_lines[i]
        if ln.startswith("Dialogue:"):
            parts = ln.split(",", 9)
            st = _ts(parts[1])
            ed = _ts(parts[2])
            body = parts[9]
            if not body.strip():
                i += 1
                continue

            syls = []
            jp_chars = []
            t_cur = st
            for m in _K_RE.finditer(body):
                dur = int(m.group(1)) * 0.01
                txt = _norm_spaces(m.group(2))
                # 若是纯休止符 {\k74} (txt == ""), 仅推进时间游标 t_cur!
                if txt:
                    syls.append(Syl(t_cur, t_cur + dur, dur, txt))
                    jp_chars.append(txt)
                t_cur += dur

            jp_plain = "".join(jp_chars) if jp_chars else _norm_spaces(re.sub(r"\{[^}]*\}", "", body))

            cn_txt = ""
            if i + 1 < len(raw_lines):
                nxt = raw_lines[i + 1].strip()
                if nxt.startswith("; CN:"):
                    cn_txt = _norm_spaces(nxt[5:].strip())
                    i += 1

            out.append(AssLine(len(out), st, ed, jp_plain, cn_txt, syls))
        i += 1
    return out
