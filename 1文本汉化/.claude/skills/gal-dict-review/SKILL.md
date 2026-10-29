---
name: gal-dict-review
description: 独立审查一份已经生成好的 galgame 项目 GPT 字典。只出报告，不改文件。主审 GalTransl++ 的 ProjGptDict.toml + NameTable.toml，并对 GalTransl 8.4.2 / 喵喵的 TSV 做格式复检。用语料证据、风险分层和子代理对抗审查，找出假词条、备注失实、撞名、子串污染、高频称谓漏收等问题。
---

# gal-dict-review

> **本 skill 只是审查的起点，不是上限。**
> 除了下面列出的脚本和步骤，你可以用**任何你认为有效的方法**来审查这份字典：
> 自己写临时脚本、换检索角度、对照其它资料、开更多视角的子代理、抽样上下文、
> 统计共现、检查原文与译文的语义偏差、做反向翻译验证……方法不限。
> 唯一的要求是：**每条结论都要能引用 `[文件#序号]` 证据，给不出证据就标「不确定」。**

## 0. 定位

**只审不改。**

- 产出：`review_report.md`、`risk_entries.tsv`、`evidence.tsv`、`missing_honorifics.tsv`
- 不产出：修正版字典、覆盖原文件、自动删词
- 与 `gal-dict-merge` 分开：审查者**独立读原文**，不复用生产阶段的备注当证据
- 中间产物统一放 `<工作区>/test/dictwork/`，不要散落在 `翻译/` 根目录

审查的心态是“反驳”，不是“确认”。默认怀疑，要求引用 `[文件#序号]`。

---

## 1. 输入

| 项 | 必需 | 说明 |
|---|---|---|
| 主字典 | ✅ | GPP 的 `ProjGptDict.toml`（也支持 TSV） |
| 姓名表 | ✅（GPP） | `NameTable.toml` |
| 原文目录 | ✅ | `gt_input/*.json` |
| 人物表 | 可选 | 主要角色、别名、基名 |
| 自造词表 | 可选 | 梦境术语、组织、招式 |
| VNDB 信息 | 可选 | 只取别名 / 性别 / 关系 |
| GT / 喵喵 TSV | 可选 | 只做格式复检 |

主审范围：**GPP 的 `ProjGptDict.toml` + `NameTable.toml`**。
GT / 喵喵 TSV：只检查表头、`#` 注释、Tab、条数，不做语义审查。

---

## 2. 流程

### 2.1 冻结与备份

审查期间不改原文件。先确认：

- 字典路径；
- 姓名表路径；
- 原文目录；
- 目标工具（默认 GPP）。

### 2.2 建语料

```bash
python scripts/build_corpus.py <gt_input> -o _dictwork/corpus.txt
```

### 2.3 机械门禁

```bash
python scripts/check_dict.py ProjGptDict.toml \
    --corpus _dictwork/corpus.txt --target gpp --batch-size 16
```

要求 **0 ERROR**。WARN 全部记录进报告，不忽略。

### 2.4 风险分层

```bash
python scripts/audit.py --dict ProjGptDict.toml --corpus _dictwork/corpus.txt \
    --characters characters.txt --coined coined.txt \
    --out risk_entries.tsv
```

覆盖策略：

| 优先级 | 范围 |
|---|---|
| **P0** | zero_hit / 主要角色 / 自造词 → **100% 审** |
| **P1** | name_only / body_heavy / short_word / 敬称 / 撞名 → **100% 审** |
| **P2** | 低频 / 派生不一致 / 同 rep 多 org → 抽样审 |

### 2.5 证据表

```bash
python scripts/evidence.py --dict ProjGptDict.toml \
    --corpus _dictwork/corpus.txt --samples 3 --out evidence.tsv
```

每个 org 给出：

- 正文命中 / name 命中；
- 说话人分布；
- 最多 3 条 `[文件#序号] 说话人| 正文` 证据；
- flags：`zero_hit` / `name_only` / `body_heavy` / `short_word`。

### 2.6 缺失高频词扫描

```bash
python scripts/scan_honorifics.py --input gt_input \
    --dict ProjGptDict.toml --name-table NameTable.toml \
    --only-missing --out missing_honorifics.tsv
```

扫描「名字 + 敬称」组合，输出字典/姓名表都没覆盖的候选：

```text
suffix  name  combined  count  in_dict  in_name_table  status
さん    高原  高原さん   332    no       no             候选
先輩   ルートウィッジ ルートウィッジ先輩 31 no no       候选
```

这是目前 `check_dict.py` 查不出来的“原文高频、但字典根本没有”的问题。

### 2.7 对抗审查（子代理）

开 2～3 个独立子代理，每个只负责一个视角。要求：

1. 逐条读 `risk_entries.tsv` 中分配给自己的条目；
2. 用 `q.py` / `evidence.tsv` 查原文；
3. **每条结论必须引用 `[文件#序号]`**；
4. 给不出证据就标“不确定”，不许写成确定语气；
5. 输出 `severity | org | 问题 | 证据 | 建议`。

#### 视角 A · 事实

> 你的任务是**反驳**字典里的备注。逐条问：“这句话在原文里有证据吗？”
> 特别注意：生成器幻觉、把普通语法当成设定词、把断句当成独立称呼、
> 只看单句就写“平时/总是”、VNDB 的年级 tag 与原文学制不符。

#### 视角 B · 一致性

> 检查：
> - 同一人物的所有写法是否共享同一个基名；
> - 有没有两个不同角色共用同一个中文名；
> - 长短词译文是否保持派生关系；
> - 全角/半角、旧字体、假名/汉字变体是否都覆盖；
> - `〜先輩`、`〜さん`、`〜様` 的译法是否跨条目统一。

#### 视角 C · 运行时

> 检查 GPP 的实际行为：
> - 短词是否在正文高频命中，污染提示词；
> - `name_only` 条目是否应该放 `NameTable.toml`；
> - `useGPTDictToReplaceName` 与 NameTable 的顺序是否会让姓名替换被绕过；
> - 每批命中密度是否过高；
> - GT TSV 是否误带表头或 `#` 注释。

**主代理必须抽查子代理的关键证据行后再采纳。**

### 2.8 运行时模拟

- `check_dict.py --batch-size 16` 的 mean/p90/p99/max；
- NameTable round-trip：用 `name_table.py --dry-run` 再跑一次，应全部“保留原值”；
- GT TSV：`check_dict.py --target galtransl`；
- 喵喵 TSV：`check_dict.py --target nyanya`。

### 2.9 出报告

只写报告，不改字典。报告模板见第 4 节。

---

## 3. 风险标记说明

| flag | 含义 | 处理 |
|---|---|---|
| `zero_hit` | 语料 0 命中 | P0：确认写法差异或假词条 |
| `main_character` | name 命中 ≥100 或在人物表 | P0：逐条核对 |
| `coined` | 在自造词表 | P0：逐条核对 |
| `name_only` | 只在 name 出现 | P1：建议移入姓名表 |
| `body_heavy` | 正文 ≥100、name 很少 | P1：检查提示词污染 |
| `short_word` | org ≤2 字且正文 ≥50 | P1：检查子串污染 |
| `honorific` | 以敬称结尾 | P1：检查跨条目一致 |
| `same_rep` | 多个 org 共用同一 rep | P2：确认是否同一人物 |
| `derived_inconsistent` | 短词译文不是长词译文的子串 | P2：检查派生 |
| `low_freq` | 总命中 ≤2 | P2：抽样确认是否自造词 |

**不要按频率批量删词。** 低频自造词保留；P2 只是抽样，不是删除线。

---

## 4. 报告模板

```markdown
# 字典审查报告

## 结论
- 条目总数：
- P0：N 条
- P1：N 条
- P2：N 条（抽样 N 条）
- 机械门禁：0 ERROR / N WARN

## P0 · 必须处理
| # | org | 问题 | 证据 | 建议 |
|---|---|---|---|---|

## P1 · 强烈建议处理
| # | org | 问题 | 证据 | 建议 |
|---|---|---|---|---|

## P2 · 抽样发现
| # | org | 问题 | 证据 | 建议 |
|---|---|---|---|---|

## 缺失高频词
| 组合 | 次数 | 建议去向 |
|---|---:|---|

## 覆盖清单
- 主要角色：N/N
- 自造词：N/N
- name_only：N/N
- body_heavy / short_word：N/N
- 缺失高频候选：N 条

## 未覆盖 / 抽样说明
- 普通物品/地点抽样：N/M
- 未审条目及原因：

## 工具输出
- check_dict：
- audit：
- scan_honorifics：
```

---

## 5. 明确不做

- 不改字典、不覆盖原文件；
- 不按频率批量删词；
- 不沿用 merge 阶段的备注当证据；
- 不把“查不到”直接判成“错误”，标“不确定”；
- 不凭空补译名或设定。

---

## 6. 常见错误与对应检查

| 错误类型 | 检查手段 |
|---|---|
| 假词条 / 语法误解析 | 事实子代理 + `evidence.tsv` |
| 撞名 / 同 rep 多 org | `audit.py` 的 `same_rep` + 证据 |
| 备注失实 / 臆造 | 事实子代理，要求引用原文 |
| 子串污染（`声`、`男`） | `audit.py` 的 `body_heavy` / `short_word` |
| 说话人标签进错表 | `name_only` + NameTable 检查 |
| 高频称谓漏收 | `scan_honorifics.py` |
| 派生不一致 | `audit.py` 的 `derived_inconsistent` |
| GT TSV 表头 / `#` 注释 | `check_dict.py --target galtransl` |
| NameTable 被绕过 | 运行时子代理 + GPP 源码顺序 |
| 每批命中过多 | `check_dict.py --batch-size` |
