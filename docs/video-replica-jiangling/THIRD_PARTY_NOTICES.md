# 第三方与本地适配说明

## qisi-video-remix

来源：https://github.com/wyuzhi/qisi-video-remix

作者：qisi。完整 Skill、README、references、examples、agents 与 MIT LICENSE 从用户现有安装复制，保留版权与许可证。主流程通过调用范围适配其提示词能力，未改动上游 Skill 本身。

## video-depth-anything 配套 Skill

来源为用户现有本地 Skill。本套件的分享版移除了个人盘符与显卡配置，使用 ToolRoot／PythonPath 或用户环境变量；运行脚本增加了明确的缺项提示与临时工作目录清理范围检查。交接参考说明改为通用深度提取范围，避免带入独立多候选付费生成建议。

推理依赖项目：https://github.com/DepthAnything/Video-Depth-Anything

官方项目代码使用 Apache 2.0 许可。模型权重需要单独下载，Small 与 Base／Large 的许可不同；具体条款请按官方仓库与对应模型卡核对。本套件不包含上游推理程序或模型权重，因此本地调用脚本的许可不能替代上游授权。

## Quan 配置资料

平台入口与飞书链接由用户提供，安装文字由用户截图整理。为避免带入账号、路径或令牌，截图原图不进入分享包。本套件不再分发截图中下载的第三方 MCP 安装器。

## 主 Skill 与新增检查工具

主 Skill 和新增的只读检查工具使用其目录内的 MIT LICENSE。该许可不覆盖个人 Quan 账号、平台服务、上游模型权重或第三方独立文件的使用条件。
