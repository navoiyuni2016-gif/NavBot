// Signed device fixture drives the actual HTTP queue; no Windows printer is used.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),net=require('node:net');
(async()=>{let server,browser,temp;try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-native-'));const listener=net.createServer();await new Promise(r=>listener.listen(0,'127.0.0.1',r));const port=listener.address().port;await new Promise(r=>listener.close(r));const base='http://127.0.0.1:'+port;
 server=spawn('python3',[path.join(__dirname,'../navbot/app.py'),'--port',String(port),'--db',path.join(temp,'test.sqlite3'),'--seed-demo']);for(let i=0;i<100;i++){try{if((await fetch(base+'/api/catalog')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const admin=await browser.newContext();
 async function post(url,data,headers={}){const response=await admin.request.post(base+url,{data,headers});assert.equal(response.status(),200,await response.text());return response.json()}
 await post('/api/login',{username:'admin',password:'Navbot-Test-2026!'});const credentials=await post('/api/admin/kiosk-printer',{action:'pair'});
 async function agent(data){return post('/api/kiosk-printer/agent',{worker_id:credentials.worker_id,...data},{Authorization:'Bearer '+credentials.token})}
 await agent({action:'poll',ready:true,printer_name:'Offline test physical printer'});
 const context=await browser.newContext({viewport:{width:1280,height:1024}}),page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.addInitScript(()=>{window.printCalls=0;window.print=()=>{window.printCalls++;throw Error('Browser print must NOT run in agent mode')}});
 await page.goto(base+'/kiosk');await page.locator('.tile').first().click();const response=page.waitForResponse(r=>r.url().endsWith('/api/ticket'));await page.locator('.tile').first().click();assert.equal((await response).status(),200);await page.waitForFunction(()=>document.querySelectorAll('.tile').length===5&&!document.querySelector('.tile:disabled'));
 assert.equal(await page.evaluate(()=>window.printCalls),0);assert.equal(await page.locator('.kiosk-ticket-feedback,#print-ticket,#new-ticket').count(),0);assert.equal(context.pages().length,1);
 const job=(await agent({action:'poll',ready:true,printer_name:'Offline test physical printer'})).job;assert(job.fresh);assert.equal(job.receipt.number,'A-001');await agent({action:'ack',ticket_id:job.ticket_id,claim:job.claim,state:'spooled'});
 const staff=await admin.newPage();await staff.goto(base+'/admin');await staff.locator('[data-view=devices]').click();await staff.locator('#kiosk-printer-panel').getByText('Windows navbatiga yuborildi',{exact:true}).waitFor();
 const archive=await admin.request.get(base+'/downloads/NAVBOT-NATIVE.zip');assert.equal(archive.status(),200);assert.equal((await archive.body()).subarray(0,2).toString(),'PK');
 staff.on('dialog',dialog=>dialog.accept());const downloadPromise=staff.waitForEvent('download');await staff.locator('#pair-kiosk-printer').click();const download=await downloadPromise;const config=JSON.parse(await fs.readFile(await download.path(),'utf8'));assert.equal(config.server_url,base);assert(config.token);assert.equal(download.suggestedFilename(),'printer-config.json');
 assert.deepEqual(errors,[]);console.log('PASS: actual agent queue, browser print NEVER called, no receipt UI or popups, immediate main menu, spool ack, admin setup and private config download, native ZIP. Windows hardware remains unverified.');
 }finally{if(browser)await browser.close();if(server){server.kill();await new Promise(r=>server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exit(1)});
