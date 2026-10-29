# 在 WorkBuddy 配置自己的 Quan MCP

本说明依据用户提供的两张教程截图整理。原文入口：[飞书配置教程](https://shikongjikeai.feishu.cn/docx/ZERzd17u9olDGYxStjackVKRndd?from=from_copylink)。用户指定的平台入口：[jl5180.quantv.com](https://jl5180.quantv.com)。截图内容作为配置参考，不代表本套件维护者已登录验证每一个系统安装包。

本套件不附带 Quan 安装器、个人账号、令牌或积分。截图中的账户、路径和凭证均不复用，也不把截图原图打包分发。

## 一 下载对应系统版本并解压

打开原教程，下载与操作系统和处理器架构一致的版本。截图提供以下名称，下载前以原文当前附件为准：

| 系统 | 截图中的安装包 |
| --- | --- |
| macOS Apple Silicon | QuantV-MCP-macOS-Apple-Silicon.zip |
| macOS Intel | QuantV-MCP-macOS-Intel.zip |
| Windows ARM64 | QuantV-MCP-Windows-arm64.zip |
| Windows x64 | QuantV-MCP-Windows-x64.zip |

Windows 用户可在“设置 → 系统 → 关于 → 系统类型”查看架构。下载后先完整解压，不能在压缩包预览中直接运行安装入口。

## 二 运行安装器并使用本人的凭证

截图中的 Windows 入口是“安装并生成配置.bat”，macOS 入口是“安装并生成配置.command”。以实际解压文件为准。

1. 在浏览器登录自己的 Quan 账户。
2. 按教程在本人已登录页面打开开发者工具，进入 `Application → Local storage → 当前平台站点`。
3. 找到 `token` 和 `refreshToken`。`token` 对应安装器的 `QUANTV_ACCESS_TOKEN`。`refreshToken` 对应 `QUANTV_REFRESH_TOKEN`，截图注明这一项可留空。
4. 在本机安装器提示处粘贴自己的值并回车。不要把这些值发给 AI、其他用户或放进 Skill 文件。不要将认证值写入示例或提交仓库。
5. 安装器会输出 MCP 配置，并保存本机配置文件。截图显示安装器会准备匹配的 Node 运行时并检查站点与令牌。不同版本的实际行为需要用户核对。

截图使用的站点域名与本次平台入口可能不同。`QUANTV_BASE_URL`、运行程序和脚本绝对路径，应来自本人安装器生成的配置或平台提供方确认的配置，不把他人的路径或域名盲目覆盖进本机。

## 三 在 WorkBuddy 添加连接器

1. 打开“专家·技能·连接器”，进入“连接器”。
2. 点击“自定义连接器”，在 MCP 服务管理中选择“添加 MCP”。
3. 加入安装器生成的 `quantv-generation` 服务对象。配置外层已经有 `mcpServers` 时，将新服务合并到该对象中；保留已有的其他服务，避免重复嵌套 `mcpServers`。
4. 保存配置，回到 MCP 列表。首次连接时按界面提示信任该服务，并打开启用开关。
5. 查看连接状态与工具名称。若当前对话没有新工具，重新打开对话，必要时完整退出并重启 WorkBuddy。

以下仅说明 JSON 结构，不是可以直接运行的个人配置。真实值只填在用户自己的本机配置中：

```json
{
  "mcpServers": {
    "quantv-generation": {
      "command": "<安装器生成的 Node 程序绝对路径>",
      "args": ["<安装器生成的 server.mjs 绝对路径>"],
      "env": {
        "QUANTV_BASE_URL": "<安装器或平台确认的服务地址>",
        "QUANTV_ACCESS_TOKEN": "<仅在本机填写本人的令牌>",
        "QUANTV_REFRESH_TOKEN": "<仅在本机填写，可按安装器要求留空>",
        "QUANTV_SUBMISSION_JOURNAL_FILE": "<本人本机任务记录文件路径>"
      }
    }
  }
}
```

## 四 本 Skill 需要额外核对视频工具

教程标题是“quantv 生图和文本转语音 MCP”。因此，“连接成功”不能证明当前插件同时具备视频生成能力。

本工作流要求 `quantv_list_models`、`quantv_generate_image`、`quantv_upload_media`、`quantv_generate_video`、`quantv_get_task` 五项工具同时可用。`quantv_wait_task` 可以作为可选查询工具。

若只有生图与语音工具，先取得支持视频提交与素材上传的连接器版本，或由用户自己的开发环境完成对应扩展。当前套件只打包三个 Skill，不分发未经确认授权的第三方 MCP 程序，也不把“修改过的本机插件”当作所有用户已具备的能力。

安装验收时只核对名称，并可调用公开模型列表工具读取模型信息。不要通过生成图片或视频来试探连接是否成功。缺项、认证失败或权限不明时停止，用户完成自己的配置后再继续。
