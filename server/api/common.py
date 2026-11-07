"""各 API 共用的工具。"""
import re
import secrets

from flask import request

ID_RE = re.compile(r"^[0-9A-Za-z]{1,6}$")


# 各資料表的編號格式，沿用組上資料庫現有的寫法：
#   會員 M00001、預約 S00001、評論 V00001、收藏清單 F00001、標籤 t00001；餐廳為 6 碼十六進位（例如 32d2db）
ID_PREFIX = {"member": "M", "reserve": "S", "review": "V", "favlist": "F", "tag": "t"}


def new_id(cur, table, column):
    """產生下一個編號，並確認沒有重複。"""
    prefix = ID_PREFIX.get(table.lower())
    if prefix:
        # 先鎖住資料表，避免兩個請求同時拿到同一個編號
        cur.execute(f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE")
        cur.execute(
            f"""SELECT COALESCE(MAX(SUBSTRING({column} FROM 2)::int), 0) + 1 AS n
                  FROM {table} WHERE {column} ~ %s""",
            (f"^{prefix}[0-9]{{5}}$",),
        )
        n = cur.fetchone()["n"]
        if n > 99999:
            raise ApiError(500, "系統忙碌中，請稍後再試")
        return f"{prefix}{n:05d}"
    for _ in range(20):
        candidate = secrets.token_hex(3)
        cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", (candidate,))
        if not cur.fetchone():
            return candidate
    raise ApiError(500, "系統忙碌中，請稍後再試")


def clean_id(value, label="編號"):
    """檢查從網址或表單傳來的編號格式。"""
    value = (str(value).strip() if value is not None else "")
    if not ID_RE.match(value):
        raise ApiError(404, "找不到這筆資料")
    return value


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def body():
    """取得 JSON 請求內容（沒有就回傳空 dict）。"""
    return request.get_json(silent=True) or {}


def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_datetime(value):
    """接受 'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DDTHH:MM'，回傳 'YYYY-MM-DD HH:MM'。"""
    if not isinstance(value, str):
        return None
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})", value.strip())
    return f"{m.group(1)} {m.group(2)}:{m.group(3)}" if m else None


def parse_date(value):
    if not value:
        return None
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value.strip()):
        return value.strip()
    raise ApiError(400, "日期格式不正確")


# 資料表沒有區域欄位，由地址判斷行政區
DISTRICT_SQL = """CASE WHEN r.address LIKE '%%鹽埕區%%' THEN '鹽埕區'
                       WHEN r.address LIKE '%%鼓山區%%' THEN '鼓山區'
                       ELSE '其他' END"""

# 預約用：每組客人假設用餐 2 小時，前後 2 小時內的預約視為同一時段
DINING_INTERVAL = "2 hours"

# 預約時段（用餐開始時間）
TIME_SLOTS = ["11:30", "12:00", "12:30", "13:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00"]

STATUS_LABEL = {"pending": "待確認", "confirmed": "已確認", "rejected": "已拒絕", "cancelled": "已取消", "completed": "已完成"}
STATUSES = tuple(STATUS_LABEL)


# 餐廳照片：資料庫的 picture 欄位存「圖片網址」或「data:image/...;base64,...」（直接存進資料庫的圖片）。
# 回傳給前端時，存在資料庫裡的圖片改成 /api/restaurants/<rid>/picture，避免列表一次傳一大串資料。
PICTURE_SQL = """CASE WHEN r.picture LIKE 'data:%%' THEN '/api/restaurants/' || TRIM(r.rId) || '/picture?v=' || LEFT(MD5(r.picture), 8)
                      ELSE NULLIF(TRIM(r.picture), '') END"""
MAX_PICTURE_LEN = 2_000_000  # 約 1.5 MB 的圖片


def clean_picture(value):
    """檢查前端送來的圖片：空白＝沒有圖片；/api/... ＝沿用原本的圖片（回傳 KEEP）。"""
    value = (value or "").strip()
    if not value:
        return None
    if value.startswith("/api/"):
        return KEEP
    if value.startswith("data:image/"):
        if len(value) > MAX_PICTURE_LEN:
            raise ApiError(400, "圖片太大，請換一張較小的圖片")
        return value
    if re.match(r"^https?://", value):
        return value
    raise ApiError(400, "圖片格式不正確")


KEEP = object()
