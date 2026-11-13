# 项目数据与放行契约

文件由 Codex 建立和维护，用户只提供内容、素材和决定。`templates/` 提供空字段，示例中的占位和 `pending` 不能当作通过。所有路径相对项目根目录，哈希为实际文件 SHA256；素材库在外部时先把实际使用的安全副本固定进项目。

## 唯一时间与表格

`project.json` 字段：`schema_version:1`、`project_id`、`producer_id`、整数 `duration_ms,fps,width,height`、`inputs:{script,audio,assets}`。输入路径分别指稿件、原配音与 `ASSET_ROLES.csv`。`anchor_tolerance_ms` 默认150毫秒，用于检查需要说明的锚点偏差；它不替代语义审片。`max_full_screen_effect_uses` 默认2，其他值应来自已锁定的用户安排。

| 文件 | 必需字段与含义 |
|---|---|
| `CUE_TIMELINE.csv` | `cue_id,start_ms,end_ms,spoken_text,anchor_ms`。一行一个语义句，ID 唯一，时间来自实际配音，锚点在句内 |
| `ASSET_ROLES.csv` | `asset_id,path,sha256,source,meaning,allowed_sections,allowed_start_ms,allowed_end_ms,max_uses,sensitive_handling`。许可与文件字节一起锁定 |
| `SHOT_SCRIPT.csv` | `cue_id,shot_id,section,start_ms,end_ms,visual_subject,visual_event,event_ms,read_hold_ms,asset_ids,effect_id,timing_note`。每句一行，时间对应 cue；动作偏离锚点超过容差时写理由并接受审片 |
| `MOTION_ADAPTATION.csv` | `section,cue_ids,huashu_grammar,recommended_card,alternative_card,reference_demo,reason`。所有 cue 恰好覆盖一次；推荐卡须给准确 demo，使用 huashu 语法时卡名写 `none` |
| `MOTION_BUDGET.csv` | `section,max_major,notes`。各章节唯一，记录主要动作上限与用途；包含试片选段的额外约束 |
| `RENDER_MANIFEST.csv` | `cue_id,start_frame,end_frame,asset_ids,effect_id,major_motion,full_screen`。从实际代码运行导出，每句一行；`major_motion,full_screen` 为0或1，标记该句拥有的动作事件 |
| `ASSET_USAGE.csv` | `cue_id,asset_id,start_frame,end_frame`。从实际执行导出每段真实可见区间，`cue_id` 为相交的归属句。允许局部出现或连续跨句及静音停顿，跨越的所有句仍核对章节和引用。无外部素材时保留表头 |

多 ID、章节和素材字段使用 `|` 分隔。`STYLE_LOCK.md` 保存视觉及读图约束。支持整数帧率1至240、最长7天的视频，超出范围返回格式错误。整数帧区间左闭右开，起止对 cue 时间的离散偏差不超过1帧，总帧数使用整数向上取整。实际资产许可也转换到帧边界，避免毫秒到帧的舍入误报。

连续可见素材合并为一次出现，跨镜头和静音仍可连续，不按句边界人为切断窗口；中断后再次入镜计新一次。运行引用必须与分镜和素材职责一致。检查器无法证明清单真实来自代码，独立审查还需核实生成方式及实际成片。

## 指纹和证据

```text
python <skill>/scripts/check_project.py --project <项目> --fingerprint
```

命令输出 `input_fingerprint` 与 `plan_fingerprint`。输入指纹包含稿件、声音、素材表、cue 表及画幅/帧率/时长等配置；方案指纹再加入分镜、适配、预算与风格。把输出登记到 `GATES.json`。该命令只计算指纹，不放行。

文件引用统一写为 `{"path":"qa/notes.md","sha256":"实际64位哈希"}`。每个闸口的 `evidence` 是非空引用数组，不能只给文件名或不存在的链接。

## GATES.json

根对象含 `schema_version:1` 和 G0 至 G3。每个闸口含：

- `status`：只有 `pass` 能放行，其他状态阻断该阶段及后续。
- `input_fingerprint`：当前输入指纹；G1/G2/G3 另含 `plan_fingerprint`。
- `evidence`：实际证据数组。

G0/G1 的 `decision` 为 `{"mode":"user|prior_user|delegated","record":文件引用}`。对应本次用户选择、既有确认或明确自主委托。记录原话/消息标识和适用范围；程序只验证记录存在及哈希，Agent 和审查者负责核实来源。

G0 另含 `review_capability:{status,mode,sample_ms,evidence}`。`mode` 只接受 `continuous_av` 或 `segmented_av`，样段至少10秒，原音频不足10秒时使用全部。必须真实验证同步音画审查方法；能力待验时继续独立工作，不完整渲染。

G1 另含非空 `previews` 文件引用数组。完整分镜与全片适配必须已经生成，G1 选择及证据与当前方案绑定。

G2 另含：

- `code_review:{status,independent,reviewer_id,evidence}`，通过且审查者不同于 `producer_id`。
- `sample_review`：实际样段审查文件引用；G2 状态来自审片结论，失败不能标 `pass`。
- `code_snapshot`：实际实现源码的非空文件引用数组，源码改变会使旧 G2 失效。
- `runtime_manifest`：实际执行导出的 `RENDER_MANIFEST.csv` 引用。
- `asset_usage`：实际执行导出的 `ASSET_USAGE.csv` 引用。分镜先核对许可章节与相交时段，实际可见窗口在 G2 逐段核对；素材消失一帧后再出现计为新一次。

## G3 的三种报告

G3 有当前 `video` 引用，`open_issues` 必须明确为 `[]`。另有 `semantic,technical,motion`，各含 `video_sha256` 和 `report` 文件引用。三者必须指向当前视频。

语义报告为 JSON：

```json
{
  "status": "pass",
  "video_sha256": "当前成片实际哈希",
  "mode": "segmented_av",
  "independent": true,
  "reviewer_id": "独立审查者标识",
  "coverage_ms": [[0, 10000], [10000, 20000]],
  "raw_evidence": [{"path": "审片/逐句有声记录.md", "sha256": "实际哈希"}]
}
```

覆盖区间必须覆盖从0到实际音频结束。这个20秒区间只示范格式。`frames_only`、仅转录或音轨相关性不能作为有声语义验收。审查日志须列句 ID、所见所听、实际方法、问题和复核结果。

技术报告 JSON 含 `status:"pass"`、`video_sha256`、`raw_evidence` 非空文件数组，以及 `checks`，其中 `full_decode,dimensions_fps,duration,audio_sync,srt,subtitle_safe,privacy,first_last_frame` 均为 `"pass"`。原始工具报告、关键帧和人工核对记录作为证据，不填未经验证的状态。

动效 `report` 指向 huashu `film_gate.py --json` 的原始 JSON，检查器直接读取 `gate_light` 和 `verdict`，不能靠外层状态覆盖红灯。绿灯或黄灯可进入后续检查，黄灯另需 `yellow_notes` 逐段说明。运行报告本身未包含视频哈希时，通过 G3 引用绑定该次测量的成片。

## 使用与边界

```text
python <skill>/scripts/check_project.py --project <项目> --gate G0
python <skill>/scripts/check_project.py --project <项目> --gate G1
python <skill>/scripts/check_project.py --project <项目> --gate G2
python <skill>/scripts/check_project.py --project <项目> --gate G3 --report <项目>/qa/release-check.json
```

退出0表示记录检查通过，退出2表示失败。检查器不运行外部命令、不联网、不删除或移动文件。可选报告只写项目内未作为输入读取的 JSON 路径。

指纹变化后重做受影响审查，再记录真实结论。程序核验不了用户确认的真实性、语义动画质量、审片者是否实际听看或字段是否被虚构；这些属于独立审查的职责。工具检查通过不能单独等同于最终成片合格。
