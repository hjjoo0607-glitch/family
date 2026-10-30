"""장보기 알림메모 — streamlit run app.py
GitHub 저장소에 app.py와 requirements.txt를 올리고 Streamlit Community Cloud에서
app.py를 실행 파일로 지정하세요. GitHub Pages는 Python 앱을 실행하지 않습니다.
선택 사항: Streamlit Secrets에 APP_URL = "https://앱주소.streamlit.app" 설정.
QR은 웹 앱 주소를 여는 방식이며 카메라 스캔 기능이나 푸시 알림은 아닙니다.
데이터는 SQLite에 즉시 저장됩니다. Community Cloud의 로컬 디스크는 재시작/
재배포 때 유실될 수 있으므로 장기 보관은 외부 DB 연결이 필요합니다.
목록 URL은 접근 열쇠입니다. URL/QR을 가진 사람은 같은 목록을 보고 수정합니다.
"""
from __future__ import annotations

import io
import os
import re
import secrets
import sqlite3
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlsplit, urlunsplit, urlencode

import qrcode
import streamlit as st

DB_PATH = os.environ.get("SHOPPING_DB_PATH", "shopping_memo.sqlite3")
CATEGORIES = ["🥬 야채", "🍎 과일", "🥩 육류", "🐟 수산물", "🥛 유제품·달걀", "🍚 곡물·식재료", "🥫 가공·냉동", "🧴 생활용품", "🛍️ 기타"]
PRIORITIES = {1: "🔴 1 꼭 구매", 2: "🟡 2 가격 보고", 3: "🟢 3 저렴할 때"}


def connect():
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    with connect() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            list_id TEXT NOT NULL, category TEXT NOT NULL, name TEXT NOT NULL,
            priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 3),
            unit TEXT NOT NULL, planned_qty REAL NOT NULL CHECK(planned_qty > 0),
            target_price INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending','deferred','purchased')),
            actual_price INTEGER, actual_qty REAL, total INTEGER,
            created_at TEXT NOT NULL, purchased_at TEXT
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_items_list ON items(list_id, status)")


def get_items(list_id, status):
    with connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM items WHERE list_id=? AND status=? ORDER BY priority,id",
            (list_id, status))]


def add_item(list_id, category, name, priority, unit, qty, target):
    name, unit = name.strip(), unit.strip()
    if not name or not unit or len(name) > 50 or len(unit) > 12:
        raise ValueError("상품명(1~50자)과 단위(1~12자)를 확인해 주세요.")
    if priority not in (1, 2, 3) or qty <= 0 or target < 0:
        raise ValueError("중요도, 수량, 기준 단가를 확인해 주세요.")
    with connect() as db:
        db.execute("""INSERT INTO items
            (list_id,category,name,priority,unit,planned_qty,target_price,created_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (list_id, category, name, priority, unit, qty, target, datetime.now().isoformat()))


def price_total(price, qty):
    return int((Decimal(str(price)) * Decimal(str(qty))).quantize(
        Decimal('1'), rounding=ROUND_HALF_UP))


def purchase(list_id, item_id, price, qty):
    if price < 0 or qty <= 0:
        raise ValueError("단가는 0원 이상, 수량은 0보다 커야 합니다.")
    with connect() as db:
        result = db.execute("""UPDATE items SET status='purchased', actual_price=?,
            actual_qty=?, total=?, purchased_at=?
            WHERE list_id=? AND id=? AND status='pending'""",
            (price, qty, price_total(price, qty), datetime.now().isoformat(), list_id, item_id))
        return result.rowcount == 1


def set_status(list_id, item_id, old, new):
    with connect() as db:
        result = db.execute("""UPDATE items SET status=?, actual_price=NULL,
            actual_qty=NULL,total=NULL,purchased_at=NULL
            WHERE list_id=? AND id=? AND status=?""", (new, list_id, item_id, old))
        return result.rowcount == 1


def label(item):
    return f"{item['priority']}순위 · {item['name']} · {item['planned_qty']:g}{item['unit']}"


def build_url(base, list_id):
    parts = urlsplit(base.strip())
    if parts.scheme not in ('https', 'http') or not parts.netloc or parts.username or parts.password:
        raise ValueError("https://로 시작하는 실제 배포 주소를 입력해 주세요.")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode({'list': list_id}), ''))


def main():
    st.set_page_config(page_title="장보기 알림메모", page_icon="🛒", layout="centered", initial_sidebar_state="collapsed")
    st.markdown("""<style>
    #MainMenu, footer {visibility:hidden;}
    .block-container {max-width:540px;padding:1rem .8rem 1.2rem;}
    [data-testid="stVerticalBlock"] {gap:.45rem;}
    h1 {font-size:1.5rem!important;padding:0!important;}
    [data-testid="stMetricValue"] {font-size:1.45rem;}
    [data-testid="stMetricLabel"] {font-size:.8rem;}
    .stButton button, [data-testid="stPopover"] button {min-height:44px;}
    @media(max-width:640px){
      [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:.4rem;}
      [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]{width:0!important;min-width:0!important;flex:1 1 0!important;}
      .block-container {padding-top:.7rem;}
    }
    </style>""", unsafe_allow_html=True)
    initialize()
    token = st.query_params.get('list', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{24,80}', token):
        token = secrets.token_urlsafe(24)
        st.query_params['list'] = token
    pending = get_items(token, 'pending')
    deferred = get_items(token, 'deferred')
    cart = get_items(token, 'purchased')
    total = sum(i['total'] for i in cart)

    st.title("🛒 장보기 알림메모")
    st.caption("1 꼭 구매 · 2 가격 보고 · 3 저렴할 때만")
    cols = st.columns(3)
    cols[0].metric("남은 품목", f"{len(pending)}개")
    cols[1].metric("카트 품목", f"{len(cart)}개")
    cols[2].metric("카트 총액", f"{total:,}원")

    left, right = st.columns(2)
    with left:
        with st.popover("＋ 메모 추가", use_container_width=True):
            with st.form('add', clear_on_submit=True):
                category = st.selectbox("카테고리", CATEGORIES)
                name = st.text_input("상품명", max_chars=50, placeholder="예: 방울토마토 500g")
                priority = st.selectbox("중요도", [1, 2, 3], format_func=lambda p: PRIORITIES[p], index=1)
                unit = st.text_input("구매 단위", value="개", max_chars=12, help="봉, 팩, kg 등. 가격은 이 단위당 금액입니다.")
                qty = st.number_input("예정 수량", min_value=.01, max_value=100000.0, value=1.0, step=1.0)
                target = st.number_input("살 만한 기준 단가(원)", min_value=0, max_value=100000000, value=0, step=100, help="0이면 기준 없음. 실제 단가가 기준보다 높으면 보류를 권합니다.")
                if st.form_submit_button("저장", use_container_width=True):
                    try:
                        add_item(token, category, name, priority, unit, qty, target)
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.rerun()
    with right:
        with st.popover("🧾 카트·보류", use_container_width=True):
            st.markdown(f"**카트 합계 {total:,}원** · 보류 {len(deferred)}개")
            if cart:
                with st.container(height=190, border=False):
                    for item in cart:
                        st.text(f"{item['name']}\n{item['actual_price']:,}원 × {item['actual_qty']:g}{item['unit']} = {item['total']:,}원")
                chosen = st.selectbox("잘못 담았다면 되돌리기", cart, format_func=lambda i: i['name'], key='undo_cart')
                if st.button("카트에서 빼고 메모로 복구", use_container_width=True):
                    set_status(token, chosen['id'], 'purchased', 'pending')
                    st.rerun()
            else:
                st.caption("카트가 비어 있습니다.")
            if deferred:
                restore = st.selectbox("보류한 메모", deferred, format_func=label, key='restore')
                if st.button("보류 해제", use_container_width=True):
                    set_status(token, restore['id'], 'deferred', 'pending')
                    st.rerun()

    if pending:
        selected = st.selectbox("살 물건 · 중요도순", pending, format_func=label, key='selected')
        st.caption(f"{selected['category']} · 기준 단가 " + (f"{selected['target_price']:,}원/{selected['unit']}" if selected['target_price'] else "미설정"))
        a, b = st.columns(2)
        with a:
            price = st.number_input(f"실제 단가(원/{selected['unit']})", min_value=0, max_value=100000000, value=int(selected['target_price']), step=100, key=f"price_{selected['id']}")
        with b:
            quantity = st.number_input(f"실제 수량({selected['unit']})", min_value=.01, max_value=100000.0, value=float(selected['planned_qty']), step=1.0, key=f"qty_{selected['id']}")
        subtotal = price_total(price, quantity)
        expensive = selected['target_price'] > 0 and price > selected['target_price']
        if expensive:
            st.caption("⚠️ 기준보다 비싸요. 필요 없다면 보류하세요.")
        elif selected['priority'] == 3:
            st.caption("💡 3순위: 저렴하지 않으면 보류해도 괜찮아요.")
        else:
            st.caption(f"이번 품목 {subtotal:,}원 · 담은 뒤 {total + subtotal:,}원")
        a, b = st.columns(2)
        with a:
            if st.button(f"🛒 담기 {subtotal:,}원", type='primary', use_container_width=True):
                if purchase(token, selected['id'], price, quantity):
                    st.toast("메모에서 빼고 카트에 기록했어요.")
                st.rerun()
        with b:
            if st.button("💸 비싸서 보류", use_container_width=True):
                set_status(token, selected['id'], 'pending', 'deferred')
                st.rerun()
    else:
        st.info("살 물건이 없어요. 메모를 추가하거나 보류 목록을 확인하세요.")

    with st.popover("🔗 QR · 사용 안내", use_container_width=True):
        st.caption("현재 목록 주소를 북마크하세요. QR/주소를 가진 사람은 목록을 함께 수정할 수 있습니다.")
        try:
            default_url = st.secrets.get('APP_URL', '')
        except Exception:
            default_url = ''
        base = st.text_input("배포된 앱 주소", value=default_url, placeholder="https://my-shopping.streamlit.app")
        if base:
            try:
                url = build_url(base, token)
            except ValueError as exc:
                st.error(str(exc))
            else:
                buffer = io.BytesIO()
                qrcode.make(url).save(buffer, format='PNG')
                st.image(buffer.getvalue(), width=190)
                st.link_button("현재 목록 열기", url)
                st.code(url, language=None)
                st.download_button("QR 이미지 저장", buffer.getvalue(), 'shopping-qr.png', 'image/png')
        st.caption("가격은 단위당 금액입니다. 예: 500g 1팩에 3,000원이면 단위=팩, 단가=3,000, 수량=1. 소수 수량도 가능하며 품목 금액은 원 단위 반올림합니다.")
        st.caption("담기 전 단가·수량을 확인하세요. 0원은 무료 상품일 때만 사용하세요. 카트 합계는 입력액 기준으로 할인·봉투값 등은 자동 반영되지 않습니다.")
        st.caption("단일 화면·선택형 목록입니다. 작은 화면/확대 글꼴/키보드 사용 중에는 스크롤이 생길 수 있습니다. 펼친 입력 창과 영수증에는 필요한 만큼 스크롤이 있습니다.")
        st.warning("저장: 로컬 SQLite. 서버 재시작·재배포 시 데이터가 사라질 수 있습니다. 장기 보관·여러 서버 운영에는 외부 DB가 필요합니다. 여러 휴대폰이 함께 사용할 때 최신 내용은 새로고침으로 확인하세요.")
        st.caption("GitHub에 두 파일 업로드 → Streamlit Community Cloud에서 저장소 연결 → app.py 배포 → 위에 배포 주소 입력 → QR 저장. 앱 실행 후 만들어진 ?list=... 주소를 계속 사용하세요.")
        if st.button("🔄 최신 내용 새로고침", use_container_width=True):
            st.rerun()


if __name__ == '__main__':
    main()
