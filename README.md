# 电影质感创作 Skill

`craft-cinematic-visuals` 是一个用于图像、视频、分镜和实拍素材的电影质感创作技能。它的核心原则是：先尊重原始摄影、光源和媒介属性，再做可自然成立的电影化处理。

对于已有照片，技能默认不使用生成式重绘，而是优先采用非生成式像素调色，避免人物、文字、空间和物体细节被模型改写。

## 功能概览

- 分析图像或视频为什么缺少电影质感。
- 为画面设计镜头语言、光线、色彩、材质、运动和声音建议。
- 为文生图、图生图、文生视频、图生视频生成可执行提示词。
- 为现有照片输出自然平衡、情绪偏移、质感增强三个渐进版本。
- 在明确需要重构时，提供类型片、时代影像或广告视觉方向。
- 使用本地调色脚本保持图像几何、文字和人物身份不变。

## 目录结构

```text
craft-cinematic-visuals/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── cinematic-language.md
│   ├── film-style-atlas.md
│   ├── look-archetypes.md
│   ├── multi-variant-workflow.md
│   ├── natural-integration.md
│   ├── prompt-patterns.md
│   └── quality-control.md
└── scripts/
    └── grade_image.py
```

## 安装方式

将 `craft-cinematic-visuals` 文件夹复制到 Codex 技能目录：

```bash
cp -R craft-cinematic-visuals ~/.codex/skills/
```

如果使用已经打包好的版本，先解压：

```bash
unzip dist/craft-cinematic-visuals-20260616.zip
cp -R craft-cinematic-visuals ~/.codex/skills/
```

## 使用示例

直接在 Codex 对话里调用：

```text
使用 $craft-cinematic-visuals，把这张照片自然地优化成电影质感，保留原始光线和媒介属性。
```

更多示例：

```text
使用 $craft-cinematic-visuals，分析这张照片为什么显得不够电影感，并给出修改路线。
```

```text
使用 $craft-cinematic-visuals，为这张产品图输出三个自然渐进的电影质感版本，保持 Logo 和包装文字不变。
```

```text
使用 $craft-cinematic-visuals，为一个雨夜便利店场景设计文生图提示词。
```

```text
使用 $craft-cinematic-visuals，为这段故事做 8 个镜头的分镜和统一 Look Bible。
```

## 处理原则

技能会先判断任务属于哪一类：

- **非生成式调色**：已有照片、截图、监控、档案、产品图和含文字画面默认使用。只改曝光、曲线、白平衡、局部层级、饱和度、锐度和轻微质地。
- **生成式编辑**：只有当用户明确要求改变天气、时间、光源结构、场景、服装、构图或物体时使用。
- **从零生成**：没有现有素材，或用户希望重新创作场景时使用。
- **方案设计**：只需要拍摄建议、分镜、调色方向或提示词时使用。

默认三种结果不是硬套三种电影风格，而是同一原片的三个自然强度：

1. **自然平衡**：修正曝光、白平衡、曲线和数字锐度。
2. **情绪偏移**：轻微偏冷、偏暖、压低或通透，但不改变光源拓扑。
3. **质感增强**：增加密度、层级和轻微质地，仍保持原片可信。

## 本地调色工具

`scripts/grade_image.py` 用于几何保持的像素调色。它不会重画人物、文字或场景。

依赖：

- Python
- Pillow
- NumPy

在 Codex 桌面环境里，先使用工作区依赖提供的 Python。示例：

```bash
python craft-cinematic-visuals/scripts/grade_image.py \
  --input input.png \
  --output output.png \
  --preset source-neutral \
  --strength 0.55
```

可用预设：

- `source-neutral`：中性自然校正。
- `cool-contained`：轻微冷静，保护中性色和肤色。
- `warm-muted`：轻微温暖，降低数字生硬感。
- `dense-neutral`：增加密度和层次，不明显改变色温。

保护文字、Logo 或界面区域：

```bash
python craft-cinematic-visuals/scripts/grade_image.py \
  --input input.png \
  --output output.png \
  --preset cool-contained \
  --strength 0.58 \
  --protect-rect 0,0,520,125 \
  --protect-rect 1150,0,1448,125
```

`--protect-rect` 格式为：

```text
x1,y1,x2,y2
```

## 打包

当前发布包位于：

```text
dist/craft-cinematic-visuals-20260616.zip
```

重新打包：

```bash
mkdir -p dist
zip -r dist/craft-cinematic-visuals-20260616.zip craft-cinematic-visuals \
  -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'
```

验证压缩包：

```bash
zip -T dist/craft-cinematic-visuals-20260616.zip
unzip -l dist/craft-cinematic-visuals-20260616.zip
```

## 开发注意事项

- 不要把测试输出、缓存文件或 `.DS_Store` 放进技能包。
- 不要在技能目录内额外添加 README、安装指南或变更日志；技能本体应保持精简。
- 更新 `SKILL.md` 后，确认 `agents/openai.yaml` 的描述和默认提示仍然一致。
- 修改调色脚本后，至少用一张含人物和文字的图像测试保护区域与自然度。

## 已打包版本校验

```text
SHA-256: a6fedea460a52f3986e69ae78e90441182cc6c0cf1b2d779c1f2d68b6870b551
```

