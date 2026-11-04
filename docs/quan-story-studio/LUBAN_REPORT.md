# quan-story-studio 鲁班打磨报告

## 1. 验料结果

真实问题成立。历史人物口播视频需要把文本、音频、镜头、图片和可编辑草稿接在同一时间轴上。该 Skill 的独特资产是 Coli 字级对齐、镜头锚点、拼版复核和剪映草稿脚本。公开传播的阻碍是私人音色和模型 ID 写死，缺少个人配置检查与安装说明。

结论：适合公开分享。首轮聚焦个人 Quan MCP 与音色配置的安全边界。

## 2. 访行记录

| 同行 | 类型 | 可借鉴的做法 | 本轮采用情况 |
| --- | --- | --- | --- |
| [hyperframe-video-production](https://github.com/LeslieLeung/skills/blob/main/skills/hyperframe-video-production/SKILL.md) | 直接 | 配音、镜头与时间轴逐项记录 | 保留现有字级时间轴 |
| [video-production-skill](https://github.com/Aaryan-Kapoor/video-production-skill/blob/main/skills/video-production/SKILL.md) | 直接 | 每次任务有独立目录和产物清单 | 保留项目目录规范 |
| [spark-video director](https://github.com/JohnKeating1997/spark-video/blob/main/references/spark-video-director/SKILL.md) | 间接 | 生图前确认分镜，生成后复核 | 保留两次确认点 |
| [Video Production on ClawHub](https://clawhub.ai/omerflo/skills/video-production) | 间接 | 展示可执行的输入输出路径 | README 加六步产物表 |
| [remotion-best-practices on skills.sh](https://www.skills.sh/remotion-dev/skills/remotion-best-practices) | 手艺 | 首屏给出安装命令与仓库入口 | README 给安装入口 |
| [Uttera on ClawHub](https://clawhub.ai/uttera/skills/uttera) | 手艺 | 列清语音样本、API 与费用条件 | 首屏说明个人 MP3 与额度 |
| [CLI Anything video creation on Tessl](https://tessl.io/registry/skills/github/HKUDS/CLI-Anything/cli-hub-matrix-video-creation) | 手艺 | 预检只显示配置状态 | 增加不显示令牌的 preflight |

## 3. 过尺记录

原版有 `SKILL.md`、工作脚本和参考文档，缺 README、个人配置模板、预检、测试和演示。原版正文与参考文件中有固定的 `referenceId`、语音模型 ID 与图像模型 ID。改写后，仓库里只保留字段占位符，使用者必须提供自己的 MCP JSON、参考 MP3、音色 ID 和模型 ID。

`scripts/preflight.py` 检查 MCP 服务、HTTPS Quan 域名、令牌字段、MP3 编码和个人 ID。检查脚本不发网络请求，不输出令牌。当前 Agent 仍需核对活跃 MCP 的工具列表、音色和模型归属。Skill 指令要求检查失败时停止 Quan 生成。

## 4. 慢刨与验证

修改前原版已备份到本机临时目录并记录 SHA256。改动集中在 MCP 与音色的个人化入口，保留分镜、时间轴和剪映脚本。

1. `python -m unittest discover -s skills/quan-story-studio/tests -v`：三项测试通过，覆盖空模板拒绝、个人配置通过且不泄露令牌、拒绝把含凭据 MCP JSON 当工具报告。
2. `python skills/quan-story-studio/examples/render_demo.py`：从实际预检输出重生成 `preflight-demo.gif`。
3. 固定私人音色与模型 ID 扫描：零命中。
4. `quan_story.py doctor`：当前测试电脑缺 `pyJianYingDraft`，因此本轮未实测剪映导出。未发起付费 Quan 生成，也未验证个人账户里的音色与模型。
5. 从 GitHub 公网执行 `npx skills add https://github.com/yokadanye-prog/danye-mvp --skill quan-story-studio --agent codex --copy --yes`，返回 `status: installed`，项目目录中出现完整 Skill 文件。安装后的空模板预检按预期退出码 1。

## 5. 回炉清单

首次真实使用时验证 Quan 音色列表、模型列表和一次小样，保留不含令牌的验证记录。剪映草稿需在剪映中打开验收。后续根据使用者反馈检查不同客户端的 MCP 配置格式。

## 出师证书

| 项目 | 结果 |
| --- | --- |
| 安装入口 | README 与个人配置说明齐全，公网安装已验证 |
| 私人 ID | 已移除固定音色与模型 ID |
| 预检 | 缺配置时拒绝调用，测试通过 |
| 完整成片验证 | 等待个人 Quan 账户与剪映环境实测 |
