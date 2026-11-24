/* Local vector icons for every kiosk section and service. */
window.NavKioskDesign = (() => {
  const paths = {
    cap: '<path d="M2 9 12 4l10 5-10 5L2 9Z"/><path d="M6 12v6c4 3 8 3 12 0v-6M21 10v8"/>',
    bulb: '<path d="M8 17c0-3-3-4-3-8a7 7 0 0 1 14 0c0 4-3 5-3 8ZM9 20h6M10 23h4M12 0v2M1 9h2M21 9h2M3 2l2 2M19 4l2-2"/><path d="m11 6 2 0 1 2 2 1-1 2-2 1-1 2-2-1-1-2-1-2 2-1Z"/>',
    globe: '<circle cx="12" cy="11" r="8"/><ellipse cx="12" cy="11" rx="4" ry="8"/><path d="M4 11h16M6 6h12M6 16h12"/><path d="M3 15c-5 7 14 8 20-4" fill="none"/>',
    finance: '<path d="M11 19V9h4v10M17 19V5h4v14M9 7l5-4 4 1 4-4M19 0h3v3"/><ellipse cx="5" cy="13" rx="4" ry="2"/><path d="M1 13v6c0 3 8 3 8 0v-6M1 16c2 2 6 2 8 0"/>',
    clipboard: '<path d="M8 4H4v18h15V4h-4M9 2h5v4H9Z"/><path d="m7 11 2 2 3-4M7 17l2 2 3-4M14 11h2M14 17h2"/>',
    medical: '<path d="M8 4H4v18h16V4h-4M9 2h6v4H9Z"/><path d="M10 10h4v3h3v4h-3v3h-4v-3H7v-4h3Z"/>',
    document: '<path d="M4 2h11l5 5v15H4ZM14 2v6h6M7 11h9M7 15h7M7 19h5"/><path d="m15 21 6-7 2 2-6 7-3 1Z"/>',
    hemis: '<path d="M4 3h16v14H4ZM2 20h20l-2 2H4Z"/><text x="12" y="12" text-anchor="middle" font-size="5" font-weight="900" stroke="none" fill="white">HEMIS</text>',
    tools: '<path d="m4 2 4 4-2 2-4-4c-2 5 2 8 6 7l10 11 4-4L11 8c1-4-2-8-7-6Z"/><path d="m3 21 6-6M14 9l6-6 2 2-6 6"/>',
    layers: '<path d="m2 8 10-6 10 6-10 6ZM2 13l10 6 10-6M2 18l10 6 10-6"/>',
    microscope: '<path d="m10 2 6 4-5 9-6-4ZM9 14l-2 3M14 8c9 2 8 12-1 13M3 22h19M4 17h8M11 21v-4"/>',
    mentor: '<path d="M10 2h12v13H10M13 6h6M13 9h4"/><circle cx="5" cy="8" r="3"/><path d="M1 22v-7c0-4 8-4 8 0v7M5 16v6M8 14l6-3"/>',
    sprout: '<path d="M12 15V7M12 10C5 11 2 6 3 2c5 0 9 2 9 8ZM12 9c0-6 4-8 9-8 0 5-3 8-9 8ZM1 18l5-3 7 2 1 3 7-5 2 2-9 7-8-3H1Z"/>',
    people: '<circle cx="12" cy="7" r="4"/><circle cx="4" cy="10" r="3"/><circle cx="20" cy="10" r="3"/><path d="M6 22v-5c0-6 12-6 12 0v5ZM1 21v-5q0-4 5-3M23 21v-5q0-4-5-3"/>',
    plane: '<path d="m1 14 8-3 7-9q2-2 4 0l-4 9 7 4-2 2-8-2-5 6-3-1 2-6-5 2Z"/>',
    book: '<path d="M12 5C8 2 4 2 1 4v17c4-2 8-2 11 1 3-3 7-3 11-1V4c-4-2-8-2-11 1ZM12 5v17M4 7h4M4 11h4M16 7h4M16 11h4"/>',
    handshake: '<path d="m1 8 5-5 5 2 3-1 9 7-4 10-4 2-9-7-2-4ZM8 8l4-3 5 3-4 4-3-2-3 3M13 15l5 4M10 18l5 4"/>',
    contract: '<path d="M4 2h11l5 5v15H4ZM14 2v6h6M7 12h9M7 16h6"/><circle cx="18" cy="18" r="5"/><path d="m15 18 2 2 4-4"/>',
    stipend: '<path d="m1 7 11-5 11 5-11 5ZM6 10v5q6 5 12 0v-5"/><circle cx="17" cy="19" r="5"/><path d="M17 16v6M15 17h3l1 1-1 1h-2l-1 1 1 1h3"/>',
    briefcase: '<path d="M8 7V3h8v4M2 8h20v14H2ZM2 12l8 4h4l8-4M10 14h4v4h-4Z"/>',
    building: '<path d="M5 22V2h14v20M1 22h22M9 22v-5h6v5M8 6h2M14 6h2M8 10h2M14 10h2M8 14h2M14 14h2"/>',
    calendar: '<path d="M2 5h20v17H2ZM6 1v7M18 1v7M2 10h20M6 14h2M11 14h2M6 18h2"/><circle cx="18" cy="18" r="5"/><path d="M18 15v3l2 1"/>',
    refresh: '<path d="M21 9a9 9 0 0 0-16-5L2 8M2 2v6h6M3 15a9 9 0 0 0 16 5l3-4M16 16h6v6" fill="none"/>',
    shield: '<path d="m12 1 10 5-2 12-8 6-8-6L2 6Z"/><path d="m7 12 4 4 7-8"/>',
  };
  const sections = ['cap','bulb','globe','finance','clipboard'];
  const services = [
    ['medical','document','hemis','tools','layers'],
    ['microscope','mentor','cap','sprout','layers'],
    ['people','plane','book','handshake','layers'],
    ['contract','stipend','briefcase','document','layers'],
    ['building','calendar','refresh','shield','layers'],
  ];
  const colors = [['#c4f0ff','#198fe9'],['#b2fff0','#11c2be'],['#e9cbff','#a36bff'],['#c4f0ff','#198fe9'],['#b2fff0','#11c2be']];
  function icon(section, service=null) {
    const key = service===null?sections[section]:services[section]?.[service];
    const [light,shade]=colors[section]||colors[0],id='kiosk-icon-'+section+'-'+(service??'section');
    return `<svg data-kiosk-icon="${key||'layers'}" viewBox="-3 -3 30 30" aria-hidden="true"><defs><linearGradient id="${id}" x2="0.7" y2="1"><stop stop-color="${light}"/><stop offset="1" stop-color="${shade}"/></linearGradient></defs><g fill="url(#${id})" stroke="${light}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round">${paths[key]||paths.layers}</g></svg>`;
  }
  return {icon};
})();
