# B立即清理积压的人工启动指令

2026-11-18 10:48北京时间快照：B的rsi-notes有18个开放PR（17个Ready、1个Draft），A的CS336有9个待B回答问题，另有B的RSI Q&A #19等待核验采纳A答案。列表会变化，启动时和收尾都读取实时分页结果。

## 把这段话直接发给B的Codex

```text
现在人工启动集中清理，立即调用工具执行，不等下一次定时触发，不要只回复计划。你是ZicongHe2002，拉取lw-liuwang/codex-collaboration最新main，读AGENTS.md、docs/ROUND-ACCEPTANCE.md和docs/B-CATCHUP.md。旧github-collab skill不是额外门槛。

先gh api user核对身份，再全量分页读取rsi-notes的开放PR和待采纳讨论，以及lw-liuwang/cs336-notes全部待答问题。共享handoff用于交接，不能代替读取实际仓库。

先做无需等待A的收敛动作：核对RSI讨论#19中A的答案（独立36/47，完全一致2/13，联合率公式）；正确就采纳，回读answer.id，关闭交接#39。这是A的被采纳回答，不要用新提问代替采纳。

接着连续清理自己仓库全部开放PR，不是一轮只处理一个。先读多条diff与交接，按PR逐条串行写分支：补一个真实且正确的例子、反例、推导或修正；把双方实际成果整理为同一共同署名提交，保留A原author并添加你自己的正确Co-authored-by邮箱；核对整个最终diff/head，用merge commit合并，回读merged与落地提交后关闭交接。有分支改写时用精确旧SHA的force-with-lease，不能覆盖未读到的提交；不强推main。遇具体错误先修或交回，再继续别的PR，别卡住整批。不要仅approve就当Pair协作，不要把合并者身份当Pull Shark作者计数。Draft #20先补约定的联合率边界表，再ready和合并。Ready也按最新标准补实际共同内容。

回答CS336全部仍待你回答的问题，给必要数值、假设和来源即可，不要求长文。答案发布后将对应共享handoff改为verify-answer并指派lw-liuwang。A会核验采纳；你不需要等A回复才处理下一条。已有你的回答不重复贴，有具体追问才续答。

把当前所有可处理积压连续做完，不要做一条就停下来等15分钟；没有任意3–7条处理上限。若客户端上下文或任务被中断，保存逐项完成结果、剩余URL和阻塞，在当前任务接续。不要仅因已经输出计划或工具成功就宣称完成。第1–3项清理后再做本轮至少向CS336新发3个PR，不用新建任务掩盖旧积压。

同时核对本机worker每15分钟原生重复、每日检查08:30，两项提示词采用四项验收。复用已有任务，不手改内部配置，不用Next覆盖为单点日预约。回读真实任务状态和实际下一预约；若上午下一预约却在下午，检查MINUTELY小时过滤的UTC/北京时间解释。首个实际触发必须有heartbeat记录与工具/GitHub动作链接，ACTIVE或口头“已配置”不等于已运行。当前聊天忙碌导致触发推迟时记录状态，不把它当作已经完成的另一轮。

这是日常GitHub操作的继续授权，不再逐条问提交、合并或采纳批准。每做完一组就把实际URL、head/merge、答案节点写入本日同一daily Issue；回报重点是“完成多少、还剩什么、具体阻塞”。无可处理积压前继续当前批次，串行不并发改同一分支。
```

## 本次积压入口

- 待核验A答案：[RSI Q&A #19](https://github.com/ZicongHe2002/rsi-notes/discussions/19#discussioncomment-19697319)。
- 18个开放PR：RSI #10–#18、#20–#28；[#20](https://github.com/ZicongHe2002/rsi-notes/pull/20)为待实际补写的Draft。按[实时PR列表](https://github.com/ZicongHe2002/rsi-notes/pulls)为准。
- 9个待答问题：CS336 #10–#18，见[讨论列表](https://github.com/lw-liuwang/cs336-notes/discussions)。
- 新验收同步：[共享#47](https://github.com/lw-liuwang/codex-collaboration/issues/47)；15分钟频率同步：[共享#51](https://github.com/lw-liuwang/codex-collaboration/issues/51)。

两台机器互相不能直接启动对方Codex。GitHub Issue只提供待办，人工把上述指令发给B的Codex可以立即开工；之后再用真实触发证据确认定时是否正常。批量是一次处理多个对象，合并和署名仍逐个核对。
