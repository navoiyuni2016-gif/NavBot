// Three-language kiosk -> reception -> public TV/tablo acceptance.
// Run against a server started with --seed-demo and a disposable database.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 context.setDefaultTimeout(15000);
 const errors=[];
 context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const kiosk=await context.newPage(), operator=await context.newPage(), tv=await context.newPage(), tablo=await context.newPage();
 const base=process.env.NAVBOT_URL||'http://127.0.0.1:8081';
 await tv.addInitScript(()=>{
  window.spoken=[];
  window.speechSynthesis.speak=u=>{window.spoken.push({lang:u.lang,text:u.text,volume:u.volume});queueMicrotask(()=>u.onend?.());};
 });
 await Promise.all([kiosk.goto(base+'/kiosk'),operator.goto(base+'/login'),tv.goto(base+'/tv'),tablo.goto(base+'/tablo?id=1')]);
 await operator.locator('#login-form [name=username]').fill('manager');
 await operator.locator('#login-form [name=password]').fill('Navbot-Test-2026!');
 await operator.locator('#login-form button[type=submit]').click();
 await operator.waitForURL('**/manager');
 await operator.locator('#request-list').waitFor();
 assert.equal(await tv.locator('#audio-toggle').count(),0,'TV has no manual audio-enable control');
 await tv.locator('.waiting').waitFor();
 const current=await tv.locator('.current').boundingBox();
 const serving=await tv.locator('.serving').boundingBox();
 const waiting=await tv.locator('.waiting').boundingBox();
 assert(current.x+current.width<=serving.x+2,'TV current call must be left of serving panel');
 assert(waiting.y>=Math.max(current.y+current.height,serving.y+serving.height)-2,'Waiting queues must occupy bottom row');
 assert(waiting.width>current.width&&waiting.width>serving.width,'Waiting row spans both columns');
 const results=[];
 for(const [language,receiptLabel,timeLabel,voice] of [['Özbekça','Navbat raqami','Vaqt','uz-UZ'],['Русский','Номер очереди','Время','ru-RU'],['English','Queue number','Time','en-GB']]){
  await kiosk.getByRole('button',{name:language,exact:true}).click();
  await kiosk.locator('.tile').first().click();
  await kiosk.evaluate(()=>{window.printInvoked=0;window.print=()=>{window.printInvoked+=1}});
  await kiosk.locator('.tile').first().click();
  await kiosk.locator('.receipt').waitFor();
  const receipt=await kiosk.locator('.receipt').innerText();
  assert(receipt.includes(receiptLabel));
  assert(receipt.includes(timeLabel),'Receipt time label follows student language');
  assert(!receipt.includes('Invalid Date'));
  const number=await kiosk.locator('.receipt h2').innerText(); console.log('Testing',language,number);
  await kiosk.waitForFunction(()=>window.printInvoked===1,null,{timeout:5000});
  await kiosk.locator('#print-ticket').click();
  await kiosk.locator('#print-ticket').click();
  assert.equal(await kiosk.evaluate(()=>window.printInvoked),3,'Automatic print plus two reprints invokes printing without new ticket');
  assert.equal(await kiosk.locator('.receipt h2').innerText(),number);
  await tv.locator('.waiting').getByText(number,{exact:true}).waitFor();
  const queueRow=operator.locator('.request-row').filter({hasText:number});
  if(!results.length){await queueRow.focus();await operator.waitForTimeout(2200);assert(await queueRow.evaluate(el=>document.activeElement===el),'Polling must preserve keyboard focus on queue row')}
  await queueRow.click();
  await operator.getByTestId('queue-call').click();
  await tv.locator('.current .number').getByText(number,{exact:true}).waitFor();
  await tablo.locator('.number').getByText(number,{exact:true}).waitFor();
  await tv.waitForFunction(([v,n])=>window.spoken.some(s=>s.lang===v&&s.text.includes(n)),[voice,number],{timeout:10000});
  const firstCallCount=await tv.evaluate(()=>window.spoken.length);
  await operator.locator('[data-queue=recall]').click();
  await tv.waitForFunction(n=>window.spoken.length>n,firstCallCount,{timeout:10000});
  const blink=await tv.locator('.current').evaluate(el=>getComputedStyle(el).animationIterationCount);
  assert.equal(blink,'3','Call card flashes exactly three times');
  await operator.getByTestId('queue-start').click();
  await tv.locator('.serving').getByText('1-operator · '+number,{exact:true}).waitFor();
  assert(!(await tv.locator('.waiting').innerText()).includes(number));
  await operator.getByTestId('queue-finish').click();
  await tablo.locator('.number').getByText('—',{exact:true}).waitFor();
  await tv.waitForFunction(n=>!document.querySelector('#content').textContent.includes(n),number,{timeout:10000});
  const publicText=await tv.locator('body').innerText();
  assert(!publicText.includes('Sinov Talaba'));
  assert(!publicText.includes('100000000001'));
  assert(!publicText.includes('Transkript'));
  results.push({language,number,receipt:true,reprint:true,call:true,recall:true,serving:true,finish:true,speechLanguage:voice});
  await kiosk.locator('#new-ticket').click();
 }
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({results,pageErrors:errors,layout:'left call / right serving / bottom waiting verified at1440x1000',limits:'Speech API language/text verified; physical sound and printer not tested.'},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
