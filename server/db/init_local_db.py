"""在「本機」PostgreSQL 建立與組上資料庫相同的資料表，並匯入示範資料。

用途：沒有連上課程資料庫時，用本機資料庫測試整套系統。
執行：python db/init_local_db.py
警告：會先刪除再重建所有資料表，請不要把 .env 指向課程資料庫時執行（程式會拒絕執行）。
"""
import json
import os
import secrets
import sys
from datetime import datetime, timedelta

import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", ".env"))

if os.getenv("DB_HOST", "localhost") not in ("localhost", "127.0.0.1", ""):
    sys.exit("為了保護組上的課程資料庫，這支程式只能在本機資料庫（DB_HOST=localhost）執行。")

CAPACITY_BY_PRICE = {2: 32, 3: 40}
used = set()
counters = {}


def hid(prefix=None):
    """產生與組上資料庫相同格式的編號：前綴 + 5 位數字，或 6 碼十六進位（餐廳）。"""
    if prefix:
        counters[prefix] = counters.get(prefix, 0) + 1
        return f"{prefix}{counters[prefix]:05d}"
    while True:
        x = secrets.token_hex(3)
        if x not in used:
            used.add(x)
            return x


def at(days, hh, mm):
    d = datetime.now() + timedelta(days=days)
    return d.replace(hour=hh, minute=mm, second=0, microsecond=0)


def main():
    conn = psycopg2.connect(host=os.getenv("DB_HOST", "localhost"), port=os.getenv("DB_PORT", "5432"),
                            user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD") or None,
                            dbname=os.getenv("DB_NAME"))
    cur = conn.cursor()
    with open(os.path.join(HERE, "schema.sql"), encoding="utf-8") as f:
        cur.execute(f.read())

    restaurants = json.load(open(os.path.join(HERE, "data", "restaurants.json"), encoding="utf-8"))

    tag_id = {}
    for name in sorted({t for r in restaurants for t in r["tags"]}):
        tag_id[name] = hid("t")
        cur.execute("INSERT INTO tag (tid, tname) VALUES (%s, %s)", (tag_id[name], name))

    rest_id = {}
    for r in restaurants:
        rid = hid()
        rest_id[r["name"]] = rid
        accept = r["price"] >= 2
        cur.execute(
            """INSERT INTO restaurant (rid, rname, maxpartysize, address, pricerange, google_rate, google_num,
                                       picture, acceptres, capacity)
               VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s)""",
            (rid, r["name"], r["maxParty"], r["address"], str(r["price"]), r["rate"], r["num"],
             accept, CAPACITY_BY_PRICE.get(r["price"]) if accept else None))
        for t in r["tags"]:
            cur.execute("INSERT INTO hastag (tid, rid) VALUES (%s, %s)", (tag_id[t], rid))

    members = [
        ("admin@siwan.test", "系統管理者", None, None, "admin1234", "admin"),
        ("yijun@siwan.test", "陳怡君", "2004-05-12", "0912-345-678", "user1234", "user"),
        ("bohan@siwan.test", "林柏翰", "2003-11-02", "0922-111-222", "user1234", "user"),
        ("amy@siwan.test", "Amy", "2004-02-20", None, "user1234", "user"),
    ]
    mid = {}
    for email, name, bday, phone, pw, role in members:
        mid[email] = hid("M")
        cur.execute("INSERT INTO member VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (mid[email], email, name, bday, phone, generate_password_hash(pw), role))

    for rest, items in {
        "泰法客泰味小食光": [("打拋豬肉飯", None), ("綠咖哩雞", None), ("月亮蝦餅", None)],
        "叻沙郎": [("叻沙麵", None), ("海南雞飯", None)],
        "都瓦哩印度廚房": [("奶油雞咖哩", None), ("蒜味烤餅", None)],
    }.items():
        for name, price in items:
            cur.execute("INSERT INTO topmenu VALUES (%s, %s, %s, %s)", (rest_id[rest], name, price, "示範資料"))

    for email, rest, rating, d, text in [
        ("yijun@siwan.test", "泰法客泰味小食光", 5, -9, "打拋豬辣度剛好，飯量很夠。平日晚上六點多到還有位子，但七點後就開始排隊，建議先訂位。"),
        ("bohan@siwan.test", "泰法客泰味小食光", 5, -18, "月亮蝦餅現炸，外皮很脆。四個人點了五道菜，平均下來一人兩百多。"),
        ("amy@siwan.test", "泰法客泰味小食光", 4, -32, "味道道地，店內空間比較小，週末人多時聊天要稍微大聲一點。"),
        ("yijun@siwan.test", "鹽埕町冰果室", 4, -26, "日式老屋很好拍，冰的份量兩個人吃剛好。假日下午要等大約二十分鐘。"),
        ("yijun@siwan.test", "小豆町食堂", 5, -37, "離學校近，定食附湯和小菜，平日中午很適合一個人來。"),
        ("bohan@siwan.test", "叻沙郎", 5, -12, "叻沙湯頭很濃，可以選辣度，價格對學生很友善。"),
    ]:
        cur.execute("INSERT INTO review VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (hid("V"), rating, at(d + 1, 21, 0), at(d, 12, 0).date(), text, mid[email], rest_id[rest]))

    for email, rest, when, size, status, note in [
        ("yijun@siwan.test", "泰法客泰味小食光", at(8, 18, 0), 2, "pending", "一位不吃辣"),
        ("yijun@siwan.test", "都瓦哩印度廚房", at(15, 12, 0), 4, "confirmed", None),
        ("yijun@siwan.test", "泰法客泰味小食光", at(-9, 18, 30), 2, "completed", None),
        ("yijun@siwan.test", "鸚鵡螺餐酒館", at(-20, 19, 0), 3, "cancelled", "生日聚餐"),
        ("bohan@siwan.test", "都瓦哩印度廚房", at(9, 12, 0), 4, "pending", None),
        ("amy@siwan.test", "點22 港式點心專賣店", at(9, 13, 0), 3, "pending", None),
        ("amy@siwan.test", "叻沙郎", at(5, 12, 0), 2, "rejected", "不接受預約"),
        ("bohan@siwan.test", "泰法客泰味小食光", at(8, 18, 30), 4, "confirmed", "社團聚餐"),
    ]:
        cur.execute("INSERT INTO reserve VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (hid("S"), status, note, when, size, mid[email], rest_id[rest]))

    for email, name, public, desc, rests in [
        ("yijun@siwan.test", "想吃的店", False, "預設清單", ["叻沙郎", "食鍋者正宗南洋風味館", "HATA 烏克蘭廚房", "千義PASTA"]),
        ("yijun@siwan.test", "宵夜", True, "晚上十點後還能去的店", ["呆呆滷味", "鹽埕波臭豆腐"]),
        ("yijun@siwan.test", "帶家人來", False, "可以訂位、座位寬一點", ["都瓦哩印度廚房", "點22 港式點心專賣店", "壹捌迷你土雞鍋"]),
    ]:
        fid = hid("F")
        cur.execute("INSERT INTO favlist VALUES (%s, %s, %s, %s, %s)", (fid, name, public, desc, mid[email]))
        for r in rests:
            if r in rest_id:
                cur.execute("INSERT INTO contains VALUES (%s, %s)", (fid, rest_id[r]))

    conn.commit()
    conn.close()
    print(f"本機資料庫完成：餐廳 {len(restaurants)} 家、標籤 {len(tag_id)} 個、會員 {len(members)} 位")
    print("測試帳號：admin@siwan.test / admin1234（管理者），yijun@siwan.test / user1234（會員）")


if __name__ == "__main__":
    main()
