"""預約：新增（含座位檢查）、查看、修改、取消。"""
from flask import Blueprint, g, request

import db
from auth import login_required
from api.common import DINING_INTERVAL, ApiError, body, clean_id, new_id, parse_datetime, to_int

bp = Blueprint("reservations", __name__)

ACTIVE = ("pending", "confirmed")


def check_and_lock(cur, rid, dt, size, exclude_res_id=None):
    """在交易中檢查是否可以預約；鎖住該餐廳那一列，避免兩人同時搶最後的座位。"""
    cur.execute("SELECT rName, acceptRes, capacity, maxPartySize FROM Restaurant WHERE rId = %s FOR UPDATE", (rid,))
    rest = cur.fetchone()
    if not rest:
        raise ApiError(404, "找不到這家餐廳")
    if not rest["acceptres"]:
        raise ApiError(400, "這家餐廳不接受線上預約")
    if size < 1 or size > rest["maxpartysize"]:
        raise ApiError(400, f"人數需介於 1 到 {rest['maxpartysize']} 人")

    cur.execute("SELECT %s::timestamp > LOCALTIMESTAMP AS future", (dt,))
    if not cur.fetchone()["future"]:
        raise ApiError(400, "只能預約未來的時間")

    cur.execute(
        f"""SELECT COALESCE(SUM(partySize), 0) AS booked
              FROM Reserve
             WHERE rId = %s AND status IN ('pending', 'confirmed')
               AND dateTime > %s::timestamp - INTERVAL '{DINING_INTERVAL}'
               AND dateTime < %s::timestamp + INTERVAL '{DINING_INTERVAL}'
               AND resId <> COALESCE(%s, '')""",
        (rid, dt, dt, exclude_res_id),
    )
    left = rest["capacity"] - cur.fetchone()["booked"]
    if size > left:
        raise ApiError(409, f"這個時段只剩 {max(left, 0)} 個座位" if left > 0 else "這個時段已經客滿")
    return rest


@bp.post("/reservations")
@login_required
def create_reservation():
    data = body()
    rid = clean_id(data.get("rId"), "餐廳編號")
    size = to_int(data.get("partySize"), 0)
    dt = parse_datetime(data.get("dateTime"))
    if not dt:
        raise ApiError(400, "請選擇日期與時段")
    note = (data.get("note") or "").strip()[:200] or None

    with db.transaction() as cur:
        check_and_lock(cur, rid, dt, size)
        res_id = new_id(cur, "Reserve", "resId")
        cur.execute(
            """INSERT INTO Reserve (resId, status, note, dateTime, partySize, mId, rId)
               VALUES (%s, 'pending', %s, %s, %s, %s, %s)""",
            (res_id, note, dt, size, g.user["mid"], rid),
        )
    return {"resid": res_id}, 201


@bp.get("/me/reservations")
@login_required
def my_reservations():
    """tab = upcoming（即將到來）/ done（已完成）/ cancelled / all"""
    tab = request.args.get("tab", "upcoming")
    cond = {
        "upcoming": "s.status IN ('pending', 'confirmed') AND s.dateTime >= LOCALTIMESTAMP",
        "done": "(s.status = 'completed' OR (s.status = 'confirmed' AND s.dateTime < LOCALTIMESTAMP))",
        "cancelled": "s.status IN ('cancelled', 'rejected')",
    }.get(tab, "TRUE")
    rows = db.fetch_all(
        f"""SELECT s.resId, s.status, s.note, s.dateTime, s.partySize, s.rId, r.rName,
                   (s.dateTime >= LOCALTIMESTAMP) AS upcoming,
                   EXISTS (SELECT 1 FROM Review v WHERE v.mId = s.mId AND v.rId = s.rId) AS reviewed
              FROM Reserve s JOIN Restaurant r ON r.rId = s.rId
             WHERE s.mId = %s AND {cond}
             ORDER BY s.dateTime {"ASC" if tab == "upcoming" else "DESC"}""",
        (g.user["mid"],),
    )
    counts = db.fetch_one(
        """SELECT COUNT(*) FILTER (WHERE status IN ('pending','confirmed') AND dateTime >= LOCALTIMESTAMP) AS upcoming,
                  COUNT(*) FILTER (WHERE status = 'completed' OR (status = 'confirmed' AND dateTime < LOCALTIMESTAMP)) AS done,
                  COUNT(*) FILTER (WHERE status IN ('cancelled', 'rejected')) AS cancelled,
                  COUNT(*) AS "all"
             FROM Reserve WHERE mId = %s""",
        (g.user["mid"],),
    )
    return {"items": rows, "counts": counts}


@bp.put("/reservations/<res_id>")
@login_required
def update_reservation(res_id):
    """會員修改尚未確認的預約（時間、人數、備註），會重新檢查座位。"""
    res_id = clean_id(res_id)
    data = body()
    with db.transaction() as cur:
        cur.execute("SELECT * FROM Reserve WHERE resId = %s AND mId = %s", (res_id, g.user["mid"]))
        res = cur.fetchone()
        if not res:
            raise ApiError(404, "找不到這筆預約")
        if res["status"] != "pending":
            raise ApiError(400, "只有「待確認」的預約可以修改")
        dt = parse_datetime(data.get("dateTime")) or res["datetime"].strftime("%Y-%m-%d %H:%M")
        size = to_int(data.get("partySize"), res["partysize"])
        note = (data.get("note") or "").strip()[:200] or None
        check_and_lock(cur, res["rid"], dt, size, exclude_res_id=res_id)
        cur.execute("UPDATE Reserve SET dateTime = %s, partySize = %s, note = %s WHERE resId = %s",
                    (dt, size, note, res_id))
    return {"ok": True}


@bp.post("/reservations/<res_id>/cancel")
@login_required
def cancel_reservation(res_id):
    """取消不刪除資料，只把狀態改成 cancelled，座位會自動釋出。"""
    res_id = clean_id(res_id)
    n = db.execute(
        """UPDATE Reserve SET status = 'cancelled'
            WHERE resId = %s AND mId = %s AND status IN ('pending', 'confirmed')""",
        (res_id, g.user["mid"]),
    )
    if not n:
        raise ApiError(400, "這筆預約無法取消")
    return {"ok": True}
