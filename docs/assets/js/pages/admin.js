import { api, esc, priceHtml, showMsg, toast, requireLogin, splitDateTime, STATUS_LABEL, $, $$ } from '../api.js?v=20261107b';
import { renderLayout } from '../layout.js?v=20261107b';

const view = $('#view');
let allTags = [];

function bars(items, label = (x) => x.key, max = null) {
  const top = max ?? Math.max(1, ...items.map((x) => Number(x.n)));
  return `<ul class="bars">${items.map((x) => `
    <li><span class="k" title="${esc(label(x))}">${esc(label(x))}</span>
      <span class="track"><span class="fill" style="width:${Math.round((x.n / top) * 100)}%"></span></span>
      <span class="v">${x.n}</span></li>`).join('')}</ul>`;
}

// 兩段式確認按鈕：第一次點顯示「確定？」，四秒內再點一次才執行
function confirmClick(btn, label) {
  if (btn.dataset.confirm === '1') return true;
  const old = btn.textContent;
  btn.dataset.confirm = '1'; btn.textContent = label; btn.style.color = 'var(--err)';
  setTimeout(() => { if (btn.isConnected) { btn.dataset.confirm = ''; btn.textContent = old; btn.style.color = ''; } }, 4000);
  return false;
}

const views = {
  async stats() {
    const d = await api('/admin/stats');
    const t = d.totals;
    const statusItems = d.byStatus.map((s) => ({ ...s, key: STATUS_LABEL[s.key] || s.key }));
    view.innerHTML = `
      <p class="eyebrow">DASHBOARD</p><h1 class="page-title" style="font-size:30px;padding-bottom:24px;border-bottom:1px solid var(--ink)">總覽與統計</h1>
      <dl class="kpis">
        <div><dt>收錄餐廳</dt><dd>${t.restaurants}</dd><dd class="small">可線上預約 ${t.accept_res} 家</dd></div>
        <div><dt>會員</dt><dd>${t.members}</dd><dd class="small">不含管理者</dd></div>
        <div><dt>評論</dt><dd>${t.reviews}</dd><dd class="small">會員平均 ${t.avg_member ?? '—'} 分</dd></div>
        <div><dt>待確認預約</dt><dd style="color:var(--rose)">${t.pending}</dd><dd class="small">Google 平均 ${t.avg_google ?? '—'}</dd></div>
      </dl>
      <div class="grid2">
        <section class="panel"><h2>各價位餐廳數</h2><p class="small" style="margin:0 0 20px">依價位分類</p>
          ${bars(d.byPrice, (x) => ['', '$ 平價', '$$ 中價位', '$$$ 高價位'][x.key] || x.key)}</section>
        <section class="panel"><h2>各區域餐廳數</h2><p class="small" style="margin:0 0 20px">括號內為平均 Google 評分</p>
          ${bars(d.byDistrict, (x) => `${x.key}（${x.avg_google ?? '—'}）`)}</section>
        <section class="panel"><h2>最常見的標籤</h2><p class="small" style="margin:0 0 20px">使用該標籤的餐廳數</p>${bars(d.topTags)}</section>
        <section class="panel"><h2>預約狀態</h2><p class="small" style="margin:0 0 20px">各狀態筆數（括號內為總人數）</p>
          ${bars(statusItems, (x) => `${x.key}（${x.people} 人）`)}</section>
        <section class="panel"><h2>預約最多的餐廳</h2><p class="small" style="margin:0 0 20px">不含已取消、已拒絕；括號內為平均人數</p>
          ${d.topReserved.length ? bars(d.topReserved, (x) => `${x.key}（${x.avg_size}）`) : '<p class="muted">尚無資料</p>'}</section>
        <section class="panel"><h2>會員評分最高的餐廳</h2><p class="small" style="margin:0 0 20px">會員平均評分，括號內為評論數</p>
          ${d.topRated.length ? `<ul class="bars">${d.topRated.map((x) => `<li><span class="k" style="flex-basis:180px">${esc(x.key)}</span><span class="track"><span class="fill" style="width:${x.avg * 20}%"></span></span><span class="v">${x.avg}（${x.n}）</span></li>`).join('')}</ul>` : '<p class="muted">尚無資料</p>'}</section>
      </div>`;
  },

  async restaurants(page = 1, q = '') {
    const d = await api('/admin/restaurants', { query: { page, q } });
    const pages = Math.ceil(d.total / d.pageSize);
    view.innerHTML = `
      <p class="eyebrow">RESTAURANTS</p>
      <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:16px;padding-bottom:24px;border-bottom:1px solid var(--ink)">
        <h1 class="page-title" style="font-size:30px">餐廳與招牌菜</h1>
        <form id="rq" class="row" style="gap:10px"><label class="field" style="flex:1 1 220px">搜尋餐廳<input type="search" name="q" value="${esc(q)}" placeholder="店名或地址"></label>
          <button class="btn btn-quiet btn-sm" type="submit">搜尋</button>
          <button class="btn btn-dark btn-sm" type="button" id="add-rest">＋ 新增餐廳</button></form>
      </div>
      <div class="table-box" style="margin-top:8px"><table class="data" style="min-width:860px">
        <thead><tr><th>編號</th><th>餐廳名稱</th><th>區域</th><th>價位</th><th>Google</th><th>預約</th><th>座位</th><th>操作</th></tr></thead>
        <tbody>${d.items.map((r) => `
          <tr><td class="small">${esc(r.rid)}</td><td class="strong">${esc(r.rname)}</td><td>${esc(r.district)}</td>
            <td style="letter-spacing:.08em">${priceHtml(r.pricerange)}</td>
            <td>${r.google_rate ?? '—'}（${r.google_num ?? 0}）</td><td>${r.acceptres ? '是' : '否'}</td><td>${r.capacity ?? '—'}</td>
            <td style="white-space:nowrap">
              <button class="link-btn" data-edit="${esc(r.rid)}">編輯</button>
              <button class="link-btn" data-menu="${esc(r.rid)}" data-name="${esc(r.rname)}">招牌菜</button>
              <button class="link-btn quiet" data-del="${esc(r.rid)}">刪除</button></td></tr>`).join('')}
        </tbody></table></div>
      <p class="small" style="margin:18px 0 0">共 ${d.total} 筆
        ${page > 1 ? `<button class="link-btn" data-page="${page - 1}">上一頁</button>` : ''}　第 ${page} / ${Math.max(pages, 1)} 頁
        ${page < pages ? `<button class="link-btn" data-page="${page + 1}">下一頁</button>` : ''}</p>`;

    $('#rq').addEventListener('submit', (e) => { e.preventDefault(); views.restaurants(1, e.target.q.value.trim()); });
    $('#add-rest').addEventListener('click', () => openRest(null));
    view.onclick = async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.page) views.restaurants(Number(b.dataset.page), q);
      if (b.dataset.edit) openRest(d.items.find((r) => r.rid === b.dataset.edit));
      if (b.dataset.menu) openMenu(b.dataset.menu, b.dataset.name);
      if (b.dataset.del && confirmClick(b, '確定刪除？')) {
        try { await api('/admin/restaurants/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); toast('餐廳已刪除'); views.restaurants(page, q); }
        catch (err) { toast(err.message); }
      }
    };
    restReload = () => views.restaurants(page, q);
  },

  async reservations(status = 'pending') {
    const d = await api('/admin/reservations', { query: { status } });
    const tabs = [['pending', '待確認'], ['confirmed', '已確認'], ['completed', '已完成'], ['rejected', '已拒絕'], ['cancelled', '已取消'], ['', '全部']];
    view.innerHTML = `
      <p class="eyebrow">RESERVATIONS</p><h1 class="page-title" style="font-size:30px;padding-bottom:16px">預約管理</h1>
      <div role="tablist" style="display:flex;flex-wrap:wrap;gap:4px 28px;border-bottom:1px solid var(--ink)">
        ${tabs.map(([k, l]) => `<button role="tab" aria-selected="${k === status}" data-status="${k}" style="background:none;border:0;padding:12px 0;margin-bottom:-1px;cursor:pointer;min-height:44px;font-size:15px;border-bottom:2px solid ${k === status ? 'var(--rose)' : 'transparent'}">${l}</button>`).join('')}
      </div>
      <div class="table-box"><table class="data" style="min-width:900px">
        <thead><tr><th>編號</th><th>會員</th><th>餐廳</th><th>日期時間</th><th>人數</th><th>該時段剩餘</th><th>狀態</th><th>操作</th></tr></thead>
        <tbody>${d.items.map((r) => `
          <tr><td class="small">${esc(r.resid)}</td><td>${esc(r.mname || '—')}</td><td>${esc(r.rname)}</td>
            <td>${esc(splitDateTime(r.datetime).label)}</td><td>${r.partysize}</td><td>${r.seats_left ?? '—'}</td>
            <td><span class="badge ${esc(r.status)}">${STATUS_LABEL[r.status] || esc(r.status)}</span></td>
            <td style="white-space:nowrap">
              ${r.status === 'pending' ? `<button class="btn btn-sm" data-set="confirmed" data-id="${esc(r.resid)}">確認</button> <button class="btn btn-quiet btn-sm" data-set="rejected" data-id="${esc(r.resid)}">拒絕</button>` : ''}
              ${r.status === 'confirmed' ? `<button class="btn btn-quiet btn-sm" data-set="completed" data-id="${esc(r.resid)}">標記完成</button>` : ''}
            </td></tr>`).join('') || '<tr><td colspan="8" class="empty">沒有資料</td></tr>'}
        </tbody></table></div>`;
    view.onclick = async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      if (b.dataset.status !== undefined) views.reservations(b.dataset.status);
      if (b.dataset.set) {
        try { await api('/admin/reservations/' + encodeURIComponent(b.dataset.id), { method: 'PATCH', body: { status: b.dataset.set } }); toast('預約狀態已更新'); views.reservations(status); }
        catch (err) { toast(err.message); }
      }
    };
  },

  async tags() {
    const { items } = await api('/tags');
    allTags = items;
    view.innerHTML = `
      <p class="eyebrow">TAGS</p><h1 class="page-title" style="font-size:30px;padding-bottom:24px;border-bottom:1px solid var(--ink)">標籤管理</h1>
      <form id="tag-new" class="row" style="margin:24px 0"><label class="field" style="flex:0 1 320px">新增標籤<input name="tName" required maxlength="100"></label><button class="btn btn-sm" type="submit">新增</button></form>
      <div class="table-box"><table class="data"><thead><tr><th>編號</th><th>標籤名稱</th><th>使用的餐廳數</th><th>操作</th></tr></thead>
        <tbody>${items.map((t) => `<tr><td class="small">${esc(t.tid)}</td>
          <td><input value="${esc(t.tname)}" data-name="${esc(t.tid)}" aria-label="標籤名稱" style="max-width:260px;padding:6px 10px"></td>
          <td>${t.n}</td><td style="white-space:nowrap"><button class="link-btn" data-save="${esc(t.tid)}">儲存</button>　<button class="link-btn quiet" data-del="${esc(t.tid)}">刪除</button></td></tr>`).join('')}</tbody></table></div>`;
    $('#tag-new').addEventListener('submit', async (e) => {
      e.preventDefault();
      try { await api('/admin/tags', { method: 'POST', body: { tName: e.target.tName.value } }); toast('標籤已新增'); views.tags(); } catch (err) { toast(err.message); }
    });
    view.onclick = async (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      try {
        if (b.dataset.save) { await api('/admin/tags/' + encodeURIComponent(b.dataset.save), { method: 'PUT', body: { tName: $(`[data-name="${b.dataset.save}"]`).value } }); toast('已儲存'); }
        if (b.dataset.del && confirmClick(b, '確定刪除？')) { await api('/admin/tags/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); toast('標籤已刪除'); views.tags(); }
      } catch (err) { toast(err.message); }
    };
  },

  async reviews() {
    const { items } = await api('/admin/reviews');
    view.innerHTML = `
      <p class="eyebrow">REVIEWS</p><h1 class="page-title" style="font-size:30px;padding-bottom:24px;border-bottom:1px solid var(--ink)">評論管理</h1>
      <div class="table-box"><table class="data" style="min-width:820px"><thead><tr><th>編號</th><th>餐廳</th><th>會員</th><th>評分</th><th>內容</th><th>時間</th><th></th></tr></thead>
        <tbody>${items.map((v) => `<tr><td class="small">${esc(v.revid)}</td><td>${esc(v.rname)}</td><td>${esc(v.mname || '已刪除的會員')}</td><td>${v.rating}</td>
          <td style="max-width:360px">${esc(v.comment || '')}</td><td class="small">${esc((v.reviewtime || '').slice(0, 10))}</td>
          <td><button class="link-btn quiet" data-del="${esc(v.revid)}">刪除</button></td></tr>`).join('') || '<tr><td colspan="7" class="empty">沒有評論</td></tr>'}</tbody></table></div>`;
    view.onclick = async (e) => {
      const b = e.target.closest('[data-del]');
      if (b && confirmClick(b, '確定刪除？')) {
        try { await api('/admin/reviews/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); toast('評論已刪除'); views.reviews(); } catch (err) { toast(err.message); }
      }
    };
  },

  async members() {
    const { items } = await api('/admin/members');
    view.innerHTML = `
      <p class="eyebrow">MEMBERS</p><h1 class="page-title" style="font-size:30px;padding-bottom:24px;border-bottom:1px solid var(--ink)">會員管理</h1>
      <div class="table-box"><table class="data" style="min-width:820px"><thead><tr><th>編號</th><th>姓名</th><th>信箱</th><th>手機</th><th>評論</th><th>預約</th><th>身分</th><th></th></tr></thead>
        <tbody>${items.map((m) => `<tr><td class="small">${esc(m.mid)}</td><td class="strong">${esc(m.mname)}</td><td>${esc(m.email)}</td><td>${esc(m.phone || '')}</td>
          <td>${m.reviews}</td><td>${m.reservations}</td>
          <td><select data-role="${esc(m.mid)}" aria-label="身分" style="padding:6px 10px;width:auto"><option value="user"${m.role !== 'admin' ? ' selected' : ''}>一般會員</option><option value="admin"${m.role === 'admin' ? ' selected' : ''}>管理者</option></select></td>
          <td><button class="link-btn quiet" data-del="${esc(m.mid)}">刪除</button></td></tr>`).join('')}</tbody></table></div>`;
    view.onchange = async (e) => {
      const s = e.target.closest('[data-role]');
      if (!s) return;
      try { await api('/admin/members/' + encodeURIComponent(s.dataset.role), { method: 'PATCH', body: { role: s.value } }); toast('身分已更新'); } catch (err) { toast(err.message); views.members(); }
    };
    view.onclick = async (e) => {
      const b = e.target.closest('[data-del]');
      if (b && confirmClick(b, '確定刪除？')) {
        try { await api('/admin/members/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); toast('會員已刪除'); views.members(); } catch (err) { toast(err.message); }
      }
    };
  }
};

// ---------- 餐廳表單 ----------
let restReload = () => {};
let editingRest = null;
const rd = $('#rest-dialog');
const rf = $('#rest-form');

async function openRest(r) {
  if (!allTags.length) allTags = (await api('/tags')).items;
  editingRest = r;
  $('#rest-h').textContent = r ? `編輯餐廳：${r.rname}` : '新增餐廳';
  rf.reset();
  if (r) {
    rf.rName.value = r.rname; rf.address.value = r.address || ''; rf.priceRange.value = String(r.pricerange || '1').trim();
    rf.google_rate.value = r.google_rate ?? ''; rf.google_num.value = r.google_num ?? '';
    rf.acceptRes.checked = !!r.acceptres; rf.capacity.value = r.capacity ?? ''; rf.maxPartySize.value = r.maxpartysize ?? 4;
    rf.picture.value = r.picture || '';
  }
  const selected = new Set((r?.tag_ids || []).map((x) => x.trim()));
  $('#tag-picks').innerHTML = allTags.map((t) => `<label class="check" style="min-height:32px;font-size:14px;font-family:var(--sans)" data-tname="${esc(t.tname)}">
      <input type="checkbox" value="${esc(t.tid)}"${selected.has(t.tid.trim()) ? ' checked' : ''}>${esc(t.tname)}</label>`).join('');
  $('#tag-filter').value = '';
  showMsg($('#rest-msg'), '');
  rd.showModal();
}
$('#tag-filter').addEventListener('input', (e) => {
  const q = e.target.value.trim();
  $$('#tag-picks [data-tname]').forEach((el) => { el.hidden = q && !el.dataset.tname.includes(q); });
});
rf.addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {
    rName: rf.rName.value, address: rf.address.value, priceRange: rf.priceRange.value,
    google_rate: rf.google_rate.value, google_num: rf.google_num.value, acceptRes: rf.acceptRes.checked,
    capacity: rf.capacity.value, maxPartySize: rf.maxPartySize.value, picture: rf.picture.value,
    tagIds: $$('#tag-picks input:checked').map((x) => x.value)
  };
  try {
    if (editingRest) await api('/admin/restaurants/' + encodeURIComponent(editingRest.rid), { method: 'PUT', body });
    else await api('/admin/restaurants', { method: 'POST', body });
    rd.close(); toast('餐廳已儲存'); restReload();
  } catch (err) { showMsg($('#rest-msg'), err.message); }
});

// ---------- 招牌菜 ----------
const md = $('#menu-dialog');
const mf = $('#menu-form');
let menuRid = null;
let menuEditing = null;
async function openMenu(rid, name) {
  menuRid = rid;
  $('#menu-sub').textContent = name;
  await loadMenu();
  md.open || md.showModal();
}
async function loadMenu() {
  const { items } = await api(`/admin/restaurants/${encodeURIComponent(menuRid)}/menu`);
  $('#menu-rows').innerHTML = items.map((m) => `<tr><td class="strong">${esc(m.menuname)}</td><td>${m.price ?? '—'}</td><td>${esc(m.description || '')}</td>
    <td style="white-space:nowrap"><button class="link-btn" type="button" data-medit="${esc(m.menuname)}">編輯</button>　<button class="link-btn quiet" type="button" data-mdel="${esc(m.menuname)}">刪除</button></td></tr>`).join('')
    || '<tr><td colspan="4" class="small">尚無招牌菜</td></tr>';
  $('#menu-rows').onclick = async (e) => {
    const ed = e.target.closest('[data-medit]');
    const del = e.target.closest('[data-mdel]');
    if (ed) {
      const m = items.find((x) => x.menuname === ed.dataset.medit);
      menuEditing = m.menuname; mf.menuName.value = m.menuname; mf.price.value = m.price ?? ''; mf.description.value = m.description || '';
      $('#menu-submit').textContent = '儲存修改';
    }
    if (del && confirmClick(del, '確定？')) {
      try { await api(`/admin/restaurants/${encodeURIComponent(menuRid)}/menu/${encodeURIComponent(del.dataset.mdel)}`, { method: 'DELETE' }); loadMenu(); } catch (err) { toast(err.message); }
    }
  };
  mf.reset(); menuEditing = null; $('#menu-submit').textContent = '新增招牌菜'; showMsg($('#menu-msg'), '');
}
mf.addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = { menuName: mf.menuName.value, price: mf.price.value, description: mf.description.value };
  try {
    if (menuEditing) await api(`/admin/restaurants/${encodeURIComponent(menuRid)}/menu/${encodeURIComponent(menuEditing)}`, { method: 'PUT', body });
    else await api(`/admin/restaurants/${encodeURIComponent(menuRid)}/menu`, { method: 'POST', body });
    loadMenu();
  } catch (err) { showMsg($('#menu-msg'), err.message); }
});

$$('[data-close]').forEach((b) => b.addEventListener('click', () => b.closest('dialog').close()));

// ---------- 切換分頁 ----------
async function show(name) {
  $$('#admin-nav button').forEach((b) => b.setAttribute('aria-current', b.dataset.view === name ? 'page' : 'false'));
  view.onclick = null; view.onchange = null;
  view.innerHTML = '<p class="loading">載入中…</p>';
  try { await views[name](); } catch (err) { view.innerHTML = `<p class="empty">${esc(err.message)}</p>`; }
}
if (requireLogin({ admin: true })) {
  renderLayout('admin');
  document.querySelector('.site-footer')?.remove();
  $('#admin-nav').addEventListener('click', (e) => { const b = e.target.closest('[data-view]'); if (b) show(b.dataset.view); });
  show('stats');
}
