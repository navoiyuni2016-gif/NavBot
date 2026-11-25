/* Aggregate-only dashboard and local PNG/PDF export. No student identities exported. */
window.NavDashboard = (() => {
  const dateFormat = new Intl.DateTimeFormat("sv-SE", {
    timeZone: "Asia/Tashkent",
  });
  const day = (value) => {
    const d = new Date(value);
    return Number.isNaN(d.valueOf()) ? "" : dateFormat.format(d);
  };
  let filters = { faculty: "", course: "" };
  const groups = (rows, key) =>
    Object.entries(
      rows.reduce((a, r) => {
        const name = key(r);
        a[name] = (a[name] || 0) + 1;
        return a;
      }, Object.create(null)),
    ).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const faculty = (r) => r.student?.faculty || "Talaba biriktirilmagan",
    course = (r) =>
      r.student?.course ? `${r.student.course}-kurs` : "Kurs noma’lum";
  // Course order is academic, independent of request volume; unknown stays last.
  const courseGroups = (rows) => groups(rows, course).sort(([a], [b]) => {
    const rank = (name) => /^\d+-kurs$/.test(name) ? Number.parseInt(name, 10) : Infinity;
    return rank(a) - rank(b) || a.localeCompare(b);
  });
  let serviceSection=0;
  function model(source, catalog) {
    const rows = source.filter(
      (r) =>
        (!filters.faculty || faculty(r) === filters.faculty) &&
        (!filters.course || course(r) === filters.course),
    );
    const now = Date.now();
    return {
      total: rows.length,
      active: rows.filter((r) => r.status !== "closed").length,
      closed: rows.filter((r) => r.status === "closed").length,
      overdue: rows.filter(
        (r) =>
          r.status !== "closed" && r.deadline && Date.parse(r.deadline) < now,
      ).length,
      sections: groups(
        rows,
        (r) => catalog[r.section]?.[0]?.[0] || "Bölim noma’lum",
      ),
      services: catalog.map((entry,section)=>({
        label:entry[0][0],total:rows.filter(r=>r.section===section).length,
        items:entry[1].map((names,service)=>[names[0],rows.filter(r=>r.section===section&&r.service===service).length])
      })),
      faculties: groups(rows, faculty),
      courses: courseGroups(rows),
      daily: Array.from({ length: 7 }, (_, i) => {
        const date = day(now - (6 - i) * 86400000);
        return [date, rows.filter((r) => day(r.created_at) === date).length];
      }),
    };
  }
  const labels = [
    ["Jami murojaatlar", "total"],
    ["Faol murojaatlar", "active"],
    ["Yakunlangan", "closed"],
    ["Keçikkan", "overdue"],
  ];
  function render(host, source, catalog, esc) {
    const m = model(source, catalog);
    document.body.classList.add("dashboard-screen");
    const colors = ["#8374ff", "#2bd36f", "#69d7fa", "#da8dff", "#ffbd36"];
    const barChart = (items, vertical = false) => {
      if (!items.length) return '<p class="dash-empty">Hali ma’lumot yöq</p>';
      const max = Math.max(1, ...items.map((x) => x[1]));
      if (vertical)
        return `<div class="dash-column-chart">${items.map(([name, count], i) => `<div class="dash-column" title="${esc(name)}: ${count}"><strong>${count}</strong><div class="dash-column-track"><i style="height:${(count / max) * 100}%;background:${colors[i % colors.length]}"></i></div><span>${esc(name)}</span></div>`).join("")}</div>`;
      return `<div class="dash-horizontal-chart">${items.map(([name, count], i) => `<div class="dash-hrow"><span>${esc(name)}</span><div class="dash-htrack"><i style="width:${(count / max) * 100}%;background:${colors[i % colors.length]}"></i></div><strong>${count}</strong></div>`).join("")}<div class="dash-axis"><span>0</span><span>${max > 1 ? Math.round(max / 2) : ""}</span><span>${max}</span></div></div>`;
    };
    const options = (key, items) =>
      `<option value="">Barçasi</option>` +
      items
        .map(
          ([name]) =>
            `<option ${filters[key] === name ? "selected" : ""} value="${esc(name)}">${esc(name)}</option>`,
        )
        .join("");
    const statuses = [
      ["Yakunlangan", m.closed, "#2bd36f"],
      ["Faol murojaatlar", m.active, "#8374ff"],
    ];
    const ratio = m.total ? (m.closed / m.total) * 100 : 0;
    host.innerHTML = NavI18n.html`<div class="official-dashboard">
      <header class="dash-heading"><div><p>ToşDÖTAU · REGISTRATOR OFISI</p><h1>Faoliyat körsatkiçlari</h1><span>${day(Date.now())} · Toşkent vaqti</span></div><div class="dash-export"><button data-export="png">PNG yuklab oliş</button><button data-export="pdf">PDF yuklab oliş</button></div></header>
      <div class="dash-filters"><label>Fakultet<select data-filter="faculty">${options("faculty", groups(source, faculty))}</select></label><label>Kurs<select data-filter="course">${options("course", courseGroups(source))}</select></label><span>Umumiy natijalar: barça sanalar<br>Dinamika: oxirgi 7 kun</span></div>
      <div class="dash-kpis">${labels.map(([name, key]) => `<article data-dashboard-metric="${key}" class="dash-kpi-${key}"><span>${esc(NavI18n.t(name))}</span><div class="dash-kpi-number"><strong class="value">${m[key]}</strong><small>ta</small></div><footer>${key === "closed" ? (m.total ? Math.round(ratio) : 0) + "% bajarilgan" : "Tanlangan kesim böyiça"}</footer></article>`).join("")}</div>
      <div class="dash-panels">
        <section><header><h2>Sohalar böyiça murojaatlar</h2><span class="dash-tag">Jami ${m.total} ta</span></header>${barChart(m.sections)}</section>
        <section><header><h2>Murojaatlar holati</h2><span class="dash-tag">Umumiy</span></header><div class="dash-donut-layout"><div class="dash-donut" style="--segments:${m.total ? `#2bd36f 0% ${ratio}%,#8374ff ${ratio}% 100%` : "#2b3752 0% 100%"}" role="img" aria-label="Jami ${m.total}, yakunlangan ${m.closed}, faol ${m.active}"><div><strong>${m.total} <small>ta</small></strong><span>Jami murojaatlar</span></div></div><div class="dash-legend">${statuses.map(([name, count, color]) => `<div><i style="background:${color}"></i><span>${esc(NavI18n.t(name))}</span><strong>${count}</strong></div>`).join("")}<p>Keçikkan murojaatlar faol murojaatlar tarkibiga kiradi.</p></div></div></section>
        <section class="dash-wide dash-service-panel"><header><div><h2>Xizmatlar kesimida murojaatlar</h2><p>Bölim içidagi har bir xizmat böyiça</p></div><label class="dash-service-select">Xizmat bölimi<select id="dashboard-service-section">${m.services.map((section,i)=>`<option value="${i}" ${serviceSection===i?'selected':''}>${esc(section.label)}</option>`).join('')}</select></label></header><div class="dash-service-head"><strong>${esc(m.services[serviceSection]?.label||'')}</strong><span class="dash-tag" id="dashboard-service-total">${m.services[serviceSection]?.total||0} ta</span></div><div id="dashboard-service-bars">${barChart(m.services[serviceSection]?.items||[])}</div></section>
        <section class="dash-wide"><header><h2>Murojaatlar dinamikasi</h2><span class="dash-tag">Oxirgi 7 kun</span></header>${barChart(
          m.daily.map(([date, count]) => [date.slice(5), count]),
          true,
        )}</section>
        <section><header><h2>Fakultetlar kesimida</h2><span class="dash-tag">Murojaatlar soni</span></header>${barChart(m.faculties)}</section>
        <section><header><h2>Kurslar kesimida</h2><span class="dash-tag">Murojaatlar soni</span></header>${barChart(m.courses, true)}</section>
      </div><p class="dash-foot">NAVBOT · Vakolatingiz doirasidagi ma’lumotlar · Jami ${m.total} ta murojaat</p><div role="status" id="dash-export-status"></div></div>`;
    host.querySelector('#dashboard-service-section').onchange=event=>{serviceSection=Number(event.target.value);render(host,source,catalog,esc)};
    host.querySelectorAll("[data-filter]").forEach(
      (el) =>
        (el.onchange = () => {
          filters[el.dataset.filter] = el.value;
          render(host, source, catalog, esc);
        }),
    );
    host.querySelectorAll("[data-export]").forEach(
      (button) =>
        (button.onclick = async () => {
          const buttons = host.querySelectorAll("[data-export]");
          buttons.forEach((b) => (b.disabled = true));
          try {
            await exportFile(m, button.dataset.export);
            host.querySelector("#dash-export-status").textContent =
              "Fayl yuklab olindi";
          } catch (e) {
            host.querySelector("#dash-export-status").textContent =
              "Yuklab oliş amalga oşmadi. Qayta urinib köring.";
          } finally {
            buttons.forEach((b) => (b.disabled = false));
          }
        }),
    );
  }
  function canvas(m) {
    const sections = [
      ["Murojaatlar dinamikasi · oxirgi 7 kun", m.daily],
      ["Sohalar böyiça", m.sections],
      ...m.services.map(section=>[section.label+" · xizmatlar",section.items]),
      ["Fakultetlar kesimida", m.faculties],
      ["Kurslar kesimida", m.courses],
    ];
    const c = document.createElement("canvas");
    c.width = 1600;
    c.height =
      440 +
      sections.reduce(
        (n, [title, items]) => n + 100 + Math.max(1, items.length) * 52,
        0,
      );
    const x = c.getContext("2d");
    x.fillStyle = "#18243d";
    x.fillRect(0, 0, c.width, c.height);
    x.fillStyle = "#0f1a30";
    x.fillRect(0, 0, 1600, 170);
    x.fillStyle = "#fff";
    x.font = "bold 40px sans-serif";
    x.fillText("ToşDÖTAU · Registrator ofisi", 60, 66);
    x.font = "26px sans-serif";
    x.fillText("Faoliyat körsatkiçlari · " + day(Date.now()), 60, 115);
    x.fillText(
      "Fakultet: " +
        (filters.faculty || "Barçasi") +
        " · Kurs: " +
        (filters.course || "Barçasi"),
      60,
      152,
      1480,
    );
    labels.forEach(([title, key], i) => {
      const left = 60 + i * 380;
      x.fillStyle = ["#118ca7", "#7139e7", "#cf6617", "#b74663"][i];
      x.fillRect(left, 210, 350, 150);
      x.fillStyle = "#ffffff";
      x.font = "23px sans-serif";
      x.fillText(title, left + 22, 250);
      x.fillStyle = "#f3f6ff";
      x.font = "bold 52px sans-serif";
      x.fillText(String(m[key]), left + 22, 320);
    });
    let y = 420;
    for (const [title, items] of sections) {
      x.fillStyle = "#f3f6ff";
      x.font = "bold 28px sans-serif";
      x.fillText(title, 60, y);
      y += 48;
      const max = Math.max(1, ...items.map((v) => v[1]));
      for (const [name, count] of items) {
        x.font = "22px sans-serif";
        x.fillStyle = "#e6edfc";
        x.fillText(name, 60, y, 850);
        x.fillStyle = "#8374ff";
        x.fillRect(950, y - 20, (count / max) * 450, 24);
        x.fillStyle = "#f3f6ff";
        x.fillText(String(count), 1430, y);
        y += 52;
      }
      if (!items.length) {
        x.font = "22px sans-serif";
        x.fillText("Hali ma’lumot yöq", 60, y);
        y += 52;
      }
      y += 52;
    }
    x.font = "20px sans-serif";
    x.fillStyle = "#b5c4df";
    x.fillText(
      "NAVBOT · Umumiy natijalar: barça sanalar · Dinamika: oxirgi 7 kun",
      60,
      c.height - 30,
    );
    return c;
  }
  function pdf(c) {
    const data = atob(c.toDataURL("image/jpeg", 0.94).split(",")[1]),
      w = 842,
      h = (w * c.height) / c.width,
      stream = `q ${w} 0 0 ${h} 0 0 cm /Im0 Do Q`;
    let out = "%PDF-1.4\n",
      offset = [0];
    const obj = (id, value) => {
      offset[id] = out.length;
      out += `${id} 0 obj\n${value}\nendobj\n`;
    };
    obj(1, "<< /Type /Catalog /Pages 2 0 R >>");
    obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>");
    obj(
      3,
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${w} ${h}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>`,
    );
    obj(
      4,
      `<< /Type /XObject /Subtype /Image /Width ${c.width} /Height ${c.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${data.length} >>\nstream\n${data}\nendstream`,
    );
    obj(5, `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
    const at = out.length;
    out += "xref\n0 6\n0000000000 65535 f \n";
    for (let i = 1; i <= 5; i++)
      out += String(offset[i]).padStart(10, "0") + " 00000 n \n";
    out += `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${at}\n%%EOF`;
    return new Blob([Uint8Array.from(out, (c) => c.charCodeAt(0))], {
      type: "application/pdf",
    });
  }
  async function exportFile(m, format) {
    const c = canvas(m);
    const blob =
      format === "pdf"
        ? pdf(c)
        : await new Promise((resolve) => c.toBlob(resolve, "image/png"));
    if (!blob) throw Error("Export");
    const url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "NAVBOT-dashboard-" + day(Date.now()) + "." + format;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  return { render, model };
})();
