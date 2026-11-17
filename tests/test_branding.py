import base64
from test_workflow import WorkflowAcceptance

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVZkAAAAASUVORK5CYII=')

class BrandingAcceptance(WorkflowAcceptance):
    def test_branding_upload_replace_reset_and_permissions(self):
        payload={'target':'system_logo','mime':'image/png','data':base64.b64encode(PNG).decode()}
        self.assertEqual(self.public.request('/api/admin/branding',payload)[0],401)
        self.assertEqual(self.client('manager').request('/api/admin/branding',payload)[0],403)
        admin=self.client('admin')
        first=self.ok(admin,'/api/admin/branding',payload)['settings']['branding']['system_logo']
        self.assertEqual(self.public.opener.open(self.base+first).read(),PNG)
        second=self.ok(admin,'/api/admin/branding',payload)['settings']['branding']['system_logo']
        self.assertNotEqual(first,second)
        self.assertEqual(self.public.request(first)[0],404)
        self.ok(admin,'/api/admin/branding',{'target':'icon','key':'phone',**{k:v for k,v in payload.items() if k!='target'}})
        self.assertIn('phone',self.ok(self.public,'/api/settings')['settings']['branding']['icons'])
        self.ok(admin,'/api/admin/branding',{'target':'system_logo','remove':True})
        self.assertIsNone(self.ok(self.public,'/api/settings')['settings']['branding']['system_logo'])
        self.assertEqual(self.public.request(second)[0],404)
        self.assertEqual(admin.request('/api/admin/settings',{'settings':{'branding':{'system_logo':'javascript:alert(1)'}}})[0],400)

    def test_invalid_branding_does_not_write(self):
        admin=self.client('admin')
        for data in [{'target':'icon','key':[]},{'target':'unknown'},{'target':'kiosk_logo','mime':'image/svg+xml','data':base64.b64encode(b'<svg onload="alert(1)"/>').decode()},{'target':'system_logo','mime':'image/png','data':'not base64'}]:
            self.assertEqual(admin.request('/api/admin/branding',data)[0],400)
        self.assertEqual(self.ok(self.public,'/api/settings')['settings']['branding'],{'system_logo':None,'kiosk_logo':None,'icons':{}})

    def test_xlsx_http_add_only_and_private_students(self):
        from test_student_xlsx import workbook
        raw=workbook([['123456789012','Asl FAMILIYA','Ayol','3-kurs','Filologiya','Bakalavr','Kunduzgi']])
        payload={'data':base64.b64encode(raw).decode()}
        self.assertEqual(self.public.request('/api/students/import-xlsx',payload)[0],401)
        self.assertEqual(self.client('manager').request('/api/students/import-xlsx',payload)[0],403)
        admin=self.client('admin')
        result=self.ok(admin,'/api/students/import-xlsx',payload)
        self.assertEqual(result,{'added':1,'updated':0,'skipped':0,'total':1})
        self.assertEqual(self.ok(admin,'/api/students/import-xlsx',payload)['added'],0)
        student=self.ok(admin,'/api/student',{'hemis_id':'123456789012'})['student']
        self.assertEqual(student['full_name'],'Asl FAMILIYA')
        self.assertEqual(student['gender'],'Ayol')
        self.assertEqual(student['education_type'],'Bakalavr')
        self.assertEqual(self.public.request('/api/students')[0],401)
