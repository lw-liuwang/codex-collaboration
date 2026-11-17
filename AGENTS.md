# 双账号协作

读取 `.agents/skills/github-collab/SKILL.md`，按本机 GitHub 身份执行。A=lw-liuwang，负责 CS336；B=ZicongHe2002，负责 RSI 研究笔记。

用户已确定：三个仓库全部公开，日常 GitHub 操作全自动。以成就条件和任务交接为主，不逐条请求提交、发布、合并或答案采纳批准；不设置每日 PR 硬上限、ready 屏障或全局控制 Issue。修改身份、权限、目标仍由人类决定。

共享仓库 Issues 是唯一交接队列。Assignee 表示下一行动人，正文写对象链接、需要完成的动作和完成条件。不要只看到 review 请求就提交 review，先检查是否为 YOLO 尝试。

笔记内容放在工作仓库；本仓库提供 skill、操作说明、交接和每日摘要。不得冒用对方账号；每次实际操作后读取结果，不把调用成功直接写成成就到账。

测试：`pwsh -NoProfile -File tests/Run-Tests.ps1`。本地日志放 `.local/`。不要提交凭据。
