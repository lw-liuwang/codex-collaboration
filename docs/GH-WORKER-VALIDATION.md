# 无模型worker验证记录

2026-11-18，A本机Windows、Python3.14.8、PowerShell7.6.9，实际GitHub身份为lw-liuwang。

- `pwsh -NoProfile -File tests/Run-Tests.ps1`通过：包含原有排程、身份与分页测试，以及35项worker行为测试。覆盖结果丢失后回查、重启账本、已关闭队列续做回执、不确定请求不盲重发、修改任务拒绝、同id防重复、身份不符、新head/diff、YOLO、自approve、共同署名、旧head review、CI重跑、答案节点/作者、嵌套回复、时窗、暂停与单进程锁。
- `worker/Install-Worker.ps1 -Actor B -PlanOnly`实际构建Windows任务定义：PT30M无限期重复、IgnoreNew、PT25M上限、pythonw.exe、当前用户Interactive/Limited。没有注册B任务；WindowsPowerShell5.1的实际安装仍需在B机器确认。
- 真实A账号只读扫描成功：CS336开放PR0、Q&A14；RSI开放PR40、Discussions8。读取了讨论、评论和回复，不修改笔记。
- B配置在A身份下拒绝运行，不切换身份。GitHub真实GraphQL读取既有CS336 PR31，验证关联双方作者的同一提交`533ae24ef7951417a859cce7a2ace84c51f59581`可被正确识别；本次没有改动或重合并该PR。
- 真实写入验证：[任务127](https://github.com/lw-liuwang/codex-collaboration/issues/127)由worker领取，向[测试对象126](https://github.com/lw-liuwang/codex-collaboration/issues/126)写入操作说明、回读、提交回执并关闭。再次执行同一步后，操作评论数量仍为1。测试对象也已关闭。
- [健康状态128](https://github.com/lw-liuwang/codex-collaboration/issues/128)由A的手动验证轮创建并更新，最后成功扫描为北京时间18:08:05；这是测试证据，不表示A安装了新的30分钟后台任务。B部署应检查B自己的`worker-health/ZicongHe2002`。

首次真实写入发现GitHub列表索引存在短暂延迟：已创建的健康Issue暂时不在列表中。worker保留不确定账本并停止重复创建；下一次执行成功回查到原对象。现在创建健康页后保存返回编号并优先直接回读，另增行为测试覆盖该场景，以及关闭队列成功但响应丢失后的恢复。

生产review、merge、答案采纳和PR发布逻辑已有模拟API行为测试；本次没有为了验证而制造技术问答、批准/合并积压PR、伪造共同署名或生成内容贡献。没有从A电脑安装B服务。代码、文案已人工核对；没有运行CRAP、重复度或变异测试工具，不报告这些数值指标。

## 1.0.1：评论任务的一键恢复

2026-11-18追加。B已安装且持续轮询，但[任务135](https://github.com/lw-liuwang/codex-collaboration/issues/135)的评论POST失败后留下不确定记录。新增`worker/Repair-Worker.ps1`默认恢复这个任务，自动计算绑定字段、完整回查评论、备份数据库、恢复缺失的sent步骤并续做回执和关闭；网络仍失败时返回非零状态并保留诊断。无需重建Windows任务或手填effect key。

- `pwsh -NoProfile -File tests/Run-Tests.ps1`通过，包括48项Python行为测试。新增覆盖单任务备份、已有评论续做、回执和关闭恢复、重复运行、远端读取失败、任务中途变化、同id异Issue、已删除结果、重复评论、只读/暂停/窗口、身份错配、非评论拒绝、再次写入失败及错误信息脱敏。
- Windows PowerShell5.1实际解析入口脚本，并以A账号运行完整恢复与再次运行。构造的初始本地sent状态对应[队列143](https://github.com/lw-liuwang/codex-collaboration/issues/143)，恢复后实际发布[操作评论](https://github.com/lw-liuwang/codex-collaboration/issues/142#issuecomment-6979426597)，回执与队列关闭均已回读。再次运行返回`already_done`，目标评论仍只有1条。测试对象142已关闭，SQLite备份实际存在。
- 此真实API验证使用A自己的gh；初始sent为测试构造，不表示重现了B原始网络故障，也不表示B已经拉取或运行新版。B的实际结果仍由任务135与健康页131回读确认。

本次代码和使用文字已人工核对。原半小时计划、暂停标记和其他任务记录保持原有语义；自动轮询仍保留不确定写入，不会自动清空全部账本。评论接口缺少通用幂等键，显式恢复前未查到结果不能绝对排除远端延迟应用，不承诺跨网络故障严格exactly-once。
