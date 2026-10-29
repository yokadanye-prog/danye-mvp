# Video Replica Jiangling 完整安装套件

一次拿齐三份 Skill 文件，按同一时间轴组织原片、深度参考、图片资产和分段视频任务。

套件中的 `skills` 下有三个完整目录，请在 WorkBuddy 中逐个导入并启用。只导入主 Skill 不会自动注册两个依赖。

| 内容 | 套件是否附带 | 用户下一步 |
| --- | --- | --- |
| video-replica-jiangling 主流程 | 已附带 | 导入完整目录 |
| video-depth-anything 指令和脚本 | 已附带可配置目录的分享版 | 导入完整目录，另装自己的深度环境 |
| qisi-video-remix | 已附带上游资源和 MIT 许可证 | 导入完整目录 |
| 深度 Python 环境与模型权重 | 不附带 | 按上游指南安装并检查 |
| Quan MCP 安装器与个人凭证 | 不附带 | 按教程下载插件，用自己的账号配置 |

## 安装入口

1. [三个 Skill 的导入与首次检查](../../skills/video-replica-jiangling/references/installation.md)
2. [深度模型运行环境](../../skills/video-replica-jiangling/references/depth-runtime-setup.md)
3. [Quan 平台 MCP 配置](../../skills/video-replica-jiangling/references/quan-mcp-setup.md)

平台地址：[jl5180.quantv.com](https://jl5180.quantv.com)。教程地址：[用户提供的飞书文档](https://shikongjikeai.feishu.cn/docx/ZERzd17u9olDGYxStjackVKRndd?from=from_copylink)。套件里的文字步骤已按用户截图整理；下载附件仍以原教程为准。

基础教程介绍生图与语音 MCP，安装后还需确认存在 `quantv_upload_media` 与 `quantv_generate_video`。如果缺少视频工具，请先取得支持本工作流的插件版本。

## 装完先说这句话

```text
使用 video-replica-jiangling，只做安装验收。
检查两个配套 Skill、深度环境和五项 Quan MCP 工具，列出缺项与具体安装步骤。
不要生成图片或视频，不读取、复制或显示令牌。
```

## 终端验证

从本套件根目录运行：

```bash
python skills/video-replica-jiangling/tests/test_setup.py
python skills/video-replica-jiangling/scripts/check_setup.py --help
python skills/video-replica-jiangling/scripts/check_setup.py --probe-python
```

安装项不齐或尚未验证时，检查脚本返回退出码 2，并逐项报告 MISSING／UNVERIFIED。模型推理与付费视频生成需要在准备完成后另行验收。

## 本轮修改与证据

见 [变更说明](CHANGELOG.md)、[鲁班打磨报告](LUBAN_REPORT.md) 和 `verification` 目录。没有把未运行的推理或付费生成写成成功实测。

## 凭证与许可

分享包只带 Skill、脚本、文档和测试资料。Quan 使用者需要自己的账户与额度。qisi 的作者署名与 MIT 许可证已保留；深度模型代码和不同权重的许可单独遵循上游。详见 [第三方说明](THIRD_PARTY_NOTICES.md)。
