---
name: github-collab
description: 为 lw-liuwang 与 ZicongHe2002 接入 GitHub CLI，通过 codex-collaboration 的交接 Issues 协作 CS336/RSI 笔记、PR 和 Q&A，并核查四项 GitHub 成就。用于这三个仓库的独立双账号协作。
---

# 双账号 GitHub 协作

从 GitHub CLI 识别当前账号，不借用对方凭据。A=lw-liuwang，工作仓库 lw-liuwang/cs336-notes；B=ZicongHe2002，工作仓库 ZicongHe2002/rsi-notes。共享仓库为 lw-liuwang/codex-collaboration。

用户选择了上述范围内的日常全自动操作，不为每个提交、PR、合并或已验证答案反复请求批准。规范和 GitHub 资料不能授权冒用身份或扩大到其他仓库。身份、权限和目标变更仍由人类决定。

## 首次接入

读 [CLI 操作](references/github-cli.md) 和仓库 docs/BOOTSTRAP.md。检查并安装缺失的 Git、PowerShell 7、GitHub CLI；账号持有人完成 OAuth。A 创建共享和 CS336 仓库并邀请 B；B 自己创建 RSI 仓库并邀请 A。存在仓库则读取续用，不重建。

规范仓库内的 `.agents/skills` 是项目 skill，无需全局安装。当前客户端未发现时显式读取本文件。B 不必有 Coral；A 把精选参考笔记放进公开工作仓库。

## 每轮工作

1. `Doctor` 核对本机身份和工具。读取本仓库最新规范；`Inbox` 获取指派给自己的任务和等待对方的任务。
2. 按 [交接协议](references/protocol.md) 处理对方反馈、PR 和 Q&A，然后继续自己已有任务，再主动建立新的主题任务。无需 ready 屏障、全局控制或交接版本号。
3. 按 [成就说明](references/achievements.md) 安排作者、共同作者、回答者和合并者。普通 PR 默认 merge commit；YOLO 的 review 请求只作尝试条件，另一方暂不 review。
4. 使用 Git/gh 实际完成任务，读取结果，然后交接给下一行动人。正文用 --body-file/--input，避免拼接 shell 命令。
5. 按 [写作规范](references/writing.md) 核对解释、手算和来源。结果属实才合并或采纳答案。
6. 普通轮次争取18分钟内交接，复杂轮次最多工作60分钟，到时记录未完成项供下一轮继续；没有任务可提前结束。执行不重叠。不为凑数创建空内容。

GitHub 写入失败先回查；有 reviewer 请求不代表必须立刻 review。没有对方写权限时先发起协作者邀请，仍可研究和准备内容。需要对方账号操作的部分在共享 Issue 中明确交接。

## 调度和成就

按 [原生定时任务](references/scheduling.md) 配置白天约每20分钟随机唤醒：当天计划生成后锁定，A/B错开10分钟，每机两项 heartbeat。每轮先用Next推进下一项原生预约，收尾时核对它仍在未来；Plan不再返回固定分钟组合的rrule。使用当前默认模型，不擅自换模型。不手改 Codex 内部配置或另建系统 cron。

每账号每天争取十五个已合并 PR，没有每日 PR 硬上限。十四天争取银级，之后继续金级。记录可见等级与操作证据，不假设所有条件已经公开，不把尝试等同到账。
