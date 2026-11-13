# 安装与分享

## 四 Skill 套件

分享安装包包含 `vibe-voiceover-video`、`huashu-art-motion`、`video-shotcraft` 和额外的 `huashu-motion`。前两项是本工作流的画面与渲染依赖；`huashu-motion` 是另一套独立的动效工具，供扩展使用。

解压套件，在目录中运行：

```sh
python install.py --target ~/.codex/skills
python verify.py --target ~/.codex/skills
```

Windows PowerShell 可运行：

```powershell
python .\install.py --target "$HOME\.codex\skills"
python .\verify.py --target "$HOME\.codex\skills"
```

安装程序只复制套件文件，遇到同名旧目录时停止并提示。`--target` 可以设为其他 Agent 的 Skill 目录。首次渲染还需要按各上游项目说明准备 Python、Node、FFmpeg、浏览器及模型。套件自带源码与示例，不包含第三方 npm 包和浏览器二进制。

## 在线安装四项

当本 Skill 合并进仓库默认分支后，也可分别从各项目安装：

```sh
npx skills add yokadanye-prog/danye-mvp --skill vibe-voiceover-video -g -y
npx skills add alchaincyf/huashu-art-motion --skill huashu-art-motion -g -y
npx skills add Vincentwei1021/video-shotcraft --skill video-shotcraft -g -y
npx skills add alchaincyf/huashu-motion --skill huashu-motion -g -y
```

## 单独安装

如果只想用这份主 Skill，可以从仓库下载 `skills/vibe-voiceover-video` 到 Agent 的 Skill 目录，再分别安装 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) 与 [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)。各目录应当处于同一级。

## 来源与授权

本 Skill 采用 MIT；配套项目保留各自许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。演示角色、音乐和字体的使用权限依素材而异。分享套件不得被理解为把所有素材统一改为 MIT。
