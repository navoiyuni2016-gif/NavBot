const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext();
 context.setDefaultTimeout(15000);
 const errors=[];
 context.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
 const kiosk=await context.newPage(), operator=await context.newPage(), tv=await context.newPage(), tablo=await context.newPage();
 const base=process.env.NAVBOT_URL||'http://127.0.0.1:8081';
 await tv.addInitScript(()=>{
  window.spoken=[];
  window.speechSynthesis.speak=u=>window.spoken.push({lang:u.lang,text:u.text});
 });
 await Promise.all([kiosk.goto(base+'/kiosk'),operator.goto(base+'/operator?id=1'),tv.goto(base+'/tv'),tablo.goto(base+'/tablo?id=1')]);
 await tv.getByRole('button',{name:'Ovozni yoqiş',exact:true}).click();
 const results=[];
 for(const [language,receiptLabel,voice] of [['Özbekça','Navbat raqami','uz-UZ'],['Русский','Номер очереди','ru-RU'],['English','Queue number','en-GB']]){
  await kiosk.getByRole('button',{name:language,exact:true}).click();
  await kiosk.locator('.tile').first().click();
  await kiosk.locator('.tile').first().click();
  await kiosk.locator('.receipt').waitFor();
  assert((await kiosk.locator('.receipt').innerText()).includes(receiptLabel));
  const number=await kiosk.locator('.receipt h2').innerText(); console.log('Testing',language,number);
  // Exercise the print action without opening a system dialog.
  await kiosk.evaluate(()=>{window.print=()=>window.printInvoked=true});
  await kiosk.locator('#content > button').first().click();
  assert(await kiosk.evaluate(()=>window.printInvoked));
  await tv.locator('.waiting').getByText(number,{exact:true}).waitFor();
  await operator.getByRole('button',{name:'Keyingi raqamni çaqiriş',exact:true}).click();
  await tv.locator('.current .number').getByText(number,{exact:true}).waitFor();
  await tablo.locator('.number').getByText(number,{exact:true}).waitFor();
  await tv.waitForFunction(v=>window.spoken.some(s=>s.lang===v),voice);
  await operator.getByRole('button',{name:'Qayta çaqiriş',exact:true}).click();
  await operator.getByRole('button',{name:'Qabulni boşlaş',exact:true}).click();
  await tv.locator('.serving').getByText('1-operator · '+number,{exact:true}).waitFor();
  await operator.getByRole('button',{name:'Qabulni tugatiş',exact:true}).click();
  await tablo.locator('.number').getByText('—',{exact:true}).waitFor();
  await tv.waitForFunction(n=>!document.querySelector('#content').textContent.includes(n),number,{timeout:10000});
  results.push({language,number,receipt:true,printAction:true,call:true,recall:true,serving:true,finish:true,speechLanguage:voice});
  await kiosk.locator('#content > button').last().click();
 }
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({results,pageErrors:errors,limits:'Speech API language/text verified; physical sound and printer not tested.'},null,2));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
