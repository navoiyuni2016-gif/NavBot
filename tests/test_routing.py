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
            if i!=5:
                self.assertEqual(manager.request('/api/action',{'operator':i,'action':'call','ticket_id':tickets[-1]['id']})[0],409)
            result=self.ok(manager,'/api/action',{'operator':i,'action':'call'})
            self.assertEqual(result['desk']['code'],ticket['code'])
            self.ok(manager,'/api/action',{'operator':i,'action':'start'})
        state=self.ok(self.public,'/api/state?0,0')
        self.assertEqual({r['code'] for r in state['serving']},{t['code'] for t in tickets})
        self.assertEqual([e['prefix'] for e in state['events']],list('ABCDE'))
        self.assertEqual(self.issue(1)['code'],'B-002')

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
