const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
 const page=await browser.newPage(); page.setDefaultTimeout(15000);
 const base=process.env.NAVBOT_URL||'http://127.0.0.1:8081';
 await page.goto(base+'/login');
 await page.locator('#login-form [name=username]').fill('manager');
 await page.locator('#login-form [name=password]').fill('Navbot-Test-2026!');
 await page.locator('#login-form button[type=submit]').click();
 await page.waitForURL('**/manager');
 const response=await page.request.post(base+'/api/ticket',{data:{key:crypto.randomUUID(),lang:'uz',section:0,service:0}});
 assert.equal(response.status(),200);
 const ticket=await response.json();
 const code='A-'+String(ticket.id).padStart(3,'0');
 await page.locator('.request-row').filter({hasText:code}).click();
 await page.getByTestId('queue-call').click();
 const form=page.getByTestId('student-lookup');
 await form.waitFor();
 const id=form.locator('[name=hemis_id]');
 await id.fill('100000000001'); await form.locator('button[type=submit]').click();
 await page.locator('#student-result h3').getByText('Sinov Talaba Bir',{exact:true}).waitFor();
 await page.waitForTimeout(2200);
 assert.equal(await id.inputValue(),'100000000001');
 assert((await page.locator('#student-result').innerText()).includes('TEST-201'));
 await id.fill('999999999999'); await form.locator('button[type=submit]').click();
 await page.getByText('Talaba topilmadi. Ism-familiya yoki HEMIS IDni tekşiring.',{exact:true}).waitFor();
 assert(!(await page.locator('#student-result').innerText()).includes('Sinov Talaba Bir'));
 for(const value of [null,12,"' OR 1=1 --",'１２３４５６']){
 const result=await page.request.post(base+'/api/student',{data:{hemis_id:value}});
 assert.equal(result.status(),400);
 }
 await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/action')&&r.request().postDataJSON().action==='start'),page.getByTestId('queue-start').click()]);
 await Promise.all([page.waitForResponse(r=>r.url().endsWith('/api/action')&&r.request().postDataJSON().action==='finish'),page.getByTestId('queue-finish').click()]);
 console.log('PASS: authenticated lookup, student fields, polling preserves input/result, not found clears old data, malformed IDs rejected');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
