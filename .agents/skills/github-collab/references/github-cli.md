# Windows 接入和 GitHub 操作

## 安装、授权与身份

先检查 `git --version`、`gh --version`、`$PSVersionTable.PSVersion`。使用 PowerShell 7，只安装缺失工具：

```powershell
winget install --id Git.Git --exact --source winget
winget install --id GitHub.cli --exact --source winget
winget install --id Microsoft.PowerShell --exact --source winget
```

没有 winget 时使用各项目官方发布页，安装后重开终端。OAuth 首次授权需要账号持有人完成；之后 gh 使用本机保存的登录独立工作，不需要每次授权。不要把 token 放进仓库。

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
gh api user --jq '{login,id,name}'
```

A=lw-liuwang，B=ZicongHe2002。Doctor 核对当前身份，身份不符时修正本机登录。只在专用克隆配置 Git user.name 和 GitHub 关联邮箱，不改全局身份。可使用 `用户数字ID+login@users.noreply.github.com`，推送后检查 GitHub 识别的 author。Co-authored-by 使用实际共同作者的 GitHub 关联邮箱；只有 review 不算共同创作。

## 建仓和接受邀请

A 建公开的 codex-collaboration、cs336-notes；B 用自己的账号建公开的 rsi-notes。先 `gh repo view owner/name` 查询，已有则续用。

```powershell
gh repo create owner/name --public --source <本地目录> --remote origin --push
gh api --method PUT repos/owner/name/collaborators/peer -f permission=push
gh api user/repository_invitations --paginate
gh api --method PATCH user/repository_invitations/<邀请ID>
gh api repos/owner/name --jq '.permissions'
```

只接受这三个配置仓库的邀请。共享仓库标签为 handoff、daily、yolo。开启 Discussions 用 `gh repo edit owner/name --enable-discussions`，再查询 Q&A 类别。尚无可采纳类别时，由仓库所有者在 Discussions 的类别设置建立或选择 Question and answer 类别；普通 Issue 不提供讨论答案采纳。

## PR 和交接

在专用克隆或 worktree 操作，已有任务续用原分支。正文写 UTF-8 文件，占位符替换为实际值，参数逐项传入。

```powershell
gh pr create --repo owner/name --base main --head branch --title '具体改动' --body-file pr.md
gh issue create --repo lw-liuwang/codex-collaboration --label handoff --assignee peer --title 'review-pr: 具体对象' --body-file handoff.md
gh pr view <PR-URL> --json author,headRefOid,reviewRequests,reviews,mergeStateStatus
gh pr diff <PR-URL>
gh pr review <PR-URL> --approve --body-file review.md
gh pr merge <PR-URL> --merge --match-head-commit <核对的SHA>
gh pr view <PR-URL> --json state,mergedAt,mergeCommit
gh issue edit <交接URL> --remove-assignee peer --add-assignee me --body-file handoff.md
gh issue close <交接URL> --comment '结果链接和验证事实'
```

普通 PR 由对方检查、合并。YOLO 使用 `gh pr edit <PR-URL> --add-reviewer peer` 请求 review，然后作者在 reviews 仍为空时合并；对方先看交接 mode，不提交 review。PR assignee、reviewer 请求和已提交 review 是不同对象。

没有对方 push 权限时先准备内容，邀请接受后推送。写入超时回查对象，成功就补记录，不重复创建。使用 Refs 引用交接，避免合并 PR 时提前自动关闭仍待验收的共享 Issue。

## Discussions / Q&A

GraphQL 查询和变更写成 JSON 文件，由 `gh api graphql --input payload.json` 调用，多行正文、美元符号和反引号就不会被 shell 意外解释。示例变量替换为真实节点 ID。

查询仓库节点和可回答类别：

```graphql
query($owner:String!,$name:String!){
  repository(owner:$owner,name:$name){
    id discussionCategories(first:100){nodes{id name isAnswerable}}
  }
}
```

创建提问：

```graphql
mutation($repo:ID!,$category:ID!,$title:String!,$body:String!){
  createDiscussion(input:{repositoryId:$repo,categoryId:$category,title:$title,body:$body}){
    discussion{id number url}
  }
}
```

回答：

```graphql
mutation($discussion:ID!,$body:String!){
  addDiscussionComment(input:{discussionId:$discussion,body:$body}){comment{id url}}
}
```

提问者验证后采纳：

```graphql
mutation($answer:ID!){
  markDiscussionCommentAsAnswer(input:{id:$answer}){
    discussion{id answer{id url author{login}}}
  }
}
```

JSON 形状为 `{"query":"上面的 GraphQL 字符串","variables":{"repo":"真实节点ID"}}`，variables 按操作填写。检查响应没有 errors，并重新查询 discussion.answer.id。问题、答案和采纳结果均回填同一交接 Issue。

## 待办和排程

脚本 Inbox 完整分页读取共享仓库 open/handoff Issues，分别输出 actionRequired、waitingOnPeer、unassigned。Assignee 是下一行动人。Doctor 检查工具和本机身份，不要求全部仓库就绪。Plan 生成并锁定本地随机计划，Next 返回下一项未来时刻与单个预约的 rrule；原生任务创建/更新仍由 Codex automation_update 完成。

官方参考：[CLI 安装](https://github.com/cli/cli#installation)、[OAuth 登录](https://cli.github.com/manual/gh_auth_login)、[共同作者](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors)、[GraphQL mutations](https://docs.github.com/en/graphql/reference/mutations)。
