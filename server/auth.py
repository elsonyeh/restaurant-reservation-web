"""登入驗證：以 JWT（放在 Authorization: Bearer 標頭）辨識會員與管理者。"""
import os
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

ALGO = "HS256"


def _secret():
    return os.getenv("SECRET_KEY", "dev-only-secret")


def make_token(member):
    payload = {
        "mid": member["mid"],
        "role": member["role"],
        "name": member["mname"],
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGO)


def load_user():
    """每個請求開始時讀取 token，有效就放進 g.user。"""
    g.user = None
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        try:
            g.user = jwt.decode(header[7:], _secret(), algorithms=[ALGO])
        except jwt.PyJWTError:
            g.user = None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.user:
            return jsonify(error="請先登入"), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.user:
            return jsonify(error="請先登入"), 401
        # 以資料庫目前的身分為準（身分被調整後，不必等舊的 token 過期）
        import db
        row = db.fetch_one("SELECT role FROM Member WHERE mId = %s", (g.user.get("mid"),))
        if not row or (row["role"] or "").strip() != "admin":
            return jsonify(error="需要管理者權限"), 403
        return fn(*args, **kwargs)
    return wrapper
