"""Exercise checked-in Nginx rules against a real Nginx process and HTTP backend.

python3 tests/nginx-security.py --nginx /usr/sbin/nginx
No live NAVBOT database or credentials are used.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--nginx',required=True)
    args=parser.parse_args()
    counts={}
    slow=threading.Event()
    condition=threading.Condition()
    class Backend(BaseHTTPRequestHandler):
        def do_GET(self):
            with condition:
                counts[self.path]=counts.get(self.path,0)+1
                condition.notify_all()
            if self.path=='/slow':slow.wait(20)
            self.send_response(200)
            self.send_header('Content-Length','2')
            self.end_headers();self.wfile.write(b'{}')
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length','0')))
            self.do_GET()
        def log_message(self,*args):pass
    backend=ThreadingHTTPServer(('127.0.0.1',0),Backend)
    backend.request_queue_size=128
    thread=threading.Thread(target=backend.serve_forever,daemon=True);thread.start()
    nginx=None
    try:
        with tempfile.TemporaryDirectory(prefix='navbot-nginx-test-') as folder:
            root=Path(folder);(root/'logs').mkdir();(root/'body').mkdir();(root/'proxy').mkdir()
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            site=(ROOT/'deploy/navbot-nginx-lan.conf').read_text().replace('listen 80;',f'listen 127.0.0.1:{port};').replace('127.0.0.1:8081',f'127.0.0.1:{backend.server_port}')
            (root/'site.conf').write_text(site)
            config=f'''pid {root}/nginx.pid;
error_log {root}/error.log;
events {{ worker_connections 512; }}
http {{
 access_log off;
 client_body_temp_path {root}/body;
 proxy_temp_path {root}/proxy;
 include {root}/site.conf;
}}
'''
            (root/'nginx.conf').write_text(config)
            command=[args.nginx,'-p',str(root)+'/', '-c',str(root/'nginx.conf')]
            subprocess.run(command+['-t'],check=True)
            nginx=subprocess.Popen(command+['-g','daemon off; master_process off;'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            def request(path,method='GET',headers=None):
                c=http.client.HTTPConnection('127.0.0.1',port,timeout=25)
                try:
                    c.request(method,path,body='{}' if method=='POST' else None,headers=headers or {})
                    r=c.getresponse();r.read();return r.status,r.getheader('Server')
                finally:c.close()
            for _ in range(100):
                try:
                    if request('/login')[0]==200:break
                except OSError:time.sleep(.05)
            else:raise AssertionError('Nginx did not start')
            assert request('/login')==(200,'nginx'),'Version should be hidden'
            statuses=[request('/api/login','POST')[0] for _ in range(18)]
            assert 200 in statuses and 429 in statuses,statuses
            assert counts['/api/login']<18,'Rejected login requests must not reach backend'
            assert request('/api/login','POST',{'X-Forwarded-For':'203.0.113.10'})[0]==429,'Spoofed forwarding header must not bypass limit'
            for _ in range(500):assert request('/api/admin/audio/upload','POST')[0]==200
            assert counts['/api/admin/audio/upload']==500
            for _ in range(70):assert request('/api/state?0,0')[0]==200
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            c.putrequest('POST','/api/attachment/upload');c.putheader('Content-Length',str(17*1024*1024));c.endheaders()
            r=c.getresponse();assert r.status==413;r.read();c.close()
            assert '/api/attachment/upload' not in counts,'Oversized body must not reach backend'
            with ThreadPoolExecutor(max_workers=32) as pool:
                futures=[pool.submit(request,'/slow') for _ in range(32)]
                try:
                    with condition:
                        assert condition.wait_for(lambda:counts.get('/slow',0)==32,timeout=10),'Slow clients did not connect'
                    assert request('/api/me')[0]==429,'Excess concurrent connection should be rejected'
                finally:slow.set()
                assert all(f.result()[0]==200 for f in futures)
            assert request('/api/me')[0]==200,'Limit must clear after active requests finish'
            print('PASS: real Nginx syntax, login rate limit, forwarded-header spoof rejection, 500 sequential upload requests, TV polling, oversized body rejection, concurrent limit/recovery, hidden version. Backend is a test server; live authenticated workflows remain target acceptance checks.')
    finally:
        slow.set()
        if nginx:
            nginx.terminate();nginx.wait(timeout=5);nginx.stderr.close()
        backend.shutdown();backend.server_close();thread.join(timeout=5)


if __name__=='__main__':main()
