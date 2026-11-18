"""Execute structured GitHub jobs with gh, without a model or shell commands."""

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import quote, urlencode

VERSION = '1.0.1'
BJT = timezone(timedelta(hours=8))
HUB = 'lw-liuwang/codex-collaboration'
REPOS = {'lw-liuwang': 'lw-liuwang/cs336-notes', 'ZicongHe2002': 'ZicongHe2002/rsi-notes'}
LABEL = 'worker:task'
FENCE = re.compile(r'^```collab-task\s*\n(.*?)\n```\s*$', re.M | re.S)
FIELDS = {
    'issue_comment': {'repo', 'number', 'body'},
    'discussion_reply': {'repo', 'number', 'question_sha256', 'body'},
    'accept_answer': {'repo', 'number', 'question_sha256', 'comment_id', 'answer_sha256', 'expected_author'},
    'review_pr': {'repo', 'number', 'head', 'diff_sha256', 'event', 'body'},
    'merge_pr': {'repo', 'number', 'head', 'diff_sha256', 'joint_commit'},
    'open_pr': {'repo', 'head_branch', 'head', 'base', 'title', 'body', 'draft'},
}


class Blocked(Exception):
    """A precondition or an uncertain write needs resolution before progress."""


class Busy(Blocked):
    """Another process owns the local writer lock."""


class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def request_failure(result, method, endpoint):
    error = result.stderr.decode('utf-8', errors='replace')
    match = re.search(r'HTTP (\d{3})', error)
    status = int(match[1]) if match else None
    category = 'unknown'
    for name, pattern in [('timeout', r'timed? out|deadline exceeded'),
                          ('dns', r'no such host|getaddrinfo'),
                          ('tls', r'x509|certificate'),
                          ('connection', r'connection refused|connection reset|network is unreachable')]:
        if re.search(pattern, error, re.I):
            category = name
            break
    # Report fixed categories and numeric status only; never include raw stderr.
    return ApiError(f'gh API 请求失败: {method} {endpoint.split("?")[0]}; '
                    f'HTTP {status or "unknown"}; gh exit {result.returncode}; category={category}', status)


def receipt_body(result):
    return ('worker 已回读操作结果。\n\n```json\n'+json.dumps(result,ensure_ascii=False,indent=2)+
            '\n```\n\n这是结构化任务的执行回执，不代表新增内容判断、共同写作或徽章到账。')


def digest(value):
    if isinstance(value, str):
        value = value.replace('\r\n', '\n').encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def now():
    return datetime.now(BJT)


def in_window(at):
    return 9 <= at.astimezone(BJT).hour < 23


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def parse_task(body):
    matches = FENCE.findall(body or '')
    if len(matches) != 1:
        raise Blocked('需要且只能有一个 collab-task JSON 块；自然语言交接不会自动执行')
    try:
        task = json.loads(matches[0])
    except ValueError as exc:
        raise Blocked('任务 JSON 无效') from exc
    if not isinstance(task, dict) or set(task) != {'version', 'id', 'actor', 'operation', 'args'}:
        raise Blocked('任务字段应为 version/id/actor/operation/args')
    if type(task['version']) is not int or task['version'] != 1 or not isinstance(task['actor'], str) or task['actor'] not in REPOS:
        raise Blocked('不支持的版本或执行身份')
    if not isinstance(task['id'], str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,64}', task['id']):
        raise Blocked('id 应为8至64位字母、数字、下划线或短横线')
    op, args = task['operation'], task['args']
    if not isinstance(op, str) or op not in FIELDS or not isinstance(args, dict) or set(args) != FIELDS[op]:
        raise Blocked('不支持的操作或参数字段')
    if args['repo'] not in [HUB, *REPOS.values()]:
        raise Blocked('目标不在三个协作仓库内')
    for key, value in args.items():
        if key == 'number' and (type(value) is not int or value <= 0):
            raise Blocked('number 必须是正整数')
        if key == 'draft':
            if type(value) is not bool:
                raise Blocked('draft 必须是布尔值')
        elif key != 'number' and (not isinstance(value, str) or not value or len(value) > 60000):
            raise Blocked(f'{key} 必须是非空文本，至多60000字符')
        if key in {'head', 'joint_commit'} and not re.fullmatch(r'[0-9a-f]{40}', value):
            raise Blocked(f'{key} 必须是完整40位提交SHA')
        if key.endswith('sha256') and not re.fullmatch(r'[0-9a-f]{64}', value):
            raise Blocked(f'{key} 必须是64位SHA256')
    if op == 'review_pr' and args['event'] not in {'APPROVE', 'COMMENT', 'REQUEST_CHANGES'}:
        raise Blocked('review event 无效')
    if op == 'open_pr':
        if args['base'] != 'main' or not re.fullmatch(r'[A-Za-z0-9_./-]{1,200}', args['head_branch']):
            raise Blocked('只支持 main 基线和同仓库已准备的分支')
        if len(args['title']) > 200:
            raise Blocked('PR 标题过长')
    return task


class Gh:
    def __init__(self, can_write=lambda: False):
        self.executable = shutil.which('gh')
        if not self.executable:
            raise Blocked('找不到 gh，请先安装 GitHub CLI')
        self.can_write = can_write

    def api(self, endpoint, method='GET', data=None, raw=False):
        if method != 'GET' and not self.can_write():
            raise Blocked('当前为只读、暂停或北京时间09–23窗口之外')
        command = [self.executable, 'api', '--hostname', 'github.com', endpoint, '--method', method]
        if raw:
            command += ['-H', 'Accept: application/vnd.github.v3.diff']
        if data is not None:
            command += ['--input', '-']
        try:
            result = subprocess.run(command, input=None if data is None else json.dumps(data).encode('utf-8'),
                                    capture_output=True, timeout=60, shell=False,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except subprocess.TimeoutExpired as exc:
            raise ApiError('gh 请求超时；写请求需先回查') from exc
        if result.returncode:
            raise request_failure(result, method, endpoint)
        return result.stdout if raw else json.loads(result.stdout or b'null')

    def pages(self, endpoint):
        result, page = [], 1
        while True:
            separator = '&' if '?' in endpoint else '?'
            batch = self.api(f'{endpoint}{separator}per_page=100&page={page}')
            if not isinstance(batch, list):
                raise ApiError('预期分页数组')
            result.extend(batch)
            if len(batch) < 100:
                return result
            page += 1

    def query(self, query, variables):
        # GraphQL reads use POST at HTTP level, but remain permitted in read-only mode.
        if not query.lstrip().startswith('query'):
            raise Blocked('GraphQL读取只能使用 query')
        command = [self.executable, 'api', '--hostname', 'github.com', 'graphql', '--input', '-']
        try:
            result = subprocess.run(command, input=json.dumps({'query': query, 'variables': variables}).encode(),
                                    capture_output=True, timeout=60, shell=False,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except subprocess.TimeoutExpired as exc:
            raise ApiError('GraphQL读取超时') from exc
        if result.returncode:
            raise request_failure(result, 'query', 'graphql')
        value = json.loads(result.stdout)
        if value.get('errors'):
            raise ApiError('GraphQL返回错误')
        return value['data']

    def mutate(self, query, variables):
        result = self.api('graphql', 'POST', {'query': query, 'variables': variables})
        if result.get('errors'):
            raise ApiError('GraphQL写入返回错误')
        return result['data']


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (key TEXT PRIMARY KEY, digest TEXT, status TEXT, detail TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS effects (key TEXT PRIMARY KEY, state TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS task_ids (id TEXT PRIMARY KEY, job_key TEXT)')
        self.db.commit()

    def bind(self, key, task_digest, task_id=None):
        if task_id:
            claimed = self.db.execute('SELECT job_key FROM task_ids WHERE id=?', (task_id,)).fetchone()
            if claimed and claimed[0] != key:
                raise Blocked('此任务id已从另一个Issue领取，禁止重复执行: ' + claimed[0])
        old = self.db.execute('SELECT digest FROM jobs WHERE key=?', (key,)).fetchone()
        if old and old[0] != task_digest:
            raise Blocked('已领取任务被编辑；请新建任务，不能改变原任务语义')
        self.db.execute('INSERT OR IGNORE INTO jobs VALUES (?,?,?,?)', (key, task_digest, 'pending', ''))
        if task_id:
            self.db.execute('INSERT OR IGNORE INTO task_ids VALUES (?,?)', (task_id, key))
        self.db.commit()

    def record(self, key, status, detail):
        self.db.execute('UPDATE jobs SET status=?, detail=? WHERE key=?', (status, json.dumps(detail, ensure_ascii=False), key))
        self.db.commit()

    def job(self, key):
        row = self.db.execute('SELECT status, detail FROM jobs WHERE key=?', (key,)).fetchone()
        return {'status':row[0],'detail':json.loads(row[1]) if row[1] else None} if row else None

    def once(self, key, write, read):
        found = read()
        if found is not None:
            self.db.execute('INSERT OR REPLACE INTO effects VALUES (?,?)', (key, 'done'))
            self.db.commit()
            return found
        old = self.db.execute('SELECT state FROM effects WHERE key=?', (key,)).fetchone()
        if old:
            raise Blocked('写入结果不确定或已被删除；等待远端回查，禁止盲目重复写入: ' + key)
        self.db.execute('INSERT INTO effects VALUES (?,?)', (key, 'sent'))
        self.db.commit()
        try:
            write()
        except Blocked:
            # Gh raises this before sending a request when the window closes or PAUSE appears.
            self.db.execute('DELETE FROM effects WHERE key=?', (key,))
            self.db.commit()
            raise
        except ApiError as exc:
            found = read()
            if found is None:
                if exc.status and 400 <= exc.status < 500:
                    self.db.execute('DELETE FROM effects WHERE key=?', (key,))
                    self.db.commit()
                raise
        found = read()
        if found is None:
            raise Blocked('请求后未回读到结果；下次先回查，禁止重复写入: ' + key)
        self.db.execute('UPDATE effects SET state=? WHERE key=?', ('done', key))
        self.db.commit()
        return found


@contextmanager
def exclusive(path):
    handle = open(path, 'a+b')
    try:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise Busy('另一个 worker 正在运行') from None
    try:
        yield
    finally:
        handle.close()


COMMENT_FIELDS = 'id url body author{login}'


class Worker:
    def __init__(self, config, state, gh=None, apply=False, clock=now):
        self.config, self.state, self.clock, self.apply = config, Path(state), clock, apply
        self.actor = config['actor']
        if self.actor not in REPOS or set(config.get('trusted_authors', [])) - set(REPOS):
            raise Blocked('配置身份或信任作者无效')
        self.own = REPOS[self.actor]
        self.peer_actor = next(x for x in REPOS if x != self.actor)
        self.peer = REPOS[self.peer_actor]
        self.state.mkdir(parents=True, exist_ok=True)
        self.store = Store(self.state / 'worker.sqlite3')
        self.gh = gh or Gh(self.can_write)

    def can_write(self):
        return self.apply and in_window(self.clock()) and not (self.state / 'PAUSE').exists()

    def identity(self):
        user = self.gh.api('user')['login']
        if user != self.actor:
            raise Blocked(f'本机gh身份为{user}，配置要求{self.actor}；不会切换账号或借用凭据')
        return user

    def connection(self, query, variables, extract):
        nodes, cursor = [], None
        while True:
            connection = extract(self.gh.query(query, {**variables, 'cursor': cursor}))
            nodes.extend(connection['nodes'])
            if not connection['pageInfo']['hasNextPage']:
                return nodes
            cursor = connection['pageInfo']['endCursor']

    def discussion(self, repo, number):
        owner, name = repo.split('/')
        data = self.gh.query('query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){discussion(number:$i){id number url body author{login} category{isAnswerable} answer{id author{login}}}}}', {'o':owner,'n':name,'i':number})
        value = data['repository']['discussion']
        if value is None:
            raise Blocked('Discussion不存在')
        return value

    def comments(self, discussion_id):
        query = 'query($id:ID!,$cursor:String){node(id:$id){... on Discussion{comments(first:100,after:$cursor){pageInfo{hasNextPage endCursor}nodes{'+COMMENT_FIELDS+'}}}}}'
        return self.connection(query, {'id':discussion_id}, lambda d:d['node']['comments'])

    def thread_comments(self, discussion_id):
        comments = self.comments(discussion_id)
        for comment in comments:
            query = 'query($id:ID!,$cursor:String){node(id:$id){... on DiscussionComment{replies(first:100,after:$cursor){pageInfo{hasNextPage endCursor}nodes{'+COMMENT_FIELDS+'}}}}}'
            comment['replies'] = self.connection(query, {'id':comment['id']}, lambda d:d['node']['replies'])
        return comments

    def read_comment(self, key, repo, number, body):
        marker = '<!-- collab-worker:' + key + ' -->'
        endpoint = f'repos/{repo}/issues/{number}/comments'
        matches = []
        for comment in self.gh.pages(endpoint):
            if comment['user']['login'] == self.actor and marker in (comment['body'] or ''):
                if comment['body'].replace('\r\n','\n') != (body+'\n\n'+marker).replace('\r\n','\n'):
                    raise Blocked('已发布的回执或评论被编辑，保留现状')
                matches.append({'url':comment['html_url']})
        if len(matches) > 1:
            raise Blocked('同一任务标记存在多条评论，保留现状并检查重复原因')
        return matches[0] if matches else None

    def comment_effect(self, key, repo, number, body):
        marker = '<!-- collab-worker:' + key + ' -->'
        endpoint = f'repos/{repo}/issues/{number}/comments'
        return self.store.once(key, lambda:self.gh.api(endpoint, 'POST', {'body':body+'\n\n'+marker}),
                               lambda:self.read_comment(key, repo, number, body))

    def assigned_task(self, number, allow_closed=False):
        issue = self.gh.api(f'repos/{HUB}/issues/{number}')
        if 'pull_request' in issue or issue['user']['login'] not in self.config['trusted_authors']:
            raise Blocked('需要受信任作者发布的任务Issue')
        if ((issue['state'] != 'open' and not allow_closed) or
                self.actor not in {a['login'] for a in issue['assignees']} or
                LABEL not in {label['name'] for label in issue['labels']}):
            raise Blocked('任务状态、指派或标签已变化')
        task = parse_task(issue['body'])
        if task['actor'] != self.actor:
            raise Blocked('任务actor与执行账号不一致')
        return issue, task

    def recover_comment(self, number):
        """Explicit local recovery of one comment task, with remote reads and a backup."""
        self.identity()
        key = f'{HUB}#{number}'
        previous = self.store.job(key)
        issue, task = self.assigned_task(number, allow_closed=bool(previous and previous['status'] in {'applied','done'}))
        if task['operation'] != 'issue_comment':
            raise Blocked('一键恢复只支持issue_comment，不自动重发答案、review或merge')
        task_digest = digest(json.dumps(task, sort_keys=True, ensure_ascii=False))
        bound = self.store.db.execute('SELECT digest FROM jobs WHERE key=?', (key,)).fetchone()
        if bound and bound[0] != task_digest:
            raise Blocked('已领取任务被编辑，不能恢复不同内容')
        claimed = self.store.db.execute('SELECT job_key FROM task_ids WHERE id=?', (self.actor+':'+task['id'],)).fetchone()
        if claimed and claimed[0] != key:
            raise Blocked('此任务id已由其他Issue领取，保留不确定记录')
        effect = key+':'+task_digest
        args = task['args']
        result = self.read_comment(effect, args['repo'], args['number'], args['body'])
        receipt = self.read_comment(effect+':receipt', HUB, number, receipt_body(result)) if result else None
        if previous and previous['status'] in {'applied','done'} and result is None:
            raise Blocked('账本已有成功结果但远端评论不存在，保留删除或修改后的现状')
        if previous and previous['status'] == 'done':
            if issue['state'] != 'closed' or receipt is None:
                raise Blocked('已完成任务被重新打开或回执缺失，不覆盖人工变更')
            return {'task':issue['html_url'],'completed':True,'state':'already_done','result':result,'recovered_effects':[],'backup':None}
        missing = [(effect, result is None), (effect+':receipt', result is not None and receipt is None),
                   (effect+':close', issue['state'] == 'open')]
        resets = []
        for effect_key, absent in missing:
            old = self.store.db.execute('SELECT state FROM effects WHERE key=?', (effect_key,)).fetchone()
            if absent and old:
                if old[0] != 'sent':
                    raise Blocked('账本已完成的操作在远端缺失，不能自动重发: '+effect_key)
                resets.append(effect_key)
        if not self.apply:
            return {'task':issue['html_url'],'completed':False,'state':'planned','would_recover':resets,'result':result}
        if not self.can_write():
            raise Blocked('保持暂停标记和09–23时窗；当前不能恢复写入')
        # Check the source again before changing the ledger; the cycle also re-reads it.
        current, checked = self.assigned_task(number, allow_closed=issue['state'] == 'closed')
        if checked != task or current['state'] != issue['state']:
            raise Blocked('恢复前任务内容或状态已变化，请回查')
        backup_path = None
        if resets:
            backup_path = self.state/'backups'/f'recovery-{number}-{time.time_ns()}.sqlite3'
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(backup_path)) as backup:
                self.store.db.backup(backup)
            if not self.can_write():
                raise Blocked('恢复前已暂停或离开写入时窗，账本未改动')
            for effect_key in resets:
                self.store.db.execute('DELETE FROM effects WHERE key=? AND state=?', (effect_key,'sent'))
            self.store.db.commit()
        record = {'task':issue['html_url'],'completed':False,'state':'recovering','recovered_effects':resets,
                  'backup':str(backup_path) if backup_path else None}
        path = self.state/f'recovery-{number}.json'
        atomic_json(path, record)
        cycle = self.cycle()
        job = next((j for j in cycle['jobs'] if j['issue'] == issue['html_url']), None)
        record.update(completed=bool(job and job['state'] == 'done'), state=job['state'] if job else 'not_processed',
                      detail=job, finished_at=self.clock().isoformat())
        atomic_json(path, record)
        return record

    def checked_pr(self, args, allow_merged=False):
        pr = self.gh.api(f'repos/{args["repo"]}/pulls/{args["number"]}')
        if pr['head']['sha'] != args['head']:
            raise Blocked('PR head 已变化，需要针对新head的新任务')
        if pr.get('merged') and allow_merged:
            return pr
        if pr['state'] != 'open' or pr['draft']:
            raise Blocked('PR不是开放Ready状态')
        body = pr['body'] or ''
        if re.search(r'mode\s*=\s*yolo', body, re.I) or any(l['name'].lower() == 'mode:yolo' for l in pr['labels']):
            raise Blocked('YOLO尝试不进入普通review/共同署名合并路径')
        diff = self.gh.api(f'repos/{args["repo"]}/pulls/{args["number"]}', raw=True)
        if digest(diff) != args['diff_sha256']:
            raise Blocked('完整diff摘要不匹配')
        return pr

    def require_checks(self, args):
        required = self.config.get('required_checks', {}).get(args['repo'], [])
        if not required:
            return
        endpoint = f'repos/{args["repo"]}/commits/{args["head"]}'
        checks = self.check_runs(endpoint + '/check-runs')
        statuses = self.gh.pages(endpoint + '/statuses')
        # Both endpoints list newest records first. A rerun cannot reuse an older success.
        actual = {}
        for check in checks:
            actual.setdefault(check['name'], check['conclusion'] if check['status'] == 'completed' else 'pending')
        latest_statuses = {}
        for status in statuses:
            latest_statuses.setdefault(status['context'], status['state'])
        for name, state in latest_statuses.items():
            if name not in actual or state != 'success':
                actual[name] = state
        if any(actual.get(name) != 'success' for name in required):
            raise Blocked('必需CI检查尚未全部成功')

    def check_runs(self, endpoint):
        records, page = [], 1
        while True:
            batch = self.gh.api(endpoint + '?' + urlencode({'per_page':100,'page':page,'filter':'latest'}))['check_runs']
            records.extend(batch)
            if len(batch) < 100:
                return records
            page += 1

    def require_joint_commit(self, args):
        owner, name = args['repo'].split('/')
        query = 'query($o:String!,$n:String!,$i:Int!,$cursor:String){repository(owner:$o,name:$n){pullRequest(number:$i){commits(first:100,after:$cursor){pageInfo{hasNextPage endCursor}nodes{commit{oid authors(first:100){pageInfo{hasNextPage}nodes{user{login}}}}}}}}}'
        commits = self.connection(query, {'o':owner,'n':name,'i':args['number']}, lambda d:d['repository']['pullRequest']['commits'])
        joint = next((c['commit'] for c in commits if c['commit']['oid'] == args['joint_commit']), None)
        if not joint or joint['authors']['pageInfo']['hasNextPage']:
            raise Blocked('指定共同署名提交不在PR中或作者列表不完整')
        authors = {a['user']['login'] for a in joint['authors']['nodes'] if a['user']}
        if not set(REPOS).issubset(authors):
            raise Blocked('同一提交没有GitHub关联的双方作者；worker不会添加共同作者')

    def execute(self, task, key, issuer=None):
        op, args = task['operation'], task['args']
        repo = args['repo']
        if op in {'accept_answer','review_pr','merge_pr'} and repo != self.own:
            raise Blocked('此操作只允许自己的工作仓库')
        if op in {'discussion_reply','open_pr'} and repo != self.peer:
            raise Blocked('此操作只允许对方的工作仓库')
        if (op in {'discussion_reply','open_pr','accept_answer'} or op == 'review_pr' and args['event'] == 'APPROVE') and issuer != self.actor:
            raise Blocked('内容发布、答案判断和approve需由执行账号预先提交具体任务；不能把对方提供的内容冒充自己的成果')
        marker = '<!-- collab-worker:' + key + ' -->'
        if op == 'issue_comment':
            return self.comment_effect(key, repo, args['number'], args['body'])
        if op in {'discussion_reply','accept_answer'}:
            d = self.discussion(repo, args['number'])
            if not d['category']['isAnswerable'] or digest(d['body']) != args['question_sha256']:
                raise Blocked('需要Q&A分类且提问正文摘要必须匹配')
            if op == 'discussion_reply':
                if d['author']['login'] == self.actor:
                    raise Blocked('不能把自答当作双账号答题路径')
                def read_reply():
                    for c in self.comments(d['id']):
                        if c['author'] and c['author']['login'] == self.actor and marker in c['body']:
                            if c['body'].replace('\r\n','\n') != (args['body']+'\n\n'+marker).replace('\r\n','\n'):
                                raise Blocked('已发布答案被编辑，保留现状')
                            return {'id':c['id'],'url':c['url']}
                    return None
                return self.store.once(key, lambda:self.gh.mutate('mutation($d:ID!,$b:String!){addDiscussionComment(input:{discussionId:$d,body:$b}){comment{id}}}', {'d':d['id'],'b':args['body']+'\n\n'+marker}), read_reply)
            answer = self.gh.query('query($id:ID!){node(id:$id){... on DiscussionComment{id body author{login} discussion{id}}}}', {'id':args['comment_id']})['node']
            if not answer or answer['discussion']['id'] != d['id'] or not answer['author'] or answer['author']['login'] != self.peer_actor or args['expected_author'] != self.peer_actor or digest(answer['body']) != args['answer_sha256']:
                raise Blocked('答案节点、所属讨论、对方作者或正文摘要不匹配')
            if d['answer'] and d['answer']['id'] != args['comment_id']:
                raise Blocked('已有其他采纳答案，保留现状')
            def read_answer():
                current = self.discussion(repo, args['number'])['answer']
                return current if current and current['id'] == args['comment_id'] and current['author']['login'] == self.peer_actor else None
            return self.store.once(key, lambda:self.gh.mutate('mutation($id:ID!){markDiscussionCommentAsAnswer(input:{id:$id}){discussion{id}}}', {'id':args['comment_id']}), read_answer)
        if op == 'review_pr':
            pr = self.checked_pr(args)
            if pr['user']['login'] == self.actor and args['event'] == 'APPROVE':
                raise Blocked('不能approve自己的PR')
            endpoint = f'repos/{repo}/pulls/{args["number"]}/reviews'
            def read_review():
                for r in self.gh.pages(endpoint):
                    if r['user']['login'] == self.actor and r['commit_id'] == args['head'] and marker in (r['body'] or ''):
                        wanted_state = {'APPROVE':'APPROVED','COMMENT':'COMMENTED','REQUEST_CHANGES':'CHANGES_REQUESTED'}[args['event']]
                        if r['state'] != wanted_state or r['body'].replace('\r\n','\n') != (args['body']+'\n\n'+marker).replace('\r\n','\n'):
                            raise Blocked('review已被修改或dismiss，不重复提交')
                        return {'id':r['id'],'url':r['html_url'],'commit_id':r['commit_id']}
                return None
            return self.store.once(key, lambda:self.gh.api(endpoint, 'POST', {'commit_id':args['head'],'event':args['event'],'body':args['body']+'\n\n'+marker}), read_review)
        if op == 'merge_pr':
            pr = self.checked_pr(args, allow_merged=True)
            if pr.get('merged'):
                return {'merge_commit_sha':pr['merge_commit_sha'],'head':pr['head']['sha'],'already_merged':True}
            self.require_joint_commit(args)
            reviews = self.gh.pages(f'repos/{repo}/pulls/{args["number"]}/reviews')
            reviewer = self.peer_actor if pr['user']['login'] == self.actor else self.actor
            decisions = [r for r in reviews if r['user']['login'] == reviewer and r['state'] in {'APPROVED','CHANGES_REQUESTED','DISMISSED'}]
            if not decisions or decisions[-1]['state'] != 'APPROVED' or decisions[-1]['commit_id'] != args['head']:
                raise Blocked('需要执行方针对最终head的有效approve，不能以机器检查冒充内容审核')
            self.require_checks(args)
            endpoint = f'repos/{repo}/pulls/{args["number"]}'
            def read_merge():
                value = self.gh.api(endpoint)
                if value.get('merged') and value['head']['sha'] == args['head']:
                    return {'merge_commit_sha':value['merge_commit_sha'],'head':value['head']['sha']}
                return None
            return self.store.once(key, lambda:self.gh.api(endpoint+'/merge', 'PUT', {'sha':args['head'],'merge_method':'merge'}), read_merge)
        if op == 'open_pr':
            branch = self.gh.api(f'repos/{repo}/branches/{quote(args["head_branch"], safe="")}')
            if branch['commit']['sha'] != args['head']:
                raise Blocked('待发布分支head已变化')
            commit = self.gh.api(f'repos/{repo}/commits/{args["head"]}')
            if not commit['author'] or commit['author']['login'] != self.actor:
                raise Blocked('已准备分支的head提交作者未关联执行账号')
            def read_pr():
                matches = [p for p in self.gh.pages(f'repos/{repo}/pulls?state=all')
                           if p['head']['ref'] == args['head_branch'] and p['base']['ref'] == args['base']]
                if len(matches) > 1:
                    raise Blocked('分支已有多个PR，需要明确处理对象')
                if matches:
                    p = matches[0]
                    if p['user']['login'] != self.actor or p['head']['sha'] != args['head'] or p['title'] != args['title'] or p['draft'] != args['draft'] or (p['body'] or '').replace('\r\n','\n') != (args['body']+'\n\n'+marker).replace('\r\n','\n'):
                        raise Blocked('分支已有不同PR，禁止重复发布')
                    return {'url':p['html_url'],'head':p['head']['sha']}
                return None
            return self.store.once(key, lambda:self.gh.api(f'repos/{repo}/pulls', 'POST', {'head':args['head_branch'],'base':args['base'],'title':args['title'],'body':args['body']+'\n\n'+marker,'draft':args['draft']}), read_pr)
        raise Blocked('未知操作')

    def inventory(self):
        result = {}
        for repo in [self.own, self.peer]:
            owner, name = repo.split('/')
            query = 'query($o:String!,$n:String!,$cursor:String){repository(owner:$o,name:$n){discussions(first:100,after:$cursor){pageInfo{hasNextPage endCursor}nodes{id number url body author{login} category{isAnswerable} answer{id author{login}}}}}}'
            discussions = self.connection(query, {'o':owner,'n':name}, lambda d:d['repository']['discussions'])
            for d in discussions:
                d['comments'] = self.thread_comments(d['id'])
            result[repo] = {'open_prs':self.gh.pages(f'repos/{repo}/pulls?state=open'), 'discussions':discussions}
        atomic_json(self.state / 'inventory.json', {'scanned_at':self.clock().isoformat(),'repositories':result})
        return {repo:{'open_prs':len(data['open_prs']),'discussions':len(data['discussions'])} for repo,data in result.items()}

    def cycle(self):
        started = time.monotonic()
        previous = self.state/'status.json'
        last_success = json.loads(previous.read_text(encoding='utf-8')).get('last_scan_success_at') if previous.exists() else None
        status = {'version':VERSION,'actor':self.actor,'started_at':self.clock().isoformat(),'last_scan_success_at':last_success,'apply':self.apply,'jobs':[]}
        atomic_json(self.state / 'status.json', status)
        if (self.state / 'PAUSE').exists():
            status.update(state='paused', finished_at=self.clock().isoformat())
            atomic_json(self.state / 'status.json', status)
            return status
        self.identity()
        issues = self.gh.pages(f'repos/{HUB}/issues?state=open&assignee={self.actor}')
        # A successful close can lose its response. Reconcile applied jobs even if the
        # queue issue has disappeared from the open list; do not redo the operation.
        present = {i['number'] for i in issues}
        for (key,) in self.store.db.execute('SELECT key FROM jobs WHERE status=?', ('applied',)).fetchall():
            number = int(key.rsplit('#',1)[1])
            if number not in present:
                issues.append(self.gh.api(f'repos/{HUB}/issues/{number}'))
        for issue in sorted(issues, key=lambda i:i['number']):
            if 'pull_request' in issue:
                continue
            key = f'{HUB}#{issue["number"]}'
            item = {'issue':issue['html_url']}
            status['jobs'].append(item)
            try:
                if time.monotonic() - started >= 20 * 60:
                    item.update(state='deferred', detail='本轮运行已达20分钟，下次半小时轮询优先从未完成对象继续')
                    continue
                if LABEL not in {l['name'] for l in issue['labels']}:
                    item.update(state='needs_manifest', detail='现有自然语言交接，不属于结构化执行队列')
                    continue
                if issue['user']['login'] not in self.config['trusted_authors']:
                    raise Blocked('任务作者不在本机信任列表')
                # Re-read the actual source immediately before claiming the job.
                previous_job = self.store.job(key)
                already_applied = previous_job and previous_job['status'] == 'applied'
                current, task = self.assigned_task(issue['number'], allow_closed=bool(already_applied))
                task_digest = digest(json.dumps(task, sort_keys=True, ensure_ascii=False))
                if not self.can_write():
                    item.update(state='planned', operation=task['operation'])
                    continue
                self.store.bind(key, task_digest, self.actor+':'+task['id'])
                effect_key = key + ':' + task_digest
                if already_applied:
                    result = previous_job['detail']
                else:
                    result = self.execute(task, effect_key, issuer=current['user']['login'])
                    self.store.record(key, 'applied', result)
                self.comment_effect(effect_key+':receipt', HUB, issue['number'], receipt_body(result))
                endpoint = f'repos/{HUB}/issues/{issue["number"]}'
                self.store.once(effect_key+':close', lambda:self.gh.api(endpoint,'PATCH',{'state':'closed'}),
                                lambda:True if self.gh.api(endpoint)['state'] == 'closed' else None)
                self.store.record(key, 'done', result)
                item.update(state='done', result=result)
            except (Blocked, ApiError) as exc:
                item.update(state='blocked', detail=str(exc))
                saved = self.store.job(key)
                if not saved or saved['status'] != 'applied':
                    self.store.record(key, 'blocked', {'reason':str(exc)})
                logging.warning('%s: %s', key, exc)
            finally:
                atomic_json(self.state/'status.json', status)
        status.update(state='read_only' if not self.apply else 'attention' if any(j['state'] != 'done' for j in status['jobs']) else 'complete',
                      inventory=self.inventory(), finished_at=self.clock().isoformat())
        status['last_scan_success_at'] = status['finished_at']
        if self.can_write():
            status['health_issue'] = self.publish_health(status)
        atomic_json(self.state / 'status.json', status)
        return status

    def publish_health(self, status):
        title = 'worker-health/' + self.actor
        identity_file = self.state/'health-issue.json'
        def find_health():
            if identity_file.exists():
                number = json.loads(identity_file.read_text(encoding='utf-8'))['number']
                candidate = self.gh.api(f'repos/{HUB}/issues/{number}')
                if candidate['title'] != title or candidate['user']['login'] != self.actor:
                    raise Blocked('持久保存的健康状态Issue身份不匹配')
                return candidate
            matches = [i for i in self.gh.pages(f'repos/{HUB}/issues?state=all')
                       if i['title'] == title and i['user']['login'] == self.actor and 'pull_request' not in i]
            if len(matches) > 1:
                raise Blocked('存在多个同名健康状态Issue')
            if matches:
                atomic_json(identity_file, {'number':matches[0]['number']})
                return matches[0]
            return None
        def create_health():
            created = self.gh.api(f'repos/{HUB}/issues','POST',{'title':title,'body':'worker正在初始化。'})
            atomic_json(identity_file, {'number':created['number']})
        health = self.store.once('health-create:'+self.actor, create_health, find_health)
        body = f'无模型 GitHub worker {VERSION}\n\n执行身份：{self.actor}\n最后成功全量轮询：{status["finished_at"]}\n轮询状态：{status["state"]}\n周期：Windows后台任务每30分钟；09:00–23:00北京时间允许写入。\n\n'
        body += '本页时间长期未更新表示需要检查B电脑、Windows任务历史、网络或本地日志；不依赖Codex。轮询完成不代表技术任务或四项验收全部完成。\n\n'
        for job in status['jobs']:
            body += f'- {job["issue"]}：{job["state"]}；{job.get("detail", "已回读" if job["state"]=="done" else "待执行")}\n'
            if len(body) > 55000:
                body += '\n更多对象见本机status.json；此处仅截短展示，不截断执行队列。\n'
                break
        body += '\n扫描数量：\n```json\n'+json.dumps(status['inventory'],ensure_ascii=False,indent=2)+'\n```'
        endpoint = f'repos/{HUB}/issues/{health["number"]}'
        def read_health():
            value = self.gh.api(endpoint)
            return {'url':value['html_url']} if value['body'].replace('\r\n','\n') == body else None
        return self.store.once('health-update:'+digest(body), lambda:self.gh.api(endpoint,'PATCH',{'body':body}), read_health)['url']


def load_worker(path, apply=False):
    config_path = Path(path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    state = Path(config.get('state_dir', '../.local/worker-' + config['actor']))
    if not state.is_absolute():
        state = (config_path.parent / state).resolve()
    return Worker(config, state, apply=apply)


def enqueue(worker, task):
    worker.identity()
    parse_task('```collab-task\n'+json.dumps(task)+'\n```')
    title = f'worker/{task["actor"]}/{task["id"]}'
    for issue in worker.gh.pages(f'repos/{HUB}/issues?state=all'):
        if issue['title'] == title:
            if parse_task(issue['body']) != task:
                raise Blocked('任务id已用于其他内容')
            return {'url':issue['html_url'],'existing':True}
    labels = worker.gh.pages(f'repos/{HUB}/labels')
    if LABEL not in {l['name'] for l in labels}:
        worker.gh.api(f'repos/{HUB}/labels', 'POST', {'name':LABEL,'color':'0366d6','description':'Structured jobs for the model-free gh worker'})
    body = '结构化任务；执行身份由Assignee和actor共同指定。内容与判断由任务发布者提供。\n\n```collab-task\n'+json.dumps(task,ensure_ascii=False,indent=2)+'\n```'
    if len(body) > 65000:
        raise Blocked('序列化任务正文超过GitHub Issue大小限制')
    # A lost create response is recovered by the stable title on the next invocation.
    issue = worker.gh.api(f'repos/{HUB}/issues','POST',{'title':title,'body':body,'assignees':[task['actor']],'labels':[LABEL]})
    check = worker.gh.api(f'repos/{HUB}/issues/{issue["number"]}')
    if parse_task(check['body']) != task or task['actor'] not in {a['login'] for a in check['assignees']}:
        raise Blocked('新任务回读不匹配')
    return {'url':check['html_url']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['once','doctor','status','enqueue','inspect-pr','inspect-discussion','retry-uncertain','recover-comment'])
    parser.add_argument('--config', required=True)
    parser.add_argument('--apply', action='store_true', help='allow writes during 09:00–23:00 Beijing time')
    parser.add_argument('--file')
    parser.add_argument('--repo', choices=[HUB,*REPOS.values()])
    parser.add_argument('--number', type=int)
    parser.add_argument('--effect-key')
    parser.add_argument('--confirm-not-applied', action='store_true')
    args = parser.parse_args()
    worker = load_worker(args.config, args.apply)
    handler = RotatingFileHandler(worker.state/'worker.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[handler], format='%(asctime)s %(levelname)s %(message)s')
    try:
        with exclusive(worker.state/'worker.lock'):
            if args.command == 'status':
                value = json.loads((worker.state/'status.json').read_text(encoding='utf-8'))
            elif args.command == 'doctor':
                value = {'version':VERSION,'login':worker.identity(),'state_dir':str(worker.state),'write_window_open':in_window(now()),'paused':(worker.state/'PAUSE').exists()}
                value['repositories'] = {}
                for repo in [HUB,worker.own,worker.peer]:
                    metadata = worker.gh.api('repos/'+repo)
                    push = metadata.get('permissions', {}).get('push', False)
                    value['repositories'][repo] = {'push':push}
                    if not push:
                        raise Blocked('本机账号缺少仓库写权限: ' + repo)
            elif args.command == 'once':
                value = worker.cycle()
            elif args.command == 'recover-comment':
                if not args.number or args.number <= 0:
                    raise Blocked('需要待恢复任务的正整数 --number')
                value = worker.recover_comment(args.number)
            elif args.command == 'enqueue':
                if not args.file:
                    raise Blocked('enqueue需要 --file')
                value = enqueue(worker, json.loads(Path(args.file).read_text(encoding='utf-8-sig')))
            elif args.command == 'retry-uncertain':
                if not args.effect_key or not args.confirm_not_applied:
                    raise Blocked('仅在回查远端确认未执行后，提供 --effect-key 和 --confirm-not-applied')
                cursor = worker.store.db.execute('DELETE FROM effects WHERE key=? AND state=?', (args.effect_key,'sent'))
                worker.store.db.commit()
                value = {'cleared_uncertain_effects':cursor.rowcount,'effect_key':args.effect_key}
            elif args.command == 'inspect-pr':
                if not args.repo or not args.number:
                    raise Blocked('需要 --repo 和 --number')
                worker.identity()
                pr = worker.gh.api(f'repos/{args.repo}/pulls/{args.number}')
                value = {'repo':args.repo,'number':args.number,'head':pr['head']['sha'],'diff_sha256':digest(worker.gh.api(f'repos/{args.repo}/pulls/{args.number}',raw=True))}
            else:
                if not args.repo or not args.number:
                    raise Blocked('需要 --repo 和 --number')
                worker.identity()
                d = worker.discussion(args.repo,args.number)
                value = {'id':d['id'],'question_sha256':digest(d['body']),'answer':d['answer'],'comments':worker.thread_comments(d['id'])}
                for c in value['comments']:
                    c['answer_sha256'] = digest(c['body'])
                    for reply in c['replies']:
                        reply['answer_sha256'] = digest(reply['body'])
        print(json.dumps(value,ensure_ascii=False,indent=2))
        if args.command == 'recover-comment' and args.apply and not value['completed']:
            return 1
        return 0
    except Busy as exc:
        print(str(exc))
        return 2 if args.command == 'recover-comment' else 0
    except (Blocked, ApiError, OSError, ValueError) as exc:
        logging.error('%s', exc)
        status_path = worker.state/'status.json'
        error_status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
        error_status.update(actor=worker.actor,state='error',at=now().isoformat(),detail=str(exc))
        atomic_json(status_path, error_status)
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        worker.store.db.close()


if __name__ == '__main__':
    sys.exit(main())
