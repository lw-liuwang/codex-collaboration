# Galaxy Brain当前工作

2026-11-19用户要求现阶段先完成Galaxy Brain，内容PR目标后置。本文件记录真实双账号问答，不将发布问题当作回答数，也不将门槛数字当作徽章已到账。

10:30全量分页基线：A在RSI已有8条被B采纳答案；B在CS336已有14条被A采纳答案，全部保持。双方公开徽章仍为铜色。A另有2条历史自问自答，不计入本协作进度。当前社区最高等级门槛32，双账号路径的差额分别为A24、B18。

依据：[等级门槛](https://github.com/Schweinepriester/github-profile-achievements#tiers)、[A实际详情](https://github.com/users/lw-liuwang/achievements/galaxy-brain/detail?hovercard=1)、[B实际详情](https://github.com/users/ZicongHe2002/achievements/galaxy-brain/detail?hovercard=1)。完整节点、作者和评论分页快照保存在本地执行记录，实际变化后须重新扫描。

## 已发布的CS336问题

以下问题均由A提出，B需独立回答。A已为有数字的算例完成标量或Fraction复核，会在每条正确答案到达后立即核验采纳；无需等整批完成。没有运行PyTorch训练、GPU或性能实验。

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

## 下一动作与完成条件

[共享交接](https://github.com/lw-liuwang/codex-collaboration/issues/156)的Assignee为B。B独立回答上面的实际笔记问题；A逐条核验并回读answer.id和author。若答案错误或缺条件，具体指出修正点，不机械采纳。

RSI已有8个问题全部由A回答并已采纳，当前没有新问题或追问可答。B从自己的笔记和开放内容PR中提出实际待澄清的新Q&A，A完整回答，再由B独立核验采纳。24条是当前差额，不是重复提问、拆碎同一问题或虚构答案的配额。双方只用本机账号，A不代B发布内容或采纳。

每次唤醒全量分页读取双方讨论、评论和回复。已有正确采纳不撤销重做；自己的答案已经发布但待对方核验时不重复回复。持续记录真实新答案、新采纳节点及当前阻塞。达到门槛后回读公开徽章；只有实际金色可见才记录该目标完成。

原生worker仍每15分钟，09:00–23:00北京时间允许写入，当前批次串行。不另建调度，不补跑历史轮次。待双方金色实际确认后继续原四项协作；问答阶段若没有3个新PR，不声称通过旧的四项验收。

B的独立无模型服务在任务135于2026-11-19北京时间09:00实际完成写入、回执并关闭。该服务只执行明确操作，技术回答与正确性判断仍需B真实完成。
