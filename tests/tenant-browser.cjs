const {chromium}=require('playwright'),assert=require('node:assert/strict'),{spawn,execFileSync}=require('node:child_process'),fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path'),net=require('node:net');
(async()=>{let browser,temp;const servers=[];try{
 temp=await fs.mkdtemp(path.join(os.tmpdir(),'navbot-branding-'));const root=path.resolve(__dirname,'..'),tenants=[];
 for(const letter of ['a','b']){
  let port;do{const sock=net.createServer();await new Promise(r=>sock.listen(0,'127.0.0.1',r));port=sock.address().port;await new Promise(r=>sock.close(r))}while(port>60000||port<10000);
  const spec=JSON.parse(await fs.readFile(root+'/sales/examples/university-'+letter+'.json'));spec.port=port;const profile=temp+'/'+letter+'.json',db=temp+'/'+letter+'/navbot.sqlite3';await fs.writeFile(profile,JSON.stringify(spec));
  execFileSync('python3',[root+'/sales/tenant.py','init-db',profile,'--db',db]);
  execFileSync('python3',['-c',"import sys;sys.path.insert(0,sys.argv[1]);import sqlite3,auth;d=sqlite3.connect(sys.argv[2]);d.row_factory=sqlite3.Row;auth.create_user(d,{'username':'admin','full_name':'Tenant Admin','role':'admin','department':'Registrar','operator':None,'password':'Tenant-Browser-2026!'});d.execute('UPDATE users SET must_change_password=0');d.commit();d.close()",root+'/navbot',db]);
  const process=spawn('python3',[root+'/navbot/app.py','--db',db,'--port',String(port),'--tenant',spec.id]);process.stdout.resume();process.stderr.resume();servers.push(process);
  for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:'+port+'/api/catalog',{headers:{Host:spec.domain}})).ok)break}catch{}await new Promise(r=>setTimeout(r,50))}
  tenants.push({...spec,url:'http://'+spec.domain+':'+port});
 }
 browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--no-proxy-server','--host-resolver-rules=MAP a.navbot.example.uz 127.0.0.1,MAP b.navbot.example.uz 127.0.0.1']});
 const context=await browser.newContext({viewport:{width:1440,height:1050}}),errors=[];
 for(const tenant of tenants){
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));await page.goto(tenant.url+'/login');await page.locator('#login-form').waitFor();assert.match(await page.locator('.institution').innerText(),new RegExp(tenant.university_short[0],'i'));
  await page.locator('[name=username]').fill('admin');await page.locator('[name=password]').fill('Tenant-Browser-2026!');await page.locator('#login-form button').click();await page.locator('.dash-heading').waitFor();assert.match(await page.locator('.dash-heading').innerText(),new RegExp(tenant.university_short[0],'i'));assert.equal(await page.locator('body').innerText().then(text=>text.includes('ToşDÖTAU')),false);
  await page.screenshot({path:'/tmp/navbot-tenant-'+tenant.id+'.png',fullPage:true});
  await page.locator('[data-view=execution]').click();await page.locator('#execution-board').waitFor();assert.match(await page.locator('#execution-board .eyebrow').innerText(),new RegExp(tenant.university_short[0],'i'));
  await page.locator('[data-view=settings]').click();await page.locator('#settings-form').waitFor();assert.equal(await page.locator('[name=university_short_0]').inputValue(),tenant.university_short[0]);
  await page.goto(tenant.url+'/kiosk');await page.locator('.kiosk-grid').waitFor();assert.match(await page.locator('#brand').innerText(),new RegExp(tenant.university[0]));await page.goto(tenant.url+'/tv');await page.locator('#brand').waitFor();assert.match(await page.locator('#brand').innerText(),new RegExp(tenant.university_short[0],'i'));await page.close();
 }
 assert.deepEqual(errors,[]);console.log('PASS two tenant domains: isolated branding on login, dashboard, execution, settings, kiosk and TV; no page errors');
}finally{await browser?.close();for(const server of servers){server.kill();await new Promise(r=>server.exitCode!==null?r():server.once('exit',r))}if(temp)await fs.rm(temp,{recursive:true,force:true})}})().catch(error=>{console.error(error);process.exit(1)});
