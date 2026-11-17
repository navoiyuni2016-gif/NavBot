// Full browser journey against an isolated local server, no production data.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const net=require('node:net');
const PASSWORD='Navbot-Test-2026!';
const root=path.resolve(__dirname,'..');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function freePort(){const server=net.createServer();await new Promise(r=>server.listen(0,'127.0.0.1',r));const port=server.address().port;await new Promise(r=>server.close(r));return port}
(async()=>{
 let server,browser,temp,logs='';
 try{
 let base=process.env.NAVBOT_URL;
 if(!base){
  temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-browser-'));
  const port=await freePort();base='http://127.0.0.1:'+port;
  server=spawn(process.env.PYTHON||'python3',[path.join(root,'navbot/app.py'),'--port',String(port),'--db',path.join(temp,'browser.sqlite3'),'--seed-demo']);
  server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
  let ready=false;
  for(let i=0;i<120;i++){try{if((await fetch(base+'/api/catalog')).ok){ready=true;break}}catch{}if(server.exitCode!==null)break;await delay(100)}
  assert(ready,'Server startup failed: '+logs);
 }
 browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const pageErrors=[];
 async function newContext(){const context=await browser.newContext({viewport:{width:1440,height:1000}});context.setDefaultTimeout(15000);context.on('page',p=>p.on('pageerror',e=>pageErrors.push(e.message)));return context}
 async function login(role,password=PASSWORD){const context=await newContext();const page=await context.newPage();await page.goto(base+'/login');await page.locator('#login-form [name=username]').fill(role);await page.locator('#login-form [name=password]').fill(password);await page.locator('#login-form button[type=submit]').click();await page.waitForURL(url=>!url.pathname.endsWith('/login'));return page}
 async function postAction(page,testid,fields){await page.getByTestId(testid).click();const form=page.locator('#operation-form');await form.waitFor();for(const [name,value] of Object.entries(fields)){const input=form.locator('[name='+name+']');if(await input.evaluate(el=>el.tagName)==='SELECT')await input.selectOption(String(value));else await input.fill(String(value))}const response=page.waitForResponse(r=>r.url().endsWith('/api/request/action')&&r.request().method()==='POST');await form.locator('button[type=submit]').click();const result=await response;assert.equal(result.status(),200,await result.text());await form.waitFor({state:'detached'});return (await result.json()).request}
 async function selectRequest(page,number){await page.locator('.request-row').filter({hasText:number}).click();await page.locator('.summary-banner').getByText(number,{exact:true}).waitFor()}
 const publicContext=await newContext();const kiosk=await publicContext.newPage(),tv=await publicContext.newPage(),tablo=await publicContext.newPage();
 await Promise.all([kiosk.goto(base+'/kiosk'),tv.goto(base+'/tv'),tablo.goto(base+'/tablo?id=1')]);
 await kiosk.getByRole('button',{name:'Özbekça',exact:true}).click();await kiosk.locator('.tile').first().click();await kiosk.locator('.tile').first().click();await kiosk.locator('.receipt').waitFor();
 const queue=await kiosk.locator('.receipt h2').innerText();
 const manager=await login('manager');
 await manager.locator('.request-row').filter({hasText:queue}).click();
 await manager.getByTestId('queue-call').click();
 await tv.locator('.current .number').getByText(queue,{exact:true}).waitFor();
 await tablo.locator('.number').getByText(queue,{exact:true}).waitFor();
 const number=await manager.locator('.summary-banner .piece strong').first().innerText();
 await manager.getByTestId('queue-start').click();
 await tv.locator('.serving').getByText('1-operator · '+queue,{exact:true}).waitFor();
 const lookup=manager.getByTestId('student-lookup');await lookup.locator('[name=hemis_id]').fill('100000000001');await lookup.locator('button[type=submit]').click();await manager.locator('#student-result h3').getByText('Sinov Talaba Bir',{exact:true}).waitFor();
 const link=manager.getByTestId('request-link');await link.locator('[name=note]').fill('Ingliz tilida transkript kerak — brauzer sinovi');
 const linkedResponse=manager.waitForResponse(r=>r.url().endsWith('/api/request/action')&&r.request().postDataJSON().action==='update');await link.locator('button[type=submit]').click();const linked=await linkedResponse;assert.equal(linked.status(),200,await linked.text());
 await manager.getByTestId('request-assign').click();const form=manager.locator('#operation-form');const executorId=await form.locator('[name=assignee_id] option').filter({hasText:'Sinov Ijrochi'}).getAttribute('value');
 await form.locator('[name=assignee_id]').selectOption(executorId);
 const due=new Date(Date.now()+3*86400000).toISOString().slice(0,16);
 await form.locator('[name=deadline]').fill(due);await form.locator('[name=internal_basis]').fill('Lokal SINOV, ichki qoida 1-band');await form.locator('[name=legal_basis]').fill('Tasdiqlanmagan — faqat sinov');await form.locator('[name=reason]').fill('Transkript tayyorlash');
 const assignResponse=manager.waitForResponse(r=>r.url().endsWith('/api/request/action')&&r.request().postDataJSON().action==='assign');await form.locator('button[type=submit]').click();const assigned=await assignResponse;assert.equal(assigned.status(),200,await assigned.text());let request=(await assigned.json()).request;const deadline=request.deadline;
 await form.waitFor({state:'detached'});
 const executor=await login('executor');await selectRequest(executor,number);
 assert((await executor.locator('#request-detail').innerText()).includes('Ingliz tilida transkript kerak'));
 assert((await executor.locator('.deadline').innerText()).includes('qoldi'));
 assert(Number(await executor.locator('#notify-count').innerText())>0);
 request=await postAction(executor,'request-return',{reason:'Boshqa mas’ulga tegishli — sinov qaytarish'});
 assert.equal(request.deadline,deadline);
 await manager.locator('[data-filter=returned]').click();await selectRequest(manager,number);
 request=await postAction(manager,'request-assign',{assignee_id:executorId,reason:'Aniqlashtirildi, qayta ijroga'});
 assert.equal(request.deadline,deadline);assert.equal(request.number,number);
 await selectRequest(executor,number);await executor.getByTestId('request-submit').waitFor();
 request=await postAction(executor,'request-submit',{answer:'Transkript tayyorlandi — sinov javobi'});
 const head=await login('head');await selectRequest(head,number);
 await head.locator('[data-action=correct]').click();let correction=head.locator('#operation-form');await correction.locator('[name=reason]').fill('Tarjima tekshirilsin');const corrected=head.waitForResponse(r=>r.url().endsWith('/api/request/action'));await correction.locator('button[type=submit]').click();assert.equal((await corrected).status(),200);await correction.waitFor({state:'detached'});
 await selectRequest(executor,number);await executor.getByTestId('request-submit').waitFor();request=await postAction(executor,'request-submit',{answer:'Tarjima tekshirildi, transkript tayyor'});
 await selectRequest(head,number);await head.getByTestId('request-approve').waitFor();request=await postAction(head,'request-approve',{result:'Talabaga transkript berildi'});
 assert.equal(request.status,'closed');assert.equal(request.deadline,deadline);assert(request.closed_at);assert(request.answered_at);
 await manager.getByTestId('queue-finish').click();await tablo.locator('.number').getByText('—',{exact:true}).waitFor();
 await tv.waitForFunction(n=>!document.querySelector('#content').textContent.includes(n),queue,{timeout:10000});
 await manager.locator('#menu [data-view=archive]').click();await selectRequest(manager,number);assert((await manager.locator('.timeline').innerText()).includes('Tarjima tekshirilsin'));
 const director=await login('director');await director.locator('#report-result tbody tr').filter({hasText:number}).waitFor();
 assert((await director.locator('#report-result').innerText()).includes('Talabaga transkript berildi'));
 const csv=await director.request.get(await director.locator('#report-download').getAttribute('href').then(x=>new URL(x,base).href));assert.equal(csv.status(),200);assert((await csv.text()).includes(number));
 const admin=await login('admin');
 const created=await admin.request.post(base+'/api/admin/user',{data:{username:'browsernew',full_name:'Brauzer Sinov Menejeri',role:'manager',department:'Registrar',operator:8,password:'Initial-Browser-2026!'}});assert.equal(created.status(),200,await created.text());
 const fresh=await login('browsernew','Initial-Browser-2026!');await fresh.locator('#password-form').waitFor();const passwordForm=fresh.locator('#password-form');await passwordForm.locator('[name=current_password]').fill('Initial-Browser-2026!');await passwordForm.locator('[name=new_password]').fill('Changed-Browser-2026!');await passwordForm.locator('[name=confirm_password]').fill('Changed-Browser-2026!');await passwordForm.locator('button[type=submit]').click();await fresh.waitForURL('**/login');await fresh.locator('#login-form [name=username]').fill('browsernew');await fresh.locator('#login-form [name=password]').fill('Changed-Browser-2026!');await fresh.locator('#login-form button[type=submit]').click();await fresh.waitForURL('**/manager');await fresh.locator('#request-list').waitFor();
 assert.deepEqual(pageErrors,[]);
 if(process.env.NAVBOT_SCREENSHOT_DIR){await fs.mkdir(process.env.NAVBOT_SCREENSHOT_DIR,{recursive:true});await manager.screenshot({path:path.join(process.env.NAVBOT_SCREENSHOT_DIR,'manager-archive.png'),fullPage:true});await director.screenshot({path:path.join(process.env.NAVBOT_SCREENSHOT_DIR,'director-report.png'),fullPage:true});await tv.screenshot({path:path.join(process.env.NAVBOT_SCREENSHOT_DIR,'tv.png'),fullPage:true})}
 console.log(JSON.stringify({passed:['kiosk receipt','manager queue call/start','TV/tablo sync','HEMIS lookup and link','assign with deadline/bases','executor notification and return','reroute preserves number/deadline','submit/correct/resubmit/approve','archive/history','director report/CSV','first-login password change'],number,queue,pageErrors,limits:'Actual Telegram/LMS, printer, physical sound and Windows runtime not tested.'},null,2));
 }finally{if(browser)await browser.close();if(server){server.kill('SIGTERM');await new Promise(r=>server.exitCode!==null?r():server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
