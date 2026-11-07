import { api, esc, priceHtml, rate, $ } from '../api.js?v=20261107n';
import { renderLayout } from '../layout.js?v=20261107n';

renderLayout('home');

const state = { q: '', district: '', price: '', sort: 'google', tags: new Set(), acceptRes: false, page: 1 };
const form = $('#search-form');

async function loadSummary() {
  try {
    const s = await api('/summary');
    $('#summary').innerHTML = `
      <li>收錄餐廳 ${s.restaurants} 家</li>
      <li>鹽埕區 ${s.yancheng} 家 · 鼓山區 ${s.gushan} 家</li>
      <li>可線上訂位 ${s.accept_res} 家</li>`;
  } catch (e) {
    $('#summary').innerHTML = '<li>暫時無法載入，請稍後再試</li>';
  }
}

async function loadTags() {
  const { items } = await api('/tags');
  const top = items.filter((t) => t.n > 0).slice(0, 12);
  $('#tag-buttons').innerHTML = top.map((t) =>
    `<button type="button" class="tag-btn" aria-pressed="false" data-tag="${esc(t.tname)}">${esc(t.tname)}</button>`).join('');
  $('#tag-cloud').innerHTML = top.map((t) =>
    `<li><a href="#results" data-tag="${esc(t.tname)}">${esc(t.tname)} <span style="font-size:13px;color:var(--rose)">${t.n}</span></a></li>`).join('');
}

async function loadList() {
  const list = $('#rest-list');
  list.innerHTML = '<li class="loading">載入中…</li>';
  const slow = setTimeout(() => {
    const el = list.querySelector('.loading');
    if (el) el.textContent = '載入中…';
  }, 4000);
  try {
    const data = await api('/restaurants', {
      query: {
        q: state.q, district: state.district, price: state.price, sort: state.sort, page: state.page,
        tags: [...state.tags].join(','), acceptRes: state.acceptRes ? '1' : ''
      }
    });
    $('#result-meta').textContent = `共 ${data.total} 家`;
    if (!data.items.length) {
      list.innerHTML = '<li class="empty">沒有符合條件的餐廳。</li>';
    } else {
      const start = (data.page - 1) * data.pageSize;
      list.innerHTML = data.items.map((r, i) => `
        <li class="rest-row">
          <span class="no">${String(start + i + 1).padStart(2, '0')}</span>
          <div class="name">
            <a href="restaurant.html?id=${r.rid}">${esc(r.rname)}</a>
            <span>${esc(r.district)}${r.acceptres ? '　·　可線上訂位' : ''}</span>
          </div>
          <div class="tags chips">${(r.tags || []).slice(0, 4).map((t) => `<span class="chip">${esc(t)}</span>`).join('')}</div>
          <div class="price">${priceHtml(r.pricerange)}</div>
          <div class="rate">
            <b>★ ${rate(r.google_rate)}</b>
            <span class="small">(${r.google_num ? r.google_num.toLocaleString() : 0})</span>
          </div>
          <a class="go" href="restaurant.html?id=${r.rid}">查看餐廳</a>
        </li>`).join('');
    }
    renderPager(data.total, data.pageSize);
    clearTimeout(slow);
  } catch (e) {
    clearTimeout(slow);
    list.innerHTML = `<li class="empty">${esc(e.message)}</li>`;
    $('#pager').innerHTML = '';
  }
}

function renderPager(total, size) {
  const pages = Math.ceil(total / size);
  const nav = $('#pager');
  if (pages <= 1) { nav.innerHTML = ''; return; }
  const nums = [];
  for (let p = 1; p <= pages; p++) {
    if (p === 1 || p === pages || Math.abs(p - state.page) <= 1) nums.push(p);
    else if (nums[nums.length - 1] !== '…') nums.push('…');
  }
  nav.innerHTML = nums.map((p) => p === '…'
    ? '<span style="min-width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center">…</span>'
    : `<button type="button" data-page="${p}"${p === state.page ? ' aria-current="page"' : ''}>${p}</button>`).join('');
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(form);
  Object.assign(state, { q: fd.get('q').trim(), district: fd.get('district'), price: fd.get('price'), sort: fd.get('sort'), page: 1 });
  loadList();
});
form.sort.addEventListener('change', () => form.requestSubmit());
form.district.addEventListener('change', () => form.requestSubmit());
form.price.addEventListener('change', () => form.requestSubmit());

$('#accept-res').addEventListener('change', (e) => { state.acceptRes = e.target.checked; state.page = 1; loadList(); });

function toggleTag(tag) {
  if (state.tags.has(tag)) state.tags.delete(tag); else state.tags.add(tag);
  document.querySelectorAll('#tag-buttons .tag-btn').forEach((b) => b.setAttribute('aria-pressed', state.tags.has(b.dataset.tag)));
  state.page = 1;
  loadList();
}
$('#tag-buttons').addEventListener('click', (e) => { const b = e.target.closest('[data-tag]'); if (b) toggleTag(b.dataset.tag); });
$('#tag-cloud').addEventListener('click', (e) => {
  const a = e.target.closest('[data-tag]');
  if (!a) return;
  state.tags.clear();
  toggleTag(a.dataset.tag);
});
$('#pager').addEventListener('click', (e) => {
  const b = e.target.closest('[data-page]');
  if (!b) return;
  state.page = Number(b.dataset.page);
  loadList();
  $('#results').scrollIntoView({ behavior: 'smooth' });
});

loadSummary();
loadTags().catch(() => {});
loadList();
