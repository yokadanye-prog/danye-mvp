# 剪映草稿

`edit/plan.json` 是唯一的时间轴真源，草稿由它生成。不要手改草稿，改 plan 再重新导。

## plan.json 结构

```json
{
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "crf": 18,
  "audio": "../配音正式/容闳_完整版.mp3",
  "shots": [
    {
      "id": "S001",
      "image": "../配图/S001.png",
      "start": 0.0,
      "end": 3.06,
      "zoom": [1.0, 1.07],
      "pivot": [0.5, 0.5],
      "anchor": "耶鲁毕业"
    }
  ]
}
```

- `start` / `end` 单位秒，**必须首尾相接**：上一镜的 `end` 就是下一镜的 `start`，误差超过 0.01 秒 `verify` 会报错。
- `zoom` 两个值：`[起, 止]`，都 ≥ 1。`[1.0,1.07]` 是缓慢推近，`[1.07,1.0]` 是缓慢拉远。奇偶交替，观感最稳。
- `pivot` 是推拉的锚点，`[0.5,0.5]` 居中。人物偏左时用 `[0.35,0.5]`，避免推到空处。
- `audio` 可选；不填就是无声草稿。
- `subtitles` 可选；填了也**不会上屏**，只在需要时作定位参考（`export_draft.py` 默认不加文字轨，除非 `--with-subtitles`）。

`quan_story.py plan` 会自动算 `image` 的相对路径。跨盘时写绝对路径。

## 导出

```bash
python scripts/export_draft.py edit/plan.json --name "容闳_edit_v1"
```

草稿落到剪映草稿目录，列表里直接出现。脚本会做这些事：

1. 把图片和音频复制进 `草稿/materials/`（按内容哈希命名），草稿自包含，原项目目录删了也不影响。
2. 逐帧写缩放关键帧（`fps × 镜长` 个点），Ken Burns 缓动在剪映里是真曲线，不是两帧之间插值。
3. 音频放独立轨，图片铺满画面（cover + 4% 余量）。
4. 写完回写 `edit/jianying_draft.json` 和 `resolved_plan.json`。

`--drafts-root` 找不到草稿目录时才用，值就是剪映设置里显示的草稿位置。

## 命名与版本

| 场景 | 名字 |
| --- | --- |
| 首次 | `<人物名>_edit_v1` |
| 改时间轴 | `_v2`、`_v3` |
| 只换某几张图 | 同名重导（`--overwrite`），会先备份旧草稿 |

**不要覆盖用户正在剪的草稿。** 默认行为就是拒绝同名，这是刻意的。

## 三个典型报错

| 报错 | 原因 | 解决 |
| --- | --- | --- |
| `末镜没有盖住全部旁白` | 时间轴比配音短 | 回 `build` 重算，或手动把末镜 `end` 改到音频时长 |
| `音频时长两次探测差超过一帧` | MP3 带 Xing 头 | 用 `-write_xing 0` 重编码为 CBR |
| `与上一镜有间隙、重叠或零帧` | 手改了某一镜的 start/end | 跑 `verify` 定位，改回连续 |

## 草稿打不开、或改不动

剪映打开过某个草稿后，`draft_content.json` 会被加密成 base64 密文，程序再也读不了、也改不了。

**不要试图解密或原地修改。** 正确做法是生成一个新名字的草稿（`_v2`），旧草稿留着让用户自己删。

判断方法：读 `draft_content.json`，开头是 `{` 就是明文，是长串 base64 就是加密了。

## 换了配音怎么办

片子配完图才发现配音要重录时，**不要重排分镜**：

```bash
quan_story.py realign \
  --storyboard 分镜/STORYBOARD.json \
  --old-timing transcription/v1/coli_asr.json \
  --new-timing transcription/v2/coli_asr.json
```

它按"字符位置"把每个镜界从旧时间轴映射到新时间轴——图、顺序、提示词全不动，只有时间变。之后重新 `plan` + `export`，用新草稿名。

梅兰芳那次 333 秒换 293 秒、41 镜，就是靠这一步 10 秒完成的；如果重排分镜，等于重做一遍。

## 上屏字幕（一般不用）

口播视频默认不带字幕：竖屏画面本来就满，字幕压脸。只有用户明确要时才：

```bash
python scripts/export_draft.py edit/plan.json --name "xxx_edit_v1" --with-subtitles
```

前提是 plan 里有 `subtitles` 字段指向 SRT。
