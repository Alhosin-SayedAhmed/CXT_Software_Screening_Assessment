(() => {
  const $ = (id) => document.getElementById(id);
  const form = $('trackForm');
  const input = $('orderInput');
  const btn = $('trackBtn');
  const errBox = $('trackError');
  const result = $('result');
  let STAGES = [];

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ar-EG', { dateStyle: 'medium', timeStyle: 'short' });

  function showError(msg) {
    errBox.textContent = msg;
    errBox.classList.remove('hidden');
    result.classList.add('hidden');
  }

  function render(o) {
    errBox.classList.add('hidden');
    const idx = STAGES.findIndex((s) => s.key === o.stage);
    const whenByStage = {};
    for (const h of o.history || []) whenByStage[h.stage] = h.changed_at;

    $('rNumber').textContent = '#' + o.order_number;
    $('rProduct').textContent = o.product ? 'المنتج: ' + o.product : '';
    $('rStage').textContent = STAGES[idx] ? STAGES[idx].label : o.stage;
    $('rUpdated').textContent = 'آخر تحديث: ' + fmt(o.updated_at);
    const pct = STAGES.length > 1 ? Math.round((idx / (STAGES.length - 1)) * 100) : 100;
    requestAnimationFrame(() => { $('rBar').style.width = Math.max(pct, 4) + '%'; });

    const list = $('rTimeline');
    list.replaceChildren();
    STAGES.forEach((s, i) => {
      const li = document.createElement('li');
      if (i <= idx) li.classList.add('done');
      if (i === idx) { li.classList.add('current'); li.setAttribute('aria-current', 'step'); }
      const dot = document.createElement('span');
      dot.className = 'dot';
      dot.textContent = i <= idx ? '✓' : String(i + 1);
      const title = document.createElement('div');
      title.className = 'step-title';
      title.textContent = s.label;
      const desc = document.createElement('div');
      desc.className = 'step-desc';
      desc.textContent = s.description || '';
      li.append(dot, title, desc);
      if (i <= idx && whenByStage[s.key]) {
        const t = document.createElement('div');
        t.className = 'step-time';
        t.textContent = fmt(whenByStage[s.key]);
        li.append(t);
      }
      list.append(li);
    });

    const note = $('rNote');
    if (o.note) { note.textContent = o.note; note.classList.remove('hidden'); }
    else note.classList.add('hidden');

    result.classList.remove('hidden');
  }

  async function track(number) {
    number = String(number || '').trim().replace(/^#/, '');
    if (!number) return showError('اكتب رقم الطلب الأول');
    btn.disabled = true;
    try {
      const res = await fetch('/api/track/' + encodeURIComponent(number));
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return showError(data.error || 'حصلت مشكلة، جرب تاني');
      render(data);
      const url = '/track/' + encodeURIComponent(data.order_number);
      if (location.pathname !== url) history.replaceState(null, '', url);
    } catch {
      showError('مفيش اتصال بالإنترنت، جرب تاني');
    } finally {
      btn.disabled = false;
    }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); track(input.value); });

  fetch('/api/config').then((r) => r.json()).then((cfg) => {
    STAGES = cfg.stages || [];
    if (cfg.storeName) {
      $('storeLink').textContent = cfg.storeName;
      document.title = 'تتبع طلبك — ' + cfg.storeName;
    }
    if (cfg.storeUrl) {
      $('storeLink').href = cfg.storeUrl;
      const a = document.createElement('a');
      a.href = cfg.storeUrl;
      a.textContent = 'ارجع للمتجر';
      $('foot').append(a);
    }
    // يدعم اللينكات: /track/123  أو  /?order=123
    const m = location.pathname.match(/^\/track\/([^/]+)/);
    const fromUrl = m ? decodeURIComponent(m[1]) : new URLSearchParams(location.search).get('order');
    if (fromUrl) { input.value = fromUrl; track(fromUrl); }
  });
})();
