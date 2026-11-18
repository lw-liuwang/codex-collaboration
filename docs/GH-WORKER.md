# 每半小时运行的无模型 GitHub worker

这是独立的 Windows 后台任务。Windows 任务计划程序每30分钟启动 Python，通过本机已登录的 GitHub CLI 读取云端队列并执行任务；关闭 Codex 不影响它。运行时只需要 Python 标准库和 `gh`，不需要模型、API Key、Codex 插件或本地模型。

任务来自共享仓库 [codex-collaboration 的 Issues](https://github.com/lw-liuwang/codex-collaboration/issues)。执行器完整分页读取指定给本账号的任务，顺序执行，回读结果后写回执并关闭任务。每次还完整分页扫描两个工作仓库的开放PR、Discussions、评论与回复，把自然语言待办和阻塞保留下来。

## 给 B 安装

**直接下载、解压、双击：** [下载准备好的程序包](https://github.com/lw-liuwang/codex-collaboration/archive/refs/heads/main.zip)，解压后双击根目录的 `B-START.cmd`。使用B自己的Windows账号，保持本机 `gh` 登录为 `ZicongHe2002`；B已安装的Git、Python和GitHub CLI继续使用，不需要Codex。

入口自动找到现有 `GitHubCollabWorker-B` 的程序和数据库目录，在干净的main上快进更新，然后运行任务135的恢复与回读。保留原30分钟计划、数据库和暂停状态；有暂停、已禁用、只读安装、未知配置、分支或未提交修改时显示具体原因并停止，不覆盖。若已有worker正在执行，等该轮退出后再次双击即可。

首次安装且没有已有任务时，入口使用当前Git检出；从ZIP运行时自动克隆到 `%LOCALAPPDATA%\GitHubCollabWorker\codex-collaboration`，随后安装并立即请求首轮扫描。下载目录可删除，已安装的稳定目录须保留。窗口结束时保留结果供查看；安装请求成功与实际GitHub任务完成分别以健康页和任务135回读为准。下面的命令行入口仍可用于诊断。

在 **B 自己的 Windows 账号**下打开 PowerShell。需要 Python 3.10+（包含 `pythonw.exe`）、Git 和 GitHub CLI；用 `gh auth status` 确认当前账号是 `ZicongHe2002`。安装器也会核对身份，身份不符就拒绝注册任务，不会借用 A 的凭据。

首次克隆：

```powershell
gh repo clone lw-liuwang/codex-collaboration
cd codex-collaboration
powershell -NoProfile -ExecutionPolicy Bypass -File worker/Install-Worker.ps1 -Actor B
```

已经克隆时，在干净的 main 上执行 `git pull --ff-only`，再运行安装命令。执行一次安装即可：立即启动一轮，之后每30分钟运行，Windows 登录后也会启动。任务名为 `GitHubCollabWorker-B`，同名安装会更新任务，保留配置、数据库与暂停标记。不要移动此目录或卸载它使用的 Python。

首次只验证安装与轮询，可加 `-ReadOnly`。查看实际计划而不安装可用 `-PlanOnly`。确认运行后，再用不带 `-ReadOnly` 的安装命令启用写操作。没有逐项弹出的批准流程。

它以当前 Windows 用户身份运行，避免 SYSTEM 无法访问 `gh` 登录凭据。电脑需要开机、联网并保持该用户登录；锁屏可继续，关机、休眠或注销期间不能轮询。Windows 不保证精确到秒的触发。每个账号只部署一份；本机任务设置不并发、崩溃后间隔1分钟重试最多3次，单次上限25分钟。worker处理任务达到20分钟后，把剩余对象留给下轮，为收尾扫描留出时间；后续半小时任务独立启动。所有 GitHub 写请求逐次检查北京时间09:00–23:00窗口，窗口外只读，不补造错过的工作。

安装不读取或改写 Codex 配置。在 B 上停用旧的 Codex GitHub 写入任务后使用此执行器，避免两个执行器同时修改对象。此仓库提供可安装代码；仅发布代码不等于已在 B 电脑安装成功。

## 能执行的操作

| operation | 对象与前提 |
| --- | --- |
| `issue_comment` | 三个协作仓库中指定Issue或PR的确定文本评论；带唯一回执标记 |
| `discussion_reply` | 对方仓库的Q&A；问题正文SHA256匹配，发布预先准备的答案 |
| `accept_answer` | 自己仓库的Q&A；问题、答案节点、答案正文SHA256及对方作者全匹配；保留其他已有采纳 |
| `review_pr` | 自己仓库的Ready PR；绑定完整head和完整diff摘要；不自approve、不review YOLO |
| `merge_pr` | 自己仓库的Ready PR；绑定head和diff；需要最终head的有效approve、同一提交中GitHub关联的双方作者、已配置的CI全部成功；固定merge commit |
| `open_pr` | 对方仓库中已准备分支；head提交作者关联执行账号；只创建PR，不编写或改写提交 |

内容发布（答案或新PR）、答案正确性判断和 `APPROVE` 任务必须由执行账号自己提交。例如 B 先准备具体内容或确定答案正确，再由 B 发布一次结构化任务，后台负责执行与恢复；A不能把自己写的答案交给B脚本发布，冒充B的独立成果。A可以给B发普通操作指令或合并已有真实共同成果的任务。

**无模型不等于能自动判断任意技术内容。** worker 不会自动研究、补写笔记、证明答案正确、伪造共同作者或为凑数量生成PR。哈希匹配只证明对象没有变化。已有的40个RSI开放PR仍需要真实补写与内容审核；脚本不会把它们全部自动批准合并，也不会因此宣称四项验收通过。自然语言交接会显示 `needs_manifest`，需要提供准确任务参数与缺少的真实成果。无需模型的领域专用校验可另行写成固定程序，但当前版本不执行云端传来的代码或命令。

## 发布一个任务

Issue需满足：带 `worker:task` 标签、Assignee为执行账号、作者在本机信任列表、正文包含且只包含一个 `collab-task` JSON代码块。安装默认信任A/B两个账号，目标只限三个协作仓库。

例如让B在共享Issue中发布一条操作说明，先保存为 `task.json`，把 `number` 换成实际对象：

```json
{
  "version": 1,
  "id": "b-comment-20261118-001",
  "actor": "ZicongHe2002",
  "operation": "issue_comment",
  "args": {
    "repo": "lw-liuwang/codex-collaboration",
    "number": 0,
    "body": "这里填写已经确定的操作说明和下一行动人。"
  }
}
```

示例的0是故意无效的占位符，避免误发。A使用本机A账号发布给B的任务：

```powershell
python -X utf8 worker/collab_worker.py enqueue --config worker/config.A.json --file task.json --apply
```

B发布自己的任务，改用安装生成的配置：

```powershell
python -X utf8 worker/collab_worker.py enqueue --config .local/installed-worker-B/config.json --file task.json --apply
```

`enqueue` 自动创建标签、设置Assignee并回读任务。同一id重复调用会先查找已有Issue；同一个id出现在不同Issue时，worker不会重复执行。手动建Issue也可以：把整个JSON放在以三反引号加 `collab-task` 开头的代码块内，并设置相同标签和指派。

执行中的任务参数被冻结；需要修改语义时新建不同id的任务，不编辑已领取任务的head或正文。任务没有任意shell、脚本下载、模型调用、force push、删除分支或修改凭据操作。

## 其他操作的参数

所有参数均在 `args` 中；下列字段必须完整提供，不接受额外字段。`head`、`joint_commit`为完整40位SHA，`*_sha256`为64位SHA256，正文哈希先把CRLF归一为LF再按UTF-8计算。完整diff摘要直接使用 `gh` 返回的原始字节。

| 操作 | args字段 |
| --- | --- |
| `discussion_reply` | `repo`, `number`, `question_sha256`, `body` |
| `accept_answer` | `repo`, `number`, `question_sha256`, `comment_id`, `answer_sha256`, `expected_author` |
| `review_pr` | `repo`, `number`, `head`, `diff_sha256`, `event`, `body`；event为APPROVE、COMMENT或REQUEST_CHANGES |
| `merge_pr` | `repo`, `number`, `head`, `diff_sha256`, `joint_commit` |
| `open_pr` | `repo`, `head_branch`, `head`, `base`, `title`, `body`, `draft`；base固定main，draft是JSON布尔值 |

只读获取PR绑定字段：

```powershell
python -X utf8 worker/collab_worker.py inspect-pr --config worker/config.A.json --repo ZicongHe2002/rsi-notes --number 81
```

只读获取问题摘要、答案节点和评论/回复摘要：

```powershell
python -X utf8 worker/collab_worker.py inspect-discussion --config worker/config.A.json --repo ZicongHe2002/rsi-notes --number 59
```

`merge_pr`检查指定共同署名提交确实在PR内，并且GitHub把双方关联为这个提交的作者；它不能从trailer证明双方真实写作，真实内容协作仍是前提。别人提交的PR需要本机账号对最终head的有效approve；自己的PR需要对方的approve。既有技术审核可以形成一个预先确定的 `review_pr` 任务，不能用模板式“检查通过”冒充内容审稿。YOLO当前只识别并跳过，完全不走自动review/merge路径。

本机配置的 `required_checks` 按仓库设置必需CI名称。默认空列表表示没有额外命名CI门槛，**不表示CI已运行**；GitHub自身的分支保护仍生效。服务不运行PR代码。GitHub API可能返回权限限制、冲突或需要的检查，均记录为具体阻塞并继续其他独立任务。

## 状态、暂停与恢复

### B 当前任务135的一键恢复

在 B 已安装服务的共享仓库目录中运行：

```powershell
git pull --ff-only origin main
powershell -NoProfile -ExecutionPolicy Bypass -File worker/Repair-Worker.ps1
```

第二条命令默认使用B已安装的配置和任务135，不需要手填effect key。它核对本机身份、指派、可信作者及任务内容，完整分页回查目标评论和回执；已有结果直接续做，缺失的`sent`步骤先备份SQLite数据库，再进行一次明确的恢复尝试，最后执行正常轮询并回读任务完成结果。再次运行不会重复发布已完成的评论。恢复报告为`.local/installed-worker-B/recovery-135.json`，数据库备份位于同目录的`backups/`。

它保留原半小时计划、暂停标记和数据库，仅支持确定文本的`issue_comment`任务。不会替B生成答案、审核或合并PR。已完成操作被删除、评论被编辑或重复、任务内容改变、身份不符、窗口外及暂停状态均停止恢复，不覆盖现状。若GitHub或网络故障仍在，命令返回失败，并报告HTTP状态、gh退出码及固定错误类别；原始stderr和凭据不会写入健康页。

只读检查可加`-ReadOnly`；其他已安装目录可用`-WorkerRoot`。恢复其他评论任务时传`-QueueIssue`，例如`-QueueIssue 142`。这是一项显式的本机恢复操作：评论接口没有通用幂等键，远端未查到结果仍不能绝对排除延迟应用，因此不在半小时轮询里自动清空所有不确定记录。其他任务的记录保持不变。

### 服务控制

```powershell
powershell -NoProfile -File worker/Control-Worker.ps1 -Actor B -Action Status
powershell -NoProfile -File worker/Control-Worker.ps1 -Actor B -Action Pause
powershell -NoProfile -File worker/Control-Worker.ps1 -Actor B -Action Resume
powershell -NoProfile -File worker/Control-Worker.ps1 -Actor B -Action Uninstall
```

暂停标记持久保存，重装和重启都不会自动恢复；暂停后已发出的请求可能完成，后续写请求不再发送。卸载保留日志和数据库。自定义安装目录时，这些命令也应传同一个 `-WorkerRoot`。

本地状态位于 `.local/installed-worker-B/`：

- `status.json`：启动、结束与最近成功全量轮询时间，各任务结果或具体阻塞。
- `inventory.json`：完整PR/讨论/评论/回复快照。
- `worker.sqlite3`：任务绑定和逐步写入账本，重启复用。
- `worker.log`：错误日志，自动轮转。

启用写入后的首轮自动建立并持续更新同一个 `worker-health/ZicongHe2002` Issue。它记录最后成功扫描时间及待办URL。即使服务停了，旧时间也会保留，便于识别未执行；不靠Codex口头报告“已触发”。只读模式不创建或更新这个Issue。服务不会估计或宣称徽章到账。

写请求先落账本，失败先回查标记或目标状态。回读成功后续做回执、关闭任务；新一轮不会重复发评论或采纳答案。遇到请求结果不确定且远端暂时查不到时，保留 `sent` 并阻塞该步，防止超时后盲发第二次。GitHub评论接口没有通用幂等键，因此不承诺跨网络故障的严格exactly-once。

通常下轮能回读并恢复。若确认远端确实未发生该操作，操作者可以用错误日志里的完整effect key解除单步不确定状态，再等下轮：

```powershell
python -X utf8 worker/collab_worker.py retry-uncertain --config .local/installed-worker-B/config.json --effect-key '<完整effect key>' --confirm-not-applied
```

不要删除整个数据库重试；这会丢失重复执行保护。此恢复命令只改自己的worker账本，不读取或改写Codex内部数据。

## 开发验证

```powershell
python -X utf8 -m unittest discover -s tests -p test_worker.py -v
pwsh -NoProfile -File tests/Run-Tests.ps1
python -X utf8 worker/collab_worker.py doctor --config worker/config.A.json
python -X utf8 worker/collab_worker.py once --config worker/config.A.json
```

最后一条没有 `--apply`，只做真实只读扫描。B配置在A身份下必须拒绝；这里的A配置仅用于A本机验证，不给B借用。

本实现由Codex辅助开发；安装后的运行不使用Codex。生产部署状态和实际验证记录分别记录，不能把mock测试当作B已安装或技术内容已完成。
