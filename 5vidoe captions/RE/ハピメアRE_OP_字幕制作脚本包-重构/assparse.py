# -*- coding: utf-8 -*-
"""opre.ass 解析器 —— 整个特效字幕包的唯一事实来源。

从 Aegisub 导出的 opre.ass 读取:
  - 每句日文的句级时间 (start/end)
  - 逐音节卡拉OK时间 (\\k 厘秒, 累加成每个音节的 [k_start, k_end])
  - 每句对应的中文译文 (写在 ASS 的 "; CN:" 注释行里, 与 Dialogue 一一对应)

对外只暴露 load_lines() -> List[Line]; 渲染脚本不再碰任何 json。
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple

DEFAULT_ASS = "../opre.ass"

_K_RE = re.compile(r"\{([^}]*)\}([^{]*)")        # {标签}后面跟的文本
_KTAG_RE = re.compile(r"\\[kK][fo]?(\d+)")       # \k \kf \ko \K


def _ts(s: str) -> float:
    """ASS 时间串 h:mm:ss.cc -> 秒"""
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


@dataclass
class Syl:
    """一个卡拉OK音节"""
    text: str          # 音节文字 (已去掉多余空白)
    start: float       # 该音节在视频时间轴上的起点 (秒)
    end: float         # 终点 (秒)

    @property
    def dur(self) -> float:
        return self.end - self.start


@dataclass
class Line:
    li: int                        # 行号 0..n-1
    start: float                   # 句起点 (秒)
    end: float                     # 句终点 (秒)
    jp: str                        # 日文整句 (无标签, 无多余空白)
    cn: str                        # 中文译文
    syls: List[Syl] = field(default_factory=list)

    @property
    def dur(self) -> float:
        return self.end - self.start

    def word_times(self) -> List[Tuple[str, float]]:
        """兼容旧接口: [(音节, 起点秒), ...]"""
        return [(s.text, s.start) for s in self.syls]


def _parse_syllables(text: str, line_start: float) -> Tuple[str, List[Syl]]:
    """解析一条 Dialogue 的 Text 字段里的 \\k 卡拉OK, 返回 (整句日文, 音节表)。

    Aegisub 里偶尔会在 \\k 片段前混进多余空格 (如 '{\\k27} 無'),
    这里把每个音节两端的空白 strip 掉, 但时间照常累加 (空白也占时长)。
    """
    syls: List[Syl] = []
    cursor = line_start
    plain = []
    for tag, seg in _K_RE.findall(text):
        m = _KTAG_RE.search(tag)
        cs = int(m.group(1)) if m else 0          # 厘秒
        dur = cs / 100.0
        token = seg.strip()
        if token:                                  # 跳过纯空白音节, 但时长仍计入
            syls.append(Syl(token, cursor, cursor + dur))
            plain.append(token)
        cursor += dur
    return "".join(plain), syls


def load_lines(ass_path: str = DEFAULT_ASS, cn_texts: List[str] = None) -> List[Line]:
    """解析 ASS -> Line 列表。

    中文译文优先级:
      1) 显式传入的 cn_texts (长度须与行数一致)
      2) ASS 里紧跟在该 Dialogue 下一行的 '; CN: 译文' 注释
      3) 空串
    """
    raw = open(ass_path, encoding="utf-8-sig").read().splitlines()
    lines: List[Line] = []
    for idx, ln in enumerate(raw):
        if not ln.startswith("Dialogue:"):
            continue
        b = ln.split(",", 9)
        start, end, textfield = _ts(b[1]), _ts(b[2]), b[9]
        jp, syls = _parse_syllables(textfield, start)
        li = len(lines)
        cn = ""
        if cn_texts and li < len(cn_texts):
            cn = cn_texts[li]
        else:
            # 向后找紧邻的 '; CN:' 注释 (允许中间夹空行)
            for nxt in raw[idx + 1:]:
                t = nxt.strip()
                if not t:
                    continue
                if t.startswith("; CN:") or t.startswith(";CN:"):
                    cn = t.split(":", 1)[1].strip()
                break
        lines.append(Line(li, start, end, jp, cn, syls))
    return lines


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ASS
    for L in load_lines(path):
        print(f"[{L.li:2d}] {L.start:6.2f}-{L.end:6.2f}  {L.jp}")
        print(f"      CN: {L.cn}")
        print("      " + " | ".join(f"{s.text}@{s.start:.2f}" for s in L.syls))
