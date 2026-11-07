"""餐廳：搜尋、篩選、詳細資料、標籤、預約時段的剩餘座位。"""
import base64
import binascii

from flask import Blueprint, Response, g, request

import db
from api.common import DINING_INTERVAL, DISTRICT_SQL, PICTURE_SQL, TIME_SLOTS, ApiError, clean_id, parse_date, to_int

bp = Blueprint("restaurants", __name__)

PAGE_SIZE = 10

SORTS = {
    "google": "r.google_rate DESC NULLS LAST, r.google_num DESC NULLS LAST",
    "member": "member_rate DESC NULLS LAST, member_num DESC",
    "reviews": "member_num DESC, r.google_num DESC NULLS LAST",
    "price": "TRIM(r.priceRange) ASC, r.google_rate DESC NULLS LAST",
}


@bp.get("/restaurants")
def list_restaurants():
    """查詢：關鍵字、區域、價位、標籤（全部符合）、只看可預約、排序、分頁。"""
    where, params = [], []

    q = (request.args.get("q") or "").strip()
    if q:
        where.append("""(r.rName ILIKE %s OR r.address ILIKE %s
                         OR EXISTS (SELECT 1 FROM HasTag ht JOIN Tag t ON t.tId = ht.tId
                                     WHERE ht.rId = r.rId AND t.tName ILIKE %s)
                         OR EXISTS (SELECT 1 FROM TopMenu tm WHERE tm.rId = r.rId AND tm.menuName ILIKE %s))""")
        like = f"%{q}%"
        params += [like, like, like, like]

    district = request.args.get("district")
    if district in ("鹽埕區", "鼓山區"):
        where.append("r.address LIKE %s")
        params.append(f"%{district}%")

    price = request.args.get("price")
    if price in ("1", "2", "3"):
        where.append("TRIM(r.priceRange) = %s")
        params.append(price)

    tags = [t for t in (request.args.get("tags") or "").split(",") if t.strip()]
    if tags:
        # 必須同時擁有所有選取的標籤
        where.append("""r.rId IN (SELECT ht.rId FROM HasTag ht JOIN Tag t ON t.tId = ht.tId
                                   WHERE t.tName = ANY(%s)
                                   GROUP BY ht.rId HAVING COUNT(DISTINCT t.tName) = %s)""")
        params += [tags, len(tags)]

    if request.args.get("acceptRes") in ("1", "true"):
        where.append("r.acceptRes = TRUE")

    order = SORTS.get(request.args.get("sort"), SORTS["google"])
    page = max(to_int(request.args.get("page"), 1), 1)

    sql = f"""
        SELECT r.rId, r.rName, r.address, r.priceRange, r.acceptRes,
               r.google_rate, r.google_num, {PICTURE_SQL} AS picture,
               {DISTRICT_SQL} AS district,
               ROUND(AVG(v.rating), 1) AS member_rate,
               COUNT(v.revId) AS member_num,
               (SELECT COALESCE(array_agg(t.tName ORDER BY t.tName), '{{}}')
                  FROM HasTag ht JOIN Tag t ON t.tId = ht.tId WHERE ht.rId = r.rId) AS tags,
               COUNT(*) OVER () AS total
          FROM Restaurant r
          LEFT JOIN Review v ON v.rId = r.rId
         {"WHERE " + " AND ".join(where) if where else ""}
         GROUP BY r.rId
         ORDER BY {order}, r.rId
         LIMIT {PAGE_SIZE} OFFSET %s"""
    rows = db.fetch_all(sql, params + [(page - 1) * PAGE_SIZE])
    total = rows[0]["total"] if rows else 0
    for r in rows:
        r.pop("total", None)
    return {"items": rows, "total": total, "page": page, "pageSize": PAGE_SIZE}


@bp.get("/restaurants/<rid>")
def restaurant_detail(rid):
    rid = clean_id(rid, "餐廳編號")
    # 一次查詢取回餐廳、標籤、招牌菜、評論與評分統計（減少和資料庫往返的次數）
    rest = db.fetch_one(
        f"""SELECT r.rId, r.rName, r.address, r.priceRange, r.maxPartySize, r.capacity, r.acceptRes,
                   r.google_rate, r.google_num, {PICTURE_SQL} AS picture, {DISTRICT_SQL} AS district,
                   (SELECT COALESCE(json_agg(t.tName ORDER BY t.tName), '[]')
                      FROM HasTag ht JOIN Tag t ON t.tId = ht.tId WHERE ht.rId = r.rId) AS tags,
                   (SELECT COALESCE(json_agg(json_build_object('menuname', m.menuName, 'price', m.price,
                                                               'description', m.description) ORDER BY m.menuName), '[]')
                      FROM TopMenu m WHERE m.rId = r.rId) AS menu,
                   (SELECT COALESCE(json_agg(json_build_object(
                              'revid', v.revId, 'rating', v.rating, 'comment', v.comment,
                              'visitdate', to_char(v.visitDate, 'YYYY-MM-DD'),
                              'reviewtime', to_char(v.reviewTime, 'YYYY-MM-DD HH24:MI'),
                              'mid', v.mId, 'mname', COALESCE(mb.mName, '已刪除的會員'))
                            ORDER BY v.reviewTime DESC NULLS LAST), '[]')
                      FROM Review v LEFT JOIN Member mb ON mb.mId = v.mId WHERE v.rId = r.rId) AS reviews,
                   (SELECT json_build_object('avg', ROUND(AVG(rating), 1), 'n', COUNT(*),
                              's5', COUNT(*) FILTER (WHERE rating = 5), 's4', COUNT(*) FILTER (WHERE rating = 4),
                              's3', COUNT(*) FILTER (WHERE rating = 3), 's2', COUNT(*) FILTER (WHERE rating = 2),
                              's1', COUNT(*) FILTER (WHERE rating = 1))
                      FROM Review WHERE rId = r.rId) AS review_summary
              FROM Restaurant r WHERE r.rId = %s""", (rid,)
    )
    if not rest:
        raise ApiError(404, "找不到這家餐廳")

    # 登入時：附上這位會員的收藏清單（標示哪些已包含此餐廳）
    if g.user:
        rest["my_lists"] = db.fetch_all(
            """SELECT f.fId, f.fName,
                      EXISTS (SELECT 1 FROM Contains c WHERE c.fId = f.fId AND c.rId = %s) AS contains
                 FROM Favlist f WHERE f.mId = %s ORDER BY f.fId""", (rid, g.user["mid"]))
    return rest


@bp.get("/restaurants/<rid>/picture")
def picture(rid):
    """輸出存在資料庫裡的餐廳照片。"""
    rid = clean_id(rid, "餐廳編號")
    row = db.fetch_one("SELECT picture FROM Restaurant WHERE rId = %s", (rid,))
    pic = (row or {}).get("picture") or ""
    if not pic.startswith("data:image/") or ";base64," not in pic:
        raise ApiError(404, "找不到這張圖片")
    head, data = pic.split(",", 1)
    try:
        raw = base64.b64decode(data)
    except (binascii.Error, ValueError):
        raise ApiError(404, "找不到這張圖片")
    resp = Response(raw, mimetype=head[5:].split(";")[0])
    resp.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return resp


@bp.get("/restaurants/<rid>/availability")
def availability(rid):
    rid = clean_id(rid, "餐廳編號")
    """某一天各時段的剩餘座位 = 座位數 − 前後 2 小時內有效預約（待確認、已確認）的人數總和。"""
    day = parse_date(request.args.get("date"))
    if not day:
        raise ApiError(400, "請選擇日期")
    rest = db.fetch_one("SELECT acceptRes, capacity, maxPartySize FROM Restaurant WHERE rId = %s", (rid,))
    if not rest:
        raise ApiError(404, "找不到這家餐廳")
    if not rest["acceptres"]:
        return {"acceptRes": False, "slots": []}

    slots = [f"{day} {t}" for t in TIME_SLOTS]
    rows = db.fetch_all(
        f"""SELECT to_char(s.t, 'HH24:MI') AS time,
                   r.capacity - COALESCE(SUM(v.partySize), 0) AS seats_left,
                   s.t <= LOCALTIMESTAMP AS past
              FROM unnest(%s::timestamp[]) AS s(t)
              CROSS JOIN Restaurant r
              LEFT JOIN Reserve v
                     ON v.rId = r.rId
                    AND v.status IN ('pending', 'confirmed')
                    AND v.dateTime > s.t - INTERVAL '{DINING_INTERVAL}'
                    AND v.dateTime < s.t + INTERVAL '{DINING_INTERVAL}'
             WHERE r.rId = %s
             GROUP BY s.t, r.capacity
             ORDER BY s.t""",
        (slots, rid),
    )
    return {"acceptRes": True, "capacity": rest["capacity"], "maxPartySize": rest["maxpartysize"], "slots": rows}


@bp.get("/tags")
def tags():
    return {"items": db.fetch_all(
        """SELECT t.tId, t.tName, COUNT(ht.rId) AS n
             FROM Tag t LEFT JOIN HasTag ht ON ht.tId = t.tId
            GROUP BY t.tId ORDER BY n DESC, t.tName""")}


@bp.get("/summary")
def summary():
    """首頁 INFORMATION 區塊的統計數字。"""
    return db.fetch_one(
        """SELECT COUNT(*) AS restaurants,
                  COUNT(*) FILTER (WHERE address LIKE '%%鹽埕區%%') AS yancheng,
                  COUNT(*) FILTER (WHERE address LIKE '%%鼓山區%%') AS gushan,
                  ROUND(AVG(google_rate) FILTER (WHERE google_rate > 0), 2) AS avg_google,
                  COUNT(*) FILTER (WHERE TRIM(priceRange) = '1') AS cheap,
                  COUNT(*) FILTER (WHERE acceptRes) AS accept_res
             FROM Restaurant""")
