(() => {
  const $ = (id) => document.getElementById(id);
  const form = $('trackForm');
  const input = $('orderInput');
  const btn = $('trackBtn');
  const errBox = $('trackError');
  const result = $('result');
  let STAGES = [];
  let shown = null; // الطلب اللي معروض دلوقتي
  const REFRESH_MS = 20000;

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ar-EG', { dateStyle: 'medium', timeStyle: 'short' });
  const arNum = (n) => Number(n).toLocaleString('ar-EG');

  // ---------- الأيقونات (SVG) ----------
  const SVG_NS = 'http://www.w3.org/2000/svg';
  const ICONS = {
    clipboard: [['rect', { x: 5, y: 4, width: 14, height: 17, rx: 2 }], ['path', { d: 'M9 4V3h6v1' }], ['path', { d: 'M8.5 13l2.5 2.5 4.5-5' }]],
    box: [['path', { d: 'M3 7.5l9-4.5 9 4.5-9 4.5z' }], ['path', { d: 'M3 7.5V17l9 4.5 9-4.5V7.5' }], ['path', { d: 'M12 12v9.5' }]],
    gear: [
      ['circle', { cx: 12, cy: 12, r: 3 }],
      ['circle', { cx: 12, cy: 12, r: 6.5 }],
      ...Array.from({ length: 8 }, (_, i) => {
        const a = (i * Math.PI) / 4;
        const p = (r) => `${(12 + r * Math.cos(a)).toFixed(2)} ${(12 + r * Math.sin(a)).toFixed(2)}`;
        return ['path', { d: `M${p(6.5)}L${p(9.5)}`, 'stroke-width': 2.6 }];
      }),
    ],
    shield: [['path', { d: 'M12 3l7.5 3v5.5c0 4.5-3.2 8.2-7.5 9.5-4.3-1.3-7.5-5-7.5-9.5V6z' }], ['path', { d: 'M8.8 12.2l2.2 2.2 4.2-4.4' }]],
    package: [['rect', { x: 3.5, y: 8, width: 17, height: 12.5, rx: 1.5 }], ['path', { d: 'M2.5 4.5h19V8h-19z' }], ['path', { d: 'M10 12h4' }]],
    truck: [['path', { d: 'M10 6h11.5v10.5H10z' }], ['path', { d: 'M10 9.5H6.2L3 13v3.5h7' }], ['circle', { cx: 6.5, cy: 17.5, r: 1.8 }], ['circle', { cx: 17.5, cy: 17.5, r: 1.8 }]],
    home: [['path', { d: 'M3.5 11L12 3.8l8.5 7.2V20a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1z' }], ['path', { d: 'M9 14.5l2.2 2.2 4-4.2' }]],
    check: [['path', { d: 'M5.5 12.5l4.5 4.5 8.5-9.5', 'stroke-width': 2.6 }]],
    dot: [['circle', { cx: 12, cy: 12, r: 4 }]],
  };

  function icon(name) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('class', 'ico');
    svg.setAttribute('aria-hidden', 'true');
    for (const [tag, attrs] of ICONS[name] || ICONS.dot) {
      const el = document.createElementNS(SVG_NS, tag);
      for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
      svg.append(el);
    }
    return svg;
  }

  const iconOf = (stage) => (stage && ICONS[stage.icon] ? stage.icon : 'dot');

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function showError(msg) {
    shown = null;
    errBox.textContent = msg;
    errBox.classList.remove('hidden');
    result.classList.add('hidden');
  }

  // ---------- عرض النتيجة ----------
  function render(o, { scroll = true } = {}) {
    shown = { number: o.order_number, updated_at: o.updated_at };
    errBox.classList.add('hidden');
    const total = STAGES.length;
    const idx = Math.max(0, STAGES.findIndex((s) => s.key === o.stage));
    const cur = STAGES[idx];
    const isLast = idx === total - 1;
    const whenByStage = {};
    for (const h of o.history || []) whenByStage[h.stage] = h.changed_at;

    // نشيل النتيجة القديمة ونرجعها عشان الحركة تتعاد من الأول
    result.classList.add('hidden');
    void result.offsetWidth;

    // البطاقة العلوية
    $('rNumber').textContent = '#' + o.order_number;
    $('rStage').textContent = cur ? cur.label : o.stage;
    $('rStep').textContent = isLast ? 'خلصت كل المراحل 🎉' : `المرحلة ${arNum(idx + 1)} من ${arNum(total)}`;
    $('rProduct').textContent = o.product ? 'المنتج: ' + o.product : '';
    $('rUpdated').textContent = 'آخر تحديث: ' + fmt(o.updated_at) + ' · الصفحة بتتحدّث لوحدها';

    const iconBox = $('rIcon');
    iconBox.className = 'hero-icon anim-' + iconOf(cur);
    iconBox.replaceChildren(icon(iconOf(cur)));

    const ring = $('rRing');
    ring.style.transition = 'none';
    ring.style.strokeDashoffset = '276.46';

    const burst = $('rBurst');
    burst.replaceChildren();
    if (isLast) {
      const colors = ['var(--brand)', '#f59e0b', '#ec4899', '#6366f1', '#22c55e'];
      for (let i = 0; i < 14; i++) {
        const p = document.createElement('i');
        p.style.setProperty('--a', (i * 360) / 14 + 'deg');
        p.style.setProperty('--c', colors[i % colors.length]);
        p.style.setProperty('--d', 0.9 + (i % 3) * 0.08 + 's');
        burst.append(p);
      }
    }

    // الخط الزمني
    const list = $('rTimeline');
    list.replaceChildren();
    STAGES.forEach((s, i) => {
      const state = i < idx || (isLast && i === idx) ? 'done' : i === idx ? 'current' : 'pending';
      const li = el('li', 'step ' + state);
      li.style.setProperty('--i', i);
      if (i === idx) li.setAttribute('aria-current', 'step');

      const node = el('span', 'node' + (state === 'current' ? ' anim-' + iconOf(s) : ''));
      node.append(icon(state === 'done' ? 'check' : iconOf(s)));
      const line = el('span', 'line');
      line.append(el('span', 'line-fill'));

      const body = el('div', 'step-body');
      const title = el('div', 'step-title', s.label);
      if (i === idx && !isLast) title.append(el('span', 'now-tag', 'دلوقتي'));
      body.append(title);
      if (s.description) body.append(el('div', 'step-desc', s.description));
      if (i <= idx && whenByStage[s.key]) body.append(el('div', 'step-time', fmt(whenByStage[s.key])));

      li.append(node, line, body);
      list.append(li);
    });

    const note = $('rNote');
    if (o.note) { note.textContent = o.note; note.classList.remove('hidden'); }
    else note.classList.add('hidden');

    result.classList.remove('hidden');

    // تعبئة الدايرة بعد ما الكارت يظهر
    const pct = total ? (idx + 1) / total : 1;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      ring.style.transition = '';
      ring.style.strokeDashoffset = String(276.46 * (1 - pct));
    }));
    if (scroll) result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // بيشيّك على Supabase كل شوية، ولو الطلب اتغيّر بيعرض التحديث بالحركة
  async function refresh() {
    if (!shown || document.hidden) return;
    try {
      const data = await fetchOrder(shown.number);
      if (data && shown && data.order_number === shown.number && data.updated_at !== shown.updated_at) {
        render(data, { scroll: false });
      }
    } catch { /* مفيش نت دلوقتي — هنجرب المرة الجاية */ }
  }
  setInterval(refresh, REFRESH_MS);
  document.addEventListener('visibilitychange', refresh);

  // بيسأل Supabase عن الطلب. بيرجع null لو الرقم مش موجود
  async function fetchOrder(number) {
    const { data, error } = await APP.db.rpc('track_order', { p_order_number: number });
    if (error) throw error;
    return data;
  }

  async function track(number) {
    number = String(number || '').trim().replace(/^#/, '');
    if (!number) return showError('اكتب رقم الطلب الأول');
    if (!APP.configured) return showError(APP.notConfiguredMessage);
    btn.disabled = true;
    try {
      const data = await fetchOrder(number);
      if (!data) return showError('رقم الطلب ده مش موجود. اتأكد من الرقم وجرب تاني.');
      render(data);
      const url = '/track/' + encodeURIComponent(data.order_number);
      if (location.pathname !== url) history.replaceState(null, '', url);
    } catch {
      showError('حصلت مشكلة في الاتصال، جرب تاني');
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); track(input.value); });

  async function init() {
    const cfg = APP.cfg;
    if (cfg.STORE_NAME) {
      $('storeLink').textContent = cfg.STORE_NAME;
      document.title = 'تتبع طلبك — ' + cfg.STORE_NAME;
    }
    if (cfg.STORE_URL) {
      $('storeLink').href = cfg.STORE_URL;
      const a = document.createElement('a');
      a.href = cfg.STORE_URL;
      a.textContent = 'ارجع للمتجر';
      $('foot').append(a);
    }
    if (!APP.configured) return showError(APP.notConfiguredMessage);

    // المراحل متخزنة في Supabase (جدول stages)
    const { data, error } = await APP.db.from('stages').select('key, label, description, icon').order('position');
    if (error) return showError('حصلت مشكلة في الاتصال، جرب تاني');
    STAGES = data || [];

    // يدعم اللينكات: /track/123  أو  /?order=123
    const m = location.pathname.match(/^\/track\/([^/]+)/);
    const fromUrl = m ? decodeURIComponent(m[1]) : new URLSearchParams(location.search).get('order');
    if (fromUrl) { input.value = fromUrl; track(fromUrl); }
  }
  init();
})();
