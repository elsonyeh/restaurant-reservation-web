// 呼叫後端 API、管理登入狀態、共用的小工具
const API_BASE = (window.SIWAN_API_BASE || '').replace(/\/$/, '');

export const auth = {
  get token() { try { return localStorage.getItem('siwan_token'); } catch { return null; } },
  get user() { try { return JSON.parse(localStorage.getItem('siwan_user') || 'null'); } catch { return null; } },
  save(token, member) {
    try {
      localStorage.setItem('siwan_token', token);
      localStorage.setItem('siwan_user', JSON.stringify(member));
    } catch { /* 無痕模式等情況無法儲存 */ }
  },
  clear() { try { localStorage.removeItem('siwan_token'); localStorage.removeItem('siwan_user'); } catch {} }
};

export async function api(path, { method = 'GET', body, query } = {}) {
  let url = API_BASE + '/api' + path;
  if (query) {
    const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ''));
    if ([...qs].length) url += '?' + qs;
  }
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth.token) headers.Authorization = 'Bearer ' + auth.token;

  let res;
  try {
    res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error('目前無法連線，請稍後再試');
  }
  let data = null;
  try { data = await res.json(); } catch { /* 沒有內容 */ }
  if (res.status === 401 && auth.token) {
    auth.clear();
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
  setTimeout(() => el.remove(), 2600);
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
    location.href = 'login.html?next=' + encodeURIComponent(location.pathname.split('/').pop() + location.search);
    return null;
  }
  if (admin && u.role !== 'admin') {
    location.href = 'index.html';
    return null;
  }
  return u;
}
