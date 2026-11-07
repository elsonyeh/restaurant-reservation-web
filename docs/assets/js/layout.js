// 每一頁共用的頁首與頁尾
import { auth, esc } from './api.js?v=20261107h';

const USER_ICON = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="8" r="4"></circle><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"></path></svg>';

export function renderLayout(active) {
  const u = auth.user;
  const nav = [
    ['index.html', '找餐廳', 'home'],
    ['reservations.html', '我的預約', 'reservations'],
    ['favorites.html', '我的收藏', 'favorites'],
    ['member.html', '會員中心', 'member']
  ];
  if (u && u.role === 'admin') nav.push(['admin.html', '管理後台', 'admin']);

  const header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML = `
    <div class="wrap-wide">
      <a href="index.html" class="logo" aria-label="留席 SAVED SEAT 首頁">
        <span class="l1">SAVED SEAT</span><span class="l2">RESERVE · 留席</span>
      </a>
      <nav class="main-nav" aria-label="主選單">
        ${nav.map(([href, label, key]) => `<a href="${!u && key !== 'home' ? 'login.html?next=' + href : href}"${key === active ? ' aria-current="page"' : ''}>${label}</a>`).join('')}
      </nav>
      <div class="header-actions">
        ${u
          ? `<a href="member.html" class="btn btn-outline btn-sm">${USER_ICON}${esc(u.mname)}</a>
             <button type="button" class="btn btn-quiet btn-sm" id="logout-btn">登出</button>`
          : `<a href="login.html" class="btn btn-outline btn-sm">${USER_ICON}登入 / 註冊</a>`}
      </div>
    </div>`;
  document.body.prepend(header);

  const logout = header.querySelector('#logout-btn');
  if (logout) logout.addEventListener('click', () => { auth.clear(); location.href = 'index.html'; });

  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="wrap">
      <a href="index.html" class="logo" aria-label="回首頁"><span class="l1" style="font-size:24px">SAVED SEAT</span><span class="l2">RESERVE · 留席</span></a>
      <p class="small" style="margin:0;line-height:1.8">中山大學周邊餐廳訂位與評價<br>© 2026 留席 SAVED SEAT</p>
    </div>`;
  document.body.appendChild(footer);
}
