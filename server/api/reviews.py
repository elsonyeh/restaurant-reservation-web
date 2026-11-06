"""評論：新增、修改、刪除、查看自己的評論。"""
from flask import Blueprint, g

import db
from auth import login_required
from api.common import ApiError, body, clean_id, new_id, parse_date, to_int

bp = Blueprint("reviews", __name__)


def _validate(data):
    rating = to_int(data.get("rating"))
    if rating not in (1, 2, 3, 4, 5):
        raise ApiError(400, "評分需為 1 到 5 分")
    comment = (data.get("comment") or "").strip()
    if len(comment) > 1000:
        raise ApiError(400, "評論內容最多 1000 字")
    return rating, comment or None, parse_date(data.get("visitDate"))


@bp.post("/reviews")
@login_required
def create_review():
    data = body()
    rid = clean_id(data.get("rId"), "餐廳編號")
    rating, comment, visit = _validate(data)
    if not db.fetch_one("SELECT 1 FROM Restaurant WHERE rId = %s", (rid,)):
        raise ApiError(404, "找不到這家餐廳")
    if db.fetch_one("SELECT 1 FROM Review WHERE mId = %s AND rId = %s", (g.user["mid"], rid)):
        raise ApiError(409, "你已經評論過這家餐廳，可以到會員中心修改")
    with db.transaction() as cur:
        rev_id = new_id(cur, "Review", "revId")
        cur.execute(
            """INSERT INTO Review (revId, rating, comment, visitDate, reviewTime, mId, rId)
               VALUES (%s, %s, %s, %s, LOCALTIMESTAMP(0), %s, %s)""",
            (rev_id, rating, comment, visit, g.user["mid"], rid),
        )
    return {"revid": rev_id}, 201


@bp.put("/reviews/<rev_id>")
@login_required
def update_review(rev_id):
    rev_id = clean_id(rev_id)
    rating, comment, visit = _validate(body())
    n = db.execute(
        """UPDATE Review SET rating = %s, comment = %s, visitDate = %s, reviewTime = LOCALTIMESTAMP(0)
            WHERE revId = %s AND mId = %s""",
        (rating, comment, visit, rev_id, g.user["mid"]),
    )
    if not n:
        raise ApiError(404, "找不到這則評論")
    return {"ok": True}


@bp.delete("/reviews/<rev_id>")
@login_required
def delete_review(rev_id):
    rev_id = clean_id(rev_id)
    if g.user.get("role") == "admin":
        n = db.execute("DELETE FROM Review WHERE revId = %s", (rev_id,))
    else:
        n = db.execute("DELETE FROM Review WHERE revId = %s AND mId = %s", (rev_id, g.user["mid"]))
    if not n:
        raise ApiError(404, "找不到這則評論")
    return {"ok": True}


@bp.get("/me/reviews")
@login_required
def my_reviews():
    return {"items": db.fetch_all(
        """SELECT v.revId, v.rating, v.comment, v.visitDate, v.reviewTime, v.rId, r.rName
             FROM Review v JOIN Restaurant r ON r.rId = v.rId
            WHERE v.mId = %s ORDER BY v.reviewTime DESC""", (g.user["mid"],))}
