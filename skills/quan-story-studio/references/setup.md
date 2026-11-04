# 配置自己的 Quan MCP 与参考 MP3

平台入口是 [jl5180.quantv.com](https://jl5180.quantv.com)。请在自己的 Quan 账户完成 MCP 安装和授权，由安装器生成本机 MCP JSON。配置文件和令牌仅保留在本机。不要把它们复制到 Skill 仓库或聊天消息。

## 1. 准备 MCP

在 Agent 客户端添加安装器生成的 `quantv-generation` 服务，并启用连接。MCP JSON 中须含 `mcpServers.quantv-generation.env.QUANTV_BASE_URL` 和 `QUANTV_ACCESS_TOKEN`。`QUANTV_BASE_URL` 应为 HTTPS Quan 域名。使用安装器给出的实际地址，不手工猜测 API 路径。

当前客户端需要能看到 `quantv_list_models`、`quantv_list_voices`、`quantv_generate_speech`、`quantv_generate_image`。连接状态提示成功之后，仍要查看工具列表。

## 2. 准备自己的音色

准备一段有使用授权的参考 MP3。先在 Quan 平台用该 MP3 创建或选择自己的音色，记下平台返回的 `referenceId`。当前连接器若没有创建音色的工具，就在 Quan 平台界面完成。MP3 文件与 `referenceId` 都属于使用者，技能不附带任何人的音色或音频。

在当前账户可用模型列表里选择语音模型和图像模型，分别记录其 ID。不要复制公开示例或其他账户的模型 ID。

## 3. 填写本机配置

在技能目录复制 `setup.example.json` 为 `.quan-story.local.json`，填写 MCP JSON 路径、参考 MP3 路径、自己的音色 ID 与模型 ID。`.quan-story.local.json`、MCP JSON 和 MP3 都不要提交到 Git。也可以通过 `QUAN_STORY_SETUP` 指向其他位置的个人配置文件。

```bash
python scripts/preflight.py --setup .quan-story.local.json
python scripts/quan_story.py doctor
```

在技能目录运行上述命令。`preflight.py` 只检查本地文件与配置字段，且不显示令牌。输出 `LOCAL_SETUP_READY` 后，Agent 仍需在当前连接的 MCP 中核对音色和模型确实可用。任何项目生成之前都执行这一检查。切换 Quan 账户或音色后重新检查。

如需自动核对工具名称，可提供只含名称的 JSON：

```json
{"tools":[{"name":"quantv_list_models"},{"name":"quantv_list_voices"},{"name":"quantv_generate_speech"},{"name":"quantv_generate_image"}]}
```

然后运行 `python scripts/preflight.py --setup .quan-story.local.json --tools-json tools.json`。不要把带令牌的 MCP JSON 当作工具报告传入。

## 4. 调用边界

检查未通过时停止所有 Quan 生成调用。只调用当前客户端里用户自己启用的 Quan MCP 工具。不得读取其他人的本机 MCP 配置、借用其他人的 `referenceId`、从 MCP 配置提取令牌后直调 HTTP，或把参考 MP3 放进公开仓库。首次付费生图前先确认镜数与画面方向。
