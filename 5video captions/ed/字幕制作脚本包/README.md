# ハピメア ED 中日双语字幕（极简版）

不再做 OP 那套特效，只保留干净的楷书双语版式：**中文左下 / 日文右上**，统一使用 `TW-Kai-98_1.ttf`（教育部标准楷书）。

## 版式

| 项目 | 设置 |
|---|---|
| 日文 | 48px，右上角，右对齐，右边距 84 / 顶边距 54 |
| 中文 | 48px，左下角，左对齐，左边距 74 / 底边距 62 |
| 字形 | 2x 超采样楷书，深墨描边 2.4px + 投影 + 亮底暗色柔光 |
| 衬底 | 贴身暗红柔光块（RGB 62,10,18 / alpha 122 / 外扩 14×7px / 模糊 11px），只裹住文字本体，避免与原片滚动的 staff 署名糊在一起 |
| 动效 | 整行 0.22s 淡入 + 8px 上浮，句尾 0.30s 淡出；无卡拉OK、无扭曲退场 |
| 超长行 | 自动逐级缩小字号（下限 34px），永不出安全区 |

## 目录

```
ed/字幕制作脚本包/
├── config.py     版式/字号/配色/目标清单
├── assparse.py   读 eda.ass 里 Dialogue 的日文 + 紧随其后的 `; CN:` 中文
├── textline.py   单行字形精灵（描边+投影+柔光+暗衬底）与淡入淡出
├── gen.py        渲染单支视频的 RGBA 裸流（PREVIEW_T0/END 可截段）
├── render.py     整片合成 + 帧数校验（VFR 安全管线）
├── make_ass.py   生成可继续编辑的 *_中日.ass
├── quick.py      总览图 / 1:1 字幕带，改完参数 3 秒看效果
├── still.py      单帧静帧校对（输出到 _check/）
└── preview.py    短段预览 mp4（带音轨，几秒出片）
```

## 常用命令

```bash
python make_ass.py                     # 生成 5 支 *_中日.ass

# —— 改完 config.py 后, 先用这三条快速看效果, 不要直接整片渲染 ——
python quick.py FD/eda --band          # 3 秒：全部歌词行的 1:1 字幕带（左中右日）
python quick.py FD/eda --cols 2        # 3 秒：整帧总览（2 列，看构图是否压字）
python quick.py FD/edb 3 7 12          # 只看第 3/7/12 句
python still.py FD/eda 8.5 30          # 1 秒：指定时间点的单帧
python preview.py FD/eda 68 76         # 5 秒：8 秒带音轨的动态预览 mp4

# —— 确认没问题再出片 ——
python render.py FD/eda                # 单支约 1 分钟
python render.py                       # 全部 5 支约 5 分钟
```

> 整片渲染慢在 x264 编码（5 支合计约 19,000 帧）。调版式、调色、调边距这类改动，用 `quick.py` / `preview.py` 就够了，只有最终交付才需要跑 `render.py`。

## 成片

输出与基底视频同目录，命名 `*_中日字幕成片.mkv`（H.264 + 原音轨复制，帧数与基底一致）。

| 基底 | 成片 |
|---|---|
| `本体/eda.mkv` | `本体/eda_中日字幕成片.mkv` |
| `FD/eda.mkv` | `FD/eda_中日字幕成片.mkv` |
| `FD/edb.mkv` | `FD/edb_中日字幕成片.mkv` |
| `FD/edc.mkv` | `FD/edc_中日字幕成片.mkv` |
| `FD/edd.mkv` | `FD/edd_中日字幕成片.mkv` |

## 渲染管线注意

这些 ED 视频是 Theora/Vorbis 的 VFR 基底（标称 24fps，含静止段），必须沿用：

```text
[1:v][0:v]overlay=0:0:shortest=1
-fps_mode passthrough
-c:a copy
```

并且字幕裸流要比基底末尾多生成 1 帧，否则 overlay 会吃掉最后一个主帧。`render.py` 出片后会自动比对帧数，不一致直接报错。
