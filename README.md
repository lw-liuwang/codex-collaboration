# Codex GitHub 双账号协作

两台独立 Windows Codex，通过本仓库提供的 skill 和交接 Issues，协作维护两个主题仓库，并核查 YOLO、Pair Extraordinaire、Galaxy Brain 和 Pull Shark。

| 身份 | 自建工作仓库 | 主题 |
| --- | --- | --- |
| A：lw-liuwang | [cs336-notes](https://github.com/lw-liuwang/cs336-notes) | CS336 原理、图解、手算和学习笔记 |
| B：ZicongHe2002 | [rsi-notes](https://github.com/ZicongHe2002/rsi-notes) | Recursive Self-Improvement 研究笔记，由 B 建立资料和任务 |

## 把这个链接交给 B

让 B 的账号持有人把 [启动提示词](docs/BOOTSTRAP.md#给-b-的启动提示词) 发给自己的 Codex。它读取本仓库、安装配置 GitHub CLI、确认自己的身份、接受邀请、创建自己的 RSI 仓库，再领取本仓库指派给它的交接任务。工作仓库链接是否已经存在，以实际查询为准。

本机已克隆规范仓库时，项目 skill 位于 [.agents/skills/github-collab](.agents/skills/github-collab/SKILL.md)。会话和原生定时任务从规范仓库启动即可，不需要覆盖全局 skills。

## 日常怎么做

- A 向 B 的 RSI 仓库提交 PR，B 验收合并；B 向 A 的 CS336 仓库提交 PR，A 验收合并。Pull Shark 归 PR 作者。
- 双方共同完成的内容，在实际提交中正确保留共同作者，用 merge commit 合并。
- A 问实际 CS336 问题、B 回答、A 验证采纳，帮助 B 积累 Galaxy Brain；B 问 RSI、A 回答时反向进行。
- YOLO 单独尝试：作者请求对方 review，再在尚无 review 时自行合并。关联交接标记 yolo，对方不要抢先 review。这是待验证路径，不保证发放。
- 每次需要对方行动，在本仓库建或更新一个交接 Issue，指定下一行动人。没有待办就主动研究主题、撰写和提交，不必等待双方统一启动。

每天09–23时段约每20分钟随机唤醒，生成当天计划后锁定，A/B错开10分钟；普通轮次争取18分钟内交接，复杂轮次最多一小时且不重叠；每账号每天争取十五个已合并 PR，不设置硬数量上限。十四天争取银级，之后继续向金级积累。没有实际内容不做空提交；成就按真实页面核查。

## 说明

- [GitHub CLI 安装和操作](.agents/skills/github-collab/references/github-cli.md)
- [PR / Q&A 的交接方式](.agents/skills/github-collab/references/protocol.md)
- [门槛、限制与证据](.agents/skills/github-collab/references/achievements.md)
- [原生定时任务](.agents/skills/github-collab/references/scheduling.md)
- [笔记形式和验证](.agents/skills/github-collab/references/writing.md)

文档和脚本由 OpenAI Codex 辅助整理。接入状态、运行记录和实际成就以 Issues 中的证据为准。
