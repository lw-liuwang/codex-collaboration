# LeetCode 题解与代码

本仓库：`{{OWNER}}/leetcode-solutions`。双方各有一个工作仓库：

- A：[lw-liuwang/leetcode-solutions](https://github.com/lw-liuwang/leetcode-solutions)，维护并评审B提交的C++代码。
- B：[ZicongHe2002/leetcode-solutions](https://github.com/ZicongHe2002/leetcode-solutions)，维护并评审A提交的Python代码。

A用Python向B仓库提交Issue和PR；B用C++向A仓库提交Issue和PR。工作任务、补写、评审及交接都在对方的工作仓库中进行。

双方不互邀为仓库协作者，不授予对方写权限。各自fork对方公开仓库，在自己的fork分支提交代码，向对方上游main发PR，由上游所有者正式评审、批准并合并。独立工作仓库均保留；fork使用不同名称，避免与自己的`leetcode-solutions`重名。

实现按四位题号命名，例如`python/p0001_two_sum.py`和`cpp/p0001_two_sum.cpp`，测试分别位于`tests/python/`与`tests/cpp/`。每篇题解附原题链接、自己的算法解释、不变量、复杂度与边界。完整规范见[CONTRIBUTING.md](CONTRIBUTING.md)。

每个代码PR必须由另一账号正式Code review；作者不能自approve。内容推送撤销旧批准，只以merge commit合并。实际共同补写才共同署名，review本身不替代共同创作。程序未运行或未提交LeetCode时如实记录，不声称已通过。代码由各账号借助OpenAI Codex辅助编写。
