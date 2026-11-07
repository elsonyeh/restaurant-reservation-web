import { api, auth, esc, imgSrc, priceHtml, rate, stars, showMsg, today, toast, $ } from '../api.js?v=20261107k';
import { renderLayout } from '../layout.js?v=20261107k';

renderLayout('home');

const rid = new URLSearchParams(location.search).get('id');
const main = $('#main');
let rest = null;
let selectedSlot = null;

async function load() {
  if (!rid) { main.innerHTML = '<p class="empty">找不到這家餐廳。<a href="index.html">回餐廳列表</a></p>'; return; }
  try {
    rest = await api('/restaurants/' + encodeURIComponent(rid));
  } catch (e) {
    main.innerHTML = `<p class="empty">${esc(e.message)}　<a href="index.html">回餐廳列表</a></p>`;
    return;
  }
  document.title = `${rest.rname}｜留席 SAVED SEAT`;
  render();
  if (rest.acceptres) loadSlots();
}

function render() {
  const r = rest;
  const s = r.review_summary || { n: 0 };
  const user = auth.user;
  const myReview = user ? r.reviews.find((v) => (v.mid || '').trim() === (user.mid || '').trim()) : null;

  const picture = r.picture
    ? `<img src="${esc(imgSrc(r.picture))}" alt="${esc(r.rname)} 的照片" style="width:100%;height:clamp(240px,36vw,480px);object-fit:cover">`
    : `<div class="marble" style="height:clamp(200px,26vw,340px);display:flex;align-items:center;justify-content:center;text-align:center;padding:24px">
         <span style="font-size:clamp(26px,4vw,40px);letter-spacing:.12em;color:var(--rose-dark)">${esc(r.rname)}</span>
       </div>`;

  const dist = [5, 4, 3, 2, 1].map((k) => {
    const n = s['s' + k] || 0;
    const w = s.n ? Math.round((n / s.n) * 100) : 0;
    return `<li><span class="k" style="flex-basis:36px">${k} ★</span><span class="track" style="height:2px;background:var(--line)"><span class="fill" style="width:${w}%"></span></span><span class="v">${n}</span></li>`;
  }).join('');

  main.innerHTML = `
  <div class="wrap" style="padding-top:28px">
    <nav aria-label="麵包屑" class="small" style="display:flex;flex-wrap:wrap;gap:8px">
      <a href="index.html" style="color:var(--faint)">餐廳列表</a><span aria-hidden="true">/</span><span>${esc(r.district)}</span><span aria-hidden="true">/</span><span style="color:var(--ink)">${esc(r.rname)}</span>
    </nav>
    <div style="display:flex;flex-wrap:wrap;justify-content:space-between;align-items:flex-end;gap:24px 40px;padding:40px 0 36px">
      <div style="display:flex;flex-direction:column;gap:14px;flex:1 1 480px;min-width:0">
        <p class="eyebrow">${esc(r.district)}</p>
        <h1 style="margin:0;font-size:clamp(28px,4vw,40px);font-weight:400;letter-spacing:.06em;line-height:1.35">${esc(r.rname)}</h1>
        <div style="display:flex;flex-wrap:wrap;gap:8px 22px;font-size:15px;color:var(--body);align-items:baseline">
          <span><b style="font-weight:500">★ ${rate(r.google_rate)}</b> <span class="small">Google · ${(r.google_num || 0).toLocaleString()} 則</span></span>
          ${s.n ? `<span style="color:var(--line-strong)" aria-hidden="true">|</span>
          <span><b style="font-weight:500">★ ${rate(s.avg)}</b> <span class="small">會員 · ${s.n} 則</span></span>` : ''}
          <span style="color:var(--line-strong)" aria-hidden="true">|</span>
          <span>${priceHtml(r.pricerange)}</span>
        </div>
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:12px">
        <button type="button" class="btn btn-outline" id="fav-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M6 3h12v18l-6-4-6 4z"></path></svg>
          ${r.my_lists && r.my_lists.some((l) => l.contains) ? '已收藏' : '加入收藏'}
        </button>
        ${r.acceptres ? '<a href="#reserve" class="btn">立即預約</a>' : ''}
      </div>
    </div>
  </div>
  <div class="wrap">${picture}</div>

  <div class="wrap" style="padding-top:64px;padding-bottom:64px">
    <div class="cols">
      <div class="col">
        <h2 class="h-col" style="margin-bottom:22px">INFORMATION</h2>
        <ul class="bullets">
          <li>${esc(r.address || '地址未提供')}</li>
          <li>價位 ${'$'.repeat(Number(r.pricerange) || 0) || '—'}・建議 1–${r.maxpartysize || 4} 人用餐</li>
          <li>${r.acceptres ? `可線上訂位・每筆最多 ${r.maxpartysize} 人` : '不提供線上訂位'}</li>
        </ul>
      </div>
      <div class="col">
        <h2 class="h-col" style="margin-bottom:22px">TAGS</h2>
        <div class="chips">${r.tags.length ? r.tags.map((t) => `<span class="chip" style="font-size:14px;padding:6px 12px">${esc(t)}</span>`).join('') : '<span class="muted">尚無標籤</span>'}</div>
        ${(r.public_lists || []).length ? `
        <p style="margin:32px 0 12px;font-size:15px;color:var(--body)">被收錄在 ${r.public_lists.length} 份公開清單</p>
        <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:8px">
          ${r.public_lists.map((l) => `<li style="font-size:15px"${l.description ? ` title="${esc(l.description)}"` : ''}>
            <span style="font-weight:500">${esc(l.fname)}</span><span class="small">・${esc(l.owner)} 的清單</span></li>`).join('')}
        </ul>` : ''}
      </div>
    </div>
  </div>

  ${r.menu.length ? `
  <section aria-labelledby="menu-h" class="marble" style="padding:84px 0">
    <div class="wrap" style="max-width:840px">
      <div style="text-align:center;margin-bottom:40px">
        <h2 id="menu-h" style="margin:0;font-size:24px;font-weight:500;letter-spacing:.06em">TOP MENU</h2>
        <p style="margin:10px 0 0;font-size:15px;color:var(--muted)">招牌菜</p>
      </div>
      <ul style="margin:0;padding:0;list-style:none;display:flex;flex-direction:column;gap:26px">
        ${r.menu.map((m) => `
        <li style="display:flex;flex-direction:column;gap:6px">
          <div style="display:flex;align-items:baseline;gap:12px">
            <span style="font-size:18px;font-weight:500">${esc(m.menuname)}</span>
            <span style="flex:1 1 auto;border-bottom:1px dotted #B9A6A2;transform:translateY(-4px)" aria-hidden="true"></span>
            <span style="font-family:var(--sans);font-size:15px">${m.price != null ? 'NT$ ' + Number(m.price).toLocaleString() : '價格未提供'}</span>
          </div>
          ${m.description ? `<span style="font-size:14px;color:var(--muted);line-height:1.8">${esc(m.description)}</span>` : ''}
        </li>`).join('')}
      </ul>
    </div>
  </section>` : ''}

  ${r.acceptres ? `
  <section id="reserve" aria-labelledby="res-h" class="wrap" style="padding-top:88px;padding-bottom:88px">
    <div class="sec-head" style="margin-bottom:36px"><div><h2 id="res-h" style="display:inline">RESERVATION</h2><span class="sub">線上訂位</span></div></div>
    <div style="display:flex;flex-wrap:wrap;gap:40px 64px">
      <form id="res-form" class="form" style="flex:2 1 440px;min-width:0">
        <div class="row">
          <label class="field">用餐日期<input type="date" name="date" min="${today()}" value="${today(1)}" required></label>
          <label class="field">用餐人數（上限 ${r.maxpartysize} 人）
            <select name="size">${Array.from({ length: r.maxpartysize }, (_, i) => `<option value="${i + 1}"${i === 1 ? ' selected' : ''}>${i + 1} 人</option>`).join('')}</select>
          </label>
        </div>
        <fieldset style="border:0;margin:0;padding:0">
          <legend style="font-size:14px;color:var(--muted);margin-bottom:10px;padding:0">用餐時段</legend>
          <div id="slots" style="display:flex;flex-wrap:wrap;gap:10px"><span class="small">載入中…</span></div>
        </fieldset>
        <label class="field">備註（選填）<textarea name="note" rows="3" maxlength="200" placeholder="例如：一位不吃辣、需要兒童椅" style="resize:vertical"></textarea></label>
        <p class="msg err" id="res-msg" hidden></p>
        <div class="row" style="align-items:center">
          <button type="submit" class="btn" style="letter-spacing:.2em">送出預約</button>
          
        </div>
      </form>
      <aside aria-label="預約說明" style="flex:1 1 260px;border-left:1px solid var(--line-strong);padding-left:40px">
        <p class="eyebrow" style="letter-spacing:.3em">SELECTED</p>
        <p style="margin:6px 0 0;font-size:20px;font-weight:500" id="sel-label">請選擇時段</p>
        <p style="margin:6px 0 22px;font-size:15px;color:var(--body)" id="sel-seats"></p>
        <ul class="bullets" style="font-size:14px;gap:12px">
          <li>額滿或已過的時段無法選擇</li>
          <li>店家確認後，可在「我的預約」查看</li>
          <li>無法前往請提早取消</li>
        </ul>
      </aside>
    </div>
  </section>` : ''}

  <section aria-labelledby="rev-h" class="wrap" style="padding-top:${r.acceptres ? 0 : 88}px;padding-bottom:96px">
    <div class="sec-head" style="margin-bottom:40px">
      <div><h2 id="rev-h" style="display:inline">REVIEWS</h2><span class="sub">會員評論</span></div>
      <span class="meta">共 ${s.n} 則</span>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:48px 64px">
      <div style="flex:1 1 280px;display:flex;flex-direction:column;gap:28px;min-width:0">
        ${s.n ? `<div style="display:flex;align-items:baseline;gap:12px">
          <span style="font-size:56px;font-weight:400;line-height:1">${rate(s.avg)}</span>
          <span style="font-size:15px;color:var(--muted)">/ 5・會員平均</span>
        </div>
        <ul class="bars" style="font-size:13px;gap:10px">${dist}</ul>` : ''}
        <div${s.n ? ' style="border-top:1px solid var(--line);padding-top:24px"' : ''}>
          ${!user ? `<p style="margin:0;font-size:15px">想留下評論？<a href="login.html?next=${encodeURIComponent('restaurant.html?id=' + rid)}" style="color:var(--rose-dark);border-bottom:1px solid var(--rose)">登入會員</a></p>`
            : myReview ? `<p style="margin:0;font-size:15px">你已經評論過這家店，可以到 <a href="member.html" style="color:var(--rose-dark);border-bottom:1px solid var(--rose)">會員中心</a> 修改。</p>`
            : `<form id="rev-form" class="form" style="gap:14px">
                <p style="margin:0;font-size:17px;font-weight:500">寫下你的評論</p>
                <div class="row" style="gap:14px">
                  <label class="field" style="flex:1 1 110px">評分<select name="rating"><option value="5">5 分</option><option value="4">4 分</option><option value="3">3 分</option><option value="2">2 分</option><option value="1">1 分</option></select></label>
                  <label class="field" style="flex:1 1 140px">用餐日期<input type="date" name="visitDate" max="${today()}"></label>
                </div>
                <label class="field">評論內容<textarea name="comment" rows="4" maxlength="1000" style="resize:vertical"></textarea></label>
                <p class="msg err" id="rev-msg" hidden></p>
                <button type="submit" class="btn btn-outline" style="align-self:flex-start">發表評論</button>
              </form>`}
        </div>
      </div>
      <ol style="flex:2 1 460px;margin:0;padding:0;list-style:none;min-width:0">
        ${r.reviews.length ? r.reviews.map((v) => `
        <li style="padding:0 0 28px;margin-bottom:28px;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:10px">
          <div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:6px 16px;align-items:baseline">
            <span style="font-size:17px;font-weight:500">${esc(v.mname)}</span>
            <span class="small">${v.visitdate ? '用餐 ' + v.visitdate + '・' : ''}發表於 ${esc((v.reviewtime || '').slice(0, 10))}</span>
          </div>
          ${stars(v.rating)}
          ${v.comment ? `<p style="margin:0;font-size:16px;line-height:2;color:var(--body);white-space:pre-line">${esc(v.comment)}</p>` : ''}
        </li>`).join('') : '<li class="empty" style="padding-top:0">目前還沒有評論。</li>'}
      </ol>
    </div>
  </section>`;

  bind();
}

async function loadSlots() {
  const form = $('#res-form');
  const box = $('#slots');
  const size = Number(form.size.value);
  box.innerHTML = '<span class="small">載入中…</span>';
  try {
    const data = await api(`/restaurants/${encodeURIComponent(rid)}/availability`, { query: { date: form.date.value } });
    box.innerHTML = data.slots.map((s) => {
      const disabled = s.past || s.seats_left < size;
      const sub = s.past ? '已過' : s.seats_left < size ? '額滿' : s.seats_left <= 8 ? '名額有限' : '可預約';
      return `<button type="button" class="tag-btn" data-time="${s.time}" aria-pressed="${selectedSlot === s.time && !disabled}"
                ${disabled ? 'disabled' : ''} style="min-width:92px;min-height:52px;padding:6px 14px;font-size:15px;${disabled ? 'color:#9C918E;background:#FAF8F8;cursor:not-allowed;text-decoration:line-through' : ''}">
                ${s.time}<span style="display:block;font-size:12px;color:var(--faint);text-decoration:none">${sub}</span></button>`;
    }).join('');
    if (selectedSlot && !box.querySelector(`[data-time="${selectedSlot}"]:not([disabled])`)) selectedSlot = null;
    updateSelected();
  } catch (e) {
    box.innerHTML = `<span class="msg err">${esc(e.message)}</span>`;
  }
}

function updateSelected() {
  const form = $('#res-form');
  const btn = selectedSlot && $(`#slots [data-time="${selectedSlot}"]`);
  document.querySelectorAll('#slots [data-time]').forEach((b) => {
    const on = b.dataset.time === selectedSlot;
    b.setAttribute('aria-pressed', on);
    if (!b.disabled) { b.style.background = on ? 'var(--rose)' : '#fff'; b.style.color = on ? '#fff' : ''; b.style.borderColor = on ? 'var(--rose)' : ''; }
  });
  $('#sel-label').textContent = btn ? `${form.date.value.slice(5).replace('-', ' 月 ')} 日 ${selectedSlot}` : '請選擇時段';
  $('#sel-seats').textContent = btn ? `${form.size.value} 位` : '';
}

function bind() {
  $('#fav-btn').addEventListener('click', openFav);

  const resForm = $('#res-form');
  if (resForm) {
    resForm.date.addEventListener('change', () => { selectedSlot = null; loadSlots(); });
    resForm.size.addEventListener('change', loadSlots);
    $('#slots').addEventListener('click', (e) => {
      const b = e.target.closest('[data-time]');
      if (!b || b.disabled) return;
      selectedSlot = b.dataset.time;
      updateSelected();
    });
    resForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const msg = $('#res-msg');
      if (!auth.token) { location.href = 'login.html?next=' + encodeURIComponent('restaurant.html?id=' + rid); return; }
      if (!selectedSlot) { showMsg(msg, '請先選擇用餐時段'); return; }
      try {
        await api('/reservations', { method: 'POST', body: { rId: rid, dateTime: `${resForm.date.value} ${selectedSlot}`, partySize: Number(resForm.size.value), note: resForm.note.value } });
        showMsg(msg, '');
        toast('預約已送出，等待店家確認');
        setTimeout(() => { location.href = 'reservations.html'; }, 900);
      } catch (err) {
        showMsg(msg, err.message);
        loadSlots();
      }
    });
  }

  const revForm = $('#rev-form');
  if (revForm) {
    revForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        await api('/reviews', { method: 'POST', body: { rId: rid, rating: Number(revForm.rating.value), visitDate: revForm.visitDate.value || null, comment: revForm.comment.value } });
        toast('評論已發表');
        load();
      } catch (err) { showMsg($('#rev-msg'), err.message); }
    });
  }
}

// ---------- 收藏 ----------
const dlg = $('#fav-dialog');
function openFav() {
  if (!auth.token) { location.href = 'login.html?next=' + encodeURIComponent('restaurant.html?id=' + rid); return; }
  const lists = rest.my_lists || [];
  $('#fav-lists').innerHTML = lists.length
    ? lists.map((l) => `<label class="check"><input type="checkbox" value="${esc(l.fid)}"${l.contains ? ' checked' : ''}>${esc(l.fname)}</label>`).join('')
    : '<p class="small" style="margin:0">你還沒有收藏清單，在下面輸入名稱建立一個。</p>';
  $('#fav-form').newList.value = '';
  showMsg($('#fav-msg'), '');
  dlg.showModal();
}
$('#fav-cancel').addEventListener('click', () => dlg.close());
$('#fav-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  try {
    const lists = rest.my_lists || [];
    for (const box of document.querySelectorAll('#fav-lists input[type=checkbox]')) {
      const before = lists.find((l) => l.fid === box.value)?.contains;
      if (box.checked && !before) await api(`/favlists/${encodeURIComponent(box.value)}/restaurants`, { method: 'POST', body: { rId: rid } });
      if (!box.checked && before) await api(`/favlists/${encodeURIComponent(box.value)}/restaurants/${encodeURIComponent(rid)}`, { method: 'DELETE' });
    }
    const name = $('#fav-form').newList.value.trim();
    if (name) {
      const { fid } = await api('/favlists', { method: 'POST', body: { fName: name } });
      await api(`/favlists/${encodeURIComponent(fid)}/restaurants`, { method: 'POST', body: { rId: rid } });
    }
    dlg.close();
    toast('收藏已更新');
    load();
  } catch (err) { showMsg($('#fav-msg'), err.message); }
});

load();
