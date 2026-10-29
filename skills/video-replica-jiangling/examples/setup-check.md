# 安装检查示例

以下是可复现的安装验收场景，不代表已生成视频。

| 输入条件 | 应报告的缺项 | 后续动作 |
| --- | --- | --- |
| 只导入主 Skill | video-depth-anything 与 qisi-video-remix | 导入套件中的两个完整目录并启用 |
| 三个 Skill 在，但没有深度环境 | 工具目录、Python、Small checkpoint 或 FFmpeg | 按深度环境指南安装，重新检查 |
| 基础 Quan 插件已连通，仅有生图和语音 | quantv_upload_media、quantv_generate_video | 升级到提供这些工具的连接器版本 |
| 工具列表未提供给检查脚本 | 五项 MCP 工具均为 UNVERIFIED | 在 WorkBuddy 中核对，或提供只含名称的报告 |

从主 Skill 目录运行边界测试：

```bash
python tests/test_setup.py
```

这组测试检查缺依赖时能否明确阻断，以及工具名报告是否错误使用了凭证配置。它不启动模型、不下载权重、不连接 Quan、不产生生成费用。

在完整真实环境中，还需要手动核对 Skill 已启用、实际视频可读、深度输出时间轴与画质，然后由用户决定是否提交付费视频。
