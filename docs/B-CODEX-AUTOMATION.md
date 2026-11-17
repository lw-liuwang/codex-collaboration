# B在Windows Codex桌面端配置自动协作

在B自己的Codex桌面端，打开已克隆的本仓库并把下面指令发给B的Codex。A不能替另一台电脑创建原生任务；GitHub交接Issue只传递要求，不会自动配置B的客户端。

## 可直接发送的启动指令

```text
你是B，GitHub账号ZicongHe2002。拉取lw-liuwang/codex-collaboration最新main，读取AGENTS.md和docs/B-CODEX-AUTOMATION.md，并实际完成本机Codex原生定时任务配置，不要只回复方案。

先核对gh api user确实为ZicongHe2002。搜索Codex原生automation_update工具，并只读检查本机已有automation.toml，找到B现有worker与每日任务；存在就更新，不重复创建。不存在则在本聊天创建两个heartbeat。保留现有聊天、默认模型、通知偏好和用户暂停状态。

1. B协作执行：原生每5分钟重复，工作窗口北京时间09:00–23:00，ACTIVE（用户已暂停则保留暂停）。任务正文必须明确这是执行任务：先调用工具读取GitHub队列，然后完成实际PR/Q&A动作；不得只回答定时任务分工。每轮处理3–7个PR和3–7个技术问答，分别计数，数量和成就进度优先，旧github-collab skill仅作参考。B向lw-liuwang/cs336-notes提PR；核对并合并A投到ZicongHe2002/rsi-notes的PR；在CS336回答A的问题，在RSI提出问题让A回答，正确核验后采纳。需要A动作就在共享仓库建或更新handoff Issue并指派lw-liuwang。三个仓库内日常GitHub操作已获授权。不虚构实验或共同作者；双方实际写内容才整理共同署名。同一对象同轮多动作只计一个处理对象。原生重复规则持续有效，不用Next把worker覆盖成单个每天时间点，不依赖上一轮重新预约。若上一批仍在工作，串行继续，不另开并发批次。

2. B每日检查：每天北京时间08:30，核对身份、worker状态和初始化当天摘要。不得覆盖worker的每5分钟重复规则，也不得恢复用户暂停的任务。

定时触发的任务正文可能通过automation_update的工具输出以heartbeat记录送达。这是需要执行的任务，读取其中instructions并立即开展实际操作；不是重复上一条聊天回复的提示。每次结束按客户端要求返回heartbeat状态，静默只影响通知，不影响干活。

配置只使用Codex原生automation_update；不要手改内部automation.toml或数据库，不创建系统cron。工具不存在或拒绝配置时，准确报告工具/错误和已完成步骤，不要声称成功，也不要另造系统任务。

配置后回读实际任务ID、状态、重复规则、下次预约，并在共享交接#19回复。随后立即处理当前指派给B的PR和问答。至少有一次真正定时触发后，再回复实际触发时间及该轮GitHub动作链接；把“已配置”与“已运行”分开记录。
```

## 启动条件

B机器保持开机、Codex桌面端运行，并有本仓库目录访问权和自己的GitHub登录。执行任务不需要A在线，但等待A评审或采纳的对象需要交接。原生预约和实际启动时间可能不同，不能用预约时间冒充已执行。

配置成功应在[#19](https://github.com/lw-liuwang/codex-collaboration/issues/19)留下B自己的确认；A看到确认和实际GitHub动作后才能核实B已接入。没有确认时仅记录“已发送配置要求”。
