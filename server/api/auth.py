"""會員：註冊、登入、查看與修改個人資料。"""
import hmac
import re

from flask import Blueprint, g
from werkzeug.security import check_password_hash, generate_password_hash

import db
from auth import login_required, make_token
from api.common import ApiError, body, new_id, parse_date

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def password_ok(stored, given):
    """新註冊的會員存雜湊值；組上原有的測試帳號是明碼，兩種都能登入。"""
    stored = stored or ""
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, given)
    return hmac.compare_digest(stored.encode(), given.encode())


@bp.post("/register")
def register():
    data = body()
    email = (data.get("email") or "").strip().lower()
    name = (data.get("mName") or "").strip()
    password = data.get("password") or ""
    if not EMAIL_RE.match(email):
        raise ApiError(400, "請輸入有效的電子信箱")
    if not name:
        raise ApiError(400, "請輸入姓名")
    if len(password) < 8:
        raise ApiError(400, "密碼至少需要 8 個字元")
    if db.fetch_one("SELECT 1 FROM Member WHERE LOWER(email) = %s", (email,)):
        raise ApiError(409, "這個信箱已經註冊過了")

    with db.transaction() as cur:
        mid = new_id(cur, "Member", "mId")
        cur.execute(
            """INSERT INTO Member (mId, email, mName, password, birthday, phone, role)
               VALUES (%s, %s, %s, %s, %s, %s, 'user')
               RETURNING mId, email, mName, role""",
            (mid, email, name, generate_password_hash(password), parse_date(data.get("birthday")),
             data.get("phone") or None),
        )
        member = cur.fetchone()
    return {"token": make_token(member), "member": member}, 201


@bp.post("/login")
def login():
    data = body()
    email = (data.get("email") or "").strip().lower()
    m = db.fetch_one("SELECT * FROM Member WHERE LOWER(email) = %s", (email,))
    if not m or not password_ok(m["password"], data.get("password") or ""):
        raise ApiError(401, "信箱或密碼錯誤")
    member = {k: m[k] for k in ("mid", "email", "mname", "role")}
    return {"token": make_token(member), "member": member}


@bp.get("/me")
@login_required
def me():
    row = db.fetch_one(
        """SELECT m.mId, m.email, m.mName, m.birthday, m.phone, m.role,
                  (SELECT COUNT(*) FROM Review v WHERE v.mId = m.mId) AS review_count,
                  (SELECT COUNT(*) FROM Reserve s WHERE s.mId = m.mId
                      AND s.status IN ('pending', 'confirmed') AND s.dateTime >= LOCALTIMESTAMP) AS active_reserve_count,
                  (SELECT COUNT(*) FROM Favlist f WHERE f.mId = m.mId) AS favlist_count
             FROM Member m WHERE m.mId = %s""",
        (g.user["mid"],),
    )
    if not row:
        raise ApiError(404, "找不到會員")
    return row


@bp.put("/me")
@login_required
def update_me():
    data = body()
    name = (data.get("mName") or "").strip()
    password = data.get("password") or ""
    if not name:
        raise ApiError(400, "姓名不可空白")
    if password and len(password) < 8:
        raise ApiError(400, "新密碼至少需要 8 個字元")
    member = db.execute(
        """UPDATE Member
              SET mName = %s, birthday = %s, phone = %s,
                  password = COALESCE(%s, password)
            WHERE mId = %s
        RETURNING mId, email, mName, birthday, phone, role""",
        (name, parse_date(data.get("birthday")), data.get("phone") or None,
         generate_password_hash(password) if password else None, g.user["mid"]),
    )
    return {"member": member, "token": make_token(member)}
