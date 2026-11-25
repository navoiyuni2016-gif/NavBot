const {chromium}=require('playwright'),assert=require('node:assert/strict'),{spawn,execFileSync}=require('node:child_process'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),net=require('node:net'),crypto=require('node:crypto');
(async()=>{let server,browser,temp;try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-owner-'));
 const root=path.resolve(__dirname,'../navbot'),db=temp+'/test.sqlite3',password='Owner-Test-Password-2026!';
 execFileSync('python3',['-c',`import sys;sys.path.insert(0,sys.argv[1]);import app,auth,owner_control;from pathlib import Path;app.DATABASE=Path(sys.argv[2]);app.initialize(True);db=app.connection();db.execute('INSERT INTO owner_account VALUES(1,?,?,?,-1)',('owner',auth._hash('Owner-Test-Password-2026!'),'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'));db.commit();db.close()`,root,db]);
 const sock=net.createServer();await new Promise(r=>sock.listen(0,'127.0.0.1',r));const port=sock.address().port;await new Promise(r=>sock.close(r));const base='http://127.0.0.1:'+port;
 server=spawn('python3',[root+'/app.py','--port',String(port),'--db',db]);server.stdout.resume();server.stderr.resume();
 for(let i=0;i<100;i++){try{if((await fetch(base+'/owner')).ok)break}catch{}await new Promise(r=>setTimeout(r,50))}
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1280,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/owner');await page.locator('#login-form [name=username]').fill('owner');await page.locator('#login-form [name=password]').fill(password);
 const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));const mac=crypto.createHmac('sha1',Buffer.from('12345678901234567890')).update(counter).digest(),offset=mac[19]&15,code=String((mac.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,'0');
 await page.locator('[name=code]').fill(code);await page.locator('#login-form button').click();await page.locator('#console').waitFor({state:'visible'});
 assert.match(await page.locator('#service-state').innerText(),/faol/);
 const kiosk=await browser.newPage();await kiosk.goto(base+'/kiosk');await kiosk.locator('.kiosk-grid').waitFor();
 page.on('dialog',dialog=>dialog.accept());
 await page.locator('#change-form [name=reason]').fill('Contract review');await page.locator('#change-form [name=password]').fill(password);await page.locator('#change-button').click();await page.waitForFunction(()=>document.querySelector('#service-state').textContent.includes('to‘xtatilgan'));
 assert.equal((await page.request.get(base+'/api/state')).status(),503);
 await kiosk.waitForFunction(()=>document.querySelector('h1')?.textContent.includes('vaqtincha'));assert.match(await kiosk.locator('h1').innerText(),/vaqtincha/);
 await page.screenshot({path:'/tmp/navbot-owner-control.png',fullPage:true});
 await page.reload();await page.locator('#console').waitFor({state:'visible'});
 await page.locator('#change-form [name=reason]').fill('License confirmed');await page.locator('#change-form [name=password]').fill(password);await page.locator('#change-button').click();await page.waitForFunction(()=>document.querySelector('#service-state').textContent==='Xizmat faol');
 assert.equal((await page.request.get(base+'/api/state')).status(),200);
 await kiosk.locator('.kiosk-grid').waitFor({timeout:20000});await kiosk.close();
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await page.locator('#logout').click();await page.locator('#login').waitFor({state:'visible'});assert.equal((await page.request.get(base+'/api/owner/status')).status(),401);assert.deepEqual(errors,[]);
 console.log('PASS owner MFA login, pause, maintenance, session reload, resume, logout and mobile layout');
}finally{await browser?.close();if(server){server.kill();await new Promise(r=>server.exitCode!==null?r():server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}})().catch(error=>{console.error(error);process.exit(1)});
