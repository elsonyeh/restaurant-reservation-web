"""收藏清單：建立、修改、刪除清單，加入或移除餐廳（Contains）。"""
from flask import Blueprint, g

import db
from auth import login_required
from api.common import DISTRICT_SQL, ApiError, body, clean_id, new_id

bp = Blueprint("favlists", __name__)


def _own(fid):
    fid = clean_id(fid, "清單編號")
    row = db.fetch_one("SELECT * FROM Favlist WHERE fId = %s AND mId = %s", (fid, g.user["mid"]))
    if not row:
        raise ApiError(404, "找不到這個清單")
    return row


def _fields(data):
    name = (data.get("fName") or "").strip()
    if not name:
        raise ApiError(400, "請輸入清單名稱")
    return name[:50], bool(data.get("isPublic")), (data.get("description") or "").strip()[:200] or None


@bp.get("/me/favlists")
@login_required
def my_lists():
    lists = db.fetch_all(
        """SELECT f.fId, f.fName, f.isPublic, f.description,
                  (SELECT COUNT(*) FROM Contains c WHERE c.fId = f.fId) AS n
             FROM Favlist f WHERE f.mId = %s ORDER BY f.fId""", (g.user["mid"],))
    items = db.fetch_all(
        f"""SELECT c.fId, r.rId, r.rName, r.priceRange, r.google_rate, {DISTRICT_SQL} AS district
              FROM Contains c
              JOIN Favlist f ON f.fId = c.fId
              JOIN Restaurant r ON r.rId = c.rId
             WHERE f.mId = %s ORDER BY r.rName""", (g.user["mid"],))
    for lst in lists:
        lst["restaurants"] = [i for i in items if i["fid"] == lst["fid"]]
    return {"items": lists}


@bp.post("/favlists")
@login_required
def create_list():
    name, public, desc = _fields(body())
    with db.transaction() as cur:
        fid = new_id(cur, "Favlist", "fId")
        cur.execute("INSERT INTO Favlist (fId, fName, isPublic, description, mId) VALUES (%s, %s, %s, %s, %s)",
                    (fid, name, public, desc, g.user["mid"]))
    return {"fid": fid}, 201


@bp.put("/favlists/<fid>")
@login_required
def update_list(fid):
    fid = _own(fid)["fid"]
    name, public, desc = _fields(body())
    db.execute("UPDATE Favlist SET fName = %s, isPublic = %s, description = %s WHERE fId = %s",
               (name, public, desc, fid))
    return {"ok": True}


@bp.delete("/favlists/<fid>")
@login_required
def delete_list(fid):
    fid = _own(fid)["fid"]
    db.execute("DELETE FROM Favlist WHERE fId = %s", (fid,))
    return {"ok": True}


@bp.post("/favlists/<fid>/restaurants")
@login_required
def add_restaurant(fid):
    fid = _own(fid)["fid"]
    rid = clean_id(body().get("rId"), "餐廳編號")
    db.execute("INSERT INTO Contains (fId, rId) VALUES (%s, %s) ON CONFLICT DO NOTHING", (fid, rid))
    return {"ok": True}, 201


@bp.delete("/favlists/<fid>/restaurants/<rid>")
@login_required
def remove_restaurant(fid, rid):
    fid = _own(fid)["fid"]
    rid = clean_id(rid, "餐廳編號")
    db.execute("DELETE FROM Contains WHERE fId = %s AND rId = %s", (fid, rid))
    return {"ok": True}
