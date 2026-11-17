# 接入步骤

把下面提示词交给 ZicongHe2002 自己机器的 Codex。对方不需要访问 A 的 Coral，也不需要 A 的凭据。

## 给 B 的启动提示词

```text
请接入 https://github.com/lw-liuwang/codex-collaboration。
我是 GitHub 账号 ZicongHe2002 的持有人。请读取 README、AGENTS.md、.agents/skills/github-collab/SKILL.md 和相关说明，按此规范独立协作。
检查并安装缺失的 Git、PowerShell 7、GitHub CLI，使用官方来源；需要 OAuth 或系统确认时让我完成。gh 当前登录必须是 ZicongHe2002，不使用对方凭据。
克隆规范仓库到专用目录（默认 %USERPROFILE%/src/codex-collaboration），将其作为此聊天和定时任务的根目录；项目 skill 已在 .agents/skills 中，无需覆盖全局配置。
接受共享规范仓库和 CS336 仓库的协作者邀请。你自己创建公开仓库 ZicongHe2002/rsi-notes，邀请 lw-liuwang 为 write 协作者。若仓库已存在则读取续用。
RSI 指 Recursive Self-Improvement。第一阶段只做研究笔记；由你建立公开资料清单、首批主题和任务，A 会参与撰写和核查。自行在你的工作仓库建立指向共享协议的 AGENTS.md，开启 Discussions/Q&A。
这三个仓库范围内的日常任务、提交、PR、真实验证、合并、Q&A和验证后答案采纳都自动执行，不逐条等我确认。身份、权限和目标变更仍由人类决定。
从共享仓库指派给我的交接 Issue 开始：Assignee是下一行动人，正文说明对象、动作、mode和完成条件。看到 review 请求先检查是不是YOLO，不直接review。
配置本机两项 Codex 原生heartbeat：08:30每日排程、每天十个随机时段的协作执行，每轮最多一小时。实际任务ID只保存在本机，不替对方配置。不等ready屏障；遇到对方操作需求就交接，其他内容继续做。
每天争取十五个已合并有效PR，不设硬数量上限。主要由你向A的CS336仓库开PR，A向你的RSI仓库开PR；双方共同完成的提交正确署名；你提出实际RSI问题、A回答、你验证采纳，反向处理CS336问题。
先运行仓库测试和Doctor，报告你实际完成的登录、建仓、邀请、任务配置和未完成项，然后继续工作。操作成功与成就到账分开记录，不伪造作者、答案或验证结果。
```

## A 的步骤

A 发布规范仓库和精选 CS336 笔记，分别邀请 B，创建 handoff、daily、yolo 标签；在 CS336 开启 Discussions，确认 Q&A 可采纳。A 配置自己的两项原生任务并把需要 B 做的动作写成交接 Issue。B 的仓库建立后，A 接受邀请并开始跨仓库贡献。不使用另一账号代建仓库。

## 命令入口

在规范仓库运行，Actor 按本机身份填写：

```powershell
pwsh -NoProfile -File tests/Run-Tests.ps1
pwsh -NoProfile -File .agents/skills/github-collab/scripts/Invoke-Collab.ps1 -Action Doctor -Actor ZicongHe2002
pwsh -NoProfile -File .agents/skills/github-collab/scripts/Invoke-Collab.ps1 -Action Inbox -Actor ZicongHe2002
pwsh -NoProfile -File .agents/skills/github-collab/scripts/Invoke-Collab.ps1 -Action Plan -Actor ZicongHe2002
```

首次没有 gh 时通过公开网页或 HTTPS 读安装说明。Doctor 检查工具和本机身份，不建立全队启动屏障。原生任务的创建与更新使用 Codex 对应工具，不是运行脚本就自动配置好了。
