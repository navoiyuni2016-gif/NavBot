import base64
from uuid import uuid4
from test_workflow import WorkflowAcceptance


class AttachmentAcceptance(WorkflowAcceptance):
    def payload(self, request, name='javob.txt', data='Sinov javob hujjati'.encode(), key=None):
        return {'id':request['id'],'version':request['version'],'key':key or str(uuid4()),'name':name,'data':base64.b64encode(data).decode()}

    def test_attachments_follow_request_and_enforce_private_access(self):
        _, request=self.assigned_request()
        data=self.payload(request)
        self.assertEqual(self.public.request('/api/attachment/upload',data)[0],401)
        self.assertEqual(self.client('manager2').request('/api/attachment/upload',data)[0],403)
        result=self.ok(self.client('executor'),'/api/attachment/upload',data)['request']
        self.assertGreater(result['version'],request['version'])
        self.assertEqual(len(result['attachments']),1)
        self.assertEqual(result['attachments'][0]['name'],'javob.txt')
        url=result['attachments'][0]['url']
        self.assertEqual(self.public.request(url)[0],401)
        self.assertEqual(self.client('manager2').request(url)[0],200)
        for role in ('manager','executor','head','director','admin'):
            status,body,headers=self.client(role).request(url)
            self.assertEqual(status,200)
            self.assertEqual(body,'Sinov javob hujjati')
            self.assertIn('attachment;',headers.get('Content-Disposition',''))
        # Retry the identical upload after a lost response must not add another file.
        retried=self.ok(self.client('executor'),'/api/attachment/upload',data)['request']
        self.assertEqual(retried['version'],result['version'])
        self.assertEqual(len(retried['attachments']),1)
        for role in ('manager','head','director','admin'):
            result=self.ok(self.client(role),'/api/attachment/upload',self.payload(result,name=role+'-ilova.txt'))['request']
        self.assertEqual(len(result['attachments']),5)
        result=self.transition('executor',result,'submit',answer='Hujjat ilova qilindi')
        result=self.transition('head',result,'approve',result='Tasdiqlandi')
        self.assertEqual(self.client('manager').request(url)[0],200)
        self.assertEqual(self.client('admin').request('/api/attachment/upload',self.payload(result))[0],409)

    def test_invalid_files_and_stale_writes_do_not_add_attachments(self):
        _, request=self.assigned_request()
        for name,body in [('../bad.txt',b'text'),('bad.html',b'<script/>'),('fake.pdf',b'no pdf'),('empty.txt',b''),('fake.docx',b'not zip')]:
            status,_,_=self.client('executor').request('/api/attachment/upload',self.payload(request,name,body))
            self.assertEqual(status,400)
        payload=self.payload(request);payload['version']-=1
        self.assertEqual(self.client('executor').request('/api/attachment/upload',payload)[0],409)
        current=next(r for r in self.requests('manager') if r['id']==request['id'])
        self.assertEqual(current['version'],request['version'])
        self.assertEqual(current['attachments'],[])


for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in AttachmentAcceptance.__dict__:
        setattr(AttachmentAcceptance,_name,None)
del WorkflowAcceptance
