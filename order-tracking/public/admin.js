(() => {
  const $ = (id) => document.getElementById(id);
  let STAGES = [];
  let filterStage = '';
  let editingId = null;
  let ordersById = new Map();

  const fmt = (iso) =>
    new Date(iso).toLocaleString('ar-EG', { dateStyle: 'short', timeStyle: 'short' });
  const stageLabel = (key) => (STAGES.find((s) => s.key === key) || {}).label || key;

  // ---------- الكلام مع Supabase ----------
  const db = APP.db;
  const normNumber = (v) => String(v || '').trim().replace(/^#/, '').slice(0, 50);
  const clean = (v, max) => (v === undefined ? undefined : String(v).trim().slice(0, max));

  // بيحوّل أخطاء Supabase لرسالة مفهومة
  function fail(error) {
    if (!error) return;
    const code = error.code || '';
    if (code === '23505') throw new Error('رقم الطلب ده متسجل قبل كده');
    if (code === '42501' || code === 'PGRST301' || code === 'PGRST303' || /JWT/i.test(error.message || '')) {
      showLogin();
      throw new Error('انتهت الجلسة أو الحساب مش أدمن. سجّل الدخول تاني.');
    }
    if (code === '23503') throw new Error('مرحلة غير صحيحة');
    if (code === '23514') throw new Error('في خانة مكتوب فيها كلام أطول من المسموح');
    throw new Error('حصلت مشكلة، جرب تاني');
  }

  function orderFields(b) {
    const out = {
      customer_name: clean(b.customer_name, 100),
      phone: clean(b.phone, 30),
      product: clean(b.product, 200),
      note: clean(b.note, 500),
      stage: b.stage || undefined,
    };
    Object.keys(out).forEach((k) => out[k] === undefined && delete out[k]);
    return out;
  }

  const store = {
    async login(email, password) {
      const { error } = await db.auth.signInWithPassword({ email: email.trim(), password });
      if (error) throw new Error('الإيميل أو الباسورد غلط');
      if (!(await store.isAdmin())) {
        await db.auth.signOut();
        throw new Error('الحساب ده مش متسجّل كأدمن. ضيفه في جدول admins (شوف README).');
      }
    },
    async logout() { await db.auth.signOut(); },
    async isAdmin() {
      const { data: { session } } = await db.auth.getSession();
      if (!session) return false;
      const { data, error } = await db.rpc('is_admin');
      return !error && data === true;
    },
    async list(search, stage) {
      const [list, counts] = await Promise.all([
        db.rpc('admin_list_orders', { p_search: search, p_stage: stage }),
        db.rpc('admin_order_counts'),
      ]);
      fail(list.error); fail(counts.error);
      return {
        orders: list.data || [],
        counts: Object.fromEntries((counts.data || []).map((r) => [r.stage, r.n])),
      };
    },
    async create(b) {
      const order_number = normNumber(b.order_number);
      if (!order_number) throw new Error('لازم تكتب رقم الطلب');
      const { data, error } = await db.from('orders').insert({ order_number, ...orderFields(b) }).select().single();
      fail(error);
      return data;
    },
    async update(id, b) {
      const { data, error } = await db.from('orders').update(orderFields(b)).eq('id', id).select();
      fail(error);
      if (!data || !data.length) throw new Error('الطلب مش موجود');
      return data[0];
    },
    async remove(id) {
      const { data, error } = await db.from('orders').delete().eq('id', id).select('id');
      fail(error);
      if (!data || !data.length) throw new Error('الطلب مش موجود');
    },
  };

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
    $('email').focus();
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
      await store.login($('email').value, $('password').value);
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
    await store.logout().catch(() => {});
    showLogin();
  });

  // ---------- إضافة طلب ----------
  $('addForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    $('addBtn').disabled = true;
    try {
      const o = await store.create(body);
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
    let data;
    try { data = await store.list($('search').value.trim().slice(0, 100), filterStage); } catch (err) { toast(err.message); return; }
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
          await store.update(o.id, { stage: sel.value });
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
          try { await store.remove(o.id); toast('اتحذف'); load(); }
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
      await store.update(editingId, body);
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
  async function init() {
    if (!APP.configured) {
      showLogin();
      setError($('loginError'), APP.notConfiguredMessage);
      $('loginBtn').disabled = true;
      return;
    }
    const { data, error } = await db.from('stages').select('key, label').order('position');
    if (error) { showLogin(); setError($('loginError'), 'مش قادر يتصل بـ Supabase. اتأكد من config.js'); return; }
    STAGES = data || [];
    const sel = $('fStage');
    STAGES.forEach((s) => sel.append(new Option(s.label, s.key)));
    if (await store.isAdmin()) showDash(); else showLogin();
  }
  init();
})();
