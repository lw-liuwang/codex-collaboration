# Galaxy Brain完成记录

2026-11-19北京时间11:33:47，双方公开主页及成就详情均已实际显示 **Galaxy Brain x4，100% unlocked（金色）**。双方各有32条真实跨账号采纳，用户“先完成Galaxy Brain”的目标已完成。

| 账号 | 本项目跨账号采纳 | 本次新增 | 公开32nd accepted answer |
| --- | ---: | ---: | --- |
| A / lw-liuwang | 32 | RSI 24条 | [RSI #125 / A答案](https://github.com/ZicongHe2002/rsi-notes/discussions/125#discussioncomment-19724959) |
| B / ZicongHe2002 | 32 | CS336 18条 | [CS336 #51 / B答案](https://github.com/lw-liuwang/cs336-notes/discussions/51#discussioncomment-19724979) |

公开证据：[A详情](https://github.com/users/lw-liuwang/achievements/galaxy-brain/detail?hovercard=1)、[B详情](https://github.com/users/ZicongHe2002/achievements/galaxy-brain/detail?hovercard=1)。两个主页均返回`galaxy-brain-gold-9c2c03fd1acf.png`，详情均为x4和100% unlocked。双方独立回答、核验后采纳；A侧全部新增答案与采纳节点保存在[今日摘要158](https://github.com/lw-liuwang/codex-collaboration/issues/158)及[交接156](https://github.com/lw-liuwang/codex-collaboration/issues/156)。收尾完整分页读取双方各32条讨论、各32条评论和24条核验回复，没有待回答的追问或待采纳答案。

本次问题及数值均为教学构造；核验使用独立推导、标量/有理数计算及固定来源，没有声称模型、训练、AMP/GPU或性能实测。A另外2条历史自答不计入本协作进度，已有正确采纳没有撤销重做。

后续恢复[原四项内容协作](ROUND-ACCEPTANCE.md)。本次问答阶段工作仓库新PR为0，不将它写成四项验收通过；不再为Galaxy金色重复发题。原生15分钟重复和09–23写窗口保持，用户暂停仍须停止。

## 10:30开始时的基线

10:30全量分页基线：A在RSI已有8条被B采纳答案；B在CS336已有14条被A采纳答案，全部保持。双方公开徽章仍为铜色。A另有2条历史自问自答，不计入本协作进度。当前社区最高等级门槛32，双账号路径的差额分别为A24、B18。

依据：[等级门槛](https://github.com/Schweinepriester/github-profile-achievements#tiers)、[A实际详情](https://github.com/users/lw-liuwang/achievements/galaxy-brain/detail?hovercard=1)、[B实际详情](https://github.com/users/ZicongHe2002/achievements/galaxy-brain/detail?hovercard=1)。完整节点、作者和评论分页快照保存在本地执行记录，实际变化后须重新扫描。

## 已完成的18个CS336问题

以下问题均由A提出，B已独立回答，A已逐条核验采纳并回读answer.id和author。A还回答了B提出的[RSI #102](https://github.com/ZicongHe2002/rsi-notes/discussions/102)至[RSI #125](https://github.com/ZicongHe2002/rsi-notes/discussions/125)全部24个不同问题，B已逐条独立核验采纳。

| Q&A | 问题 |
| --- | --- |
| [#34](https://github.com/lw-liuwang/cs336-notes/discussions/34) | 梯度累积为什么通常不需要retain_graph=True？ |
| [#35](https://github.com/lw-liuwang/cs336-notes/discussions/35) | model.eval与no_grad分别改变什么，推理时为什么常常同时需要？ |
| [#36](https://github.com/lw-liuwang/cs336-notes/discussions/36) | expand几乎不复制数据，广播后的梯度为什么仍要相加？ |
| [#37](https://github.com/lw-liuwang/cs336-notes/discussions/37) | 前向后原地改动被保存的张量，为什么可能使backward报版本错误？ |
| [#38](https://github.com/lw-liuwang/cs336-notes/discussions/38) | 相同有效批量下，含BatchNorm的梯度累积为什么不等于一次大批前向？ |
| [#39](https://github.com/lw-liuwang/cs336-notes/discussions/39) | inverted dropout保持期望，是否也保持平方激活和损失的期望？ |
| [#40](https://github.com/lw-liuwang/cs336-notes/discussions/40) | AMP为什么必须先unscale再裁剪，缩放梯度上的阈值会变成什么？ |
| [#41](https://github.com/lw-liuwang/cs336-notes/discussions/41) | Adam对整体缩放损失真的完全不敏感吗，epsilon会怎样破坏等价？ |
| [#42](https://github.com/lw-liuwang/cs336-notes/discussions/42) | KV cache中query比key短时，普通左上三角mask为什么可能错位？ |
| [#43](https://github.com/lw-liuwang/cs336-notes/discussions/43) | 把两篇文档拼成一条序列，只有因果mask能否保证文档相互隔离？ |
| [#44](https://github.com/lw-liuwang/cs336-notes/discussions/44) | 语料perplexity为什么不能直接平均每条文本的perplexity？ |
| [#45](https://github.com/lw-liuwang/cs336-notes/discussions/45) | 目标概率浮点下溢为零时，直接从logits算交叉熵为何仍可能有限？ |
| [#46](https://github.com/lw-liuwang/cs336-notes/discussions/46) | ignore_index会删除softmax里的padding类别吗？ |
| [#47](https://github.com/lw-liuwang/cs336-notes/discussions/47) | checkpoint保存随机状态，能否同时保证有副作用的前向只执行一次？ |
| [#48](https://github.com/lw-liuwang/cs336-notes/discussions/48) | 分段重算的段长怎样影响激活存储，为什么不是段越短越省？ |
| [#49](https://github.com/lw-liuwang/cs336-notes/discussions/49) | LayerNorm与RMSNorm都做归一化，为什么只有前者通常对整体平移不变？ |
| [#50](https://github.com/lw-liuwang/cs336-notes/discussions/50) | FlashAttention不保存完整注意力矩阵，为什么仍不等于线性计算量？ |
| [#51](https://github.com/lw-liuwang/cs336-notes/discussions/51) | 知识蒸馏常乘温度平方，这能在任意温度下完全抵消温度的影响吗？ |

## 完成方式与后续约定

[共享交接](https://github.com/lw-liuwang/codex-collaboration/issues/156)的真实问答动作均已完成，完成条件包括最终答案节点、作者及双方公开金色。错误或缺条件的答案仍应具体修正，不能机械采纳。

RSI保留原8条采纳，加上本次24条为32；CS336保留原14条，加上本次18条为32。问题来自笔记与开放内容PR的不同技术边界，没有重复拆碎同一问题、冒用对方身份或自答自采纳替代双账号路径。

每次唤醒全量分页读取双方讨论、评论和回复。已有正确采纳不撤销重做；自己的答案已经发布但待对方核验时不重复回复。持续记录真实新答案、新采纳节点及当前阻塞。达到门槛后回读公开徽章；只有实际金色可见才记录该目标完成。

原生worker仍每15分钟，09:00–23:00北京时间允许写入，批次串行。不另建调度，不补跑历史轮次；后续按原四项协作处理内容PR与真实新问题。

B的独立无模型服务在任务135于2026-11-19北京时间09:00实际完成写入、回执并关闭。该服务只执行明确操作，技术回答与正确性判断仍需B真实完成。
