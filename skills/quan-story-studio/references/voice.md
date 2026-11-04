# Quan 配音

通过 `scripts/preflight.py` 后，使用当前用户连接的 `quantv_list_voices` 和 `quantv_generate_speech`。每位用户须使用自己的 Quan API 凭据、参考 MP3 与由该账户创建或选择的音色。`quantv_wait_task` 与 `quantv_upload_media` 仅在当前连接器提供且任务需要时使用。

## 音色表：认 referenceId，不认 id

```text
quantv_list_voices({ officialOnly: true })
```

返回里每条音色有两个标识：`id` 是音色条目的编号，`referenceId` 才是生成语音要填的那个。传错会报"音色不存在"。

从当前用户的 `.quan-story.local.json` 读取音色和模型 ID，随后在当前账户的音色和模型列表里核对：

```json
{
  "referenceId": "<本人账户的 voice_reference_id>",
  "modelId": "<本人账户的 speech_model_id>"
}
```

若用户只有参考 MP3，先引导其在 Quan 平台创建音色并取得 `referenceId`。当前 MCP 连接器若未提供音色创建工具，不要假设 `quantv_upload_media` 会自动创建音色。换音色前必须让用户听样。用户只说"换个声音"没给名字时，列出 2–3 个当前账户可用的候选。

## 生成参数

```json
{
  "text": "全文",
  "referenceId": "<本人账户的 voice_reference_id>",
  "modelId": "<本人账户的 speech_model_id>",
  "speed": 1,
  "volume": 0,
  "wait": true
}
```

- `speed` 只有 `0.5 / 1 / 2` 三档。**没有 0.88 这种值**——需要微调语速时不要在这里试，用 ffmpeg（见文末）。
- `volume` 只有 `-1 / 0 / 1`。默认 0。
- `wait: true` 直接等结果，比自己轮询 `quantv_wait_task` 省事。
- 文字上限不明确，实测 2000 字以内一次成功。超长稿先按段落切、再拼接（会有轻微语气断裂，尽量一次成）。

## 试听：先 15 秒，再全文

第一次用某个音色、或用户对音色有疑问时：

1. 取正文开头 200–300 字（到第一个自然停顿处截断）
2. 生成小样 → `配音试听/<人物>_开头试听.mp3`
3. 交给用户听，明确问一句"这个音色对吗"

用户已经在参考视频里确认过音色时跳过试听，直接全文生成。

## 重复调用会被去重

同一段 `text` + 同一个 `referenceId`，平台会命中缓存，返回**和上次完全相同的文件**（MD5 一致）。表现是"重新生成了但时长一秒不差"。

真要重做，加：

```json
{ "forceNew": "CONFIRM_NEW_CHARGE" }
```

这是**重新扣费**的动作，只在用户明确说"重新生成一版"时用。网络报错的重试**绝不能**加这个字段。

## 三种必须停下来核验的情况

| 现象 | 判断 | 处置 |
| --- | --- | --- |
| 重生成后时长一模一样 | 命中缓存 | 确认是否要 `forceNew` |
| 换了音色，时长差 30 秒以上 | 音色确实换了 | 正常，重新转录 + `realign` |
| 换了音色，时长几乎没变 | **很可能没换成功** | 让用户听，别只看时长 |

第二、三种的区别只有"听"能确认。曾经出现过 333 秒和 293 秒两个版本并存、都叫"完整版"的情况，最后靠时长差 40 秒才定位到旧文件音色是错的。**文件名里带音色或时长的标记**能省掉这类排查。

## 转录

```bash
coli asr -j --model sensevoice --language zh "配音正式/xxx_完整版.mp3" > transcription/v1/coli_asr.json
```

`coli_asr.json` 里有 `tokens` 和 `timestamps` 两个等长数组——**每个汉字一个时间戳**，这是整条流水线的时间基准。只保留 SRT 会丢掉字级精度，分镜时间就会退化成"按句估算"。

同时用 `coli` 的 SRT 输出存一份 `transcript.srt`，给需要上屏的场合备用（本流水线默认不上屏）。

转录后核对一次：`coli_asr.json` 的 `duration` 与 MP3 实测时长差应在 0.1 秒内；正文与转录的字数差超过 8% 说明稿子和音频不是同一版。

## 语速自查

```bash
python scripts/quan_story.py probe --audio 配音正式/xxx.mp3 --text 正文.md
```

- `chars_per_second` 落在 **4.5–5.8**：正常
- 低于 4.2：可能语速被调慢、或文本里有大量停顿符号
- 高于 6.0：语速偏快，5 分钟的片子会挤进 4 分钟，图数要相应增加

## 变速兜底（不改音色，只改时长）

配音时长与既定图数不匹配、又不方便重录时：

```bash
ffmpeg -y -i in.mp3 -filter:a "atempo=0.87948" -c:a libmp3lame -b:a 192k -write_xing 0 out.mp3
```

- `atempo` 是无损变速且保持音高，0.88 倍听不出变调。
- **加 `-write_xing 0`**：否则 ffprobe 会因 Xing 头报出两个相差约 0.04 秒的时长，导出草稿时校验会失败。
- 变速是线性变换，分镜时间可以直接按同比例缩放（333.56 → 293.36 就是 ×0.8794），不需要重新转录。
