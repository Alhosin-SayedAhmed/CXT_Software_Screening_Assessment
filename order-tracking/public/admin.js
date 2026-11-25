(() => {
  const $ = (id) => document.getElementById(id);
  let STAGES = [];
  let filterStage = '';
  let editingId = null;
  let ordersById = new Map();

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ar-EG', { dateStyle: 'short', timeStyle: 'short' });
  const stageLabel = (key) => (STAGES.find((s) => s.key === key) || {}).label || key;

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      ...opts,
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && !path.endsWith('/login')) { showLogin(); throw new Error(data.error); }
    if (!res.ok) throw new Error(data.error || 'حصلت مشكلة');
    return data;
  }

  let toastTimer;
  function toast(msg) {
    const t = $('toast');
    t.textContent = msg;
    t.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add('hidden'), 2500);
  }

  function setError(el, msg) {
    el.textContent = msg || '';
    el.classList.toggle('hidden', !msg);
  }

  function trackUrl(number) {
    return location.origin + '/track/' + encodeURIComponent(number);
  }

  // تحويل رقم مصري 01xxxxxxxxx لصيغة واتساب 201xxxxxxxxx
  function waPhone(phone) {
    let p = String(phone || '').replace(/[^\d]/g, '');
    if (p.startsWith('00')) p = p.slice(2);
    if (p.startsWith('01') && p.length === 11) p = '2' + p;
    return p;
  }

  function showLogin() {
    $('dashView').classList.add('hidden');
    $('loginView').classList.remove('hidden');
    $('password').focus();
  }

  function showDash() {
    $('loginView').classList.add('hidden');
    $('dashView').classList.remove('hidden');
    load();
  }

  // ---------- تسجيل الدخول ----------
  $('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    $('loginBtn').disabled = true;
    try {
      await api('/api/admin/login', { method: 'POST', body: { password: $('password').value } });
      $('password').value = '';
      setError($('loginError'));
      showDash();
    } catch (err) {
      setError($('loginError'), err.message);
    } finally {
      $('loginBtn').disabled = false;
    }
  });

  $('logoutBtn').addEventListener('click', async () => {
    await api('/api/admin/logout', { method: 'POST' }).catch(() => {});
    showLogin();
  });

  // ---------- إضافة طلب ----------
  $('addForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    $('addBtn').disabled = true;
    try {
      const o = await api('/api/admin/orders', { method: 'POST', body });
      e.target.reset();
      setError($('addError'));
      toast('اتضاف الطلب #' + o.order_number);
      $('fNumber').focus();
      load();
    } catch (err) {
      setError($('addError'), err.message);
    } finally {
      $('addBtn').disabled = false;
    }
  });

  // ---------- القائمة ----------
  let searchTimer;
  $('search').addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(load, 250);
  });

  async function load() {
    const params = new URLSearchParams({ search: $('search').value.trim(), stage: filterStage });
    let data;
    try { data = await api('/api/admin/orders?' + params); } catch { return; }
    renderChips(data.counts || {});
    renderRows(data.orders || []);
  }

  function renderChips(counts) {
    const box = $('chips');
    box.replaceChildren();
    const total = Object.values(counts).reduce((a, b) => a + b, 0);
    const mk = (key, label, n) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'chip' + (filterStage === key ? ' active' : '');
      b.append(label + ' ');
      const num = document.createElement('b');
      num.textContent = n;
      b.append(num);
      b.addEventListener('click', () => { filterStage = key; load(); });
      box.append(b);
    };
    mk('', 'الكل', total);
    STAGES.forEach((s) => mk(s.key, s.label, counts[s.key] || 0));
  }

  function td(label, content, cls) {
    const c = document.createElement('td');
    if (label) c.dataset.label = label;
    if (cls) c.className = cls;
    if (content instanceof Node) c.append(content); else c.textContent = content || '—';
    return c;
  }

  function btn(text, cls, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn-sm ' + cls;
    b.textContent = text;
    b.addEventListener('click', onClick);
    return b;
  }

  function renderRows(orders) {
    ordersById = new Map(orders.map((o) => [o.id, o]));
    const tbody = $('rows');
    tbody.replaceChildren();
    $('empty').classList.toggle('hidden', orders.length > 0);

    for (const o of orders) {
      const tr = document.createElement('tr');

      const sel = document.createElement('select');
      sel.setAttribute('aria-label', 'مرحلة الطلب ' + o.order_number);
      STAGES.forEach((s) => sel.append(new Option(s.label, s.key, false, s.key === o.stage)));
      sel.addEventListener('change', async () => {
        sel.disabled = true;
        try {
          await api('/api/admin/orders/' + o.id, { method: 'PATCH', body: { stage: sel.value } });
          toast('#' + o.order_number + ' ← ' + stageLabel(sel.value));
          load();
        } catch (err) {
          toast(err.message);
          sel.value = o.stage;
        } finally {
          sel.disabled = false;
        }
      });

      const actions = document.createElement('div');
      actions.className = 'actions';
      actions.append(
        btn('نسخ اللينك', 'btn-ghost', async () => {
          try { await navigator.clipboard.writeText(trackUrl(o.order_number)); toast('اتنسخ لينك التتبع'); }
          catch { prompt('انسخ اللينك:', trackUrl(o.order_number)); }
        }),
      );
      if (o.phone) {
        actions.append(btn('واتساب', 'btn-ghost', () => {
          const msg = `أهلاً ${o.customer_name || ''}، طلبك رقم ${o.order_number} حالياً في مرحلة: ${stageLabel(o.stage)}.\nتقدر تتابع طلبك من هنا: ${trackUrl(o.order_number)}`;
          window.open('https://wa.me/' + waPhone(o.phone) + '?text=' + encodeURIComponent(msg), '_blank', 'noopener');
        }));
      }
      actions.append(
        btn('تعديل', 'btn-ghost', () => openEdit(o.id)),
        btn('حذف', 'btn-danger', async () => {
          if (!confirm('متأكد إنك عاوز تحذف الطلب #' + o.order_number + '؟')) return;
          try { await api('/api/admin/orders/' + o.id, { method: 'DELETE' }); toast('اتحذف'); load(); }
          catch (err) { toast(err.message); }
        }),
      );

      tr.append(
        td('', '#' + o.order_number, 'num'),
        td('العميل', [o.customer_name, o.phone].filter(Boolean).join(' — ')),
        td('المنتج', o.product),
        td('المرحلة', sel),
        td('آخر تحديث', fmt(o.updated_at), 'when'),
        td('', actions),
      );
      tbody.append(tr);
    }
  }

  // ---------- التعديل ----------
  const dlg = $('editDialog');
  function openEdit(id) {
    const o = ordersById.get(id);
    if (!o) return;
    editingId = id;
    $('editTitle').textContent = 'تعديل الطلب #' + o.order_number;
    $('eName').value = o.customer_name;
    $('ePhone').value = o.phone;
    $('eProduct').value = o.product;
    $('eNote').value = o.note;
    setError($('editError'));
    dlg.showModal();
  }
  $('cancelBtn').addEventListener('click', () => dlg.close());
  $('editForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    $('saveBtn').disabled = true;
    try {
      await api('/api/admin/orders/' + editingId, { method: 'PATCH', body });
      dlg.close();
      toast('اتحفظ');
      load();
    } catch (err) {
      setError($('editError'), err.message);
    } finally {
      $('saveBtn').disabled = false;
    }
  });

  // ---------- تحديث تلقائي ----------
  // لو حد عدّل في Supabase مباشرة، القائمة بتتحدّث لوحدها كل 30 ثانية
  setInterval(() => {
    const busy = document.hidden || dlg.open || $('dashView').classList.contains('hidden') ||
      (document.activeElement && document.activeElement.closest('#rows'));
    if (!busy) load();
  }, 30000);

  // ---------- البداية ----------
  Promise.all([fetch('/api/config').then((r) => r.json()), api('/api/admin/me')]).then(([cfg, me]) => {
    STAGES = cfg.stages || [];
    const sel = $('fStage');
    STAGES.forEach((s) => sel.append(new Option(s.label, s.key)));
    if (me.admin) showDash(); else showLogin();
  });
})();
