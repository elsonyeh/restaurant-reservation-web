// 呼叫後端 API、管理登入狀態、共用的小工具
const API_BASE = (window.API_BASE_URL || '').replace(/\/$/, '');

export const auth = {
  get token() { try { return localStorage.getItem('gs_token'); } catch { return null; } },
  get user() { try { return JSON.parse(localStorage.getItem('gs_user') || 'null'); } catch { return null; } },
  save(token, member) {
    try {
      localStorage.setItem('gs_token', token);
      localStorage.setItem('gs_user', JSON.stringify(member));
    } catch { /* 無痕模式等情況無法儲存 */ }
  },
  clear() { try { localStorage.removeItem('gs_token'); localStorage.removeItem('gs_user'); } catch {} }
};

let slowNoticed = false;

export async function api(path, { method = 'GET', body, query } = {}) {
  let url = API_BASE + '/api' + path;
  if (query) {
    const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ''));
    if ([...qs].length) url += '?' + qs;
  }
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth.token) headers.Authorization = 'Bearer ' + auth.token;

  // 連線超過 4 秒（例如主機剛被喚醒）時，提示一次請使用者稍候
  const slow = setTimeout(() => { if (!slowNoticed) { slowNoticed = true; toast('資料準備中，第一次開啟可能需要半分鐘，請稍候'); } }, 4000);
  let res;
  try {
    res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    clearTimeout(slow);
    throw new Error('目前無法連線，請稍後再試');
  }
  clearTimeout(slow);
  let data = null;
  try { data = await res.json(); } catch { /* 沒有內容 */ }
  if (res.status === 401 && auth.token) {
    // 登入已失效（例如過期）：清掉登入資料，回到登入頁後再回來
    auth.clear();
    location.replace('login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search));
    throw new Error('登入已過期，請重新登入');
  }
  if (!res.ok) throw new Error((data && data.error) || `發生錯誤（${res.status}）`);
  return data;
}

// 把文字轉成安全的 HTML（避免使用者輸入的內容被當成程式碼執行）
export function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function priceHtml(p) {
  const n = Number(p) || 0;
  return `<span aria-label="${['', '平價', '中價位', '高價位'][n] || ''}">${'$'.repeat(n)}<i style="font-style:normal;color:#C9BDBA">${'$'.repeat(Math.max(3 - n, 0))}</i></span>`;
}

/** 圖片網址：存在資料庫裡的圖片由後端 /api/... 提供 */
export function imgSrc(p) {
  return p && p.startsWith('/api/') ? API_BASE + p : (p || '');
}

/** 評分統一顯示一位小數（5 → 5.0），沒有評分顯示 — */
export function rate(x) {
  const n = Number(x);
  return x == null || x === '' || !n ? '—' : n.toFixed(1);
}

export function stars(n) {
  const k = Math.round(Number(n) || 0);
  return `<span style="color:var(--rose);letter-spacing:.15em" aria-label="${k} 分">${'★'.repeat(k)}<span style="color:#DCCFCC">${'★'.repeat(5 - k)}</span></span>`;
}

export const STATUS_LABEL = { pending: '待確認', confirmed: '已確認', rejected: '已拒絕', cancelled: '已取消', completed: '已完成' };

const WEEK = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
export function splitDateTime(s) {
  // s = 'YYYY-MM-DD HH:MM'
  const [d, t] = String(s).split(' ');
  const [y, m, day] = d.split('-').map(Number);
  const dt = new Date(y, m - 1, day);
  return { date: d, time: t, month: `${m} 月`, day: String(day), week: WEEK[dt.getDay()], label: `${m}/${day}（${WEEK[dt.getDay()].slice(1)}）${t}` };
}

export function today(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function toast(text) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.setAttribute('role', 'status');
  el.textContent = text;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), text.length > 20 ? 5000 : 2600);
}

export function showMsg(el, text, ok = false) {
  el.hidden = !text;
  el.className = 'msg ' + (ok ? 'ok' : 'err');
  el.textContent = text || '';
}

// 需要登入的頁面：沒登入就帶到登入頁，登入後再回來
export function requireLogin({ admin = false } = {}) {
  const u = auth.user;
  if (!u || !auth.token) {
    location.replace('login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search));
    return null;
  }
  if (admin && u.role !== 'admin') {
    location.replace('index.html');
    return null;
  }
  return u;
}
