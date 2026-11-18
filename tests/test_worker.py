import importlib.util
import json
import sqlite3
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

MODULE = Path(__file__).resolve().parents[1] / 'worker' / 'collab_worker.py'
spec = importlib.util.spec_from_file_location('worker', MODULE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
A, B = 'lw-liuwang', 'ZicongHe2002'
HEAD, JOINT = 'a' * 40, 'b' * 40
DIFF = b'diff --git a/note.md b/note.md\n+corrected example\n'


def task(operation, args, actor=A):
    return {'version':1, 'id':'example-0001', 'actor':actor, 'operation':operation, 'args':args}


def manifest(value):
    return '```collab-task\n' + json.dumps(value) + '\n```'


class FakeGh:
    def __init__(self):
        self.login = A
        self.gets, self.lists = {}, {}
        self.calls = []
        self.query = Mock()
        self.mutate = Mock()
        self.lose_comment_response = False

    def api(self, endpoint, method='GET', data=None, raw=False):
        self.calls.append((endpoint, method, data))
        if endpoint == 'user':
            return {'login':self.login}
        if raw:
            return DIFF
        if method == 'POST' and endpoint.endswith('/comments'):
            comments = self.lists.setdefault(endpoint, [])
            comments.append({'user':{'login':self.login}, 'body':data['body'], 'html_url':'https://example/comment/1'})
            if self.lose_comment_response:
                self.lose_comment_response = False
                raise w.ApiError('lost response')
            return comments[-1]
        if method == 'PUT' and endpoint.endswith('/merge'):
            self.gets[endpoint[:-6]].update(merged=True,merge_commit_sha='c'*40,state='closed')
            return {'merged':True,'sha':'c'*40}
        if method == 'PATCH':
            self.gets[endpoint].update(data)
            return self.gets[endpoint]
        if method == 'GET':
            return self.gets[endpoint]
        raise AssertionError((endpoint,method,data))

    def pages(self, endpoint):
        self.calls.append((endpoint,'PAGES',None))
        if endpoint.startswith(f'repos/{w.HUB}/issues?state=open&assignee='):
            return [i for key,i in self.gets.items() if key.startswith(f'repos/{w.HUB}/issues/') and key.rsplit('/',1)[-1].isdigit() and i['state']=='open']
        return self.lists.get(endpoint, [])


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.gh = FakeGh()
        self.worker = w.Worker({'actor':A,'trusted_authors':[A,B]}, self.temp.name, self.gh, apply=True,
                               clock=lambda:datetime.fromisoformat('2026-11-18T10:00:00+08:00'))

    def tearDown(self):
        self.worker.store.db.close()
        self.temp.cleanup()

    def args_pr(self):
        return {'repo':w.REPOS[A], 'number':1, 'head':HEAD, 'diff_sha256':w.digest(DIFF)}

    def setup_pr(self):
        self.gh.gets[f'repos/{w.REPOS[A]}/pulls/1'] = {'head':{'sha':HEAD}, 'state':'open', 'draft':False,
            'body':'a technical contribution', 'labels':[], 'user':{'login':B}, 'merged':False}

    def test_strict_manifest(self):
        valid = task('issue_comment', {'repo':w.HUB,'number':1,'body':'hello'})
        self.assertEqual(w.parse_task(manifest(valid)), valid)
        for body in ['please merge', manifest(valid)+'\n'+manifest(valid), manifest({**valid,'command':'whoami'})]:
            with self.assertRaises(w.Blocked):
                w.parse_task(body)
        valid['args']['repo'] = 'outsider/repo'
        with self.assertRaises(w.Blocked):
            w.parse_task(manifest(valid))
        valid['actor'] = []
        with self.assertRaises(w.Blocked):
            w.parse_task(manifest(valid))

    def test_identity_does_not_switch_accounts(self):
        self.gh.login = B
        with self.assertRaises(w.Blocked):
            self.worker.identity()
        self.assertEqual(self.gh.calls, [('user','GET',None)])

    def test_window_uses_beijing_time(self):
        self.assertFalse(w.in_window(datetime.fromisoformat('2026-11-18T00:59:59+00:00')))
        self.assertTrue(w.in_window(datetime.fromisoformat('2026-11-18T01:00:00+00:00')))
        self.assertTrue(w.in_window(datetime.fromisoformat('2026-11-18T14:59:59+00:00')))
        self.assertFalse(w.in_window(datetime.fromisoformat('2026-11-18T15:00:00+00:00')))

    def test_pause_survives_new_worker(self):
        (Path(self.temp.name)/'PAUSE').touch()
        self.assertFalse(self.worker.can_write())
        status = self.worker.cycle()
        self.assertEqual(status['state'],'paused')
        self.assertEqual(self.gh.calls,[])

    def test_rest_pagination_exceeds_100(self):
        gh = object.__new__(w.Gh)
        gh.api = Mock(side_effect=[list(range(100)), [100,101]])
        self.assertEqual(gh.pages('repos/a/b/issues?state=open'),list(range(102)))
        self.assertIn('page=2',gh.api.call_args.args[0])

    def test_graphql_pagination(self):
        self.gh.query.side_effect = [
            {'list':{'nodes':[1],'pageInfo':{'hasNextPage':True,'endCursor':'next'}}},
            {'list':{'nodes':[2],'pageInfo':{'hasNextPage':False,'endCursor':None}}}]
        self.assertEqual(self.worker.connection('query',{},lambda d:d['list']),[1,2])
        self.assertEqual(self.gh.query.call_args.args[1]['cursor'],'next')

    def test_duplicate_comment_after_lost_response_is_recovered(self):
        self.gh.lose_comment_response = True
        self.worker.comment_effect('job-one',w.HUB,1,'hello')
        self.worker.comment_effect('job-one',w.HUB,1,'hello')
        self.assertEqual(sum(method=='POST' for _,method,_ in self.gh.calls),1)

    def test_uncertain_write_is_not_blindly_retried_after_restart(self):
        self.worker.store.db.execute('INSERT INTO effects VALUES (?,?)',('crashed','sent'))
        self.worker.store.db.commit()
        self.worker.store.db.close()
        self.worker.store = w.Store(Path(self.temp.name)/'worker.sqlite3')
        write = Mock()
        with self.assertRaises(w.Blocked):
            self.worker.store.once('crashed',write,lambda:None)
        write.assert_not_called()

    def test_rejected_api_write_can_retry(self):
        write = Mock(side_effect=w.ApiError('forbidden',403))
        with self.assertRaises(w.ApiError):
            self.worker.store.once('rejected',write,lambda:None)
        self.assertIsNone(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',('rejected',)).fetchone())

    def test_window_closing_does_not_poison_effect_ledger(self):
        with self.assertRaises(w.Blocked):
            self.worker.store.once('window',Mock(side_effect=w.Blocked('window closed')),lambda:None)
        self.assertIsNone(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',('window',)).fetchone())

    def test_changed_claimed_task_cannot_change_semantics(self):
        self.worker.store.bind('job','digest1')
        with self.assertRaises(w.Blocked):
            self.worker.store.bind('job','digest2')

    def test_same_task_id_in_two_issues_cannot_execute_twice(self):
        self.worker.store.bind('issue1','digest','actor:unique-id')
        with self.assertRaises(w.Blocked):
            self.worker.store.bind('issue2','digest','actor:unique-id')

    def test_raw_api_disallows_writes_outside_window(self):
        gh = object.__new__(w.Gh)
        gh.executable = 'gh'
        gh.can_write = lambda:False
        with patch.object(w.subprocess,'run') as command:
            with self.assertRaises(w.Blocked):
                gh.api('repos/a/b/issues', 'POST', {'body':'test'})
            command.assert_not_called()

    def test_full_inventory_reads_nested_reply_bodies(self):
        d = {'id':'discussion','number':1}
        c = {'id':'comment','body':'answer','author':{'login':B}}
        self.worker.comments = Mock(return_value=[c])
        self.worker.connection = Mock(side_effect=lambda query,variables,extract:
            [{'id':'reply','body':'new followup','author':{'login':A}}] if 'replies(first' in query else [dict(d)])
        self.worker.inventory()
        result = json.loads((Path(self.temp.name)/'inventory.json').read_text(encoding='utf-8'))
        self.assertEqual(result['repositories'][w.REPOS[A]]['discussions'][0]['comments'][0]['replies'][0]['body'],'new followup')

    def test_review_submission_binds_head_and_reconciles_lost_reply(self):
        self.setup_pr()
        endpoint = f'repos/{w.REPOS[A]}/pulls/1/reviews'
        original_api = self.gh.api
        def submit(endpoint_arg, method='GET', data=None, raw=False):
            if endpoint_arg == endpoint and method == 'POST':
                self.gh.lists[endpoint] = [{'id':1,'html_url':'review-url','user':{'login':A},
                    'commit_id':data['commit_id'],'state':'APPROVED','body':data['body']}]
                raise w.ApiError('lost response')
            return original_api(endpoint_arg,method,data,raw)
        self.gh.api = Mock(side_effect=submit)
        args = {**self.args_pr(),'event':'APPROVE','body':'A supplied this exact content review decision'}
        result = self.worker.execute(task('review_pr',args),'review',issuer=A)
        self.assertEqual(result['commit_id'],HEAD)
        self.worker.execute(task('review_pr',args),'review',issuer=A)
        self.assertEqual(sum(c.args[0]==endpoint and c.args[1]=='POST' for c in self.gh.api.call_args_list if len(c.args)>1),1)

    def test_prepared_branch_creates_pr_and_recovers_without_duplicate(self):
        repo = w.REPOS[B]
        args = {'repo':repo,'head_branch':'topic','head':HEAD,'base':'main','title':'A complete note','body':'Prepared content with B supplement task','draft':False}
        self.gh.gets[f'repos/{repo}/branches/topic'] = {'commit':{'sha':HEAD}}
        self.gh.gets[f'repos/{repo}/commits/{HEAD}'] = {'author':{'login':A}}
        original_api = self.gh.api
        def create(endpoint,method='GET',data=None,raw=False):
            if endpoint == f'repos/{repo}/pulls' and method == 'POST':
                self.gh.lists[f'repos/{repo}/pulls?state=all'] = [{'head':{'ref':'topic','sha':HEAD},'base':{'ref':'main'},
                    'user':{'login':A},'body':data['body'],'title':data['title'],'draft':data['draft'],'html_url':'pr-url'}]
                return {}
            return original_api(endpoint,method,data,raw)
        self.gh.api = Mock(side_effect=create)
        result = self.worker.execute(task('open_pr',args),'open',issuer=A)
        self.assertEqual(result,{'url':'pr-url','head':HEAD})
        self.worker.execute(task('open_pr',args),'open',issuer=A)
        self.assertEqual(sum(c.args[0]==f'repos/{repo}/pulls' and c.args[1]=='POST' for c in self.gh.api.call_args_list if len(c.args)>1),1)

    def test_edited_remote_comment_does_not_create_replacement(self):
        self.worker.comment_effect('job',w.HUB,1,'hello')
        self.gh.lists[f'repos/{w.HUB}/issues/1/comments'][0]['body'] = 'changed\n<!-- collab-worker:job -->'
        with self.assertRaises(w.Blocked):
            self.worker.comment_effect('job',w.HUB,1,'hello')
        self.assertEqual(sum(method=='POST' for _,method,_ in self.gh.calls),1)

    def test_new_head_and_yolo_block_normal_review(self):
        self.setup_pr()
        args = {**self.args_pr(),'event':'APPROVE','body':'content decision supplied in this job'}
        pr = self.gh.gets[f'repos/{w.REPOS[A]}/pulls/1']
        for changes in [{'head':{'sha':'d'*40}}, {'head':{'sha':HEAD},'body':'mode=yolo'}]:
            pr.update(changes)
            with self.assertRaises(w.Blocked):
                self.worker.execute(task('review_pr',args),'review',issuer=A)
        self.assertFalse(any(m=='POST' for _,m,_ in self.gh.calls))

    def test_diff_drift_is_blocked(self):
        self.setup_pr()
        with self.assertRaises(w.Blocked):
            self.worker.checked_pr({**self.args_pr(),'diff_sha256':'0'*64})

    def test_cannot_approve_own_pr(self):
        self.setup_pr()
        self.gh.gets[f'repos/{w.REPOS[A]}/pulls/1']['user']['login'] = A
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('review_pr',{**self.args_pr(),'event':'APPROVE','body':'review'}),'self',issuer=A)

    def joint_query(self, authors):
        self.gh.query.return_value = {'repository':{'pullRequest':{'commits':{'pageInfo':{'hasNextPage':False},'nodes':[
            {'commit':{'oid':JOINT,'authors':{'pageInfo':{'hasNextPage':False},'nodes':[{'user':{'login':a}} for a in authors]}}}]}}}}

    def test_merge_requires_same_associated_joint_commit(self):
        self.setup_pr()
        self.joint_query([A])
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('merge_pr',{**self.args_pr(),'joint_commit':JOINT}),'merge',issuer=B)
        self.assertFalse(any(m=='PUT' for _,m,_ in self.gh.calls))

    def test_merge_binds_head_and_reads_merge_commit(self):
        self.setup_pr()
        self.joint_query([A,B])
        self.gh.lists[f'repos/{w.REPOS[A]}/pulls/1/reviews'] = [{'user':{'login':A},'state':'APPROVED','commit_id':HEAD}]
        result = self.worker.execute(task('merge_pr',{**self.args_pr(),'joint_commit':JOINT}),'merge',issuer=B)
        self.assertEqual(result,{'merge_commit_sha':'c'*40,'head':HEAD})
        payload = next(data for _,method,data in self.gh.calls if method=='PUT')
        self.assertEqual(payload,{'sha':HEAD,'merge_method':'merge'})

    def test_old_head_approval_cannot_merge_new_head(self):
        self.setup_pr()
        self.joint_query([A,B])
        self.gh.lists[f'repos/{w.REPOS[A]}/pulls/1/reviews'] = [{'user':{'login':A},'state':'APPROVED','commit_id':'e'*40}]
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('merge_pr',{**self.args_pr(),'joint_commit':JOINT}),'merge',issuer=B)

    def test_ci_rerun_cannot_use_old_success(self):
        self.worker.config['required_checks'] = {w.REPOS[A]:['test']}
        endpoint = f'repos/{w.REPOS[A]}/commits/{HEAD}'
        self.gh.gets[endpoint+'/check-runs?per_page=100&page=1&filter=latest'] = {'check_runs':[
            {'name':'test','status':'in_progress','conclusion':None},
            {'name':'test','status':'completed','conclusion':'success'}]}
        with self.assertRaises(w.Blocked):
            self.worker.require_checks(self.args_pr())

    def test_failing_status_cannot_hide_behind_same_named_check(self):
        self.worker.config['required_checks'] = {w.REPOS[A]:['test']}
        endpoint = f'repos/{w.REPOS[A]}/commits/{HEAD}'
        self.gh.gets[endpoint+'/check-runs?per_page=100&page=1&filter=latest'] = {'check_runs':[
            {'name':'test','status':'completed','conclusion':'success'}]}
        self.gh.lists[endpoint+'/statuses'] = [{'context':'test','state':'failure'},{'context':'test','state':'success'}]
        with self.assertRaises(w.Blocked):
            self.worker.require_checks(self.args_pr())

    def test_cycle_time_budget_defers_remaining_jobs(self):
        self.gh.gets[f'repos/{w.HUB}/issues/1'] = {'number':1,'html_url':'queue-1','state':'open'}
        self.worker.inventory = Mock(return_value={})
        self.worker.publish_health = Mock(return_value='health')
        with patch.object(w.time,'monotonic',side_effect=[0,1201]):
            result = self.worker.cycle()
        self.assertEqual(result['jobs'][0]['state'],'deferred')
        self.assertEqual(result['state'],'attention')

    def test_foreign_content_cannot_be_published_as_own_contribution(self):
        args = {'repo':w.REPOS[B],'number':1,'question_sha256':'0'*64,'body':'answer'}
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('discussion_reply',args),'reply',issuer=B)

    def setup_answer(self):
        d = {'id':'discussion','body':'question','author':{'login':A},'category':{'isAnswerable':True},'answer':None}
        answer = {'id':'answer','body':'correct answer','author':{'login':B},'discussion':{'id':'discussion'}}
        self.worker.discussion = Mock(side_effect=lambda repo,number:d)
        self.gh.query.return_value = {'node':answer}
        self.gh.mutate.side_effect = lambda query,variables:d.update(answer={'id':'answer','author':{'login':B}})
        args = {'repo':w.REPOS[A],'number':1,'question_sha256':w.digest('question'),'comment_id':'answer',
                'answer_sha256':w.digest('correct answer'),'expected_author':B}
        return d,answer,args

    def test_accept_reads_answer_node_and_author(self):
        _,_,args = self.setup_answer()
        result = self.worker.execute(task('accept_answer',args),'accept',issuer=A)
        self.assertEqual(result,{'id':'answer','author':{'login':B}})
        self.worker.execute(task('accept_answer',args),'accept',issuer=A)
        self.gh.mutate.assert_called_once()

    def test_answer_changed_or_already_accepted_other_is_preserved(self):
        d,answer,args = self.setup_answer()
        answer['body'] = 'edited'
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('accept_answer',args),'accept',issuer=A)
        answer['body'] = 'correct answer'
        d['answer'] = {'id':'other'}
        with self.assertRaises(w.Blocked):
            self.worker.execute(task('accept_answer',args),'accept',issuer=A)
        self.gh.mutate.assert_not_called()

    def test_cycle_recovers_write_closes_task_and_does_not_duplicate(self):
        value = task('issue_comment',{'repo':w.REPOS[B],'number':2,'body':'a concrete operational note'})
        issue = {'number':9,'html_url':'https://example/queue/9','body':manifest(value),'user':{'login':B},
                 'labels':[{'name':w.LABEL}],'assignees':[{'login':A}],'state':'open'}
        self.gh.gets[f'repos/{w.HUB}/issues/9'] = issue
        self.gh.lose_comment_response = True
        self.worker.inventory = Mock(return_value={})
        self.worker.publish_health = Mock(return_value='https://example/health')
        first = self.worker.cycle()
        second = self.worker.cycle()
        self.assertEqual(first['jobs'][0]['state'],'done')
        self.assertEqual(second['jobs'],[])
        self.assertEqual(issue['state'],'closed')
        self.assertEqual(len(self.gh.lists[f'repos/{w.REPOS[B]}/issues/2/comments']),1)
        self.assertEqual(len(self.gh.lists[f'repos/{w.HUB}/issues/9/comments']),1)

    def test_lost_close_response_recovers_closed_queue_without_redoing_work(self):
        value = task('issue_comment',{'repo':w.REPOS[B],'number':2,'body':'one operational note'})
        issue = {'number':9,'html_url':'queue9','body':manifest(value),'user':{'login':B},'labels':[{'name':w.LABEL}],
                 'assignees':[{'login':A}],'state':'open'}
        endpoint = f'repos/{w.HUB}/issues/9'
        self.gh.gets[endpoint] = issue
        original_api = self.gh.api
        closure_pending = [False]
        def lose_close(endpoint_arg, method='GET', data=None, raw=False):
            if endpoint_arg == endpoint and method == 'PATCH':
                result = original_api(endpoint_arg,method,data,raw)
                closure_pending[0] = True
                raise w.ApiError('lost close response')
            if endpoint_arg == endpoint and method == 'GET' and closure_pending[0]:
                closure_pending[0] = False
                raise w.ApiError('read outage immediately after close')
            return original_api(endpoint_arg,method,data,raw)
        self.gh.api = Mock(side_effect=lose_close)
        self.worker.inventory = Mock(return_value={})
        self.worker.publish_health = Mock(return_value='health')
        first = self.worker.cycle()
        self.assertEqual(first['jobs'][0]['state'],'blocked')
        self.assertEqual(issue['state'],'closed')
        self.assertEqual(self.worker.store.job(f'{w.HUB}#9')['status'],'applied')
        self.worker.execute = Mock(side_effect=AssertionError('must not redo applied action'))
        second = self.worker.cycle()
        self.assertEqual(second['jobs'][0]['state'],'done')
        self.worker.execute.assert_not_called()
        self.assertEqual(len(self.gh.lists[f'repos/{w.REPOS[B]}/issues/2/comments']),1)

    def test_health_creation_reads_direct_id_before_list_index_catches_up(self):
        original_api = self.gh.api
        def create(endpoint,method='GET',data=None,raw=False):
            if endpoint == f'repos/{w.HUB}/issues' and method == 'POST':
                issue = {'number':99,'title':data['title'],'body':data['body'],'user':{'login':A},'html_url':'health99'}
                self.gh.gets[f'repos/{w.HUB}/issues/99'] = issue
                return issue
            return original_api(endpoint,method,data,raw)
        self.gh.api = Mock(side_effect=create)
        result = self.worker.publish_health({'finished_at':'2026-11-18T10:00:00+08:00','state':'complete','jobs':[],'inventory':{}})
        self.assertEqual(result,'health99')
        self.assertTrue((Path(self.temp.name)/'health-issue.json').exists())

    def test_legacy_and_untrusted_jobs_are_not_executed(self):
        for number, labels, author in [(1,[],B),(2,[{'name':w.LABEL}],'outsider')]:
            self.gh.gets[f'repos/{w.HUB}/issues/{number}'] = {'number':number,'html_url':str(number),'body':'please merge',
                'user':{'login':author},'labels':labels,'assignees':[{'login':A}],'state':'open'}
        self.worker.inventory = Mock(return_value={})
        self.worker.publish_health = Mock(return_value='health')
        result = self.worker.cycle()
        self.assertEqual([i['state'] for i in result['jobs']],['needs_manifest','blocked'])
        self.assertFalse(any(method in {'POST','PUT','PATCH'} for _,method,_ in self.gh.calls))

    def test_process_lock_rejects_second_worker(self):
        path = Path(self.temp.name)/'lock'
        with w.exclusive(path):
            with self.assertRaises(w.Blocked):
                with w.exclusive(path):
                    self.fail('second worker entered')

    def test_read_only_cycle_does_not_write_or_claim(self):
        self.worker.apply = False
        value = task('issue_comment',{'repo':w.REPOS[B],'number':2,'body':'note'})
        self.gh.gets[f'repos/{w.HUB}/issues/1'] = {'number':1,'html_url':'1','body':manifest(value),'user':{'login':B},
            'labels':[{'name':w.LABEL}],'assignees':[{'login':A}],'state':'open'}
        self.worker.inventory = Mock(return_value={})
        result = self.worker.cycle()
        self.assertEqual(result['jobs'][0]['state'],'planned')
        self.assertEqual(self.worker.store.db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
        self.assertFalse(any(method in {'POST','PUT','PATCH'} for _,method,_ in self.gh.calls))


class CommentRecoveryTests(unittest.TestCase):
    setUp = WorkerTests.setUp
    tearDown = WorkerTests.tearDown

    def prepare_recovery(self):
        value = task('issue_comment',{'repo':w.REPOS[B],'number':2,'body':'prepared operational note'})
        issue = {'number':9,'html_url':'queue9','body':manifest(value),'user':{'login':B},
                 'labels':[{'name':w.LABEL}],'assignees':[{'login':A}],'state':'open'}
        self.gh.gets[f'repos/{w.HUB}/issues/9'] = issue
        task_digest = w.digest(json.dumps(value,sort_keys=True,ensure_ascii=False))
        key = f'{w.HUB}#9'
        effect = key+':'+task_digest
        self.worker.store.bind(key,task_digest,A+':'+value['id'])
        self.worker.store.record(key,'blocked',{'reason':'old failed request'})
        self.worker.store.db.execute('INSERT INTO effects VALUES (?,?)',(effect,'sent'))
        self.worker.store.db.execute('INSERT INTO effects VALUES (?,?)',('unrelated-effect','sent'))
        self.worker.store.db.commit()
        self.worker.inventory = Mock(return_value={})
        self.worker.publish_health = Mock(return_value='health')
        return issue, value, key, effect

    def test_recovery_backs_up_and_retries_only_missing_comment(self):
        issue, value, key, effect = self.prepare_recovery()
        result = self.worker.recover_comment(9)
        self.assertTrue(result['completed'])
        self.assertEqual(result['recovered_effects'],[effect])
        self.assertEqual(issue['state'],'closed')
        self.assertEqual(len(self.gh.lists[f'repos/{w.REPOS[B]}/issues/2/comments']),1)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',('unrelated-effect',)).fetchone(),('sent',))
        backup = sqlite3.connect(result['backup'])
        try:
            self.assertEqual(backup.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))
        finally:
            backup.close()
        calls = len(self.gh.calls)
        second = self.worker.recover_comment(9)
        self.assertTrue(second['completed'])
        self.assertEqual(second['state'],'already_done')
        self.assertFalse(any(method=='POST' for _,method,_ in self.gh.calls[calls:]))

    def test_existing_remote_comment_is_reused_after_lost_response(self):
        issue, value, key, effect = self.prepare_recovery()
        endpoint = f'repos/{w.REPOS[B]}/issues/2/comments'
        self.gh.lists[endpoint] = [{'user':{'login':A},'body':value['args']['body']+'\n\n<!-- collab-worker:'+effect+' -->','html_url':'existing-operation'}]
        result = self.worker.recover_comment(9)
        self.assertTrue(result['completed'])
        self.assertEqual(result['recovered_effects'],[])
        self.assertFalse(any(e==endpoint and method=='POST' for e,method,_ in self.gh.calls))

    def test_missing_receipt_and_uncertain_close_are_recovered(self):
        issue, value, key, effect = self.prepare_recovery()
        operation = {'url':'existing-operation'}
        endpoint = f'repos/{w.REPOS[B]}/issues/2/comments'
        self.gh.lists[endpoint] = [{'user':{'login':A},'body':value['args']['body']+'\n\n<!-- collab-worker:'+effect+' -->','html_url':operation['url']}]
        self.worker.store.record(key,'applied',operation)
        for suffix in [':receipt',':close']:
            self.worker.store.db.execute('INSERT INTO effects VALUES (?,?)',(effect+suffix,'sent'))
        self.worker.store.db.commit()
        result = self.worker.recover_comment(9)
        self.assertTrue(result['completed'])
        self.assertEqual(result['recovered_effects'],[effect+':receipt',effect+':close'])
        self.assertEqual(len(self.gh.lists[endpoint]),1)

    def test_failed_remote_read_preserves_uncertain_ledger(self):
        issue, value, key, effect = self.prepare_recovery()
        self.gh.pages = Mock(side_effect=w.ApiError('read unavailable'))
        with self.assertRaises(w.ApiError):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))
        self.assertFalse((Path(self.temp.name)/'backups').exists())

    def test_changed_task_and_deleted_applied_comment_are_preserved(self):
        issue, value, key, effect = self.prepare_recovery()
        value['args']['body'] = 'edited task'
        issue['body'] = manifest(value)
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        value['args']['body'] = 'prepared operational note'
        issue['body'] = manifest(value)
        self.worker.store.record(key,'applied',{'url':'deleted-operation'})
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))

    def test_dry_run_pause_and_window_preserve_ledger(self):
        issue, value, key, effect = self.prepare_recovery()
        self.worker.apply = False
        self.assertEqual(self.worker.recover_comment(9)['state'],'planned')
        self.worker.apply = True
        pause = Path(self.temp.name)/'PAUSE'
        pause.touch()
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        pause.unlink()
        self.worker.clock = lambda:datetime.fromisoformat('2026-11-18T23:00:00+08:00')
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))
        self.assertFalse(any(method in {'POST','PATCH'} for _,method,_ in self.gh.calls))

    def test_duplicate_remote_comments_block_recovery(self):
        issue, value, key, effect = self.prepare_recovery()
        comment = {'user':{'login':A},'body':value['args']['body']+'\n\n<!-- collab-worker:'+effect+' -->','html_url':'duplicate'}
        self.gh.lists[f'repos/{w.REPOS[B]}/issues/2/comments'] = [comment,comment.copy()]
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))

    def test_recovery_rejects_wrong_identity_and_non_comment_tasks(self):
        issue, value, key, effect = self.prepare_recovery()
        self.gh.login = B
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.gh.login = A
        value = task('review_pr',{'repo':w.REPOS[A],'number':1,'head':HEAD,'diff_sha256':w.digest(DIFF),'event':'COMMENT','body':'prepared review'})
        issue['body'] = manifest(value)
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)

    def test_recovery_reports_new_write_failure_without_claiming_success(self):
        issue, value, key, effect = self.prepare_recovery()
        endpoint = f'repos/{w.REPOS[B]}/issues/2/comments'
        original = self.gh.api
        def fail_comment(endpoint_arg,method='GET',data=None,raw=False):
            if endpoint_arg == endpoint and method == 'POST':
                raise w.ApiError('HTTP 403',403)
            return original(endpoint_arg,method,data,raw)
        self.gh.api = Mock(side_effect=fail_comment)
        result = self.worker.recover_comment(9)
        self.assertFalse(result['completed'])
        self.assertEqual(result['state'],'blocked')
        self.assertIn('HTTP 403',result['detail']['detail'])
        self.assertEqual(issue['state'],'open')

    def test_recovery_preserves_ledger_when_source_changes_during_check(self):
        issue, value, key, effect = self.prepare_recovery()
        original = self.worker.assigned_task
        calls = []
        def change_before_retry(number,allow_closed=False):
            calls.append(number)
            if len(calls) == 2:
                edited = json.loads(json.dumps(value))
                edited['args']['body'] = 'different instruction'
                issue['body'] = manifest(edited)
            return original(number,allow_closed)
        self.worker.assigned_task = Mock(side_effect=change_before_retry)
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))
        self.assertFalse(any(method=='POST' for _,method,_ in self.gh.calls))

    def test_other_issue_claim_of_same_id_cannot_clear_uncertain_effect(self):
        issue, value, key, effect = self.prepare_recovery()
        self.worker.store.db.execute('UPDATE task_ids SET job_key=? WHERE id=?',('other-issue',A+':'+value['id']))
        self.worker.store.db.commit()
        with self.assertRaises(w.Blocked):
            self.worker.recover_comment(9)
        self.assertEqual(self.worker.store.db.execute('SELECT state FROM effects WHERE key=?',(effect,)).fetchone(),('sent',))


class RequestFailureTests(unittest.TestCase):
    def test_http_status_is_visible_without_raw_stderr(self):
        result = subprocess.CompletedProcess([],1,b'',b'gh: private payload secret-token-value (HTTP 403)')
        error = w.request_failure(result,'POST','repos/a/b/issues?private=hidden')
        self.assertEqual(error.status,403)
        self.assertIn('HTTP 403',str(error))
        self.assertIn('gh exit 1',str(error))
        self.assertNotIn('secret',str(error))
        self.assertNotIn('hidden',str(error))

    def test_transport_category_is_fixed_text(self):
        result = subprocess.CompletedProcess([],1,b'',b'dial tcp: lookup example: no such host; credential=secret')
        error = w.request_failure(result,'POST','graphql')
        self.assertIsNone(error.status)
        self.assertIn('category=dns',str(error))
        self.assertNotIn('credential',str(error))


if __name__ == '__main__':
    unittest.main()
