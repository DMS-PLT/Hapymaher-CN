# -*- coding: utf-8 -*-
"""ed 字幕解析 —— 日文正文来自 Dialogue, 中文译文来自紧随其后的 `; CN:` 注释行。"""
import re
from dataclasses import dataclass

_TAG_RE = re.compile(r"\{[^}]*\}")


def _ts(s: str) -> float:
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _clean(text: str) -> str:
    text = _TAG_RE.sub("", text)
    text = text.replace("\\N", " ").replace("\\n", " ").replace("\\h", " ")
    # 全角空格 (U+3000) 换半角, 气口留白收紧一点, 长句更省横向空间
    text = text.replace("\u3000", " ")
    while "  " in text:
        text = text.replace("  ", " ")
    return text.strip()


@dataclass
class Line:
    idx: int
    start: float
    end: float
    jp: str
    cn: str

    @property
    def dur(self) -> float:
        return self.end - self.start


def load_lines(ass_path: str):
    raw = open(ass_path, encoding="utf-8-sig").read().splitlines()
    out = []
    for i, ln in enumerate(raw):
        if not ln.startswith("Dialogue:"):
            continue
        b = ln.split(",", 9)
        start, end = _ts(b[1]), _ts(b[2])
        jp = _clean(b[9])
        if not jp:
            continue                      # 纯间奏空行, 不排版
        cn = ""
        for nxt in raw[i + 1:]:
            s = nxt.strip()
            if not s:
                continue
            if s.startswith("; CN:"):
                cn = _clean(s[5:])
            break
        out.append(Line(len(out), start, end, jp, cn))
    return out
