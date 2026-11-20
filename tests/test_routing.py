from test_workflow import WorkflowAcceptance
from uuid import uuid4

class RoutingAcceptance(WorkflowAcceptance):
    def issue(self,section):
        return self.ok(self.public,'/api/ticket',{'key':str(uuid4()),'lang':'uz','section':section,'service':0})

    def test_five_independent_codes_and_operator_inboxes(self):
        tickets=[self.issue(i) for i in range(5)]
        self.assertEqual([t['code'] for t in tickets],['A-001','B-001','C-001','D-001','E-001'])
        for i,ticket in enumerate(tickets,1):
            manager=self.client('manager' if i==1 else 'manager'+str(i))
            requests=self.ok(manager,'/api/requests')['requests']
            self.assertEqual({r['queue_number'] for r in requests},{t['code'] for t in tickets})
            result=self.ok(manager,'/api/action',{'operator':i,'action':'call'})
            self.assertEqual(result['desk']['code'],ticket['code'])
            self.ok(manager,'/api/action',{'operator':i,'action':'start'})
        state=self.ok(self.public,'/api/state?0,0')
        self.assertEqual({r['code'] for r in state['serving']},{t['code'] for t in tickets})
        self.assertEqual([e['prefix'] for e in state['events']],list('ABCDE'))
        self.assertEqual(self.issue(1)['code'],'B-002')

    def test_any_operator_accepts_any_prefix_and_actual_window_is_announced(self):
        first=self.issue(0);second=self.issue(4)
        result=self.ok(self.client('manager3'),'/api/action',{'operator':3,'action':'call','ticket_id':first['id']})
        self.assertEqual((result['desk']['code'],result['desk']['operator']),('A-001',3))
        self.assertEqual(self.client('manager').request('/api/action',{'operator':1,'action':'call','ticket_id':first['id']})[0],409)
        result=self.ok(self.client('manager'),'/api/action',{'operator':1,'action':'call'})
        self.assertEqual(result['desk']['id'],second['id'])
        event=self.ok(self.public,'/api/state?0,0')['events']
        self.assertEqual([(e['prefix'],e['operator']) for e in event],[('A',3),('E',1)])
        row=next(r for r in self.ok(self.client('manager3'),'/api/requests')['requests'] if r['ticket_id']==first['id'])
        own=self.ok(self.client('manager3'),'/api/me')['user']
        self.assertEqual(row['manager_id'],own['id'])
        updated=self.ok(self.client('manager3'),'/api/request/action',{'id':row['id'],'version':row['version'],'action':'update','hemis_id':'100000000001','content':'Qabul qilindi'})
        self.assertEqual(updated['request']['student_id'],'100000000001')

    def test_simultaneous_claims_have_only_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        ticket=self.issue(2);one=self.client('manager');two=self.client('manager2');barrier=Barrier(2)
        def claim(client,operator):
            barrier.wait()
            return client.request('/api/action',{'operator':operator,'action':'call','ticket_id':ticket['id']})[0]
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(claim,one,1);b=pool.submit(claim,two,2)
            self.assertEqual(sorted([a.result(),b.result()]),[200,409])
        self.assertEqual(len(self.ok(self.public,'/api/state?0,0')['events']),1)

    def test_route_edits_apply_only_to_new_tickets_and_old_codes_survive(self):
        old=self.issue(0)
        admin=self.client('admin');routes=self.ok(admin,'/api/settings')['settings']['section_routes']
        routes[0]={'section':0,'prefix':'Z','operator':5}
        routes[4]={'section':4,'prefix':'A','operator':1}
        self.ok(admin,'/api/admin/settings',{'settings':{'section_routes':routes}})
        new=self.issue(0)
        self.assertEqual((new['code'],new['target_operator']),('Z-001',5))
        old_state=self.ok(self.public,'/api/state')['waiting'][0]
        self.assertEqual((old_state['code'],old_state['target_operator']),('A-001',1))
        self.assertEqual(self.ok(self.client('manager'),'/api/action',{'operator':1,'action':'call'})['desk']['id'],old['id'])
        self.assertEqual(self.ok(self.client('manager5'),'/api/action',{'operator':5,'action':'call'})['desk']['id'],new['id'])
        self.assertEqual(self.issue(4)['code'],'A-002')

    def test_duplicate_route_letters_or_operators_are_rejected(self):
        admin=self.client('admin');routes=self.ok(admin,'/api/settings')['settings']['section_routes']
        routes[1]['prefix']='A'
        self.assertEqual(admin.request('/api/admin/settings',{'settings':{'section_routes':routes}})[0],400)
        self.assertEqual(self.issue(1)['code'],'B-001')

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in RoutingAcceptance.__dict__:setattr(RoutingAcceptance,_name,None)
del WorkflowAcceptance
