---
name: quan-story-studio
description: 视频号历史人物故事口播视频的六步流水线，使用用户自己的 Quan MCP、API 凭据和参考 MP3 音色，完成写稿、配音、分镜、生图、时间轴与剪映草稿。用户说「制作历史人物故事」「Quan 配音和生图」「按旁白做分镜」「发送到剪映草稿箱」时使用。必须先通过本地配置检查并核对当前 MCP 账户的音色与模型。需要普通故事写作、非 Quan 图片或不使用剪映草稿时，使用其他合适工具。
---

# Quan 故事工坊

一支 4–6 分钟的历史人物口播视频，从一句选题到剪映草稿箱，六步走完。

这个技能聚焦 **Quan 平台配音 + Quan 平台生图 + 剪映草稿**。每位使用者需配置自己的 Quan API 凭据、参考 MP3 音色和对应的音色 ID。运行时必须使用当前用户授权的 MCP 服务，不能调用作者或其他人的账号配置。

## 使用前的硬性检查

先按照 [个人配置说明](references/setup.md) 在技能目录准备 `.quan-story.local.json`。从技能目录运行：

```bash
python scripts/preflight.py --setup .quan-story.local.json
python scripts/quan_story.py doctor
```

`preflight.py` 只读取用户指定的 MCP 配置，检查 Quan 域名、令牌是否已填、参考 MP3 是否可解码、音色及模型 ID 是否已填。它不会打印令牌，也不会发起网络请求。检查失败时停止 Quan MCP 调用。检查通过后，仍须在当前 Agent 运行环境确认 `quantv_list_models`、`quantv_list_voices`、`quantv_generate_speech`、`quantv_generate_image` 可用，且音色 ID 与模型 ID 属于当前连接的账户。无法确认时停止生成，请用户完成自己的 Quan 配置。不得从他人的 MCP 配置中提取令牌，也不得绕过 MCP 直调 HTTP。

| | story-studio | 本技能 |
| --- | --- | --- |
| 配音 | 豆包语音 | 用户自己的 Quan 音色（`referenceId`） |
| 配图 | 宿主图像工具 | 用户自己的 Quan 图像模型 |
| 图数怎么定 | 用户指定或模块默认 | 按实测语速算三档，用户挑一个 |
| 用户确认点 | 看情况 | 固定两道闸门：画面方向、拼版复核 |
| 时间轴 | 转录对齐 | Coli 字级时间戳 + 锚点定位 |
| 终点 | 草稿或本地 MP4 | 直接落剪映草稿箱 |

时间轴是这条流水线里最容易翻车的地方，所以它被工具化成了命令，不靠手算：
`scripts/quan_story.py` 用 Coli 的**字级时间戳**把每个镜头的起止卡到具体某个字上，误差约 0.1 秒。

---

## 一、流水线

```text
①  写稿/定稿        →  正文.md（1500–2000 字）
②  Quan 配音        →  配音正式/人物名_完整版.mp3
③  定图数 + 出分镜   →  分镜/STORYBOARD.json（每镜一句画面 + 锚点）
        └─ 闸门 A：用户确认画面方向和图数
④  Quan 批量生图     →  配图/S001.png …
        └─ 闸门 B：拼版复核，用户指认要重做的镜
⑤  时间轴 + 校验     →  edit/plan.json
⑥  写入剪映草稿     →  剪映草稿箱里出现《人物名_edit_v1》
```

本地依赖检查先做一次：

```bash
python scripts/quan_story.py doctor
```

缺 `pyJianYingDraft` / Pillow / ffprobe 时，按 `references/pitfalls.md` 的「环境」一节补齐。技能可继承 `story-studio` 已装好的本地运行时。MCP 和音色仍需逐人配置。

---

## 二、第 ① 步：定稿

正文建议 1500–2000 字，以适合口播的具体场景和人物动作为主。要写新稿可用 `story-studio` 的写作模块；用户已有稿就直接进第 ② 步。

交付前只确认两件事：**字数**、**每一句都能被画出来**。第二件事决定第 ③ 步顺不顺——抽象议论句（"这就是中国人的骨气"）配不出具体画面，写稿时就要换成可拍的动作或物件。

产物：`<项目>/正文.md`

---

## 三、第 ② 步：Quan 配音

先确认 `preflight.py` 通过，再用当前用户的 `quantv_list_voices` 核对 `.quan-story.local.json` 里的 `voice_reference_id`。用户需自行在 Quan 平台用自己的参考 MP3 创建或选择音色，并填写平台返回的 `referenceId`。参考 MP3 不上传到技能仓库。`speech_model_id` 应从当前账户可用模型中选取，不沿用其他人的 ID。首次使用或换音色时让用户先听 15 秒。

流程：

1. **试听**：取正文开头 200–300 字生成 15–25 秒小样，交用户确认。用户已在别处确认过音色时跳过。
2. **正式**：全文一次生成，`wait=true`。返回的 `quantv_*` 任务与音频一起存到 `配音正式/quan_task.json`。
3. **验时长**：`quan_story.py probe --audio ... --text ...` 看时长和语速。语速落在 **4.5–5.8 字/秒** 属正常，明显偏快偏慢说明音色或文本不对。
4. **转录**：Coli 出 `coli_asr.json`（带字级时间戳）+ `transcript.srt`，存 `transcription/v1/`。

⚠️ 同一段文本 + 同一个 `referenceId` 重复调用可能命中平台去重。真要重生成必须加 `forceNew: "CONFIRM_NEW_CHARGE"`（会重新计费，仅在用户明确要求时用）。
⚠️ 换音色后一定要听，不要只看时长——曾经出现过"文件换了、音色没换"的情况。

细节与音色核验方法见 `references/voice.md`。

产物：`配音正式/<人物>_完整版.mp3`、`transcription/v1/{coli_asr.json,transcript.srt}`

---

## 四、第 ③ 步：定图数，出分镜

### 图数由语速算，不让用户凭感觉猜

```bash
python scripts/quan_story.py suggest --audio "配音正式/xxx.mp3" --text "正文.md"
```

它按实测时长给三档：

| 档位 | 每镜 | 节奏感 | 五分钟片子的参考 |
| --- | --- | --- | --- |
| 快 | 6 秒 | 信息密、转场多，适合强情节 | ≈ 55 张 |
| **标准** | **8 秒** | **默认档，适合一般人物叙事** | **≈ 40 张** |
| 舒缓 | 10 秒 | 留白多，适合抒情传记 | ≈ 33 张 |

把三档报给用户，让他选一个数字。用户给了具体张数就按他的来，不改。

### 分镜怎么写

先写一份镜头草稿 `分镜/sheet.json`。顶层定风格和人物，`shots` 里一镜一条：

```json
{
  "title": "容闳 · 41镜",
  "style_id": "historical-realism",
  "era": "晚清至民国",
  "prompt": {
    "prefix": "历史写实风叙事插画，…（风格句，见 references/images.md）",
    "suffix": "色彩低饱和…9:16竖版，无字幕、无文字、无水印、无边框。"
  },
  "characters": [
    { "id": "RONGHONG", "name": "容闳", "appearance": "清末中国人，蓄长辫，穿中式长袍" }
  ],
  "shots": [
    {
      "id": "S012",
      "anchor": "大学四年，他半工半读，给同学办过伙食",
      "description": "耶鲁校园一角，容闳在简陋的厨房帮同学准备餐食，衣袖挽起，一旁堆着书本。",
      "shot_size": "中景",
      "viewpoint": "平视",
      "subject": "耶鲁半工半读",
      "character_ids": ["RONGHONG"],
      "character_age": "26岁"
    }
  ]
}
```

- `prefix` / `suffix` 只写一遍，脚本把它拼到每一镜上，保证全片风格统一。
- `characters` 决定人物描述，`character_age` 让同一个人在不同镜里变年龄而不是变脸。
- `anchor` 是这一镜口播原文的**开头一句**，必须能在正文里逐字找到。时间轴靠它定位，写错这句整镜都会偏。
- `description` 只写画面里看得见的东西：谁、在哪、做什么、什么光。不写心理活动，不写"象征"。
- 一镜一件事。一句话里跨了场景就拆两镜。

然后再拼风格、算时间：

```bash
python scripts/quan_story.py build \
  --sheet 分镜/sheet.json --text 正文.md \
  --timing transcription/v1/coli_asr.json \
  --audio 配音正式/xxx_完整版.mp3 \
  --out 分镜/STORYBOARD.json
```

输出会报三件事，都要看：

```text
镜数 41 | 总时长 244.17s | 平均 5.96s | 最短 2.93s | 最长 13.66s
计时依据：token（transcript-tokens） | 转录精确 31 镜 / 相似度 10 镜 / 插值 0 镜
```

**插值镜数必须为 0**。出现"按序号均分""必须人工定位"的镜，说明锚点没对上，回到 sheet 改 anchor 再跑，不要带着错误进生图。

### 闸门 A：给用户看方向

把 `STORYBOARD.md`（每镜：镜号 / 时长 / 一句话画面 / 景别）发出去，同时说清三件事：

- 总镜数、总时长、平均每镜几秒
- 画风（默认历史写实，其他见 `references/images.md`）
- 有没有需要提前说明的画面（敏感人物、文字招牌、真实照片）

用户确认或调整后才进第 ④ 步。用户说"直接做"就跳过等确认，但仍要先把这三件事写清楚。

---

## 五、第 ④ 步：Quan 批量生图

每镜调用 `quantv_generate_image`：

```text
prompt   = 镜头的完整提示词（build 已拼好，见 STORYBOARD.json 的 prompt 字段）
ratio    = 9:16
resolution = 1K
modelId  = .quan-story.local.json 中的 image_model_id，先与当前账户的可用模型核对
```

**批量节奏**：一次并行提交 5 张，收完再发下一批。41 张大约 8 批。每张成功后立刻下载到 `配图/Sxxx.png`，并把返回 URL 记进 `_img_urls.txt`。

单张失败（超时、内容审核、返回空）先原样重试一次；再失败就**简化提示词**——去掉抽象修饰、只留"谁在哪做什么"，通常就过了。

### 闸门 B：拼版复核

```bash
python scripts/quan_story.py contact --plan edit/plan.json --columns 5 --thumb-width 220
```

产出一张带镜号和时长的拼版，用户一眼扫完。重点提醒他看四类问题：

| 现象 | 处置 |
| --- | --- |
| 画面里出现乱码文字、伪汉字招牌 | 提示词加"画面不出现任何文字"，重生成该镜 |
| 该黑白却是彩色（或反过来） | 风格句写死"纯黑白灰阶照片风格" |
| 人物跨镜不像同一个人 | 每镜提示词都带同一段人物描述，必要时传参考图 |
| 与旁白说的不是一回事 | 改 `description` 后重生成，不要只改提示词尾部 |

只有用户指认的镜才重做，不要自己顺手全重生成——每张都要花额度。

---

## 六、第 ⑤ 步：时间轴与校验

```bash
python scripts/quan_story.py plan \
  --storyboard 分镜/STORYBOARD.json \
  --audio 配音正式/xxx_完整版.mp3 \
  --out edit/plan.json

python scripts/quan_story.py verify edit/plan.json
```

`verify` 检查：镜界连续、首镜从 0 开始、末镜盖住全部旁白、图片齐全且比例对、有没有同图重复、有没有过短过长的镜。**不通过不要导出**。

`zoom` 默认奇偶交替推拉（`[1.0,1.07]` / `[1.07,1.0]`），让相邻镜头方向相反，观感不呆板。

---

## 七、第 ⑥ 步：写入剪映草稿箱

```bash
python scripts/export_draft.py edit/plan.json --name "人物名_edit_v1"
```

草稿直接出现在剪映的草稿列表里，双击就能改。默认竖屏 1080×1920 / 30fps / 整段配音 / **字幕不上屏**（SRT 只用于定位）。

- 草稿名用 `<人物名>_edit_v1`，改版就 `_v2`，**不要覆盖**用户正在剪的草稿。
- 导出成功后 `edit/jianying_draft.json` 会记下草稿路径、时长、镜数，把它作为交付凭证报给用户。
- 草稿目录找不到时加 `--drafts-root "剪映设置里显示的草稿位置"`。

---

## 八、命令速查

| 命令 | 用途 |
| --- | --- |
| `doctor` | 查依赖、ffprobe、Coli、草稿目录 |
| `probe --audio --text` | 报时长、字数、实际语速 |
| `suggest --audio --text` | 三档镜数建议 |
| `build --sheet --text --timing --audio --out` | 镜头草稿 → 带时间的 STORYBOARD |
| `realign --storyboard --old-timing --new-timing` | 换了配音后，按字符位置重排旧镜界 |
| `plan --storyboard --audio --out` | STORYBOARD → 剪映时间轴 |
| `verify plan.json` | 导出前体检 |
| `contact --plan` | 拼版复核图 |
| `export_draft.py plan.json --name …` | 写进剪映草稿箱 |

`realign` 是补救命令：片子配好图之后发现配音要重录，不要重排分镜——重录、转录，然后 `realign` 一次，图、提示词、顺序全不动。

---

## 九、项目目录

```text
<人物名>/
├── 正文.md
├── 基础信息表.md            # 生卒、关键年份、事件顺序（写稿核对用）
└── 版本1/
    ├── 配音正式/
    │   ├── <人物>_完整版.mp3
    │   ├── narration.txt        # 实际朗读的文本（去掉标题）
    │   └── quan_task.json
    ├── transcription/v1/
    │   ├── coli_asr.json        # 字级时间戳，最重要
    │   └── transcript.srt
    ├── 分镜/
    │   ├── sheet.json           # 镜头草稿（人写的）
    │   ├── STORYBOARD.json      # 带时间（脚本写的）
    │   └── STORYBOARD.md
    ├── 配图/S001.png …
    └── edit/
        ├── plan.json
        └── jianying_draft.json
```

改稿、换配音、重做图都开新目录（`版本2/`、`transcription/v2/`、`plan_v2.json`），旧版本留着。

---

## 十、收工前自检

1. **图数与时长**：`镜数 × 平均秒数 ≈ 配音时长`，末镜不留黑。
2. **音画同步**：随机挑 3 镜，在剪映里听切点那一句是否与画面同拍。
3. **人物一致性**：把 S001 和 S041 并排看，是同一个人的脸。
4. **文字穿帮**：任选 5 张放大看招牌、书页、报纸，不能有伪汉字。
5. **草稿可改**：草稿能打开、能拖动、素材不丢（文件都在草稿的 materials 里）。

交付时按"文稿 / 配音 / 分镜 / 配图 / 草稿"五样分别说清哪些已完成、哪些还缺，不要把"图片已生成"说成"片子已做完"。

---

## 参考

- `references/voice.md` — Quan 音色：试听、正式生成、去重缓存、音色核验、变速兜底
- `references/images.md` — Quan 生图：三类画风提示词模板、批量节奏、失败与穿帮修复
- `references/draft.md` — 剪映草稿：时间轴字段、导出、校验、版本管理
- `references/pitfalls.md` — 四次实战踩过的坑与现场处置
