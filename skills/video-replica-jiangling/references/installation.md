# 安装与首次使用

本套件面向 WorkBuddy 的本地 Skill 工作流。一次下载包含三个 Skill 的完整文件；用户仍需安装自己的深度模型环境和 Quan MCP。主 Skill 的安装成功不代表所有运行条件已准备好。

## 一 认识安装包

```text
video-replica-jiangling-suite/
  README.md
  skills/
    video-replica-jiangling/
      SKILL.md
      references/
      scripts/check_setup.py
    video-depth-anything/
      SKILL.md
      scripts/infer-depth.ps1
      references/
    qisi-video-remix/
      SKILL.md
      README.md
      LICENSE
      references/
      examples/
```

保留三个文件夹内的子目录和文件。仅复制三个 SKILL.md 会丢失深度执行脚本与 qisi 的交付格式。

## 二 在 WorkBuddy 导入三个 Skill

1. 解压分享包，打开 `skills` 文件夹。
2. 进入 WorkBuddy 的技能管理，使用当前版本提供的本地安装或导入入口。
3. 分别选择 `video-depth-anything`、`qisi-video-remix` 和 `video-replica-jiangling` 三个完整目录。如果界面只接收压缩包，将每个目录分别压缩，保持压缩包内有对应 Skill 目录及其 SKILL.md。
4. 逐个启用，重新打开对话，确认可以按这三个名称调用。不同 WorkBuddy 版本的入口文字可能不同，以用户实际界面为准。
5. 使用本机 Skill 目录安装的用户，应将三个文件夹放在同一层；主 Skill 使用相邻相对路径指向两个配套 Skill。

套件未提供会自动更改宿主配置的安装脚本，也未验证一条第三方 CLI 命令能在所有 WorkBuddy 版本自动导入。请以工具列表与 Skill 实际可读取状态验收。

## 三 安装深度模型环境

`video-depth-anything` 只提供指令和调用脚本，模型权重与 Python 虚拟环境需要另装。详细步骤见 [深度环境安装指南](depth-runtime-setup.md)。

需要准备 Video Depth Anything 官方项目、兼容当前操作系统和显卡的 Python/PyTorch 依赖、Small 相对深度权重，以及 ffmpeg 和 ffprobe。分享版脚本通过 `VIDEO_DEPTH_ANYTHING_HOME` 或 `-ToolRoot` 定位用户的工具目录。

套件内深度执行脚本以 Windows PowerShell 为主要测试对象；macOS 的 Quan MCP 安装支持不能作为深度推理脚本跨平台已验证的证据。其他系统请按上游文档配置并单独验收。

## 四 配置个人 Quan MCP

平台入口：[jl5180.quantv.com](https://jl5180.quantv.com)。按照 [Quan MCP 配置步骤](quan-mcp-setup.md) 使用自己的登录账户安装插件、生成配置、在 WorkBuddy 中添加并信任连接器。

工具至少需要以下五项：

```text
quantv_list_models
quantv_generate_image
quantv_upload_media
quantv_generate_video
quantv_get_task
```

连接状态为绿色只说明 MCP 服务连通。截图中的基础教程主要介绍生图与文本转语音；若安装包未提供视频与素材上传工具，应先向插件提供方取得支持相应工具的版本，停在准备阶段。不要让 Agent 从个人配置提取令牌后绕过连接器直调 HTTP。

## 五 进行无扣费检查

在 WorkBuddy 新对话中发送：

```text
使用 video-replica-jiangling，只做安装验收。
逐项检查三个 Skill、深度运行环境、ffmpeg/ffprobe、模型权重，以及五项 Quan MCP 工具。
报告 PASS、MISSING 或 UNVERIFIED，缺项给具体安装步骤。
不要生成图片或视频，不读取、复制或显示令牌。
```

也可以在终端运行只读环境检查。下面的相对路径要求当前目录为本套件根目录；Python 命令名称根据用户环境选择。

```bash
python skills/video-replica-jiangling/scripts/check_setup.py --help
python skills/video-replica-jiangling/scripts/check_setup.py --probe-python
```

如需让脚本核对 MCP 工具名称，另行提供只含名称的 JSON 文件，例如 `{"tools":[{"name":"quantv_list_models"}]}`，再传 `--tools-json tools.json`。不要传含凭证的 mcp.json。没有工具名称报告时，该项会显示 UNVERIFIED，仍需在 WorkBuddy 中人工核对。

检查只证明安装项是否齐全，无法替代真实视频质量检查。先用用户自己的短素材验收深度提取；用户明确确认费用与参数后，再提交一段视频。收到任务 ID 后持续查询同一任务。

## 缺项与处理

| 发现的问题 | 处理 |
| --- | --- |
| 找不到配套 Skill | 从分享包导入对应完整文件夹并启用 |
| 只找到 SKILL.md，引用文件不存在 | 重新安装该 Skill 的 references、scripts 等完整目录 |
| 没有深度工具目录或权重 | 按深度环境指南配置，再运行只读检查 |
| Quan MCP 工具列表为空 | 回到连接器管理检查配置、信任和启用状态 |
| 只有生图与语音工具 | 升级到含素材上传与视频生成工具的插件版本 |
| 认证过期 | 用户在自己的账号下更新本机凭证，检查时不展示值 |
| 视频已返回任务 ID，但暂时查不到结果 | 保留 ID 继续查，不重复提交 |
