// Real isolated HTTP/SQLite boundary; drop replies after committing a receipt.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),{spawn}=require('node:child_process'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),net=require('node:net');
(async()=>{let browser,server,temp;try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-recovery-'));const socket=net.createServer();await new Promise(r=>socket.listen(0,'127.0.0.1',r));const port=socket.address().port;await new Promise(r=>socket.close(r));const base='http://127.0.0.1:'+port;
 server=spawn('python3',[path.resolve(__dirname,'../navbot/app.py'),'--port',String(port),'--db',temp+'/db.sqlite3','--seed-demo']);server.stdout.resume();server.stderr.resume();for(let i=0;i<100;i++){try{if((await fetch(base+'/api/catalog')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});const errors=[];
 const tv=await browser.newPage();tv.on('pageerror',e=>errors.push(e.message));let polls=0;
 const snapshot={current:null,waiting:[],serving:[],events:[],last:0};
 await tv.route('**/api/state?*',async route=>{polls++;if(polls===2)return;await route.fulfill({json:{...snapshot,current:polls>=3?{id:101,called:1,prefix:'C',queue_seq:101,operator:3}:null}})});
 await tv.goto(base+'/tv');await tv.locator('.tv').waitFor();
 await tv.waitForFunction(()=>document.querySelector('.current .number')?.textContent.includes('C-101'),null,{timeout:15000});assert(polls>=3,'TV must recover from a never-completing poll');await tv.close();
 const kp=await browser.newPage();kp.on('pageerror',e=>errors.push(e.message));await kp.addInitScript(()=>{window.printCount=0;window.print=()=>window.printCount++});
 let submissions=[],holdNext=true,committed=false;
 await kp.route('**/api/ticket',async route=>{submissions.push(route.request().postDataJSON());const response=await route.fetch();assert.equal(response.status(),200);if(holdNext){holdNext=false;committed=true;return}await route.fulfill({response})});
 await kp.goto(base+'/kiosk');await kp.locator('[data-choice="0"]').click();await kp.locator('[data-choice="0"]').click();
 await kp.waitForFunction(()=>window.printCount===1,null,{timeout:25000});
 assert.equal(submissions.length,2);assert.equal(submissions[0].key,submissions[1].key);assert.deepEqual(submissions[0],submissions[1]);
 let state=await(await kp.request.get(base+'/api/state?1,-1')).json();assert.equal(state.waiting.length,1,'A committed request with lost reply must not create another receipt');
 await kp.waitForFunction(()=>!document.querySelector('.tile:disabled'));
 // Lose the next committed reply, then reload while still pending.
 holdNext=true;committed=false;
 await kp.locator('[data-choice="1"]').click();await kp.locator('[data-kiosk-lang=ru]').click();await kp.locator('[data-choice="0"]').click();
 while(!committed)await new Promise(r=>setTimeout(r,30));
 const saved=await kp.evaluate(()=>JSON.parse(sessionStorage.getItem('navbot-ticket-request')));assert.equal(saved.lang,'ru');
 await kp.reload();await kp.waitForFunction(()=>window.printCount===1);
 assert.equal(submissions.length,4);assert.equal(submissions[2].key,submissions[3].key);assert.equal(submissions[3].lang,'ru');assert.notEqual(submissions[0].key,submissions[2].key);
 state=await(await kp.request.get(base+'/api/state?1,-1')).json();assert.equal(state.waiting.length,2);
 assert.equal(await kp.evaluate(()=>sessionStorage.getItem('navbot-ticket-request')),null);
 // One browser document must only print its recovered receipt once.
 assert.equal(await kp.evaluate(()=>window.printCount),1);
 // Initial API outage must wait in the app until the server is reachable.
 const boot=await browser.newPage();boot.on('pageerror',e=>errors.push(e.message));let online=false,catalogHits=0,documents=0;
 boot.on('request',r=>{if(r.isNavigationRequest()&&r.frame()===boot.mainFrame())documents++});
 await boot.route('**/api/settings',async route=>{if(!online)return route.abort('failed');await route.continue()});
 await boot.route('**/api/catalog',async route=>{catalogHits++;if(catalogHits>1&&!online)return route.abort('failed');await route.continue()});
 await boot.goto(base+'/kiosk');await boot.locator('#retry-app').waitFor();while(catalogHits<2)await new Promise(r=>setTimeout(r,50));
 assert.equal(documents,1,'Do not navigate to a network error page while server is offline');online=true;
 await boot.locator('[data-choice="0"]').first().waitFor({timeout:12000});assert.equal(documents,2);await boot.close();
 assert.deepEqual(errors,[]);console.log('PASS TV poll deadline/reconnect; lost committed receipt reply retries same nonce; pending reload keeps original language/key; exactly one receipt per selection and one print; no page errors');
}finally{await browser?.close();if(server){server.kill();await new Promise(r=>server.exitCode!==null?r():server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}})().catch(e=>{console.error(e);process.exit(1)});
