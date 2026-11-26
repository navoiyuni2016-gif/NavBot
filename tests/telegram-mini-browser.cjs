// Real HTTP + signed Telegram fixture. Never contacts Telegram or uses real tokens.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),net=require('node:net'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),token='123456789:'+'X'.repeat(35),delay=ms=>new Promise(r=>setTimeout(r,ms));
function signed(){const values={auth_date:String(Math.floor(Date.now()/1000)),query_id:'offline-test',user:JSON.stringify({id:101,first_name:'Synthetic'})};const secret=crypto.createHmac('sha256','WebAppData').update(token).digest();const check=Object.keys(values).sort().map(k=>k+'='+values[k]).join('\n');values.hash=crypto.createHmac('sha256',secret).update(check).digest('hex');return new URLSearchParams(values).toString()}
(async()=>{let server,browser,temp,logs='';try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-mini-'));const socket=net.createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));const base='http://127.0.0.1:'+port;
 server=spawn('python3',[path.join(root,'navbot/app.py'),'--port',String(port),'--db',path.join(temp,'mini.sqlite3'),'--seed-demo']);server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
 let ready=false;for(let i=0;i<100;i++){try{if((await fetch(base+'/api/catalog')).ok){ready=true;break}}catch{}await delay(100)}assert(ready,logs);
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const admin=await browser.newContext();
 async function post(api,data){const response=await admin.request.post(base+api,{data});assert.equal(response.status(),200,await response.text());return response.json()}
 await post('/api/login',{username:'admin',password:'Navbot-Test-2026!'});await post('/api/admin/integrations',{kind:'telegram',enabled:true,token});await post('/api/telegram/mini-config',{url:'https://example.com/student'});
 const code=(await post('/api/telegram/code',{hemis_id:'100000000001',identity_confirmed:true})).code;
 const users=(await (await admin.request.get(base+'/api/users')).json()).users,actor=users.find(u=>u.username==='admin');
 async function pending(content){let r=(await post('/api/request/create',{key:crypto.randomUUID(),hemis_id:'100000000001',identity_confirmed:true,channel:'phone',lang:'uz',section:0,service:0,content,note:'DO NOT DISCLOSE NOTE'})).request;
 r=(await post('/api/request/action',{id:r.id,version:r.version,action:'assign',assignee_id:actor.id,deadline:'2099-01-01T00:00:00+00:00',internal_basis:'DO NOT DISCLOSE BASIS'})).request;
 return (await post('/api/request/action',{id:r.id,version:r.version,action:'submit',answer:'Answer approved for the student'})).request}
 const pendingRequest=await pending('Request <img src=x onerror=alert(1)>');let approved=await pending('Second request');
 for(const name of ['internal.txt','Talaba_javobi.txt'])approved=(await post('/api/attachment/upload',{id:approved.id,version:approved.version,key:crypto.randomUUID(),name,data:Buffer.from(name).toString('base64')})).request;
 const selectedFile=approved.attachments.find(f=>f.name==='Talaba_javobi.txt');approved=(await post('/api/request/action',{id:approved.id,version:approved.version,action:'approve',result:'Ready',telegram_attachment_ids:[selectedFile.id]})).request;
 const context=await browser.newContext({viewport:{width:390,height:844}}),page=await context.newPage(),errors=[];page.setDefaultTimeout(12000);await page.emulateMedia({reducedMotion:'reduce'});page.on('pageerror',e=>errors.push(e.message));
 await context.route('https://telegram.org/js/telegram-web-app.js',route=>route.fulfill({contentType:'text/javascript',body:''}));
 await context.addInitScript(data=>{window.Telegram={WebApp:{initData:data,ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){},onEvent(event,handler){(this._events??={})[event]=handler},BackButton:{hide(){},show(){},onClick(){}}}}},signed());
 const html=await page.goto(base+'/student');assert(!html.headers()['x-frame-options']);assert(html.headers()['content-security-policy'].includes('https://web.telegram.org'));
 await fs.mkdir('/workspace/files',{recursive:true});await page.locator('[name=hemis_id]').waitFor();await page.screenshot({path:'/workspace/files/navbot-mini-kirish.png',fullPage:true});
 await page.locator('[name=hemis_id]').fill('100000000001');await page.locator('#link-form [type=submit]').click();await page.locator('[name=code]').fill(code);await page.locator('#link-form [type=submit]').click();await page.locator('.menu-grid').waitFor();assert.equal(await page.locator('[data-action=track] .menu-label').innerText(),'Jarayonni kuzatiş');assert((await page.locator('#screen').innerText()).includes('Şaxsingiz tasdiqlandi.'));
 const out=path.join('/workspace','files');await fs.mkdir(out,{recursive:true});await page.screenshot({path:path.join(out,'navbot-mini-menu.png'),fullPage:true});
 await page.locator('[data-action=track]').click();await page.locator(`[data-id="${pendingRequest.id}"]`).click();await page.locator('.timeline').waitFor();assert.equal(await page.locator('.timeline .done').count(),3);assert.equal(await page.locator('.timeline .current').count(),1);
 assert(!(await page.locator('#screen').innerText()).includes('Answer approved'));assert(!(await page.locator('#screen').innerText()).includes('DO NOT DISCLOSE'));await page.screenshot({path:path.join(out,'navbot-mini-jarayon.png'),fullPage:true});
 await page.locator('[data-action=home]').click();await page.locator('[data-action=requests]').click();await page.locator(`[data-id="${approved.id}"]`).click();await page.locator('.file-button').waitFor();assert.equal(await page.locator('.file-button').count(),1);assert.equal(await page.locator('.file-button').innerText().then(t=>t.includes('Talaba_javobi.txt')),true);
 const downloadPromise=page.waitForEvent('download');await page.locator('.file-button').click();const download=await downloadPromise;assert.equal(download.suggestedFilename(),'Talaba_javobi.txt');await page.screenshot({path:path.join(out,'navbot-mini-javob.png'),fullPage:true});
 await page.locator('[data-action=home]').click();await page.locator('[data-action=profile]').click();await page.locator('.profile-info').waitFor();assert((await page.locator('#screen').innerText()).includes('Sinov Talaba Bir'));
 await page.screenshot({path:path.join(out,'navbot-mini-profil.png'),fullPage:true});
 for(const width of [360,390,768]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))}
 await page.locator('[data-action=home]').click();await page.locator('[data-action=help]').click();await page.screenshot({path:path.join(out,'navbot-mini-yordam.png'),fullPage:true});await page.locator('[data-lang=ru]').click();await page.getByRole('heading',{name:'Помощь',exact:true}).waitFor();await page.locator('[data-lang=en]').click();await page.getByRole('heading',{name:'Help',exact:true}).waitFor();
 await page.locator('[data-nav=home]').click();assert.equal(await page.locator('.menu-button').count(),4);assert.equal(await page.locator('.student-nav [aria-current=page]').getAttribute('data-nav'),'home');
 await page.locator('[data-nav=requests]').click();await page.locator('.request-card').first().waitFor();assert.equal(await page.locator('.student-nav [aria-current=page]').getAttribute('data-nav'),'requests');
 await page.locator('[data-nav=profile]').click();await page.locator('.profile-info').waitFor();assert((await page.locator('.profile-info').innerText()).includes('100000000001'));
 for(const lang of ['uz','ru','en']){
  await page.locator('#lang').click();await page.locator('[data-lang='+lang+']').click();await page.locator('[data-nav=home]').click();
  for(const width of [320,390,768]){await page.setViewportSize({width,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true,'No horizontal overflow in '+lang+' at '+width)}
 }
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>{window.Telegram.WebApp.colorScheme='dark';window.Telegram.WebApp._events.themeChanged()});assert.equal(await page.locator('html').getAttribute('data-theme'),'dark');await page.screenshot({path:path.join(out,'navbot-mini-dark.png'),fullPage:true});
 await page.evaluate(()=>{window.Telegram.WebApp.colorScheme='light';window.Telegram.WebApp._events.themeChanged()});assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
 await page.locator('#lang').click();await page.locator('[data-lang=uz]').click();await page.locator('[data-nav=home]').click();await page.screenshot({path:path.join(out,'navbot-mini-menu.png'),fullPage:true});
 await page.route('**/api/telegram/mini',route=>route.abort());await page.locator('[data-nav=requests]').click();await page.locator('[data-action=retry-list]').waitFor();await page.unroute('**/api/telegram/mini');await page.locator('[data-action=retry-list]').click();await page.locator('.request-card').first().waitFor();
 const sessionStorage=await page.evaluate(()=>JSON.stringify({...localStorage,...window.sessionStorage}));assert(!sessionStorage.includes(code));assert(!sessionStorage.includes('init_data'));
 const plain=await browser.newContext();await plain.route('https://telegram.org/js/telegram-web-app.js',route=>route.fulfill({contentType:'text/javascript',body:''}));const outside=await plain.newPage();await outside.goto(base+'/student');await outside.getByText('Ilovani Telegram bot içidan oçing.',{exact:true}).waitFor();
 const staff=await admin.newPage();await staff.goto(base+'/admin');await staff.locator('[data-view=integrations]').click();await staff.locator('#telegram-mini-form').waitFor();assert.equal(await staff.locator('#telegram-mini-form [name=url]').inputValue(),'https://example.com/student');
 // Use the repository's known-good raster fixture, then verify the shared logo URL.
 const imageData='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVZkAAAAASUVORK5CYII=';
 const branding=(await post('/api/admin/branding',{target:'system_logo',mime:'image/png',data:imageData})).settings.branding;
 await page.reload();await page.locator('#student-brand img').waitFor();assert.equal(await page.locator('#student-brand img').getAttribute('src'),branding.system_logo);await page.waitForFunction(()=>document.querySelector('#student-brand img').naturalWidth>0);
 for(const width of [360,390,768]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))}
 assert.deepEqual(errors,[]);console.log('PASS: signed Mini App identity, staff OTP, real own requests, design timeline, selected download, 3 languages, mobile/tablet, no stored secrets, outside-Telegram denial, admin config.');
 }finally{if(browser)await browser.close();if(server){server.kill();await new Promise(r=>server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
