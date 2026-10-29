---
name: gal-dict-merge
description: 整合、校对、补充 galgame 翻译术语字典。输入通常是天使喵喵（Angel-Nyanya）生成字典、GalTransl 生成字典、VNDB 角色信息、人工基础项目字典，以及游戏原文 json。对照原文核对后，输出 GalTransl++ 的 ProjGptDict.toml、GalTransl 8.4.2 / 喵喵的 TSV，并生成姓名替换表（GPP NameTable.toml / 喵喵与 GT 的 name替换表.csv）。当用户要求整合字典、补充词条、统一译名/昵称、修正备注、改成 TOML/TSV、补全姓名替换表时使用。
---

# galgame 翻译字典整合流程

本流程把多份来源字典整理成可交付的术语字典，并分别导出给
**天使喵喵（Angel-Nyanya）/ GalTransl 8.4.2 / GalTransl++** 使用。

---

## 0. 先建立正确的认知（最重要）

**GPT 字典不是替换表，是给翻译模型看的术语表。**

程序把当前 batch 的原文与字典逐条做**子串匹配**，命中的条目才会作为一行
`原文 | 译文 | 备注` 附在提示词里送给 AI 模型。模型参考它自行决定怎么翻。

由此推出四条铁律：

1. **命中的是子串，不是词。** 短词会命中长词内部。
2. **写错备注不会改坏译文，但会误导模型。** 备注是给模型看的说明，不是注释。
3. **只有命中的条目进提示词。** 总条数不影响每次请求的 token；
   影响的是**每批命中多少条、备注多长**。不命中的条目只占维护成本，不占运行时 token。
4. **不同工具的匹配范围不同。** 先确认目标工具，再决定哪些条目该收、姓名走哪张表。

---

## 0.5 三个工具的字典语义（先定目标）

| | 天使喵喵（Angel-Nyanya） | GalTransl 8.4.2 | GalTransl++ |
|---|---|---|---|
| 字典格式 | TSV | TSV | TOML `gptDict` |
| 匹配对象 | **只有正文 `src`** | `说话人:正文` | `name + ":::::" + 正文` |
| 匹配方式 | 长度降序，命中后**消耗** | 长度降序，命中后**消耗** | 纯 `contains`，**不消耗**；priority 降序→长度降序 |
| 多译法 | 不支持 | `A/B` | `A||B` |
| 姓名替换 | `name替换表.csv`（`JP_Name,CN_Name,Count`） | `name替换表.csv`（`SRC_Name,DST_Name,Count`）+ `useGPTDictInName`（精确匹配） | `NameTable.toml`（`'原名' = ['译名', 次数]`）+ `useGPTDictToReplaceName` |
| 姓名替换来源 | 独立 CSV | CSV 为主；GPT 字典可覆盖 | GPT 字典 → NameTable → 译后字典 |
| `#` 注释 | 按各工具解析 | **不是注释**（会被替换成 Tab） | TOML 注释安全 |

### GPP 的两个关键细节

1. **`useGPTDictToReplaceName` 不会把条目从提示词里排除。**
   它只是额外拿同一份 GPT 字典去替换 name。`GptDictEntry` 只有
   `org / rep / note / priority`，**没有“仅 name”标记**。
   所以 `声`、`男` 这类词一旦写进 `ProjGptDict.toml`，正文每次出现都会进提示词。

2. **NameTable 是独立的姓名替换机制。**
   它只改 `name` 字段，不进提示词，也不参与“字典未使用”检查。
   GPP 的替换顺序是：GPT 字典 → NameTable → 译后字典。
   NameTable 用**原名**做 key；如果 GPT 字典先把名字改掉，NameTable 通常就查不到了。

### 由此得到的推荐分工（GPP）

- `ProjGptDict.toml`：主要角色、专有名词、设定术语、需要提示模型区分的词。
- `NameTable.toml`：**所有说话人名字和泛称标签**（`声`、`男`、`女の子`、`黒服`、`？？？` 等）。
- 关闭 `useGPTDictToReplaceName`，让 NameTable 统一负责姓名替换。

---

## 1. 开工前必须确认的 5 件事

| 项 | 说明 |
|---|---|
| 原文目录 | 一般是 `<项目>/gt_input/*.json` |
| 来源字典 | 喵喵生成 / GalTransl 生成 / 人工基础字典 / VNDB 信息 |
| 目标工具 | 喵喵 / GalTransl 8.4.2 / GalTransl++（决定输出格式与姓名表） |
| 输出路径 | 主 TOML、目标工具的 TSV、姓名替换表 |
| 低频条目策略 | **不按频率一刀切**：低频自造词保留；只处理 0 命中、解析错误、与事实相反的条目 |

---

## 2. 标准流程

```
0. 定目标工具
1. build_corpus.py       建语料
2. merge_sources.py      多来源合并：并集 + 冲突清单
3. q.py                  逐条对照原文核对
4. 写主 TOML             统一译名、修正备注、补派生写法
5. check_dict.py         体检
6. 导出目标格式           GPP TOML / GT TSV / 喵喵 TSV
7. name_table.py         生成姓名替换表
8. 试翻                  用“字典未使用”反馈修正，而不是按频率删词
```

### 第 1 步 · 建语料

```bash
python "<skill>/scripts/build_corpus.py" <input目录> -o _dictwork/corpus.txt
```

产出每行一条：`[文件名#序号] 说话人| 正文`。

### 第 2 步 · 多来源合并

```bash
python "<skill>/scripts/merge_sources.py" --base 人工基础字典.txt \
    喵喵生成.txt GalTransl生成.txt --corpus _dictwork/corpus.txt
```

看四块：

- 各来源条数、org 并集、两两重叠；
- 基准缺失的新增候选（标注“正文词 / 仅 name 字段”）；
- **同 org 不同 rep 的冲突**（必须人工拍板）；
- 各来源自身的问题。

**不要因为两个生成器重叠少就全部保留或全部丢弃。** 并集是候选池，
下一步逐条核对才是决定去留的地方。

### 第 3 步 · 逐条对照原文

用 `q.py` 查每个词的真实用法，核对：

- 备注说的对不对；
- 译文用字是否与同作品其它词条一致；
- 这个词是谁在用、指谁；
- 是正文词、name 字段词，还是两者都有。

**可以并行开子代理**，但关键证据行必须自己抽查。

### 第 4 步 · 写主 TOML

按主题分节，每节用 `# ═══` 分隔线 + 中文小节名。
同一人物的各种写法各自一条，但共享同一个基名。

**低频自造词不要删。** 出现 1 次的招式名、梦境术语、组织名，
往往正是需要统一的词。

### 第 5 步 · 体检

```bash
python "<skill>/scripts/check_dict.py" 主字典.toml \
    --corpus _dictwork/corpus.txt --target gpp --batch-size 16
```

必须 0 ERROR。重点看：

- 0 命中的 org；
- 备注里的自指、超长、Tab/换行；
- `A/B` 或 `A||B` 是否符合目标工具；
- **每批命中密度**：mean 5～10 舒服；p99 > 15 或 max > 20 要留意。

### 第 6 步 · 导出目标格式

**GalTransl++**

直接把主 TOML 命名为 `ProjGptDict.toml` 放到项目根目录。

**GalTransl 8.4.2**

```bash
python "<skill>/scripts/toml2tsv.py" 主字典.toml \
    --target galtransl -o 项目GPT字典.txt
```

- **不要表头**；
- **不要 `#` 注释**（GT 会把 `#` 当 Tab，产生空 org 伪词条）。

**天使喵喵**

```bash
python "<skill>/scripts/toml2tsv.py" 主字典.toml \
    --target nyanya -o 项目GPT字典.txt
```

- 喵喵的生成文件带 `日文原词<TAB>中文翻译<TAB>备注` 表头，保留。

### 第 7 步 · 生成姓名替换表

**GalTransl++**

```bash
python "<skill>/scripts/name_table.py" --target gpp \
    --corpus _dictwork/corpus.txt --dict 主字典.toml --table NameTable.toml
```

输出：

```toml
'透' = ['透', 7827]
'舞亜' = ['舞亚', 1484]
'声' = ['声音', 17]
```

**GalTransl 8.4.2**

```bash
python "<skill>/scripts/name_table.py" --target galtransl \
    --corpus _dictwork/corpus.txt --dict 主字典.toml --table name替换表.csv
```

输出表头：`SRC_Name,DST_Name,Count`。

**天使喵喵**

```bash
python "<skill>/scripts/name_table.py" --target nyanya \
    --corpus _dictwork/corpus.txt --dict 主字典.toml --table name替换表.csv
```

输出表头：`JP_Name,CN_Name,Count`。

### 第 8 步 · 试翻与反馈

先跑一章或一条线，导出“字典未使用”的词条，逐条判断：

- 模型换了个说法 → 改 `rep`，或改成目标工具支持的多译法；
- 词条多余 → 移出 GPT 字典（放姓名表或直接不收）；
- 模型确实没遵守 → 备注写清楚。

这一步比事前按频率猜“删不删”可靠。

---

## 3. 硬性规则

### R1 · 同一人物，所有称谓必须共享同一基名

一个人有「汉字写法 / 假名写法 / 昵称 / 绰号 / 称号」多种叫法时，每个叫法**单独一条**，
但译文必须都含同一个基名。

```
✓ ユキ     → 幸哉      ユキちゃん → 幸哉酱
✓ さっちゃん → 幸酱      香山幸      → 幸
```

### R2 · 敬称后缀

| 后缀 | 译法 | 备注 |
|---|---|---|
| ちゃん / ちゃーん | **酱** | |
| くん / 君 | **君** | |
| さん | **一般省略** | 学长/学姐语境用「前辈 / 学姐」 |
| 様 | **按语境** | 正式尊称用「先生 / 小姐」；夸张或敬称用「大人」 |
| 先輩 | **前辈 / 学姐** | 按用户偏好：男性前辈、女性学姐 |
| お嬢様 | 大小姐 | |
| 殿 | 大人 | |
| 先生（教师） | 老师 | |

**禁止用「小X」造昵称。**

### R3 · 一个 org 对应一个 rep（优先）

不同工具的多译法语法：

| 工具 | 语法 |
|---|---|
| GalTransl++ | `rep = "A||B"` |
| GalTransl 8.4.2 | `rep = "A/B"` |
| 天使喵喵 | 不支持，只能选一个 |

**优先只写一个译法。** 只有确实两种都行时才用多译法；
且用于 **name 替换**的条目不使用多译法（替换时会原样写进名字）。

### R4 · 符号变体只留裸词

`特殊モンスター好き` 和 `『特殊モンスター好き』` 只保留前者。
括号/引号由模型自行处理。

### R5 · 删条目的门槛

**不要按频率一刀切。** 低频自造词、招式名、梦境术语往往有价值。

只有以下情况才删/移出：

- 解析错误（例：`神崎はじめ` 实为「神崎をはじめ」）；
- 与另一条完全重复；
- 备注所述与正文事实相反且无法修正；
- 0 命中，且确认不是原文写法差异。

低频的**普通物品/地点/食物**可以移出 GPT 字典，
但这是为了减少提示词噪声，不是“低频就该删”。

### R6 · 备注规范

- 长度控制在 **60 字以内**；裸名角色条目可以 40～60 字，
  派生称谓/姓名标签尽量 20 字以内。
- 一句话说清「是谁 / 是什么 / 归谁」。
- 备注里的日文原词必须同时给出中文。
- **禁止自指式备注**（「同上」「见前条」）：词条逐条独立命中。
- 备注里不能有 Tab 或换行（会破坏 TSV/提示词表格）。

### R7 · 人物裸名条目写人物小传

每条 40～60 字，覆盖：性别 / 身份 / 自称 / 性格或语癖 / 关键关系。

```
{org = "雀", rep = "雀", note = "女主角，女性，鳳凰院家千金兼瑞鸟学园代理理事长；自称「私」，傲慢的大小姐口气；要的前未婚妻，云雀之姐"}
```

自称先用语料统计确认，不要凭印象。

### R8 · 术语撞名检查

同一个中文词不能指向两个人。
（典型坑：香山幸 vs 月代幸哉都简称“幸”。）

### R9 · 简体规范

- 不留繁体字；
- 不留日式和字/日本新字体；
- 译文里不应出现假名（刻意的品牌名除外）。

### R10 · 派生一致性

若 org A 是 org B 的子串，rep A 通常应当也是 rep B 的子串。

```
✓ スク水→死库水      スク水少女→死库水少女
✗ 逆玉→高攀          逆玉王子→入赘王子
```

GPP 不消耗子串，长短两条会同时送；不一致的 rep 会让模型看到互相冲突的译法。

### R11 · 高频称谓必须入库

一个「名字+敬称」形式出现上百次却没进字典，是最大的遗漏来源。
判断标准：**是否含专名**。含专名的收，纯泛称不收。

### R12 · 不臆造

所有改动都要有语料证据行。查不到就写「不确定」，不要编。

---

## 4. 工具脚本

都在本 skill 的 `scripts/` 下。

### build_corpus.py — 建语料

```bash
python scripts/build_corpus.py <input目录> -o _dictwork/corpus.txt
```

### q.py — 检索

```bash
python scripts/q.py つばさ 雀様
python scripts/q.py @30 義妹
python scripts/q.py -c 柚姫 3 3 5
python scripts/q.py -n 逆玉
python scripts/q.py -w 柚姫
```

### merge_sources.py — 多来源合并分析

```bash
python scripts/merge_sources.py --base 基准字典.txt 来源A.txt 来源B.txt \
    --corpus _dictwork/corpus.txt --out _dictwork/merge报告.txt
```

输出：概览 / 新增候选（标注正文词或仅 name）/ 冲突 / 来源自身问题。

### check_dict.py — 体检

```bash
python scripts/check_dict.py 主字典.toml \
    --corpus _dictwork/corpus.txt --target gpp --batch-size 16
```

检查：

- TOML/TSV 可解析、org 重复、空字段；
- 旧字典覆盖率；
- rep 里的假名/繁体/和字；
- 多译法语法是否符合目标工具；
- 备注超长、自指、Tab/换行；
- 派生一致性；
- 语料 0 命中；
- **每批命中密度**（mean / p90 / p99 / max）；
- **仅 name 字段出现的条目**（建议放姓名表）。

`--target` 可选 `gpp` / `galtransl` / `nyanya`。

### name_table.py — 姓名替换表

```bash
# GPP → NameTable.toml
python scripts/name_table.py --target gpp --corpus _dictwork/corpus.txt \
    --dict 主字典.toml --table NameTable.toml

# GT 8.4.2 → name替换表.csv (SRC_Name/DST_Name/Count)
python scripts/name_table.py --target galtransl --corpus _dictwork/corpus.txt \
    --dict 主字典.toml --table name替换表.csv

# 喵喵 → name替换表.csv (JP_Name/CN_Name/Count)
python scripts/name_table.py --target nyanya --corpus _dictwork/corpus.txt \
    --dict 主字典.toml --table name替换表.csv
```

- 自动识别输入表头（`JP_Name` 或 `SRC_Name`）；
- 只填空行，已有译名保留；`--overwrite` 才覆盖；
- 译不出的片段会留空并单独列出。

### toml2tsv.py — 导出 TSV

```bash
# GalTransl 8.4.2：无表头，不能有 # 注释
python scripts/toml2tsv.py 主字典.toml --target galtransl -o 项目GPT字典.txt

# 天使喵喵：带表头
python scripts/toml2tsv.py 主字典.toml --target nyanya -o 项目GPT字典.txt
```

---

## 4.5 多来源整合

### 各来源的定位

| 来源 | 是什么层 | 怎么用 |
|---|---|---|
| **VNDB 角色信息** | 事实层 | 取 Aliases / Personality / Role；Measurements 等不进备注 |
| **人工基础字典** | 已确认译法 | 优先级最高，作为 rep 基准 |
| **喵喵生成的字典** | 正文高频词，已过频率/术语校验 | rep 基准之一；name 字段不在其中 |
| **GalTransl 生成的字典** | 覆盖面层 | 只用来补 org 覆盖面，rep/note 重新判定 |

### 姓名标签 vs 正文术语

- **喵喵**：GPT 字典只作用于正文；说话人名字走 `name替换表.csv`。
- **GalTransl 8.4.2**：GPT 字典匹配 `说话人:正文`；姓名替换走 CSV，
  也可用 `useGPTDictInName` 精确匹配。
- **GalTransl++**：GPT 字典匹配 `name + ":::::" + 正文`；
  姓名替换走 `NameTable.toml`，`useGPTDictToReplaceName` 只是额外开关。

### 冲突仲裁

1. org 取并集；
2. rep 以人工确认过的为准：人工基础 > 喵喵 > GalTransl；
3. note 以 VNDB + 语料为准，冲突时语料赢；
4. 同 org 不同 rep 的冲突逐条列给用户拍板。

---

## 5. 并行核对的用法

条目多时（>150 条）可以分工：

```
主代理：人物裸名 + 称谓昵称
子代理A：组织 / 学校 / 地点
子代理B：设定 / 制度 / 活动 / 物品 / 梗
子代理C：GalTransl 独有、低频条目
```

给子代理的提示词必须包含：

1. 语料路径 + `q.py` 用法；
2. 待核对条目清单（原词 / 现译 / 现备注）；
3. 每条结论附语料证据行；不确定就写「不确定」；
4. 同时给出建议新增条目。

**子代理的结论必须抽查后再采纳。**

---

## 6. 已知的坑

- **GPP 的 `useGPTDictToReplaceName` 不会过滤提示词。**
  写进 `ProjGptDict.toml` 的每个条目都会参与提示词匹配。
  泛称标签（`声`、`男`、`女の子`）应放 `NameTable.toml`。
- **GPP 的 NameTable 用原名做 key。**
  GPT 字典先把名字改掉后，NameTable 可能查不到。
  想让 NameTable 统一负责，就关闭 `useGPTDictToReplaceName`。
- **GT 的 GPT 字典里 `#` 不是注释。**
  `#` 会被替换成 Tab，`# 说明` 变成 `org=""` 的伪词条；
  空 org 永远命中，还会让每句都可能报“字典未使用”。注释用 `//` 或干脆不写。
- **`toml2tsv.py` 的表头只给喵喵用。**
  GT 8.4.2 没有表头概念，表头会变成一条真实词条；用 `--target galtransl`。
- **`name_table.py` 要兼容两种 CSV 表头。**
  `JP_Name/CN_Name`（喵喵）和 `SRC_Name/DST_Name`（GT）。
- **短假名条目容易误伤。** 先数误报，再决定收不收。
- **单字条目 org==rep 时通常无害**，org≠rep 的单字要小心。
- **全角数字。** 先 `q.py -n` 数一下实际写法。
- **不要相信“未使用”告警的字面意思。** 它常常只是模型换了个说法。
- **导出前先备份。** TOML 与 TSV 不通用。

---

## 7. 汇报模板

```markdown
## 交付物
主字典：<路径>，共 N 条，TOML 校验通过。
导出：
- GalTransl++：ProjGptDict.toml
- GalTransl 8.4.2：项目GPT字典.txt（无表头）
- 姓名表：NameTable.toml / name替换表.csv

## 主要修正
**同人物不同名**：……
**修正错误备注**：……（附证据）
**删除/移出的条目**：……（附证据）
**统一的多译法**：……

## 新增
新增条目清单（分类）

## 需要你拍板的译法
| 原文 | 我的选择 | 备选 | 理由 |
|---|---|---|---|

## 我没有采纳的建议
……及原因
```
