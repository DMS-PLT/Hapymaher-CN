# ハピメア FD (-Fragmentation Dream-) OP《幻想楼閣》特效字幕脚本包

## 目录结构
- `config.py`：视频规格（`1920x1080@24fps`）、同族金文字体配对与**昼夜双极配色预设**（暗夜象牙白 `NIGHT_THEME` vs 纯白茶会深绯红墨 `CRIMSON_THEME`）
- `assparse.py`：解析 `../FDop.ass` 的 `\k` 卡拉OK音节（兼容空 `\k` 休止符与全角气口留白）及 `; CN:` 译文
- `effects/base.py`：2x 超采样昼夜字形缓存、零截断解析柔光云 `soft_cloud`、红茶清风波纹退场滤镜
- `effects/lyric.py`：支持昼夜主题切换、动态安全区对齐与逐字微动钩子的歌词行基类
- `effects/prologue.py`：序幕（`L00~L02`）及 `0:25` 纯白走廊双行题记原生级内嵌（`CorridorEpigraph`）
- `effects/abpart.py`：A/B 段（`L03~L10`：镂空现实、仙境扑克与谎言双影、凤蝶花瓣、红酒杯注酒与满溢染红、`61.83s` 昼夜极性翻转与哥特荆棘）
- `effects/chorus.py`：副歌高潮（`L11~L19`：拨开荆棘与垂落血珠、胸口蔷薇与赤金火种、交叉剑光斩痕与双色交融、有子星海同心涟漪、`85.75s` 病娇猩红一闪、四向哥特宝匣上锁、暖阳虹彩屋室、流金星河、歌剧红丝绒帷幕谢幕）
- `gen.py`：主渲染管线（输出原始 RGBA 帧流，支持 `PREVIEW_T0` / `PREVIEW_END` 区间渲染）
- `preview_line.py`：按句号或秒数区间快速生成预览片段
- `render.py`：全片无中间文件直连 FFmpeg 压制 `op_out.mkv`（`libx264 CRF 16` + `AAC 256k`）

## 常用命令
```bash
# 预览指定句号 (例: L07 与 L08 红酒杯满溢染红)
python preview_line.py 7 8

# 预览指定时间段 (例: 0:25 纯白走廊原生题记)
python preview_line.py --span 24.4 30.5

# 全片渲染压制成片 op_out.mkv
python render.py
```
