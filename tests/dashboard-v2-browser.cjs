const { chromium } = require("playwright"),
  assert = require("node:assert/strict"),
  { spawn } = require("node:child_process"),
  fs = require("node:fs/promises"),
  path = require("node:path"),
  os = require("node:os"),
  net = require("node:net");
(async () => {
  let browser, server, temp;
  try {
    temp = await fs.mkdtemp(path.join(os.tmpdir(), "navbot-dash-"));
    const sock = net.createServer();
    await new Promise((r) => sock.listen(0, "127.0.0.1", r));
    const port = sock.address().port;
    await new Promise((r) => sock.close(r));
    const base = "http://127.0.0.1:" + port;
    server = spawn("python3", [
      path.resolve(__dirname, "../navbot/app.py"),
      "--port",
      String(port),
      "--db",
      temp + "/db.sqlite3",
      "--seed-demo",
    ]);
    server.stdout.resume();
    server.stderr.resume();
    for (let i = 0; i < 100; i++) {
      try {
        if ((await fetch(base + "/api/catalog")).ok) break;
      } catch {}
      await new Promise((r) => setTimeout(r, 100));
    }
    browser = await chromium.launch({
      executablePath: "/usr/bin/chromium",
      headless: true,
      args: ["--no-sandbox"],
    });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 1100 },
      }),
      page = await context.newPage(),
      errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(base + "/login");
    await page.locator("[name=username]").fill("admin");
    await page.locator("[name=password]").fill("Navbot-Test-2026!");
    await page.locator("#login-form button").click();
    await page.locator("[data-dashboard-metric=total]").waitFor();
    let result = await page.request.post(base + "/api/request/create", {
      data: {
        key: crypto.randomUUID(),
        channel: "phone",
        section: 0,
        service: 0,
        lang: "uz",
        hemis_id: "100000000001",
        identity_confirmed: true,
        content: "Test",
        note: "",
      },
    });
    assert.equal(result.status(), 200);
    await page.waitForFunction(
      () =>
        document.querySelector("[data-dashboard-metric=total] .value")
          ?.textContent === "1",
    );
    assert.equal(await page.locator("[data-dashboard-request]").count(), 0);
    await page.screenshot({
      path: "/tmp/navbot-dashboard-v2.png",
      fullPage: true,
    });
    for (const format of ["png", "pdf"]) {
      const download = page.waitForEvent("download");
      await page.locator(`[data-export=${format}]`).click();
      const d = await download;
      await d.saveAs("/tmp/navbot-dashboard." + format);
      const b = await fs.readFile("/tmp/navbot-dashboard." + format);
      assert(b.length > 10000);
      assert.equal(
        b.subarray(0, format === "pdf" ? 4 : 8).toString("hex"),
        format === "pdf" ? "25504446" : "89504e470d0a1a0a",
      );
    }
    await page.locator("[data-filter=course]").selectOption("2-kurs");
    assert.equal(
      await page.locator("[data-dashboard-metric=total] .value").innerText(),
      "1",
    );
    await page.setViewportSize({ width: 360, height: 800 });
    assert(
      await page
        .locator("body")
        .evaluate((e) => e.scrollWidth <= innerWidth + 1),
    );
    await page.screenshot({
      path: "/tmp/navbot-dashboard-v2-mobile.png",
      fullPage: true,
    });
    const wav=(await fs.readFile(path.resolve(__dirname,'../navbot/tv-tone.wav'))).toString('base64');
    for(const lang of ['uz','ru','en']){
      const upload=await page.request.post(base+'/api/admin/audio/upload',{data:{lang,slot:'intro',label:lang+'-sample',filename:'sample.wav',mime:'audio/wav',data:wav}});
      assert.equal(upload.status(),200);
    }
    await page.locator('#menu [data-view=audio]').click();
    await page.locator('[data-audio-language]').first().waitFor();
    assert.equal(await page.locator('[data-audio-language]').count(),3);
    assert.equal(await page.locator('[data-audio-language][open]').count(),0);
    assert.equal(await page.locator('#audio-library audio').count(),0);
    await page.locator('[data-audio-language=ru] summary').click();
    await page.locator('[data-audio-language=ru] audio').waitFor();
    assert.equal(await page.locator('[data-audio-language=ru] .audio-item strong').innerText(),'ru-sample');
    await page.locator('[data-audio-language=uz] summary').click();
    await page.locator('[data-audio-language=uz] audio').waitFor();
    await page.waitForFunction(()=>!document.querySelector('[data-audio-language=ru]').open);
    assert.equal(await page.locator('[data-audio-language=uz] .audio-item strong').innerText(),'uz-sample');
    assert.equal(await page.locator('[data-audio-language=uz] audio').getAttribute('preload'),'none');
    await page.locator('[data-audio-language=uz] [data-delete-audio]').click();
    await page.waitForFunction(()=>document.querySelector('[data-audio-language=uz] .badge')?.textContent==='0');
    const remaining=(await(await page.request.get(base+'/api/audio')).json()).clips;
    assert.deepEqual(remaining.map(c=>c.lang).sort(),['en','ru']);
    await page.locator('#audio-bulk [name=lang]').selectOption('ru');
    await page.locator('#audio-bulk [name=files]').setInputFiles({name:'s2.wav',mimeType:'audio/wav',buffer:Buffer.from(wav,'base64')});
    await page.locator('#audio-bulk button[type=submit]').click();
    await page.waitForFunction(()=>document.querySelector('[data-audio-language=ru] .badge')?.textContent==='2');
    assert.match(await page.locator('#audio-bulk-status').innerText(),/1/);

    const archiveCheck = await page.evaluate(() => {
      const original=state.requests;
      const base=original[0];
      state.requests=[base,{...base,id:999999,status:'closed',number:'NAV-ARCHIVE',queue_status:'called',ticket_id:999999}];
      state.selected=base.id;
      navigate('archive');
      const emptyHasCall=!!document.querySelector('#call-empty,[data-queue]');
      const archiveWidth=document.querySelector('.archive-layout').getBoundingClientRect().width;
      if(Math.abs(document.querySelector('.requests-list').getBoundingClientRect().width-archiveWidth)>2)throw Error('Archive must fill work area');
      if(getComputedStyle(document.querySelector('.archive-detail')).display!=='none')throw Error('Empty detail should not reserve space');
      const filters=[...document.querySelectorAll('#request-filters button')].map(b=>b.dataset.filter);
      const ids=[...document.querySelectorAll('#request-list [data-id]')].map(b=>Number(b.dataset.id));
      state.selected=999999;state.detailVersion=null;renderDetail();
      const archiveHasControls=!!document.querySelector('.queue-controls,[data-queue],#open-active-queue,[data-telegram-open],#clear-current-requests');
      const hasHistory=!!document.querySelector('.timeline');
      if(getComputedStyle(document.querySelector('.requests-list')).display!=='none')throw Error('Detail must open separately');
      document.querySelector('#archive-back').click();
      if(getComputedStyle(document.querySelector('.requests-list')).display==='none')throw Error('Back must restore archive');
      state.requests=original;state.selected=null;navigate('requests');
      const intakeHasCall=!!document.querySelector('#call-empty');
      return {emptyHasCall,filters,ids,archiveHasControls,hasHistory,intakeHasCall};
    });
    assert.deepEqual(archiveCheck,{emptyHasCall:false,filters:['closed'],ids:[999999],archiveHasControls:false,hasHistory:true,intakeHasCall:true});
    const paginationCheck=await page.evaluate(()=>{
      const original=state.requests,base=original[0],stamp=new Date().toISOString();
      state.requests=Array.from({length:125},(_,i)=>({...base,id:800000+i,number:'ARCH-'+i,status:'closed',closed_at:stamp,section:i%3,channel:i%2?'phone':'kiosk'}));
      state.selected=null;navigate('archive');
      const first=document.querySelectorAll('#request-list [data-id]').length;
      document.querySelector('[data-archive-page="2"]').click();
      const second=document.querySelectorAll('#request-list [data-id]').length;
      const secondId=document.querySelector('#request-list [data-id]').dataset.id;
      document.querySelector('#request-list [data-id]').click();document.querySelector('#archive-back').click();
      const returnId=document.querySelector('#request-list [data-id]').dataset.id;
      const form=document.querySelector('#archive-filter-form');form.elements.channel.value='phone';form.elements.section.value='1';form.requestSubmit();
      const filtered=Number(document.querySelector('#request-count').textContent);
      const filteredPage=document.querySelector('.archive-pagination nav strong').textContent;
      document.querySelector('#archive-filter-reset').click();
      const restored=Number(document.querySelector('#request-count').textContent);
      document.querySelector('[data-archive-page="2"]').click();document.querySelector('[data-archive-page="3"]').click();
      const last=document.querySelectorAll('#request-list [data-id]').length;
      const search=document.querySelector('#request-search');search.value='ARCH-124';search.dispatchEvent(new Event('input'));
      const searchCount=document.querySelectorAll('#request-list [data-id]').length;
      const searchPage=document.querySelector('.archive-pagination nav strong').textContent;
      state.requests=original;state.search='';Object.keys(archiveFilters).forEach(k=>archiveFilters[k]='');archivePage=1;state.selected=null;navigate('requests');
      return {first,second,samePage:secondId===returnId,filtered,filteredPage,restored,last,searchCount,searchPage};
    });
    assert.deepEqual(paginationCheck,{first:50,second:50,samePage:true,filtered:21,filteredPage:'1 / 1',restored:125,last:25,searchCount:1,searchPage:'1 / 1'});
    await page.locator("#menu [data-view=service-access]").click();
    await page.locator("[data-service-manager]").first().waitFor();
    const form = page.locator("[data-service-manager]").first();
    await form.locator("input").fill("Takroriy xato");
    await form.locator("button").click();
    await page.getByText("Qabul bloklangan", { exact: true }).waitFor();
    const managers = (
      await (await page.request.get(base + "/api/manager-service")).json()
    ).managers;
    const blocked = managers.find((m) => m.reason);
    const mc = await browser.newContext(),
      mp = await mc.newPage();
    await mp.goto(base + "/login");
    await mp.locator("[name=username]").fill(blocked.username);
    await mp.locator("[name=password]").fill("Navbot-Test-2026!");
    await mp.locator("#login-form button").click();
    await mp.locator("[data-dashboard-metric=total]").waitFor();
    assert.equal((await mp.request.get(base + "/api/requests")).status(), 200);
    assert.equal(
      (
        await mp.request.post(base + "/api/action", {
          data: { operator: blocked.operator, action: "call" },
        })
      ).status(),
      403,
    );
    await mc.close();
    for (const role of ["manager2", "executor", "head", "director"]) {
      const c = await browser.newContext(),
        p = await c.newPage();
      await p.goto(base + "/login");
      await p.locator("[name=username]").fill(role);
      await p.locator("[name=password]").fill("Navbot-Test-2026!");
      await p.locator("#login-form button").click();
      await p.locator("[data-dashboard-metric=total]").waitFor();
      const rows = (await (await p.request.get(base + "/api/requests")).json())
        .requests;
      assert.equal(
        await p.locator("[data-dashboard-metric=total] .value").innerText(),
        String(rows.length),
      );
      await c.close();
    }
    assert.deepEqual(errors, []);
    console.log(
      "PASS dashboard totals, filters, PNG/PDF downloads, mobile layout, service suspension UI, no page errors",
    );
  } finally {
    await browser?.close();
    if (server) {
      server.kill();
      await new Promise((r) =>
        server.exitCode !== null ? r() : server.once("exit", r),
      );
    }
    if (temp) await fs.rm(temp, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
