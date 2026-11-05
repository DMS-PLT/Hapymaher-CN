# ハピメア REGRET END OP 特效字幕包（重构 v6 · 全片分镜演出完整版）

## 文件结构

```
ハピメアRE_OP_字幕制作脚本包-重构/
├── README.md           本文件
├── assparse.py         唯一事实来源: 解析 ../opre.ass 的句时间 + \k 音节 + 中文译文
├── config.py           全局参数集中地: 帧率/尺寸/同族双字体/安全版式/颜色/动画参数
├── gen.py              渲染主入口: 组装全片四幕图层 → 输出 RGBA 裸流给 ffmpeg
├── preview_line.py     快速预览工具 (几秒出片, 调轴调特效必用)
├── render.py           跨平台一键出整片脚本 (管道直连不落临时大文件)
├── render.sh           Linux/macOS 快捷脚本
└── effects/
    ├── base.py         图层基类 + 2x 超采样抗过曝柔影字形缓存 + 在唱光晕工具
    ├── lyric.py        歌词行图层 (karaoke 在唱呼吸脉冲 / cn_slide 左滑聚拢 / chars / whole)
    ├── vine.py         3x 超采样蔷薇荆棘藤蔓图层 (带弧形弯刺、卷须与前后螺旋穿插)
    ├── pomegranate.py  有机水墨毛细石榴渗红 + 宝石透光渐变 + 欲滴石榴红珠
    ├── apart.py        A 段演出 (L00~L04: 穿刺寒芒、景深落瓣、色散刺痛、蓝蝶微尘、4帧负片反相接管、紫白妖火与轻咬牙印)
    ├── bpart.py        B 段演出 (L05~L09: 边缘色散收敛、古典双线金框、无脸失忆雾化、断钥斜裂+盒盖压梁、荆棘勒缚、鼓点频闪扭曲与碎裂入副歌)
    └── chorus.py       副歌与尾声演出 (L10~L17 + Outro: 玫瑰冲击环+泪光涟漪、新月紫粉丝带、振翅荧光蝶海、金笼敞开、星蓝护盾+祈愿十字星、金钥焊合修复、红宝石戒星芒+伸手舒展、片尾全 7 处内嵌文字同化翻译)
```

**时间轴唯一来源**: `../opre.ass`（Aegisub 精校 `\k` 卡拉OK + `; CN: ` 注释行存中文译文）  
**基底视频**: `../opre.mkv`（1920×1080 / 24fps / 103s）  
**配对字体**: 日文 `../DFKinBun-W5.ttc`（华康金文体 W5）+ 中文 `../DFJinWenW3-GB.ttf`（华康金文体简体 W3，自动微增字重对齐 W5）

---

## 快速预览（调轴/看片段）

```bash
python preview_line.py 0 1 2 3 4             # A 段预览
python preview_line.py 5 6 7 8 9             # B 段预览
python preview_line.py 10 11 12 13 14 15 16 17  # 副歌预览
python preview_line.py --span 88.0 99.0      # 片尾全 7 处画面内嵌文字同化翻译预览
```

---

## 整片合成出片

```bash
python render.py              # 输出 op_out.mkv
python render.py myfilm.mkv   # 自定义输出文件名
```

`gen.py` → `ffmpeg` 二进制管道直连，**不产生中间裸流文件**。
