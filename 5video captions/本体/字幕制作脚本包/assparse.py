# -*- coding: utf-8 -*-
"""op.ass 解析器 —— 保留句中半句气口空格与逐音节卡拉OK时间。"""
import re
from dataclasses import dataclass, field
from typing import List

import config as C

_K_RE = re.compile(r"\{([^}]*)\}([^{]*)")
_KTAG_RE = re.compile(r"\\[kK][fo]?(\d+)")


def _ts(s: str) -> float:
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


@dataclass
class Syl:
    text: str
    start: float
    end: float

    @property
    def dur(self) -> float:
        return self.end - self.start


@dataclass
class Line:
    li: int
    start: float
    end: float
    jp: str
    cn: str
    syls: List[Syl] = field(default_factory=list)

    @property
    def dur(self) -> float:
        return self.end - self.start


def _parse_syllables(text: str, line_start: float):
    syls: List[Syl] = []
    cursor = line_start
    plain = []
    for tag, seg in _K_RE.findall(text):
        m = _KTAG_RE.search(tag)
        cs = int(m.group(1)) if m else 0
        dur = cs / 100.0
        if seg.strip() == "":
            # 句中独立空白音节 (如 {\k33} ) 保留为单个半角气口空格
            if seg and plain and plain[-1] != " ":
                plain.append(" ")
                syls.append(Syl(" ", cursor, cursor + dur))
        else:
            tok = seg.strip()
            plain.append(tok)
            syls.append(Syl(tok, cursor, cursor + dur))
        cursor += dur
    # 去掉首尾可能残留的空格
    while plain and plain[-1] == " ":
        plain.pop()
        syls.pop()
    return "".join(plain), syls


def load_lines(ass_path: str = None) -> List[Line]:
    path = ass_path or C.ASS_FILE
    raw = open(path, encoding="utf-8-sig").read().splitlines()
    lines: List[Line] = []
    for idx, ln in enumerate(raw):
        if not ln.startswith("Dialogue:"):
            continue
        b = ln.split(",", 9)
        start, end, textfield = _ts(b[1]), _ts(b[2]), b[9]
        jp, syls = _parse_syllables(textfield, start)
        cn = ""
        for nxt in raw[idx + 1:]:
            s = nxt.strip()
            if not s:
                continue
            if s.startswith("; CN:"):
                cn = s[5:].strip()
            break
        lines.append(Line(len(lines), start, end, jp, cn, syls))
    return lines
