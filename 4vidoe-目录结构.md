# 4vidoe 目录结构

> 视频解包工作区。整个目录**不进版本库**（含游戏视频，约 2.7GB），
> 可按《视频解包与字幕时间轴报告.md》从游戏重新生成。本文只记录结构与用途。

## 文件树

```text
4vidoe/
├─ 本体/
│  ├─ video/                     原始 mgv + 解出的 ogv / ogg
│  │  ├─ op.mgv   op.ogv   op.ogg
│  │  ├─ eda.mgv  eda.ogv  eda.ogg
│  │  └─ edb.mgv  edb.ogv  edb.ogg
│  └─ 合并视频/                  按槽位表重建时间轴的 mkv（对轴用）
│     ├─ op.mkv
│     ├─ eda.mkv
│     └─ edb.mkv
└─ FD/
   ├─ video/
   │  ├─ op.mgv    op.ogv    op.ogg
   │  ├─ opre.mgv  opre.ogv  opre.ogg
   │  ├─ eda.mgv   eda.ogv   eda.ogg
   │  ├─ edb.mgv   edb.ogv   edb.ogg
   │  ├─ edc.mgv   edc.ogv   edc.ogg
   │  ├─ edd.mgv   edd.ogv   edd.ogg
   │  └─ door.mgv  door.ogv  door.ogg
   └─ 合并视频/
      ├─ op.mkv
      ├─ opre.mkv
      ├─ eda.mkv
      ├─ edb.mkv
      ├─ edc.mkv
      ├─ edd.mkv
      └─ door.mkv
```

## 各目录

| 目录 | 内容 | 文件数 | 大小 |
|---|---|---:|---:|
| `本体/video/` | 原始 `mgv` + 解出的 `ogv`/`ogg` | 9 | 614M |
| `本体/合并视频/` | 重建时间轴后的 mkv | 3 | 305M |
| `FD/video/` | 原始 `mgv` + 解出的 `ogv`/`ogg` | 21 | 1.2G |
| `FD/合并视频/` | 重建时间轴后的 mkv | 7 | 605M |

- **`video/`**：从游戏 `data\video\` 复制的原始 `.mgv`，以及
  `tools\RxCMVS\MGV_Editor.exe -mode extract` 解出的 `.ogv`（Theora 视频）/
  `.ogg`（Vorbis 音频）。同名 `op.mgv` 在本体和 FD 各有一份，**必须在各自目录里解**，
  否则会互相覆盖（工具把产物写到当前工作目录）。
- **`合并视频/`**：`test\rebuild_mgv_video.py` 按 `mgv` 头部的帧槽位表重建时间轴，
  再用 `mkvmerge --timestamps` 封装的 mkv。首帧 0 秒，时长 = 槽位数 ÷ 24，
  Aegisub 里视频/音频/字幕网格三者一致。**不要**用 ffmpeg 默认重封装的版本对轴
  （会丢掉静止帧的停留时长）。

## 哪些有字幕

| 游戏 | 已做字幕 | 未做 |
|---|---|---|
| 本体 | `op`、`eda` | `edb`（纯音乐，无字幕） |
| FD | `op`、`opre`、`eda`、`edb`、`edc`、`edd` | `door`（4 秒过场） |

## 重新生成

```bash
# 1) 解包：先进入该视频所在目录，产物会落在当前目录
cd "4vidoe/本体/video"
tools\RxCMVS\MGV_Editor.exe -mode extract -mgv op.mgv

# 2) 按槽位表重建时间轴
python test\rebuild_mgv_video.py op.mgv op.ogv op.ogg op.mkv
```

细节和校验方法见《视频解包与字幕时间轴报告.md》。
