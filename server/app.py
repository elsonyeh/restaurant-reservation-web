"""好位 GOOD SEAT：校園周邊餐廳評價與搜尋系統（Flask 後端）

執行：python app.py
本機執行時，http://127.0.0.1:5000 同時提供前端頁面（docs 資料夾）與 API（/api/...）。
"""
import os
from datetime import date, datetime
from decimal import Decimal

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

load_dotenv()

from auth import load_user  # noqa: E402
from api.auth import bp as auth_bp  # noqa: E402
from api.restaurants import bp as restaurants_bp  # noqa: E402
from api.reviews import bp as reviews_bp  # noqa: E402
from api.reservations import bp as reservations_bp  # noqa: E402
from api.favlists import bp as favlists_bp  # noqa: E402
from api.admin import bp as admin_bp  # noqa: E402
from api.common import ApiError  # noqa: E402

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")


class JSONProvider(DefaultJSONProvider):
    """日期輸出成 'YYYY-MM-DD'、時間輸出成 'YYYY-MM-DD HH:MM'，NUMERIC 轉成數字。"""

    @staticmethod
    def default(o):
        if isinstance(o, datetime):
            return o.strftime("%Y-%m-%d %H:%M")
        if isinstance(o, date):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


def create_app():
    app = Flask(__name__, static_folder=None)
    app.json = JSONProvider(app)
    app.json.ensure_ascii = False

    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    CORS(app, resources={r"/api/*": {"origins": origins or "*"}})

    app.before_request(load_user)

    for bp in (auth_bp, restaurants_bp, reviews_bp, reservations_bp, favlists_bp):
        app.register_blueprint(bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    @app.get("/api/health")
    def health():
        return {"ok": True}

    # ---- 錯誤處理：把常見的資料庫錯誤轉成看得懂的訊息 ----
    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return jsonify(error=err.message), err.status

    @app.errorhandler(psycopg2.Error)
    def handle_db_error(err):
        code = getattr(err, "pgcode", None)
        messages = {
            "23505": (409, "資料重複，請確認後再試"),
            "23503": (400, "相關資料不存在"),
            "23514": (400, "資料格式不正確"),
            "22P02": (400, "資料格式錯誤"),
            "22007": (400, "日期時間格式錯誤"),
            "22008": (400, "日期時間超出範圍"),
        }
        if code in messages:
            status, msg = messages[code]
            return jsonify(error=msg), status
        app.logger.exception(err)
        return jsonify(error="系統忙碌中，請稍後再試"), 500

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="找不到這個頁面"), 404

    # ---- 前端靜態頁面（與 GitHub Pages 上的 docs 資料夾相同）----
    @app.get("/")
    def index():
        return send_from_directory(DOCS_DIR, "index.html")

    @app.get("/<path:path>")
    def static_files(path):
        return send_from_directory(DOCS_DIR, path)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"好位 GOOD SEAT 已啟動：http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
