# ハピメア（Hapymaher）HD 版 + FD 简体中文汉化

Purple software《ハピメア RE.ver》与《ハピメア Fragmentation Dream RE.ver》的简体中文汉化补丁，
含全部正文译文、界面图、菜单与系统设置。

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

## 实现方式

补丁不改 `cmvs32.exe`（MD5 与装机值一致），全部在内存里做，靠一个注入的 DLL：

| 问题 | 做法 |
|---|---|
| 引擎把 Shift-JIS 双字节判定内联了 **9 份** | 9 处立即数 `0x9F → 0xFE`（GBK 首字节范围） |
| 字体只对 GB2312 生效 | `CreateFontA` 调用点的 charset `0x80 → 0x86` |
| 译文开头的全角空格 `　` 会把文本框算成 0 宽 | 构建时统一 strip |
| 引擎取字形画字，不认 Unicode | `GetGlyphOutlineA` 上做 ♪ 哨兵重映射 |
| 字体选择列表全是系统字体 | `EnumFontFamiliesExA` 过滤成 8 款验证过的字体 |

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
| `汉化实施交接文档.md` | 完整技术记录 |

## 从零复现

需要：Windows + VS 2022（含 C++ 与 Windows SDK）、Python 3.10+、正版游戏、
[RxCMVS](https://github.com/ZQF-ReVN/RxCMVS) 的工具（`PS3_Cryptor.exe` / `PS3_TextEditor.exe`，
放到 `tools/RxCMVS/`）。

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

## 致谢

- [GalTranslPP](https://github.com/julixian/GalTranslPP) — 翻译流水线
- [GalTransl](https://github.com/GalTransl/GalTransl) / [Angel-Nyanya](https://github.com/miaomiao0721/Angel-Nyanya) — 字典
- [GARbro](https://github.com/morkt/GARbro) — 解包
- [RxCMVS](https://github.com/ZQF-ReVN/RxCMVS) — `.ps3` 读写
- 全字库正楷体（TW-Kai）— <https://www.cns11643.gov.tw/>

## 免责声明

本项目仅供学习交流，**禁止整合进游戏本体、禁止转载贩卖**。
游戏版权归 Purple software 所有。若权利方有异议，请提 Issue，会立即删除相关内容。

## 授权

- 代码（`tools/`、`test/`）: [MIT](LICENSE)
- 译文（`2文本汉化输出/`）: 保留署名、禁止商用，详见 [LICENSE](LICENSE)
