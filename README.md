# Codex GitHub 双账号协作

两台独立 Windows Codex，通过本仓库提供的 skill 和交接 Issues，协作维护两个主题仓库，并核查 YOLO、Pair Extraordinaire、Galaxy Brain 和 Pull Shark。

2026-11-19当前目标：双方Pull Shark、Pair Extraordinaire达到银色或更高。两个工作仓库的[强制审批](docs/REQUIRED-REVIEW.md)均已启用并回读，至少一位非PR作者批准最终head后才能merge。操作数量和实际官方徽章分别记录。

用户已取消本次15分钟定时和每日检查，改为当前会话连续串行推进，双方四个官方目标徽章达银后结束。A两个原生任务已暂停；B已在[交接162回报](https://github.com/lw-liuwang/codex-collaboration/issues/162#issuecomment-7003142615)原生每日任务暂停、旧15分钟任务不存在、Windows worker已禁用。下方旧安装资料不构成恢复或新建定时的要求。

2026-11-18新增：[每半小时运行的无模型后台worker](docs/GH-WORKER.md)。由Windows任务计划程序直接运行Python和GitHub CLI，不依赖Codex；支持结构化GitHub操作任务、回读与重启恢复，提供B的安装脚本。技术内容的编写和正确性判断仍需真实成果，不能由机械执行替代。

| 身份 | 自建工作仓库 | 主题 |
| --- | --- | --- |
| A：lw-liuwang | [cs336-notes](https://github.com/lw-liuwang/cs336-notes) | CS336 原理、图解、手算和学习笔记 |
| B：ZicongHe2002 | [rsi-notes](https://github.com/ZicongHe2002/rsi-notes) | Recursive Self-Improvement 研究笔记，由 B 建立资料和任务 |

## 把这个链接交给 B

本次让B在现有会话执行[交接162](https://github.com/lw-liuwang/codex-collaboration/issues/162)启用强制审批，再按[交接163](https://github.com/lw-liuwang/codex-collaboration/issues/163)实际补写和合并，启动要求见[当前会话指令](docs/B-CODEX-AUTOMATION.md)。

历史安装资料仍在[后台worker](docs/GH-WORKER.md#给-b-安装)与[旧启动提示词](docs/BOOTSTRAP.md#给-b-的启动提示词)。本次不运行安装入口来新增或恢复定时。

本机已克隆规范仓库时，项目 skill 位于 [.agents/skills/github-collab](.agents/skills/github-collab/SKILL.md)，仅作工具参考；当前会话从规范仓库执行。

## 日常怎么做

- A 向 B 的 RSI 仓库提交 PR，B 验收合并；B 向 A 的 CS336 仓库提交 PR，A 验收合并。Pull Shark 归 PR 作者。
- 双方共同完成的内容，在实际提交中正确保留共同作者，用 merge commit 合并。
- A 问实际 CS336 问题、B 回答、A 验证采纳，帮助 B 积累 Galaxy Brain；B 问 RSI、A 回答时反向进行。
- A的YOLO已确认解锁；当前强制审批要求优先，不为未review尝试关闭或绕过规则。
- 每次需要对方行动，在本仓库建或更新一个交接 Issue，指定下一行动人。没有待办就主动研究主题、撰写和提交，不必等待双方统一启动。

当前按[四项检查点](docs/ROUND-ACCEPTANCE.md)完整扫描并连续串行推进，09–23时写入，达银后结束。独立无模型worker的30分钟机制不能代替技术判断或真实共同写作；本次不重新安装或启用它。普通PR需真实补写、共同署名并核对后合并；没有实际内容不做空提交，成就按真实页面核查。

## 说明

- [GitHub CLI 安装和操作](.agents/skills/github-collab/references/github-cli.md)
- [PR / Q&A 的交接方式](.agents/skills/github-collab/references/protocol.md)
- [门槛、限制与证据](.agents/skills/github-collab/references/achievements.md)
- [原生定时任务](.agents/skills/github-collab/references/scheduling.md)
- [笔记形式和验证](.agents/skills/github-collab/references/writing.md)

文档和脚本由 OpenAI Codex 辅助整理。接入状态、运行记录和实际成就以 Issues 中的证据为准。
