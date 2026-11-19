# Codex GitHub 双账号协作

两台独立 Windows Codex，通过本仓库提供的 skill 和交接 Issues，协作维护两个主题仓库，并核查 YOLO、Pair Extraordinaire、Galaxy Brain 和 Pull Shark。

2026-11-19当前目标：双方Pull Shark、Pair Extraordinaire达到银色或更高。两个工作仓库开启[强制审批](docs/REQUIRED-REVIEW.md)，至少一位非PR作者批准最终head后才能merge；A已启用，B用自己账号执行文档中的脚本。操作数量和实际官方徽章分别记录。

2026-11-18新增：[每半小时运行的无模型后台worker](docs/GH-WORKER.md)。由Windows任务计划程序直接运行Python和GitHub CLI，不依赖Codex；支持结构化GitHub操作任务、回读与重启恢复，提供B的安装脚本。技术内容的编写和正确性判断仍需真实成果，不能由机械执行替代。

| 身份 | 自建工作仓库 | 主题 |
| --- | --- | --- |
| A：lw-liuwang | [cs336-notes](https://github.com/lw-liuwang/cs336-notes) | CS336 原理、图解、手算和学习笔记 |
| B：ZicongHe2002 | [rsi-notes](https://github.com/ZicongHe2002/rsi-notes) | Recursive Self-Improvement 研究笔记，由 B 建立资料和任务 |

## 把这个链接交给 B

已安装无模型worker的B：[下载程序包](https://github.com/lw-liuwang/codex-collaboration/archive/refs/heads/main.zip)，解压后双击 `B-START.cmd`，自动更新并恢复现有任务；不需要向Codex发提示词，也不用填写任务参数。首次安装同样可用，前提与状态说明见[后台worker](docs/GH-WORKER.md#给-b-安装)。

原Codex协作模式的接入说明仍在[启动提示词](docs/BOOTSTRAP.md#给-b-的启动提示词)，用于需要模型参与的内容工作。无模型后台任务使用上面的双击入口。工作仓库链接是否已经存在，以实际查询为准。

本机已克隆规范仓库时，项目 skill 位于 [.agents/skills/github-collab](.agents/skills/github-collab/SKILL.md)。会话和原生定时任务从规范仓库启动即可，不需要覆盖全局 skills。

## 日常怎么做

- A 向 B 的 RSI 仓库提交 PR，B 验收合并；B 向 A 的 CS336 仓库提交 PR，A 验收合并。Pull Shark 归 PR 作者。
- 双方共同完成的内容，在实际提交中正确保留共同作者，用 merge commit 合并。
- A 问实际 CS336 问题、B 回答、A 验证采纳，帮助 B 积累 Galaxy Brain；B 问 RSI、A 回答时反向进行。
- A的YOLO已确认解锁；当前强制审批要求优先，不为未review尝试关闭或绕过规则。
- 每次需要对方行动，在本仓库建或更新一个交接 Issue，指定下一行动人。没有待办就主动研究主题、撰写和提交，不必等待双方统一启动。

Codex协作模式原生每15分钟触发，09–23时写入，按[每轮验收](docs/ROUND-ACCEPTANCE.md)完整扫描并串行续做。新无模型worker每30分钟轮询结构化任务，独立于此调度；启用后避免让两个执行器同时写相同对象。普通PR需真实补写、共同署名并核对后合并；没有实际内容不做空提交，成就按真实页面核查。

## 说明

- [GitHub CLI 安装和操作](.agents/skills/github-collab/references/github-cli.md)
- [PR / Q&A 的交接方式](.agents/skills/github-collab/references/protocol.md)
- [门槛、限制与证据](.agents/skills/github-collab/references/achievements.md)
- [原生定时任务](.agents/skills/github-collab/references/scheduling.md)
- [笔记形式和验证](.agents/skills/github-collab/references/writing.md)

文档和脚本由 OpenAI Codex 辅助整理。接入状态、运行记录和实际成就以 Issues 中的证据为准。
