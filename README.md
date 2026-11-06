# SIWAN TABLE 西灣食記

資料庫系統 專案一（第 8 組）：中山大學周邊（鹽埕區、鼓山區）餐廳評價、搜尋與線上預約系統。

## 系統架構

```
瀏覽器（docs/ 前端：HTML + CSS + JavaScript）
        │  fetch() 呼叫 REST API（JSON，登入後帶 JWT）
        ▼
Flask 後端（server/，Python 3.10+）
        │  psycopg2
        ▼
PostgreSQL（課程資料庫 140.117.68.35，資料庫 project_8）
```

| 層級 | 工具 |
|---|---|
| 前端 | HTML、CSS、原生 JavaScript（ES Modules），可放 GitHub Pages |
| 後端 | Python、Flask、psycopg2、PyJWT、flask-cors |
| 資料庫 | PostgreSQL（課程提供） |
| 密碼 | 新註冊會員以 werkzeug 雜湊（scrypt）儲存 |

本機執行時，Flask 同時提供前端頁面與 API，打開一個網址就能用。

## 資料夾

```
siwan-table/
├── docs/                    前端（GitHub Pages 會發布這個資料夾）
│   ├── index.html           首頁／搜尋
│   ├── restaurant.html      餐廳詳細頁（招牌菜、預約、評論）
│   ├── login.html           登入／註冊
│   ├── member.html          會員中心（個人資料、我的評論）
│   ├── reservations.html    我的預約
│   ├── favorites.html       我的收藏
│   ├── admin.html           管理後台
│   └── assets/              CSS、JS、圖片；js/config.js 設定後端網址
└── server/                  後端
    ├── app.py               主程式
    ├── db.py                資料庫連線
    ├── auth.py              登入驗證（JWT）
    ├── api/                 各功能的 API
    ├── db/schema.sql        資料表結構（與課程資料庫相同）
    ├── db/init_local_db.py  建立「本機」測試資料庫（不會碰課程資料庫）
    ├── requirements.txt
    └── .env.example         連線設定範本
```

## 在自己電腦執行（Mac）

```bash
cd siwan-table/server
conda activate db-2026            # 或任何 Python 3.10 以上的環境
pip install -r requirements.txt
cp .env.example .env              # 打開 .env，在 DB_PASSWORD= 後面填入助教給的密碼
python app.py
```

打開 http://127.0.0.1:5050 。（Mac 的 AirPlay 常佔用 5000，所以預設用 5050。）

課程資料庫要在校內網路（或可連到 140.117.68.35 的網路）才連得到。

## 功能與資料表

| 功能 | 新增 | 查詢 | 修改 | 刪除 | 資料表 |
|---|---|---|---|---|---|
| 會員 | 註冊 | 會員中心 | 修改資料、管理者改身分 | 管理者刪除 | Member |
| 餐廳 | 管理者新增 | 關鍵字、區域、價位、標籤、可預約篩選與排序 | 管理者編輯 | 管理者刪除 | Restaurant、HasTag、Tag |
| 招牌菜 | 管理者新增 | 餐廳頁 | 管理者編輯 | 管理者刪除 | TopMenu |
| 評論 | 會員發表 | 餐廳頁、我的評論 | 會員修改 | 會員或管理者刪除 | Review |
| 預約 | 會員預約（檢查座位） | 我的預約、後台 | 會員改時間人數、管理者確認／拒絕／完成 | 取消（改狀態，不刪資料） | Reserve |
| 收藏 | 建立清單、加入餐廳 | 我的收藏 | 編輯清單 | 刪除清單、移出餐廳 | Favlist、Contains |
| 標籤 | 管理者新增 | 首頁標籤 | 管理者改名 | 管理者刪除 | Tag |
| 統計 | — | 後台：各價位／區域餐廳數、熱門標籤、預約狀態、預約最多與評分最高的餐廳 | — | — | 多表 GROUP BY |

### 預約的座位檢查

同一家餐廳，與新預約時間相差不到 2 小時的「待確認」與「已確認」預約，人數加總後再加上本次人數，不可超過 `capacity`。檢查與新增在同一個交易內完成，並以 `SELECT … FOR UPDATE` 鎖住該餐廳，避免兩人同時搶最後的座位。取消或拒絕的預約不佔座位。

### 編號

沿用組上資料庫的格式：會員 M00001、預約 S00001、評論 V00001、收藏清單 F00001、標籤 t00001，餐廳為 6 碼十六進位。新增資料時由後端產生下一個編號。

## 放上網路

### 前端：GitHub Pages

1. 把整個 `siwan-table` 推到 GitHub（`.env` 已被 `.gitignore` 排除，密碼不會上傳）。
2. GitHub 專案 → Settings → Pages → Branch 選 `main`、資料夾選 `/docs` → Save。
3. 幾分鐘後網址會是 `https://你的帳號.github.io/siwan-table/`。

### 後端：需要一台能連到課程資料庫的主機

GitHub Pages 只放靜態檔案，不能執行 Python，也不能直接連 PostgreSQL，所以後端要另外執行，再把它的網址填進 `docs/assets/js/config.js` 的 `SIWAN_API_BASE`。

- **做法 A：Render（免費，網址固定，建議）**：專案根目錄已有 `render.yaml`。在 Render 選 New → Blueprint → 選這個 repo，只要填入 `DB_PASSWORD` 就會自動建立後端。完成後把 `https://…onrender.com` 填進 `docs/assets/js/config.js` 的 `DEFAULT_API`。免費方案閒置 15 分鐘會休眠，第一次開啟要等約 30 秒。前提是課程資料庫允許校外主機連線。
- **做法 B：自己的電腦＋Cloudflare Tunnel（臨時展示，目前使用）**：在 `server` 資料夾執行 `./start_public.sh`，它會啟動後端並開一條 Cloudflare 通道，畫面上會印出可以直接分享的網址。電腦和終端機要一直開著；每次重新啟動網址都會變。

前端網址設定：打開 `https://elsonyeh.github.io/restaurant-reservation-web/?api=後端網址`，瀏覽器會記住後端網址；固定網址也可以直接填在 `docs/assets/js/config.js` 的 `DEFAULT_API`。

## 目前的網址

- 網站（GitHub Pages）：https://elsonyeh.github.io/restaurant-reservation-web/
- 後端 API（Render）：https://restaurant-reservation-api-5i11.onrender.com （免費方案閒置會休眠，第一次開啟約需 50 秒）

## 測試帳號

- 課程資料庫：沿用組員建立的測試帳號（例如 `test01@example.com` 為管理者）。這些帳號的密碼是明碼，系統相容；新註冊的帳號則以雜湊儲存。
- 本機測試資料庫（`python db/init_local_db.py` 建立）：`admin@siwan.test / admin1234`（管理者）、`yijun@siwan.test / user1234`（會員）。

## 資料來源

餐廳資料整理自公開資訊與 Google 評分，照片為示意圖，僅供課程展示。
