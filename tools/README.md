# tools/ —— 汉化流水线的脚本

两个脚本，一前一后，都是纯 Python 标准库，不碰二进制格式：

| 脚本 | 干什么 | 一句话 |
|---|---|---|
| `export_scripts.py` | `.ps3` → JSON | 把游戏脚本里的文本批量抠出来（**提取**） |
| `cmvs_galtransl.py` | JSON ↔ GalTransl 项目 | 清洗 + 转成翻译工具要的格式 + 译完写回（**清洗 / 转换**） |

完整因果链和踩坑记录在工作区根目录的 **《汉化实施交接文档.md》**（§7.1 是这条流程）。

---

# 1. export_scripts.py —— 提取

把 CMVS 的 `.ps3` 脚本**批量导出**成 JSON，供翻译。

导出逻辑全在 `RxCMVS/PS3_TextEditor.exe` 的 `export` 模式里 —— 这个脚本只负责
批量循环、命名、汇总和自检。

## 前置

| 需要什么 | 在哪 |
|---|---|
| 导出工具 | `tools/RxCMVS/PS3_TextEditor.exe` |
| 已解密的脚本 | `ハピメア脚本/code/`（158 个）、`ハピメア Fragmentation Dream脚本/code/`（124 个） |

脚本开头有三个常量写死了路径，换机器要改：

```python
ROOT   = Path(r"C:\Users\DMS\Desktop\Hapymaher")
TOOL   = ROOT / "tools" / "RxCMVS" / "PS3_TextEditor.exe"
TARGETS = { "hapymaher": ROOT / "ハピメア脚本" / "code",
            "fragmentation-dream": ROOT / "ハピメア Fragmentation Dream脚本" / "code" }
```

## 用法

```bash
python tools/export_scripts.py                    # 导出全部（本体 + FD），落 output/
python tools/export_scripts.py --only hapymaher   # 只导本体
python tools/export_scripts.py --out D:\某个目录   # 换输出目录
```

跑完会打印：

```
=== hapymaher  (158 个)  →  ...\output\hapymaher
=== fragmentation-dream  (124 个)  →  ...\output\fragmentation-dream

[导出完成] 成功 282 个，失败 0 个
[自检] 输出目录共 107,142 条目，读取失败 0 个文件
```

`[自检]` 那两行是重新读一遍刚写出的 JSON —— **读取失败不为 0 就说明文件坏了**
（磁盘问题或导出中断），脚本会以退出码 1 结束。

## 产出

`output/<游戏>/<脚本名>.json`，文件名就是原脚本名加 `.json`
（`logo.ps3` → `logo.ps3.json`），方便一一对回去。

```json
{
  "Scenario": [
    { "raw": "…―─", "tra": "…―─" },
    { "raw": "「……うーん」", "tra": "「……うーん」" },
    { "raw": "透", "tra": "透" }
  ]
}
```

- `raw` = 日文原文，`tra` = 译文。**导出时两列相同**
- 文件是 **UTF-8 with BOM**，读的时候要用 `encoding="utf-8-sig"`
- 编码是 **Shift-JIS (932)**

### ⚠ 别手改这些 JSON

下游 `cmvs_galtransl.py` 是**按数组下标**跟 `.ps3` 里的文本槽一一对应的，
删掉或插入一条就全体错位，译文会灌到错误的句子上。
要过滤内容请在**下游**做（它出的 `excluded.csv` 就是干这个的）。

### 里面有啥

导出的**不只是台词**，引擎用同一个「压字符串」指令推送的全都在这儿：
台词、旁白、说话人槽、章节标题，以及引擎自己的规则串和资源路径。
清洗是下一步的事，见 §2。

---

# 2. cmvs_galtransl.py —— 清洗 + 转换

在 `output/<游戏>/*.json` 和 GalTransl 的 `gt_input` / `gt_output` 之间转换。
**这是整条流程里最容易做错的一步**，判据和理由都写在下面。

## 为什么必须先清洗

不洗的话有两个具体的坏事：

- 模型会白花 token 去「翻」`data\pack\bg.cpz` 这类资源路径
- **`start.ps3` 整份**（路径表 + 窗口标题 `ハピメア RE.ver`）会被当台词翻，
  跟《交接文档》§3.6 里单独打的那个标题补丁**打架**

所以做法是：**不可译的槽位根本不进 `gt_input`**，另出一份复核清单。
思路来自另一个项目的 `gal/tools/siglus_galtransl.py`（那边有现成的 `kind=1/2/3`
可以直接筛）；CMVS 的导出**没有这列**，判据得自己定 —— 就是下面这张表。

## 分类判据

| 槽位 | 处理 | 判据 |
|---|---|---|
| 台词 | 收 | 以 `「` 或 `『` **开头**（**允许这一行没有闭合引号**） |
| 说话人 | 收，挂成上一条的 `name` | **位置**：第 i 条是台词 ⇒ 第 i+1 条是它的说话人；且 i+1 要**长得像名字**（≤16 字、不含 `。、`、不以全角空格开头） |
| 旁白 / 章节标题 | 收 | 其余有假名或汉字的 |
| 引擎规则串 | **不收** | 裸的、不带引号、且没有假名也没有汉字（`…―─`、`。、」』）！？”～ー♪`） |
| 资源路径 / 文件名 | **不收** | 含路径分隔符，或结尾像扩展名（`data\pack\bg.cpz`、`hapymaher_re.ico`） |
| 空槽 | **不收** | |

八个判据都是踩出来的，**改之前先看一眼理由**（模块注释里有更详细的版本）：

1. **`『』` 也是对话引号** —— 209 句里有 203 句后面跟着说话人。只认 `「」` 会让这些
   台词挂不上说话人，纯符号的 `『―――――』` 还会被当引擎串剔掉。
2. **台词本身不可能是说话人** —— 电视/广播的话用 `『』` 引用、引擎不给它说话人，
   后面紧跟的就是下一句真台词。少这条判据，下一句会被当成说话人吞掉。
3. **`\n` 是换行码不是路径分隔符** —— 全语料只一条台词带它。
4. **判「有没有假名」要先剔掉 `ー`(U+30FC) 和 `・`** —— 否则
   `。、」』）！？”～ー♪` 里的 `ー` 会让这串被误判成台词。
5. **`「…………」` 这种只有符号的台词必须收** —— 它是对话的一部分，删了会断掉
   上下文连贯。所以「没有假名也没有汉字」这条**只对不带引号的裸串生效**。
6. **`　` 只洗行首** —— 29,116 条是行首一个（洗），但 4,157 条在句子中间
   （`事実ー！　事実だから…`），那是文意，动了就错。
7. **台词后面不一定跟说话人，也可能跟旁白** —— 纯位置规则会把这句旁白吞成
   `name`，而 `inject` 又把 name 槽强制写回原文，等于**漏翻**。实测本体 2 处、
   FD 2 处（`『…』` 后面跟 `　その看板が…立っていた。` 这种）。用
   `looks_like_name()` 兜住：≤16 字、不含 `。、`、不以 `　` 开头；`？？？`、
   `咲？` 是合法名字，所以不能一刀切禁问号。
8. **对白可能没有闭合引号** —— 引擎会把后半句/闭括号放到下一格。实测本体 14 行、
   FD 15 行只有开 `「`/`『`。旧判据要求整行闭合，于是后面紧跟的说话人变成独立
   `message` 送翻；模型看到孤零零一个名字，就报
   `GPPCProblem: 疑似漏括号或错位的说话人标签` / `疑似角色名错位`。
   用 `is_dialogue_start()` 判「以引号开头」即可，本体 5 处、FD 1 处名字因此归位。

## 用法

```bash
# 清洗 + 生成 gt_input / manifest / 复核清单
uv run python tools/cmvs_galtransl.py dump --game hapymaher --project test/galtransl/proj-hapymaher

# （填好 config.yaml 里的 API key，用 GalTransl 翻译）

# 把译文写回来
uv run python tools/cmvs_galtransl.py inject --game hapymaher --project test/galtransl/proj-hapymaher
```

`--game` 取 `hapymaher` / `fragmentation-dream`。
两个游戏有 7 个文件重名，所以是**两个独立工程**：`proj-hapymaher` / `proj-fd`。

## 产出

| 文件 | 说明 |
|---|---|
| `gt_input/<脚本>.json` | GalTransl 输入，`[{"name": …, "message": …}]` |
| `manifest.json` | 槽位映射，`inject` 靠它对位 |
| `excluded.csv` | **没纳入翻译的，请扫一眼** |
| `name替换表.csv` | 说话人表（DST 填了就用译名写回游戏；留空保留原文） |

`inject` **默认不就地覆盖**，写到 `output/<游戏>/translated/`，原始导出保持干净。
它宁可跳过也不猜：某个文件的 `gt_output` 条目数跟 manifest 对不上就直接跳过并报错
（`--allow-partial` 可以强制按位置尽力对齐，但那是最后一招）。

## 复核

每次改完判据都要看一眼 `excluded.csv` —— 里面应该**只有三类**：
`…―─`、`。、」』）！？”～ー♪`、`data\...` 路径。
出现别的就说明误伤了真台词。

脚本跑完还会自查「不漏台词」：源里有多少句 `「」`/`『』` 台词，
就有多少句进了 `gt_input`，对不上会直接报错。

## 已验证（2026-10-06）

| | 本体 | FD |
|---|---|---|
| 原文条目 | 64,888 | 42,254 |
| 送入翻译 | 42,109（带说话人 22,135） | 25,757（带说话人 15,985） |
| 不送翻译 | 644 | 512 |
| 行首 `　` 洗掉 | 19,879 | 9,596 |

- **往返无损**：采纳译文 / 不译原样 / 说话人原样，三项**各 0 出错**
- 用 **GalTransl 自己的加载器** `GalTransl.Loader.load_transList` 读全部 278 个文件通过
- **38,120 句**引号台词经它的 `analyse_dialogue` → `recover_dialogue_symbol` 原样还原

---

# 全流程

```
① 解包 / 解密脚本           （已做过，产物在 ハピメア脚本\code\）
② tools/export_scripts.py   —— .ps3 → JSON                     ← 提取
③ tools/cmvs_galtransl.py dump —— 清洗 + 转成 gt_input          ← 清洗
④ GalTransl 翻译             （cd GalTransl-8.2.0 && python -m GalTransl -p … -t ForGal-json）
⑤ tools/cmvs_galtransl.py inject —— 译文写回 tra
⑥ test/cntest/build_encrypted.py —— 构建成游戏能读的 .ps3
⑦ test/hooklog/run_cn.bat      —— 注入补丁 DLL 起游戏验收
```

② 和 ③ 之间**不能省** —— 直接拿 ② 的产物去翻，就是前面说的那两个坑。

---

# 常见问题

**条目数是固定的吗？**
是。② 出来本体 64,888 条 / FD 42,254 条，合计 107,142。数字对不上就是导出出了问题，
别往下走。

**能只处理一个脚本吗？**
② 没有「只导一个」的参数。想试跑单个文件，在 ③ 之后把 `gt_input/` 里只留一个
`.json` 送去做翻译最省事（`inject` 时其余文件会原样写出，不影响）。

**重跑会怎样？**
② 覆盖同名文件，不清理多余文件。③ 的 `dump` 同样只覆盖。
③ 的 `inject` 写到 `translated/`，**不动 `output/` 里的原始导出**。

**`　` 到底为什么要洗掉？**
GBK 里 `　` 是 `A1A1`，引擎的「可变文本框」算宽度时碰到它会算出接近 0 的结果，
框退化成小方块、正文全溢出。详见《交接文档》§3.3。

**译完之后还想改词典重刷译文，要重翻吗？**
不用。用 GalTransl 的 `-t rebuildr`：它从 `transl_cache/` 直接刷结果，跳过翻译。
