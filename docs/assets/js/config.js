// 後端 API 的網址。
// - 本機執行（python app.py 後開 http://127.0.0.1:5050）：前後端同一個網址，不用設定。
// - GitHub Pages：使用下面 DEFAULT_API 的後端網址（Render）。
//   測試其他後端時，可在網址後加上 ?api=後端網址，瀏覽器會記住；加上 ?api= 留空則恢復預設。
(function () {
  var DEFAULT_API = 'https://restaurant-reservation-api-5i11.onrender.com';
  var onPages = /\.github\.io$/.test(location.hostname);
  var fromUrl = new URLSearchParams(location.search).get('api');
  var saved = null;
  try {
    if (fromUrl !== null) {
      if (/^https:\/\/[\w.-]+(:\d+)?\/?$/.test(fromUrl)) localStorage.setItem('siwan_api', fromUrl.replace(/\/$/, ''));
      else if (fromUrl === '') localStorage.removeItem('siwan_api');
    }
    saved = localStorage.getItem('siwan_api');
  } catch (e) { /* 無法使用 localStorage 時改用預設值 */ }
  window.SIWAN_API_BASE = onPages ? (saved || DEFAULT_API) : '';
})();
