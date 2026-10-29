# 配置 Video Depth Anything 运行环境

安装 Skill 文件夹只安装指令和调用脚本。模型程序、Python 依赖和权重需要用户另行准备。本套件以 Small 相对深度模型与 Windows PowerShell 包装脚本为入口，未承诺全部显卡或操作系统开箱运行。

## 一 获取官方项目

来源：[Video Depth Anything 官方仓库](https://github.com/DepthAnything/Video-Depth-Anything)。先阅读其当前 README 与 requirements，选择用户可写的工具目录。

以下命令是需要用户自行执行的准备示例，执行前核对网络、磁盘与所选 Python 版本：

```powershell
git clone https://github.com/DepthAnything/Video-Depth-Anything.git
Set-Location Video-Depth-Anything
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
```

上游 requirements 包含指定版本的 PyTorch、torchvision、xformers 等依赖。不同 Python、CUDA 和 Windows 环境可能需要按上游说明调整兼容版本。某个包安装失败时先诊断该包，不能把虚拟环境创建成功当作模型已可运行，也不应在失败时自动换模型。

macOS、Linux 或其他硬件请按照上游对应说明准备环境；本套件的 Windows 脚本入口不能代替跨平台验证。

## 二 准备 Small 权重

根据官方 README 下载 [Video Depth Anything Small checkpoint](https://huggingface.co/depth-anything/Video-Depth-Anything-Small/resolve/main/video_depth_anything_vits.pth?download=true)，放在用户项目的以下相对路径：

```text
Video-Depth-Anything/
  run_streaming.py
  .venv/
  checkpoints/
    video_depth_anything_vits.pth
```

本套件不附带权重，也不自动触发下载。上游 Small 权重和 Base／Large 权重的许可不同；使用与分发前按具体型号核对上游授权。不要将所有型号统一标成同一许可。

## 三 准备视频工具

安装 FFmpeg，并使 `ffmpeg` 与 `ffprobe` 在当前终端和 WorkBuddy 的运行环境中都可调用。只在某个终端可见，不代表已运行中的 WorkBuddy 也继承了相同 PATH；必要时重启 WorkBuddy。

```powershell
ffmpeg -version
ffprobe -version
```

## 四 指定自己的工具目录

分享版 `scripts/infer-depth.ps1` 接受 `-ToolRoot`，或者使用用户自己配置的 `VIDEO_DEPTH_ANYTHING_HOME`。不要采用作者的盘符、个人目录或显卡型号。

```powershell
# 替换为自己的安装位置。此设置只作用于当前 PowerShell 会话。
$env:VIDEO_DEPTH_ANYTHING_HOME = 'C:\Tools\Video-Depth-Anything'
```

若要让 WorkBuddy 使用同一变量，用户需要在自己的系统用户环境变量中配置，并重启 WorkBuddy。也可以在每次调用分享版脚本时显式传入 `-ToolRoot`。

Python 默认从该工具目录的 `.venv\Scripts\python.exe` 查找。只有另用 Python 时，才设置 `VIDEO_DEPTH_ANYTHING_PYTHON` 或传 `-PythonPath`。

## 五 先检查 再提取

从套件根目录执行只读检查，工具目录按实际填写：

```powershell
python '.\skills\video-replica-jiangling\scripts\check_setup.py' `
  --tool-root 'C:\Tools\Video-Depth-Anything' --probe-python
```

该检查只验证文件、命令和 Python 导入，不加载模型权重推理。MCP 工具还需在 WorkBuddy 核对；缺少只含名称的工具报告时，脚本会显示 UNVERIFIED。

完成安装后，用用户自己的短片段执行一次深度提取，核对输出时长、帧率、画面轮廓与灰度方向，再把结果作为后续生成的参考。深度提取通过不能证明最终视频生成质量已通过。
