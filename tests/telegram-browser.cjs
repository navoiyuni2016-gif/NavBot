const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.NAVBOT_URL||'http://127.0.0.1:8094';
 await page.goto(base+'/login');await page.locator('[name=username]').fill('admin');await page.locator('[name=password]').fill('Navbot-Test-2026!');await page.locator('#login-form button[type=submit]').click();await page.waitForURL('**/admin');
 await page.locator('[data-view=phone]').click();
 await page.locator('#phone-form [name=hemis_id]').fill('100000000001');await page.locator('#phone-find').click();
 await page.locator('[data-telegram-open]').click();await page.locator('[data-telegram-verified]').check();await page.locator('[data-telegram-code]').click();
 const code=await page.getByRole('textbox',{name:'Bir martalik kod',exact:true}).inputValue();assert.match(code,/^[A-Z2-9]{8}$/);
 const allCookies=await page.context().cookies();assert(allCookies.some(c=>c.name==='navbot_session'));
 const config=await page.request.get(base+'/api/telegram/student?hemis_id=100000000001');assert.equal(config.status(),200);assert.equal((await config.json()).linked,false);
 assert(!JSON.stringify(await page.evaluate(()=>({...localStorage}))).includes(code));
 // Create actual pending request through the same staff API; verify outgoing file selection UI.
 async function post(path,data){const response=await page.request.post(base+path,{data});assert.equal(response.status(),200,await response.text());return response.json()}
 let r=(await post('/api/request/create',{key:crypto.randomUUID(),channel:'phone',lang:'uz',section:0,service:0,hemis_id:'100000000001',identity_confirmed:true,content:'Browser bot request'})).request;
 const users=(await (await page.request.get(base+'/api/users')).json()).users;const admin=users.find(u=>u.username==='admin');
 r=(await post('/api/request/action',{id:r.id,version:r.version,action:'assign',assignee_id:admin.id,deadline:'2099-01-01T00:00:00+00:00',internal_basis:'Test'})).request;
 r=(await post('/api/attachment/upload',{id:r.id,version:r.version,key:crypto.randomUUID(),name:'internal.txt',data:Buffer.from('private attachment').toString('base64')})).request;
 r=(await post('/api/request/action',{id:r.id,version:r.version,action:'submit',answer:'Browser approved answer'})).request;
 await page.locator('[data-view=requests]').click();await page.locator('.request-row').filter({hasText:r.number}).click();await page.getByTestId('request-approve').click();
 const selected=page.locator('[name=telegram_attachment]');assert.equal(await selected.count(),1);assert.equal(await selected.isChecked(),false);assert.equal(await page.locator('[name=telegram_new_files]').isChecked(),false);
 await selected.check();await page.locator('#operation-form button[type=submit]').click();await page.locator('#telegram-delivery').getByText('Talaba Telegramga bog‘lanishi kutilmoqda',{exact:false}).waitFor();
 await page.setViewportSize({width:390,height:844});assert.equal(await page.locator('#telegram-delivery').isVisible(),true);
 assert.deepEqual(errors,[]);console.log('PASS: staff OTP, no browser persistence, explicit outgoing-file selection, approval delivery state, mobile layout, no JS errors');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
