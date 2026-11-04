# ハピメア（Hapymaher）HD 版 + FD 简体中文汉化

Purple software《ハピメア RE.ver》与《ハピメア Fragmentation Dream RE.ver》的简体中文汉化补丁，
含全部正文译文、界面图、菜单与系统设置；另附 OP/ED 中日双语特效字幕视频包（单独分发）。

- 翻译：gemini-4-argon
- 版本：v1.0
- 作者：p端木森q

> **本仓库不含游戏本体，也不含游戏的解密脚本与原文。**
> 仓库里只有汉化补丁的**制作代码**和**译文**；游戏资源需自备正版，见「从零复现」。

---

## 成品

补丁以压缩包形式发布，解压后把内容覆盖到游戏安装目录，
运行 `cmvs32_cn.exe`（本体）/ `cmvs32_cn_FD.exe`（FD）即可，无需转区。

卸载：删掉补丁加的 `cmvs32_cn*.exe`、`cnpatch.dll`、`cnpatch_ui.txt`、`TW-Kai-98_1.ttf`、
`data\pack\script`、`data\pack\chip`，再用包内的 `还原用\start.ps3` 覆盖回去即可。
游戏自带的 `cpz` 封包一个字节都没动过，所以删干净就恢复原状。

### OP/ED 特效字幕包（单独下载）

视频字幕单独打包（见 Release 附件），不塞进主补丁：主补丁约 250MB，
视频压缩包约 919MB，解压后约 928MB。解压后**本体和 FD 分开**：
本体的 `data\video\` 覆盖到本体游戏根目录，FD 的 `data\video\` 覆盖到 FD 游戏根目录，别拷混。

包含：本体 `op` / `eda`；FD `op` / `opre` / `eda` / `edb` / `edc` / `edd`，共 8 支。
本体 `edb`（纯音乐）和 FD `door`（4 秒过场）没有字幕，视频包里也不含。

卸载：覆盖前先备份游戏的 `data\video\`，恢复时把原 mgv 拷回去。

## 实现方式

补丁不改 `cmvs32.exe`（MD5 与装机值一致），全部在内存里做，靠一个注入的 DLL：

| 问题 | 做法 |
|---|---|
| 引擎把 Shift-JIS 双字节判定内联了 **9 份** | 9 处立即数 `0x9F → 0xFE`（GBK 首字节范围） |
| 字体只对 GB2312 生效 | `CreateFontA` 调用点的 charset `0x80 → 0x86` |
| 译文开头的全角空格 `　` 会把文本框算成 0 宽 | 构建时统一 strip |
| 引擎取字形画字，不认 Unicode | `GetGlyphOutlineA` 上做 ♪ 哨兵重映射 |
| 字体选择列表全是系统字体 | `EnumFontFamiliesExA` 过滤成 8 款验证过的字体 |
| 视频文件自带的时间戳不是游戏实际时间线 | 按 `mgv` 头部帧槽位表重建；字幕对轴与回写都以槽位表为准 |

细节见 [`汉化实施交接文档.md`](汉化实施交接文档.md)（技术文档，写得很啰嗦但都是实测结论）。

## 目录

| 路径 | 内容 |
|---|---|
| `tools/` | 构建工具：导出、切槽/回填、pb3 编解码、一键构建、出包 |
| `test/hooklog/` | 补丁 DLL（`cnpatch.cpp`）、启动器（`launch.cpp`）、构建脚本 |
| `test/cntest/` | 真正的构建逻辑（`build_full.py` / `build_fd.py`） |
| `2文本汉化输出/` | **译文工作副本**（`本体_gt_output` / `FD_gt_output` + 槽位 mapping） |
| `1文本汉化/` | GalTranslPP 工程配置、字典（`Config.toml` 含密钥，不在此仓库） |
| `3UI源文件/` | 界面图源（PSD / PNG / pb3），体积大，未纳入版本管理 |
| `5vidoe captions/` | OP/ED 字幕工程（`.ass` + Python 渲染脚本）；成片、基底视频与字体不入库 |
| `4vidoe/` | 视频解包工作区（`<游戏>/video/` 存 mgv 与 ogv/ogg，`<游戏>/合并视频/` 存对轴用 mkv），可由游戏重新生成，不入库 |
| `4vidoe-目录结构.md` | `4vidoe/` 的完整文件树与各目录用途 |
| `汉化实施交接文档.md` | 完整技术记录 |
| `视频解包与字幕时间轴报告.md` | 视频链路：`mgv` 结构、时间轴真相、回写与校验 |

## 从零复现

需要：Windows + VS 2022（含 C++ 与 Windows SDK）、Python 3.10+、正版游戏、
[RxCMVS](https://github.com/ZQF-ReVN/RxCMVS) 的工具（`PS3_Cryptor.exe` / `PS3_TextEditor.exe`，
放到 `tools/RxCMVS/`）。视频字幕另需 `ffmpeg` / `ffprobe`、[MKVToolNix](https://mkvtoolnix.download/)
和同目录的 `MGV_Editor.exe`。

**仓库不含任何游戏文件**（版权原因）。第一次构建前，从游戏里复制两份原版 `start.ps3`：

```
<游戏>\data\pack\start.ps3  ->  test\backup\start.ps3.orig        （本体）
<FD>\data\pack\start.ps3    ->  test\backup\fd_start.ps3.orig     （FD）
```

它们是构建的输入（补丁要基于原版重新写路径表和标题），也是发布包里「还原用」的来源。

**第一步：解包脚本**（唯一需要手动的一步）

我们的仓库不含 cpz 解包工具（`GARbro` 是 MIT，但只发布 GUI 版）。用 [GARbro](https://github.com/morkt/GARbro/releases)
打开 `<游戏>\data\pack\script.cpz`，全选后提取到一个临时目录，然后交给整理脚本：

```bash
python tools/prepare_scripts.py <解包目录> --game 本体   # FD 用 --game fd
```

> ⚠ **本作 script.cpz 解出来的 `.ps3` 大多是明文，不需要解密**（实测对明文跑解密：
> 多数直接崩溃，少数「成功」但内容已毁）。`prepare_scripts.py` 会逐个自动探测：
> 能直接导出对白的原样拷贝，导不出的才解密并验证，验证不过按失败处理。
> 老教程里「解出来都是加密的，先批量解密」的说法是错的，别照做。

整理结果会放进 `ハピメア脚本/code`（FD 是 `ハピメア Fragmentation Dream脚本/code`）。

```bash
# 1. 整理脚本 -> 导出原文（自检判据：条目数 本体 64,888 / FD 42,254，失败 0）
python tools/export_scripts.py

# 2. 注入译文 + 构建进游戏目录
python tools/rebuild.py 本体        # FD 用 fd

# 3. 生成发布包
python tools/make_release.py
```

补丁 DLL 与启动器：

```bash
cd test/hooklog && build.bat
```

### 视频字幕（可选）

视频链路需要额外准备：`ffmpeg` / `ffprobe`、
[MKVToolNix](https://mkvtoolnix.download/)（`mkvmerge`），
以及 RxCMVS 的 `MGV_Editor.exe`（放到 `tools/RxCMVS/`）。

1. **解包**：`MGV_Editor.exe -mode extract -mgv <x.mgv>`，产出 `x.ogv` / `x.ogg`。
   它把产物写到**当前目录**，同名的本体/FD 视频要分别在各自目录里解。
2. **重建时间轴**：`python test/rebuild_mgv_video.py <x.mgv> <x.ogv> <x.ogg> <out.mkv>`。
   按 `mgv` 帧槽位表写时间戳，Aegisub 里视频/音频/字幕三者才对得上。
   **不要**用 ffmpeg 默认重封装或 `vfr`（会丢静止帧时长）。
3. **渲染字幕**：进入 `5vidoe captions/<游戏>/字幕制作脚本包`，按各包 README 跑 `render.py`。
   需要 Pillow + numpy；ED 包在 `5vidoe captions/ed/字幕制作脚本包`。
4. **回写**：`python test/pack_videos.py`。重编码 Theora → 校验帧数 → 替换 `mgv`，
   并逐字节核对索引段/音频段。原始 mgv 自动备份到 `test/backup/video/`。

**字体**：字幕脚本默认从 `5vidoe captions/` 读三款字体——
`TW-Kai-98_1.ttf`（全字库正楷体，UI 汉化和特效字幕都用它；**成品主补丁包已随附**，
本仓库因体积原因不带，构建时从全字库官网下载即可）、
`DFJinWenW3-GB.ttf` / `DFKinBun-W5.ttc`（华文金文体 W3 / DF 金文体 W5，
**商业字体，成品包也不带**，需自行下载并取得授权）。缺字体时脚本会直接报 `找不到字体`。

> 回写硬约束：新视频帧数必须等于槽位表不同值个数（本体 op 3173 / eda 3270；
> FD op 3089 / opre 2427 / eda 2928 / edb 4796 / edc 2693 / edd 4062），
> 重编码必须带 `-pix_fmt yuv420p -fps_mode passthrough`。详见
> [`视频解包与字幕时间轴报告.md`](视频解包与字幕时间轴报告.md)。

## 致谢

- [GalTranslPP](https://github.com/julixian/GalTranslPP) — 翻译流水线
- [GalTransl](https://github.com/GalTransl/GalTransl) / [Angel-Nyanya](https://github.com/miaomiao0721/Angel-Nyanya) — 字典
- [GARbro](https://github.com/morkt/GARbro) — 解包
- [RxCMVS](https://github.com/ZQF-ReVN/RxCMVS) — `.ps3` 读写、`.mgv` 抽流/替换
- 全字库正楷体（TW-Kai）— <https://www.cns11643.gov.tw/>
- [MKVToolNix](https://mkvtoolnix.download/) — 按槽位表封装 mkv
- FFmpeg — 视频解码与 Theora 重编码
- 华康金文体 W5 / 简体 W3 — 字幕字形（商业字体，仅致谢，不随仓库分发）

## 免责声明

本项目仅供学习交流，**禁止整合进游戏本体、禁止转载贩卖**。
游戏版权归 Purple software 所有。若权利方有异议，请提 Issue，会立即删除相关内容。

## 授权

- 代码（`tools/`、`test/`、`5vidoe captions/**/*.py`）: [MIT](LICENSE)
- 译文与字幕文本（`2文本汉化输出/`、`5vidoe captions/**/*.ass`）: 保留署名、禁止商用，详见 [LICENSE](LICENSE)
