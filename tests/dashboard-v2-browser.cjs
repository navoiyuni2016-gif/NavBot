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
