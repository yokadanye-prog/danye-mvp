# Video Replica Jiangling

把参考原片、深度视频、角色与场景图片，按同一时间轴交给 WorkBuddy 逐段处理。

本分享套件带齐主 Skill、video-depth-anything 和 qisi-video-remix 三份完整技能文件。用户还需在自己的电脑安装深度模型环境，并配置自己的 Quan MCP；图片与视频生成使用个人账户额度。

## 先看交付范围

已有资料包括工作流指令、本地素材上传工具的既有验证记录，以及本轮的安装检查。新版 MCP 的付费视频闭环仍待单独验证，当前没有可宣传为完整实测的批量生成示例。

## 安装顺序

1. 解压套件，在 WorkBuddy 分别导入并启用 `skills` 下三个完整 Skill 目录。
2. 按 [安装指南](references/installation.md) 配置深度模型环境，模型权重另行下载。
3. 打开 [Quan 平台](https://jl5180.quantv.com)，按照 [截图整理的配置说明](references/quan-mcp-setup.md) 安装自己的 MCP。
4. 检查五项必需 MCP 工具，特别是素材上传和视频生成。基础生图／语音插件可能没有这两项。

装完第一句话：

```text
使用 video-replica-jiangling，只做安装验收。
检查两个配套 Skill、深度运行环境和 Quan MCP，列出缺项和处理步骤。
不生成图片或视频，不读取或显示令牌。
```

如使用终端检查，从套件根目录执行：

```bash
python skills/video-replica-jiangling/scripts/check_setup.py --help
python skills/video-replica-jiangling/scripts/check_setup.py --probe-python
```

工具名称可以通过单独的无凭证 JSON 报告传入，示例见安装指南。没有该报告时，脚本将 MCP 标为 UNVERIFIED，由用户在 WorkBuddy 当前工具列表核对。

## 适用场景

人物动作与服装展示短片、角色设定的短片测试，以及原片与深度参考按同一时间轴组织的分段制作。先确认分段，再检查深度参考和图片，最后逐段提交与查看视频结果。

## 依赖适配

深度 Skill 负责提取相对灰度深度；qisi 提供已确认片段的素材与动作提示词。主流程负责分段、确认与付费调用。配套资料中的独立故事改编和多候选生成规则，不会自动扩大本任务的生成范围。

## 失败处理与凭证

缺少 Skill、脚本、权重或必需 MCP 工具时停在准备阶段。所有 Quan 操作使用当前用户自己安装的 MCP；分享包不带个人配置和令牌。任务已返回 ID 后沿该 ID 查询，新增付费请求需要用户明确决定。

## 验证

安装检查脚本为只读检查，既不联网安装也不发起生成。测试样例位于 `tests/test_setup.py` 与 `examples/setup-check.md`。安装通过只说明可进入下一步检查，模型推理、视频质量和账单仍需要用户按实际任务验收。

## 来源与署名

qisi-video-remix 由 qisi 创作，分享包保留其 [MIT 许可证](../qisi-video-remix/LICENSE) 和完整来源说明：[上游仓库](https://github.com/wyuzhi/qisi-video-remix)。

深度处理依赖 [Video Depth Anything 官方项目](https://github.com/DepthAnything/Video-Depth-Anything)。上游项目代码与各型号权重的许可需要分别核对，本套件不分发模型权重。

Quan 配置资料来自用户提供的飞书教程及截图，入口保留在本地说明中。全部安装步骤需由使用者在自己的账户与电脑上执行。

## 维护状态

本轮只处理安装依赖与首次检查。三十秒输入边界、固定场景提示词、完整视频案例，以及更多操作系统上的推理，仍属于后续验证范围。
