# 双方工作仓库强制审批

2026-11-19最新权限约定：不互邀为仓库协作者，不授予或接受对方写权限。A向B上游提交自己fork的PR，B作为上游所有者review；B向A同理。这样批准者具有上游权限且不是PR作者，保留现有强制审批，无需互邀。自己在自己仓库发起的历史配置PR，改由对方fork实际整合、另发PR再交所有者评审；外部普通review不能冒充满足强制审批。补写用PR维护者编辑或明确交回补丁，不发新邀请。

2026-11-19用户明确要求A、B都开启强制审批，并把双方Pull Shark、Pair Extraordinaire达到银色或更高作为本次目标。GitHub实际徽章与操作记录分别核对，不把开启规则当成成就到账。

用户随后取消本次15分钟定时与每日检查。审批配置后在当前会话连续串行协作，达到双方四个银色或更高官方徽章后结束；不恢复或新建定时。B须在本机暂停原生任务并回读，A的暂停结果不能代表B。

## 生效条件

两个工作仓库的默认分支使用同名规则集`Require reviewed pull requests`：至少一个批准评审、推送新内容后旧批准失效、无绕过名单，只允许merge commit。GitHub禁止PR作者批准自己的PR，普通Ready PR显式请求对方评审。所有者也没有规则绕过权限。

双方共同写作时，接收方先完成真实补写和共同署名，再核对完整最终diff、批准最终head、绑定同一head合并。`require_last_push_approval`保持false：接收方通常也是最后补写推送者，若禁止最后推送者批准，PR作者又不能自批准，两账号将无法完成审批。

现有仓库没有依赖CODEOWNERS的指定审稿人规则，本次不要求代码所有者审批；也不额外要求讨论线程全部解决。至少一位有权限的非PR作者批准是合并前置条件。不得临时关闭规则或加绕过名单执行YOLO路径。

## 双方已经启用

A仓库[cs336-notes规则集27616521](https://github.com/lw-liuwang/cs336-notes/rules/27616521)已启用并回读：active、至少1个批准、无绕过名单、当前A不可绕过，main为protected。

B仓库[RSI规则集27618831](https://github.com/ZicongHe2002/rsi-notes/rules/27618831)已于北京时间15:49启用。B的[管理员回读](https://github.com/lw-liuwang/codex-collaboration/issues/162#issuecomment-7003142615)确认无绕过名单、B不可绕过；A独立读取有效默认分支规则及protected状态，已确认至少1批准、推送撤销旧批准及只允许merge。A的非管理员响应不展示bypass_actors，不能把字段缺失误报为配置错误。

A对RSI只有push权限，规则由B自己的gh账号设置。以下命令可幂等核对已有配置，无需重复创建：

```powershell
git pull --ff-only origin main
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Enable-RequiredReview.ps1 -Actor B
```

先查看计划可加`-PlanOnly`。脚本核对账号、仓库管理员权限和北京时间09:00–23:00写入窗口；只管理上述同名规则，不改其他规则、凭据、worker或定时任务。重复运行会复用已有规则，匹配时只读，不新建重复规则。网络写入失败后先回查再决定结果。

成功后回读规则URL、至少1个批准、无绕过名单及当前账号不能绕过。B管理员回读与A独立有效规则核对均已完成；双方规则生效不代表四个银色目标徽章已经到账。

## 银色进度

社区记录的银色参考门槛为Pull Shark 128个被合并PR、Pair Extraordinaire 24个共同署名PR。参考来源是[社区成就表](https://github.com/Schweinepriester/github-profile-achievements#tiers)，GitHub未公开完整内部判定。公开API操作总数不一定等于官方成就计数：A官方第16个Pull Shark里程碑对应的PR，在公开按合并时间排序的列表中排第18，因此不能报出精确内部剩余量。

保持原四项内容协作，全量处理来件、正确问答与采纳，每轮至少向对方新发3个独立完整内容PR。真实补写后整合到同一正确共同署名提交，保留双方关联邮箱。显式request、approve和开启规则均不能代替真实内容贡献。

目前存在[GitHub官方成就获得与显示延迟通报](https://github.com/orgs/community/discussions/203416)。这不能证明具体账号的根因，也不能承诺规则开启后立即解锁。双方四个目标徽章实际为银色或更高，才记录本次目标完成；Galaxy Brain已有金色结果保持，不重复提问或撤销重采纳。
