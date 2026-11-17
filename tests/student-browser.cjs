const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage(); page.setDefaultTimeout(15000);
 await page.goto((process.env.NAVBOT_URL||'http://127.0.0.1:8081')+'/operator?id=1');
 const id=page.getByLabel('HEMIS ID', {exact:true});
 await id.fill('100000000001'); await page.getByRole('button',{name:'Qidirish',exact:true}).click();
 await page.locator('#student-result').getByText('F.I.Sh.: Sinov Talaba Bir',{exact:true}).waitFor();
 await page.waitForTimeout(1600);
 assert.equal(await id.inputValue(),'100000000001');
 assert((await page.locator('#student-result').innerText()).includes('TEST-201'));
 await id.fill('999999999999'); await page.getByRole('button',{name:'Qidirish',exact:true}).click();
 await page.getByText('Talaba topilmadi. HEMIS IDni tekshiring.',{exact:true}).waitFor();
 assert(!(await page.locator('#student-result').innerText()).includes('Sinov Talaba Bir'));
 for(const value of [null,12,"' OR 1=1 --",'１２３４５６']){
 const response=await page.request.post(new URL('/api/student',page.url()).href,{data:{hemis_id:value}});
 assert.equal(response.status(),400);
 }
 console.log('PASS: lookup, student fields, polling preserves input/result, not found clears old data, malformed IDs rejected');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
