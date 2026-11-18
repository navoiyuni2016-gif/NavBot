import base64
from test_workflow import WorkflowAcceptance

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVZkAAAAASUVORK5CYII=')
PAYLOAD = {'mime': 'image/png', 'data': base64.b64encode(PNG).decode()}

class ProfilePhotoAcceptance(WorkflowAcceptance):
    def test_private_self_service_replace_delete_and_validation(self):
        self.assertEqual(self.public.request('/api/profile/photo', PAYLOAD)[0], 401)
        for role in ('admin', 'manager', 'executor', 'head', 'director'):
            client = self.client(role)
            first = self.ok(client, '/api/profile/photo', PAYLOAD)['avatar_url']
            self.assertEqual(client.opener.open(self.base + first).read(), PNG)
            self.assertEqual(self.public.request(first)[0], 401)
            other = self.client('manager2')
            self.assertEqual(other.request(first)[0], 404)
            second = self.ok(client, '/api/profile/photo', {**PAYLOAD, 'user_id': 999})['avatar_url']
            self.assertNotEqual(first, second)
            self.assertEqual(client.request(first)[0], 404)
            self.assertEqual(self.ok(client, '/api/me')['user']['avatar_url'], second)
            for invalid in ({'mime':'image/svg+xml','data':PAYLOAD['data']}, {'mime':'image/png','data':'bad'}, {'mime':'image/png','data':base64.b64encode(b'fake').decode()}, {'mime':'image/png','data':'a'*2796205}):
                self.assertEqual(client.request('/api/profile/photo', invalid)[0], 400)
            self.assertEqual(self.ok(client, '/api/me')['user']['avatar_url'], second)
            self.assertIsNone(self.ok(client, '/api/profile/photo', {'remove':True})['avatar_url'])
            self.assertEqual(client.request(second)[0], 404)

    def test_section_logo_delete_admin_only(self):
        admin = self.client('admin')
        self.ok(admin, '/api/admin/logo', {'section':0, **PAYLOAD})
        self.ok(admin, '/api/admin/logo', {'section':1, **PAYLOAD})
        self.assertEqual(self.client('manager').request('/api/admin/logo', {'section':0,'remove':True})[0], 403)
        result = self.ok(admin, '/api/admin/logo', {'section':0,'remove':True})
        self.assertIsNone(result['settings']['section_logos'][0])
        self.assertTrue(result['settings']['section_logos'][1])
        self.assertEqual(admin.request('/api/admin/logo', {'section':False,'remove':True})[0],400)

for _name in list(WorkflowAcceptance.__dict__):
    if _name.startswith('test_') and _name not in ProfilePhotoAcceptance.__dict__:
        setattr(ProfilePhotoAcceptance, _name, None)
del WorkflowAcceptance
