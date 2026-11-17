# 成就：门槛、归属和证据

核对日期：2026-11-17。GitHub 没有为以下所有细节提供完整稳定的公开契约。门槛参考社区仓库；成功操作、累计成果和可见徽章必须分开报告。

| 成就 | 基础 | 铜 x2 | 银 x3 | 金 x4 | 主要归属 |
| --- | --- | --- | --- | --- | --- |
| YOLO | 一次解锁 | 无 | 无 | 无 | 样本中是提交并合并本人 PR 的账号；完整条件待验证 |
| Pull Shark | 2 | 16 | 128 | 1024 | 被合并 PR 的作者，不是点击合并的人 |
| Pair Extraordinaire | 1 | 10 | 24 | 48 | 被合并 PR 中实际共同署名的贡献者；双方计数分别核查 |
| Galaxy Brain | 2 | 8 | 16 | 32 | 别人发起的讨论中被采纳答案的回答者 |

## 本会话已经观察到的事实

- lw-liuwang 公开 Pull Shark 是铜级。GitHub 历史列出第 2 个为 D-Robotics/openpi_runtime#3，第 16 个为 googlecolab/google-colab-cli#172。不能据此获知目前精确总数。
- ZicongHe2002 公开 Pull Shark 为基础级；其他目标成就需接入时再次读取。
- lw-liuwang/github-workflow-lab#1 已由作者自行合并、没有 review；后续多次公开页面检查没有显示 YOLO。它不是可靠的充分条件，不反复复制该操作。

## YOLO 的下一次尝试

GitHub 上 Schweinepriester 的 YOLO 历史指向 achievement-testarea#4：2022-06-12 20:39:52 UTC 请求 ale-lit review，20:40:00 UTC 由作者合并，reviews 为空。历史标签为 Merged without a review。该历史样本支持尝试“先请求已接受邀请的协作者 review，再由作者无 review 合并”，但不证明 2026 年完整条件，也不证明 8 秒是必要等待时间。

A 在自己的 CS336 仓库、B 在自己的 RSI 仓库分别安排一个实际文档 PR。mode=yolo，任务指向作者，另一方暂不提交任何 review。检查 review 请求存在、reviews 为空、head 未变、适用检查通过后，作者 merge commit。不要删 review、绕过保护或关闭 CI 来猜条件。每账号先做一次，保存 PR 事件和结果；未到账记录未确认，不转成批量尝试。

## 普通工作怎样支持其他三项

- Pull Shark：B 向 A 的 CS336 仓库提交 PR，由 A 验收合并；A 向 B 的 RSI 仓库提交 PR，由 B 验收合并。社区对自有仓库是否计数说法冲突，这里采用跨仓库贡献，不把争议写成硬规则。
- Pair Extraordinaire：同一提交包含双方真实成果，提交消息正确包含 `Co-authored-by: Name <GitHub关联邮箱>`。只 review 不等于共同作者；PR 正文致谢不替代 commit trailer；同一 PR 多放提交不按多个 PR 估算。默认保留提交历史并核对落地主分支的共同署名。归属和计数不凭一次文案检查声称通过。
- Galaxy Brain：在公开工作仓库可采纳答案的 Q&A 中，回答由另一账号发起的真实问题，由提问者验证并采纳。A 问 CS336、B 回答，计 B；B 问 RSI、A 回答，计 A。GitHub Community Discussions 自 2024-02-06 起不发放此类成就，不在那里发布本项目问答。

## 核查与停止

只每天检查一次公开主页，以及首次解锁/预计跨等级时补查一次。页面不可读、结构改变、隐藏成就时标记 unknown，不当成零或已获得。GitHub 页面使用的 `/users/<login>/achievements/<slug>/detail`（需要 X-Requested-With）可以辅助核对历史，但它不是稳定的 REST/GraphQL API，不依赖其 HTML 计算不可见精确进度。

每天分别记录本项目新建/合并 PR、实际共同署名、采纳回答以及可见等级。十四天总结银级阶段；双方 YOLO 可见且其余三项均为金级时，各自暂停本机原生任务。未到账不虚报。

## 十四天目标怎么算

十五个合并 PR/天意味着每账号十四天约 210 个，足以覆盖 Pull Shark 银级 128 的数量门槛，不能在两周内达到金级 1024。即使从零计数，金级也需要约 74 个合并 PR/天；按十五个/天约需 69 天。这是数量推算，不是发放承诺。

Pair 银级需要 24 个符合条件的共同署名 PR，Galaxy 银级需要 16 个被采纳回答。十四天内各自完成这些数量，比金级 Pull Shark 更可行。实际安排优先在有效主题任务中覆盖共同贡献和问答，不另设每日上限；如有更多完成并验证的工作可以继续合并。

证据：[社区门槛](https://github.com/Schweinepriester/github-profile-achievements#tiers)、[YOLO 历史](https://github.com/Schweinepriester?achievement=yolo&tab=achievements)、[成功 PR](https://github.com/Schweinepriester/achievement-testarea/pull/4)、[YOLO 条件讨论](https://github.com/Schweinepriester/github-profile-achievements/discussions/6#discussioncomment-2934257)、[Galaxy Brain 讨论](https://github.com/Schweinepriester/github-profile-achievements/discussions/9)、[Community 停发公告](https://github.com/orgs/community/discussions/106536)。社区评论相互矛盾时保留未知，不把点赞数或回答被采纳当作 GitHub 官方保证。
