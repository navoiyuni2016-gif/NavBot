// Reproduce the public TV freeze modes against an isolated NavBoT demo server.
// Run: NAVBOT_URL=http://127.0.0.1:8121 node tests/tv-poll-recovery-browser.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const base=process.env.NAVBOT_URL||'http://127.0.0.1:8121';
const snapshot={current:null,serving:[],waiting:[{code:'A-001',operator:1,status:'waiting'}],last:66,events:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox'],headless:true});
 try{
  const page=await browser.newPage(),errors=[];let requests=0;
  page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/state?*',route=>{
   requests++;
   if(requests===1)return route.fulfill({json:{last:66}}); // Forces render failure.
   return route.fulfill({json:snapshot});
  });
  await page.goto(base+'/tv');
  await page.locator('.waiting .chip').getByText('A-001',{exact:true}).waitFor({timeout:7000});
  assert(requests>=2,'Render error must not stop polling');
  await delay(1700);
  assert(requests>=3,'An unchanged last call ID must not stop successful polling');
  assert.deepEqual(errors,[]);
  await page.close();

  const stalled=await browser.newPage();let attempts=0;
  await stalled.route('**/api/state?*',async route=>{
   attempts++;
   if(attempts===1){
    await delay(11000); // Longer than the 8s client timeout.
    try{await route.fulfill({json:snapshot})}catch{}
   }else await route.fulfill({json:snapshot});
  });
  await stalled.goto(base+'/tv');
  await stalled.locator('.waiting .chip').getByText('A-001',{exact:true}).waitFor({timeout:15000});
  assert(attempts>=2,'A hung fetch must be aborted and retried');
  console.log('PASS: TV polling resumes after bad JSON and an 8s hung request; unchanged call ID remains healthy.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
