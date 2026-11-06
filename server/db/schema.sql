-- SIWAN TABLE 西灣食記：校園周邊餐廳評價與搜尋系統
-- 與組上課程資料庫（project_8）目前的資料表結構相同，供本機測試或重建使用。
-- 注意：本檔會先 DROP 再建立，切勿在已有正式資料的課程資料庫上執行。
-- 主鍵皆為 6 碼文字編號（例如 32d2db），由程式產生。

DROP TABLE IF EXISTS contains, hastag, topmenu, review, reserve, favlist, tag, restaurant, member CASCADE;

CREATE TABLE member (
    mid       CHAR(6) PRIMARY KEY,
    email     VARCHAR(255) NOT NULL,
    mname     VARCHAR(100) NOT NULL,
    birthday  DATE,
    phone     VARCHAR(20),
    password  VARCHAR(255) NOT NULL,
    role      VARCHAR(50)
);

CREATE TABLE restaurant (
    rid           CHAR(6) PRIMARY KEY,
    rname         VARCHAR(255) NOT NULL,
    maxpartysize  INTEGER,
    address       TEXT,
    pricerange    VARCHAR(50),
    google_rate   NUMERIC,           -- 複合屬性 google 的 rate
    google_num    INTEGER,           -- 複合屬性 google 的 num
    picture       TEXT,
    acceptres     BOOLEAN,
    capacity      INTEGER
);

CREATE TABLE tag (
    tid    CHAR(6) PRIMARY KEY,
    tname  VARCHAR(100) NOT NULL
);

CREATE TABLE hastag (
    tid  CHAR(6) NOT NULL REFERENCES tag(tid) ON DELETE CASCADE,
    rid  CHAR(6) NOT NULL REFERENCES restaurant(rid) ON DELETE CASCADE,
    PRIMARY KEY (tid, rid)
);

-- 弱實體：主鍵 = 擁有者 rid + 部分鍵 menuname
CREATE TABLE topmenu (
    rid          CHAR(6) NOT NULL REFERENCES restaurant(rid) ON DELETE CASCADE,
    menuname     VARCHAR(255) NOT NULL,
    price        NUMERIC,
    description  TEXT,
    PRIMARY KEY (rid, menuname)
);

CREATE TABLE favlist (
    fid          CHAR(6) PRIMARY KEY,
    fname        VARCHAR(255) NOT NULL,
    ispublic     BOOLEAN DEFAULT FALSE,
    description  TEXT,
    mid          CHAR(6) REFERENCES member(mid) ON DELETE CASCADE
);

CREATE TABLE contains (
    fid  CHAR(6) NOT NULL REFERENCES favlist(fid) ON DELETE CASCADE,
    rid  CHAR(6) NOT NULL REFERENCES restaurant(rid) ON DELETE CASCADE,
    PRIMARY KEY (fid, rid)
);

CREATE TABLE review (
    revid       CHAR(6) PRIMARY KEY,
    rating      INTEGER CHECK (rating >= 1 AND rating <= 5),
    reviewtime  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    visitdate   DATE,
    comment     TEXT,
    mid         CHAR(6) REFERENCES member(mid) ON DELETE SET NULL,
    rid         CHAR(6) REFERENCES restaurant(rid) ON DELETE CASCADE
);

CREATE TABLE reserve (
    resid      CHAR(6) PRIMARY KEY,
    status     VARCHAR(50),
    note       TEXT,
    datetime   TIMESTAMP NOT NULL,
    partysize  INTEGER NOT NULL,
    mid        CHAR(6) REFERENCES member(mid) ON DELETE CASCADE,
    rid        CHAR(6) REFERENCES restaurant(rid) ON DELETE CASCADE
);
