"""管理後台：統計報表，以及餐廳、招牌菜、標籤、預約、評論、會員的管理。所有路由都需要管理者權限。"""
from flask import Blueprint, g, request

import db
from auth import admin_required
from api.common import DISTRICT_SQL, STATUSES, ApiError, body, clean_id, new_id, to_int
from api.common import KEEP, PICTURE_SQL, clean_picture

bp = Blueprint("admin", __name__)


@bp.before_request
@admin_required
def _guard():
    return None


# ---------------- 統計 ----------------
@bp.get("/stats")
def stats():
    totals = db.fetch_one(
        """SELECT (SELECT COUNT(*) FROM Restaurant) AS restaurants,
                  (SELECT COUNT(*) FROM Restaurant WHERE acceptRes) AS accept_res,
                  (SELECT COUNT(*) FROM Member WHERE role IS DISTINCT FROM 'admin') AS members,
                  (SELECT COUNT(*) FROM Review) AS reviews,
                  (SELECT COUNT(*) FROM Reserve WHERE status = 'pending') AS pending,
                  (SELECT COUNT(*) FROM Tag) AS tags,
                  (SELECT ROUND(AVG(google_rate), 2) FROM Restaurant WHERE google_rate > 0) AS avg_google,
                  (SELECT ROUND(AVG(rating), 2) FROM Review) AS avg_member""")
    by_price = db.fetch_all(
        """SELECT TRIM(priceRange) AS key, COUNT(*) AS n FROM Restaurant GROUP BY 1 ORDER BY 1""")
    by_district = db.fetch_all(
        f"""SELECT {DISTRICT_SQL} AS key, COUNT(*) AS n, ROUND(AVG(r.google_rate), 2) AS avg_google
              FROM Restaurant r GROUP BY 1 ORDER BY n DESC""")
    top_tags = db.fetch_all(
        """SELECT t.tName AS key, COUNT(*) AS n FROM HasTag ht JOIN Tag t ON t.tId = ht.tId
            GROUP BY t.tName ORDER BY n DESC, t.tName LIMIT 8""")
    by_status = db.fetch_all(
        """SELECT status AS key, COUNT(*) AS n, COALESCE(SUM(partySize), 0) AS people
             FROM Reserve GROUP BY status""")
    top_reserved = db.fetch_all(
        """SELECT r.rName AS key, COUNT(*) AS n, ROUND(AVG(s.partySize), 1) AS avg_size
             FROM Reserve s JOIN Restaurant r ON r.rId = s.rId
            WHERE s.status NOT IN ('cancelled', 'rejected')
            GROUP BY r.rName ORDER BY n DESC, r.rName LIMIT 5""")
    top_rated = db.fetch_all(
        """SELECT r.rName AS key, ROUND(AVG(v.rating), 1) AS avg, COUNT(*) AS n
             FROM Review v JOIN Restaurant r ON r.rId = v.rId
            GROUP BY r.rName HAVING COUNT(*) >= 1
            ORDER BY avg DESC, n DESC LIMIT 5""")
    return {"totals": totals, "byPrice": by_price, "byDistrict": by_district, "topTags": top_tags,
            "byStatus": by_status, "topReserved": top_reserved, "topRated": top_rated}


# ---------------- 餐廳 ----------------
def _restaurant_fields(data):
    name = (data.get("rName") or "").strip()
    if not name:
        raise ApiError(400, "請輸入餐廳名稱")
    price = str(data.get("priceRange") or "").strip()
    if price not in ("1", "2", "3"):
        raise ApiError(400, "價位需為 1、2、3")
    accept = bool(data.get("acceptRes"))
    capacity = to_int(data.get("capacity"))
    if accept and not capacity:
        raise ApiError(400, "接受預約的餐廳必須設定座位數")
    rate = data.get("google_rate")
    rate = float(rate) if rate not in (None, "") else None
    return (name, (data.get("address") or "").strip() or None, price,
            to_int(data.get("maxPartySize"), 4), capacity, accept, rate,
            to_int(data.get("google_num")), clean_picture(data.get("picture")))


def _set_tags(cur, rid, tag_ids):
    cur.execute("DELETE FROM HasTag WHERE rId = %s", (rid,))
    for tid in {clean_id(t) for t in tag_ids or []}:
        cur.execute("INSERT INTO HasTag (tId, rId) VALUES (%s, %s)", (tid, rid))


@bp.get("/restaurants")
def list_restaurants():
    q = f"%{(request.args.get('q') or '').strip()}%"
    page = max(to_int(request.args.get("page"), 1), 1)
    rows = db.fetch_all(
        f"""SELECT r.rId, r.rName, r.address, r.priceRange, r.maxPartySize, r.capacity, r.acceptRes,
                   r.google_rate, r.google_num, {PICTURE_SQL} AS picture, {DISTRICT_SQL} AS district,
                   (SELECT COALESCE(array_agg(ht.tId), '{{}}') FROM HasTag ht WHERE ht.rId = r.rId) AS tag_ids,
                   COUNT(*) OVER () AS total
              FROM Restaurant r
             WHERE r.rName ILIKE %s OR r.address ILIKE %s
             ORDER BY r.rId LIMIT 15 OFFSET %s""",
        (q, q, (page - 1) * 15))
    total = rows[0]["total"] if rows else 0
    return {"items": rows, "total": total, "page": page, "pageSize": 15}


@bp.post("/restaurants")
def create_restaurant():
    data = body()
    with db.transaction() as cur:
        rid = new_id(cur, "Restaurant", "rId")
        fields = _restaurant_fields(data)
        if fields[-1] is KEEP:
            fields = fields[:-1] + (None,)
        cur.execute(
            """INSERT INTO Restaurant (rId, rName, address, priceRange, maxPartySize, capacity, acceptRes,
                                       google_rate, google_num, picture)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (rid,) + fields)
        _set_tags(cur, rid, data.get("tagIds"))
    return {"rid": rid}, 201


@bp.put("/restaurants/<rid>")
def update_restaurant(rid):
    rid = clean_id(rid)
    data = body()
    with db.transaction() as cur:
        fields = _restaurant_fields(data)
        keep = fields[-1] is KEEP  # 圖片沒有更換就沿用資料庫裡原本的
        cur.execute(
            """UPDATE Restaurant SET rName = %s, address = %s, priceRange = %s, maxPartySize = %s,
                      capacity = %s, acceptRes = %s, google_rate = %s, google_num = %s,
                      picture = CASE WHEN %s THEN picture ELSE %s END
                WHERE rId = %s""",
            fields[:-1] + (keep, None if keep else fields[-1], rid))
        if not cur.rowcount:
            raise ApiError(404, "找不到這家餐廳")
        if "tagIds" in data:
            _set_tags(cur, rid, data.get("tagIds"))
    return {"ok": True}


@bp.delete("/restaurants/<rid>")
def delete_restaurant(rid):
    rid = clean_id(rid)
    if not db.execute("DELETE FROM Restaurant WHERE rId = %s", (rid,)):
        raise ApiError(404, "找不到這家餐廳")
    return {"ok": True}


# ---------------- 招牌菜（弱實體 TopMenu）----------------
@bp.get("/restaurants/<rid>/menu")
def list_menu(rid):
    rid = clean_id(rid)
    return {"items": db.fetch_all(
        "SELECT menuName, price, description FROM TopMenu WHERE rId = %s ORDER BY menuName", (rid,))}


@bp.post("/restaurants/<rid>/menu")
def add_menu(rid):
    rid = clean_id(rid)
    data = body()
    name = (data.get("menuName") or "").strip()
    if not name:
        raise ApiError(400, "請輸入菜名")
    db.execute("INSERT INTO TopMenu (rId, menuName, price, description) VALUES (%s, %s, %s, %s)",
               (rid, name[:255], to_int(data.get("price")), (data.get("description") or "").strip() or None))
    return {"ok": True}, 201


@bp.put("/restaurants/<rid>/menu/<path:name>")
def update_menu(rid, name):
    rid = clean_id(rid)
    data = body()
    new_name = (data.get("menuName") or name).strip()
    n = db.execute(
        "UPDATE TopMenu SET menuName = %s, price = %s, description = %s WHERE rId = %s AND menuName = %s",
        (new_name[:255], to_int(data.get("price")), (data.get("description") or "").strip() or None, rid, name))
    if not n:
        raise ApiError(404, "找不到這道招牌菜")
    return {"ok": True}


@bp.delete("/restaurants/<rid>/menu/<path:name>")
def delete_menu(rid, name):
    rid = clean_id(rid)
    if not db.execute("DELETE FROM TopMenu WHERE rId = %s AND menuName = %s", (rid, name)):
        raise ApiError(404, "找不到這道招牌菜")
    return {"ok": True}


# ---------------- 標籤 ----------------
@bp.post("/tags")
def create_tag():
    name = (body().get("tName") or "").strip()
    if not name:
        raise ApiError(400, "請輸入標籤名稱")
    with db.transaction() as cur:
        tid = new_id(cur, "Tag", "tId")
        cur.execute("INSERT INTO Tag (tId, tName) VALUES (%s, %s)", (tid, name[:100]))
    return {"tid": tid}, 201


@bp.put("/tags/<tid>")
def update_tag(tid):
    tid = clean_id(tid)
    name = (body().get("tName") or "").strip()
    if not name:
        raise ApiError(400, "請輸入標籤名稱")
    if not db.execute("UPDATE Tag SET tName = %s WHERE tId = %s", (name[:100], tid)):
        raise ApiError(404, "找不到這個標籤")
    return {"ok": True}


@bp.delete("/tags/<tid>")
def delete_tag(tid):
    tid = clean_id(tid)
    if not db.execute("DELETE FROM Tag WHERE tId = %s", (tid,)):
        raise ApiError(404, "找不到這個標籤")
    return {"ok": True}


# ---------------- 預約 ----------------
@bp.get("/reservations")
def list_reservations():
    status = request.args.get("status")
    params = []
    cond = "TRUE"
    if status in STATUSES:
        cond = "s.status = %s"
        params.append(status)
    rows = db.fetch_all(
        f"""SELECT s.resId, s.status, s.note, s.dateTime, s.partySize, s.rId, r.rName, m.mName, m.email,
                   r.capacity - (SELECT COALESCE(SUM(x.partySize), 0) FROM Reserve x
                                  WHERE x.rId = s.rId AND x.status IN ('pending','confirmed')
                                    AND x.dateTime > s.dateTime - INTERVAL '2 hours'
                                    AND x.dateTime < s.dateTime + INTERVAL '2 hours') AS seats_left
              FROM Reserve s
              JOIN Restaurant r ON r.rId = s.rId
              LEFT JOIN Member m ON m.mId = s.mId
             WHERE {cond}
             ORDER BY s.dateTime DESC LIMIT 100""", params)
    return {"items": rows}


@bp.patch("/reservations/<res_id>")
def set_reservation_status(res_id):
    res_id = clean_id(res_id)
    status = body().get("status")
    if status not in STATUSES:
        raise ApiError(400, "狀態不正確")
    if not db.execute("UPDATE Reserve SET status = %s WHERE resId = %s", (status, res_id)):
        raise ApiError(404, "找不到這筆預約")
    return {"ok": True}


# ---------------- 評論 ----------------
@bp.get("/reviews")
def list_reviews():
    return {"items": db.fetch_all(
        """SELECT v.revId, v.rating, v.comment, v.visitDate, v.reviewTime, r.rName, m.mName
             FROM Review v JOIN Restaurant r ON r.rId = v.rId LEFT JOIN Member m ON m.mId = v.mId
            ORDER BY v.reviewTime DESC LIMIT 100""")}


@bp.delete("/reviews/<rev_id>")
def delete_review(rev_id):
    rev_id = clean_id(rev_id)
    if not db.execute("DELETE FROM Review WHERE revId = %s", (rev_id,)):
        raise ApiError(404, "找不到這則評論")
    return {"ok": True}


# ---------------- 會員 ----------------
@bp.get("/members")
def list_members():
    return {"items": db.fetch_all(
        """SELECT m.mId, m.email, m.mName, m.phone, m.birthday, m.role,
                  (SELECT COUNT(*) FROM Review v WHERE v.mId = m.mId) AS reviews,
                  (SELECT COUNT(*) FROM Reserve s WHERE s.mId = m.mId) AS reservations
             FROM Member m ORDER BY m.mId""")}


@bp.patch("/members/<mid>")
def set_member_role(mid):
    mid = clean_id(mid)
    role = body().get("role")
    if role not in ("user", "admin"):
        raise ApiError(400, "身分不正確")
    if mid == g.user["mid"] and role != "admin":
        raise ApiError(400, "不能取消自己的管理者身分")
    if not db.execute("UPDATE Member SET role = %s WHERE mId = %s", (role, mid)):
        raise ApiError(404, "找不到這位會員")
    return {"ok": True}


@bp.delete("/members/<mid>")
def delete_member(mid):
    mid = clean_id(mid)
    if mid == g.user["mid"]:
        raise ApiError(400, "不能刪除自己的帳號")
    if not db.execute("DELETE FROM Member WHERE mId = %s", (mid,)):
        raise ApiError(404, "找不到這位會員")
    return {"ok": True}
