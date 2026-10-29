# RxCMVS 使用说明

CMVS 引擎（Purple software）逆向工具集，用于《ハピメア》系列脚本的文本导出与回写汉化。

- 源码：`解包工具\RxCMVS-main\`（来自 `ZQF-ReVN/RxCMVS`）
- 本目录下的 `*.exe` 是**编译产物**，源码仓库里不含，丢失需重新编译（见第五节）
- 构建环境：CMake + Ninja + MSVC 14.51（VS 18），x64

---

## 一、三个可执行文件

### 1. PS3_TextEditor.exe —— 核心，文本导出 / 回写

```bash
# 导出：明文 .ps3 → JSON
PS3_TextEditor.exe -mode export -ps3 <明文.ps3> -json <输出.json> -code 932

# 回写：翻译好的 JSON → 新 .ps3
PS3_TextEditor.exe -mode import -ps3 <明文.ps3> -json <翻译后.json> -save <新.ps3> -code 932
```

| 参数 | 说明 |
|---|---|
| `-mode export` | 从脚本里扫出全部对话文本，写进 JSON |
| `-mode import` | 把 JSON 的 `tra` 字段写回脚本，另存为新文件 |
| `-code 932` | **Shift-JIS 码页，日本 galgame 固定用这个，不要改成 936** |

> **`-ps3` 只能给单个文件，不能给目录**——工具没有批量模式，一次处理一个脚本。
> 传目录会报 `Create File Error!`。批量请用第二节的脚本。

**JSON 结构**：

```json
{
  "Scenario": [
    { "raw": "「――そんな答え、聞いた所で意味が無いだろ」", "tra": "「――那种答案，就算听了也没有意义吧」" }
  ]
}
```

- 翻译**只改 `tra`，不要动 `raw`**。
- JSON 带 UTF-8 BOM，用 Python 读时请用 `encoding="utf-8-sig"`（用 `utf-8` 会直接报错）。
- **import 时条目数必须和导出时完全一致**，多一条少一条都会直接返回 `Failure`——工具是拿 JSON 条数去比对脚本里扫出来的条数。
- import 的 `-ps3` 要传**原始明文脚本**，不是上一轮 import 出来的产物。

### 2. PS3_Cryptor.exe —— 解密 / 加密

```bash
PS3_Cryptor.exe -mode decode -ps3 <加密.ps3> -save <明文.ps3>
PS3_Cryptor.exe -mode encode -ps3 <明文.ps3> -save <加密.ps3>
```

- `decode` 输出「48 字节头 + 解压后的完整数据」，可直接喂给 PS3_TextEditor。
- `encode` 用的是**全字面量伪压缩**（每个字节前加 `0xFF` 标记），体积比游戏原版大，但游戏能正常读。

### 3. MGV_Editor.exe —— 视频拆装（文本汉化用不到）

```bash
MGV_Editor.exe -mode extract -mgv op.mgv
MGV_Editor.exe -mode replace -mgv op.mgv -ogv op.ogv
```

---

## 二、批量导出：export_scripts.py

把两个游戏的 282 个脚本全部导出成 JSON。

```powershell
python tools\RxCMVS\export_scripts.py                 # 导出全部
python tools\RxCMVS\export_scripts.py --only hapymaher   # 只导本体
python tools\RxCMVS\export_scripts.py --out D:\某目录     # 换输出目录
```

- 默认输出到 `output\hapymaher\`（158 个）与 `output\fragmentation-dream\`（124 个）
- JSON 文件名 = 原脚本名 + `.json`（`logo.ps3` → `logo.ps3.json`），方便将来一一对回去
- 跑完会打印导出统计，并**自检**一遍输出目录的条目总数和损坏文件数
- 脚本是 UTF-8 的，中文路径直接写在里面，改起来没有编码坑

**当前导出结果**（2026-10-05）：282 个文件、**107,142 条目**、0 失败，共约 17MB。

---

## 三、完整流程

```
script.cpz ──①解包──▶ *.ps3(加密) ──②decode──▶ *.ps3(明文) ──③export──▶ *.json
                                                                          │
                                                                   ④翻译 tra 字段
                                                                          ▼
script.cpz ◀──⑦打包── *.ps3(加密) ◀──⑥encode── *.ps3(新) ◀──⑤import── *.json
```

| 步骤 | 工具 | 状态 |
|---|---|---|
| ① 解包 `.cpz` → `.ps3` | GARbro | 已完成，产物在 `ハピメア脚本\code\`、`ハピメア Fragmentation Dream脚本\code\` |
| ② 解密 `.ps3` | PS3_Cryptor | 已完成（已核对头字段，现有脚本均为明文） |
| ③ 导出 JSON | PS3_TextEditor（`export_scripts.bat`） | **已完成**，107,142 条目 |
| ④ 翻译 | — | 待做 |
| ⑤ 回写 `.ps3` | PS3_TextEditor | 已冒烟验证 |
| ⑥ 加密 `.ps3` | PS3_Cryptor | 未实测 |
| ⑦ 打包回 `.cpz` | GARbro / VFS_Hook | **未验证** |

**建议**：正式批量做之前，先拿**一个**脚本走完 ⑤→⑥→⑦ 全流程，进游戏确认能读，再动全量。

---

## 四、注意事项

### 回写是「追加式」，文件只会变大

新译文追加到**文本段末尾**，code 段里对应的 4 字节 RVA 指针改指过去。所以**译文比原文长完全没问题**。

但代价是：**每 import 一次就追加一次**，反复 import 同一个文件会越滚越大。

> 要重做，就从原始解密脚本重新跑一遍，不要在旧产物上反复 import。

### 会被过滤掉的串

工具会把含 `.pb3 / .pb2 / .ps3 / .ps2 / .ogg / .wav / .mv2 / .cmv / .mgv / .cur` 的串
当作资源文件名剔除。所以 `logo.ps3` 头里写着 179 个串，实际只导出 5 条——**这是设计如此，不是丢数据**。

### 字体表别动

文本段开头那几条 `…―─`、`。、」』）！？”ー♪` 是字体/标点表，翻译时**原样保留**。

### 文本特点

条目里既有带引号的对白，也有**裸的说话人名**（如单独一条 `透`），以及以全角空格 `　` 开头的旁白。翻译时要一起处理，别当成噪声删掉。

### VFS_Hook：不打包直接替换游戏文件（有雷）

`解包工具\RxCMVS-main\src\VFS_Hook\VFSHook.ini` 里已经内置了 `[ハピメア_RE_PKG]` 和 `[ハピメアFD_RE_PKG]` 两节，写死了函数地址。但：

1. 它是 **x32-only**，x64 构建会直接跳过——要用得 `build_rxcmvs.bat x86` 重编。
2. ini 里标的是 `Engine_Ver = CMVS_380_`，而 HD 版是 **cmvs32 ver.3.90**，exe 不同，**那些硬编码地址很可能对不上**。要用必须先验证。

---

## 五、重新编译

```bash
cd C:\Users\DMS\Desktop\Hapymaher\解包工具\RxCMVS-main
C:\Users\DMS\Desktop\Hapymaher\test\build_rxcmvs.bat [x64|x86] [clean]
```

产物输出到本目录（`tools\RxCMVS\`）。

### 两条硬性约束

**1. 子模块必须用父仓库锁定的 commit，不能拉各仓库 main。**

| 子模块 | 仓库 | 锁定 commit |
|---|---|---|
| `lib/Rut` | `Dir-A/Rut` | `90b97bdd34488a9d322087b62f117460bc6478da` |
| `lib/RxHook` | `Dir-A/RxHook` | `9b4c63f4b9e434675e8a9a9a3a058b211bd77da8` |
| `lib/RxHook/third/detours/Detours` | `microsoft/Detours` | `4b8c659f549b0ab21cf649377c7a84eb708f5e68` |

> main 版的 Rut 移除了 `RxJson::JValue::ToStrView()`，RxCMVS 却还在调它，链接必失败。

**2. 重新拉依赖后必须带 `clean` 参数重编。**

tar 解压会把源文件时间戳还原成 2024 年，比已经编出来的 `.obj` 还旧，Ninja 会误判「没变化」而漏编。（本次就是这么踩的：`ToStrView` 声明在头文件里、实现没编进去，链接期才炸。）

### 其它

- **不需要 vcpkg**，Rut / RxHook 除 Detours 外零第三方依赖。
- `third\libwebp` 只有 x86 库，但 PS3 工具不引用 webp 符号，x64 也能正常链接（链接器不会去读它）。
- 本项目给 `CMakeLists.txt` 打过补丁：新增 `RXCMVS_BIN_DIR` 缓存变量，输出目录可用 `-D` 指定，默认行为不变。
- 当前 x64 构建产物只有上述三个 exe；`VFS_Hook` / `VFS_Extract` 是 x32-only，要它们得编 x86。

---

## 六、.ps3 文件格式速查

```
偏移        内容
0x00        48 字节头（12 × uint32）
0x30        Code 段   ← 字节码 + 4 字节 RVA 指针
             Un 段     ← 通常为空
              Text 段   ← 以 \0 分隔的 Shift-JIS 字符串
```

头字段：`签名 | 头大小 | ? | 解密密钥 | 文本数 | Code段大小 | Un段大小 | Text段大小 | ? | 压缩后大小 | 解压后大小 | ?`

- 数据段是「字节密钥 XOR + 加 0x7C 偏移 + 循环移位」的伪加密，外面再套一层 LZSS。
- **明文文件的大小 = 48 + 解压后大小**，可用来快速判断一个 `.ps3` 是加密态还是明文态。
