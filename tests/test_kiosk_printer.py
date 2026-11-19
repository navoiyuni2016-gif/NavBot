"""Real HTTP queue and credential tests; no Windows printer is invoked."""
import json
import sqlite3
import time
from pathlib import Path
from uuid import uuid4
from test_workflow import WorkflowAcceptance

class KioskPrinterAcceptance(WorkflowAcceptance):
    def ticket(self):return self.ok(self.public,'/api/ticket',{'key':str(uuid4()),'lang':'uz','section':0,'service':0,'print_capability':'native-v1'})
    def pair(self):return self.ok(self.client('admin'),'/api/admin/kiosk-printer',{'action':'pair'})
    def agent(self,credentials,**data):
        return self.public.request('/api/kiosk-printer/agent',{'worker_id':credentials['worker_id'],**data},headers={'Authorization':'Bearer '+credentials['token']})
    def poll(self,credentials,**data):
        code,result,_=self.agent(credentials,action='poll',ready=True,printer_name='Thermal 80mm',**data)
        self.assertEqual(code,200,result);return result['job']
    def acknowledge(self,credentials,job,state='spooled'):
        code,result,_=self.agent(credentials,action='ack',ticket_id=job['ticket_id'],claim=job['claim'],state=state)
        self.assertEqual(code,200,result)
    def test_default_browser_and_admin_only_pairing(self):
        ticket=self.ticket();self.assertEqual(ticket['print_mode'],'browser')
        self.assertEqual(self.public.request('/api/admin/kiosk-printer',{'action':'pair'})[0],401)
        self.assertEqual(self.client('manager').request('/api/admin/kiosk-printer',{'action':'pair'})[0],403)
        credentials=self.pair();metadata=self.ok(self.client('admin'),'/api/admin/kiosk-printer')
        self.assertEqual(metadata['mode'],'agent');self.assertNotIn(credentials['token'],json.dumps(metadata))
        self.assertEqual(self.agent({**credentials,'token':'wrong'},action='poll',ready=True)[0],401)
        self.assertEqual(self.public.request('/api/kiosk-printer/agent',{'action':'poll','ready':True})[0],401)
    def test_offline_prevents_ticket_and_native_queue_is_idempotent(self):
        credentials=self.pair();data={'key':str(uuid4()),'lang':'uz','section':0,'service':0,'print_capability':'native-v1'}
        self.assertEqual(self.public.request('/api/ticket',data)[0],503)
        self.assertEqual(self.public.request('/api/ticket',{k:v for k,v in data.items() if k!='print_capability'})[0],409)
        self.assertEqual(self.poll(credentials),None)
        first=self.ok(self.public,'/api/ticket',data);again=self.ok(self.public,'/api/ticket',data)
        self.assertEqual(first['id'],again['id']);self.assertEqual(first['print_mode'],'agent')
        job=self.poll(credentials);self.assertTrue(job['fresh']);self.assertEqual(job['ticket_id'],first['id'])
        self.assertEqual(job['receipt']['number'],first['code']);self.assertNotIn('student',json.dumps(job))
        repeated=self.poll(credentials);self.assertFalse(repeated['fresh']);self.assertEqual(repeated['claim'],job['claim'])
        other={**credentials,'worker_id':str(uuid4())};self.assertIsNone(self.poll(other))
        self.assertEqual(self.agent(credentials,action='ack',ticket_id=job['ticket_id'],claim='bad',state='spooled')[0],409)
        self.acknowledge(credentials,job);self.acknowledge(credentials,job);self.assertIsNone(self.poll(credentials))
    def test_interrupted_print_is_not_blindly_retried_and_operator_can_resolve(self):
        credentials=self.pair();self.poll(credentials);ticket=self.ticket();job=self.poll(credentials)
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:db.execute('UPDATE kiosk_print_jobs SET lease_until=0')
        replay=self.poll(credentials);self.assertEqual(replay['state'],'uncertain');self.assertFalse(replay['fresh']);self.assertEqual(replay['claim'],job['claim'])
        self.assertEqual(self.public.request('/api/ticket',{'key':str(uuid4()),'lang':'uz','section':0,'service':0,'print_capability':'native-v1'})[0],503)
        admin=self.client('admin')
        self.assertEqual(admin.request('/api/admin/kiosk-printer',{'action':'retry','ticket_id':ticket['id'],'reason':'Operator checked'})[0],400)
        self.ok(admin,'/api/admin/kiosk-printer',{'action':'retry','ticket_id':ticket['id'],'reason':'Operator checked','confirm_duplicate':True})
        retried=self.poll(credentials);self.assertNotEqual(retried['claim'],job['claim']);self.assertTrue(retried['fresh'])
        self.acknowledge(credentials,retried)
        self.ok(admin,'/api/admin/kiosk-printer',{'action':'browser'})
        self.assertEqual(self.agent(credentials,action='poll',ready=True)[0],401)
        self.assertEqual(self.ticket()['print_mode'],'browser')
    def test_lost_ack_can_resolve_uncertain_without_second_print(self):
        credentials=self.pair();self.poll(credentials);self.ticket();job=self.poll(credentials)
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:db.execute('UPDATE kiosk_print_jobs SET lease_until=0')
        replay=self.poll(credentials);self.assertFalse(replay['fresh'])
        # Local durable journal says it was already spooled, so acknowledge only.
        self.acknowledge(credentials,replay);self.assertIsNone(self.poll(credentials))
        self.assertEqual(self.ok(self.client('admin'),'/api/admin/kiosk-printer')['counts']['spooled'],1)
    def test_unavailable_printer_and_stale_heartbeat_refuse_new_tickets(self):
        credentials=self.pair()
        self.assertEqual(self.agent(credentials,action='poll',ready=False,printer_name='Microsoft Print to PDF')[0],200)
        data={'key':str(uuid4()),'lang':'uz','section':0,'service':0,'print_capability':'native-v1'}
        self.assertEqual(self.public.request('/api/ticket',data)[0],503)
        self.poll(credentials)
        with sqlite3.connect(Path(self.temp.name)/'test.sqlite3') as db:db.execute('UPDATE kiosk_printer SET last_seen=?',(int(time.time())-60,))
        self.assertEqual(self.public.request('/api/ticket',data)[0],503)
    def test_failed_job_requires_admin_action_and_credentials_are_redacted(self):
        credentials=self.pair();self.poll(credentials);ticket=self.ticket();job=self.poll(credentials);self.acknowledge(credentials,job,'failed')
        self.assertIsNone(self.poll(credentials))
        self.assertEqual(self.public.request('/api/ticket',{'key':str(uuid4()),'lang':'uz','section':0,'service':0,'print_capability':'native-v1'})[0],503)
        self.ok(self.client('admin'),'/api/admin/kiosk-printer',{'action':'cancel','ticket_id':ticket['id'],'reason':'Paper issue handled'})
        logs=json.dumps(self.ok(self.client('admin'),'/api/security/audit'))
        self.assertNotIn(credentials['token'],logs)
        self.assertNotIn('token_hash',json.dumps(self.ok(self.client('admin'),'/api/admin/kiosk-printer')))

for name in list(WorkflowAcceptance.__dict__):
    if name.startswith('test_') and name not in KioskPrinterAcceptance.__dict__:setattr(KioskPrinterAcceptance,name,None)
del WorkflowAcceptance
