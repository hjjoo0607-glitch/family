import base64
import hmac
from datetime import date, datetime, time
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

# -----------------------------------------------------------------------------
# 설정 (Streamlit Community Cloud 배포 후 App settings > Secrets에 입력)
# [supabase]
# url = "https://YOUR_PROJECT.supabase.co"
# service_role_key = "YOUR_SERVICE_ROLE_KEY"
# [family]
# title = "오늘 우리 집"
# [family.codes]
# 엄마 = "엄마에게_전달할_코드"
# 아빠 = "아빠에게_전달할_코드"
# 오빠 = "오빠에게_전달할_코드"
# "언니 1" = "언니1에게_전달할_코드"
# "언니 2" = "언니2에게_전달할_코드"
# 나 = "내_코드"
#
# Supabase SQL Editor에서 한 번 실행:
# create table public.family_board (
#   day date primary key,
#   payload jsonb not null default '{}'::jsonb,
#   updated_at timestamptz not null default now()
# );
# alter table public.family_board enable row level security;
# (service_role_key는 서버 비밀값입니다. 코드/깃허브 공개 저장소에 올리지 마세요.)
# -----------------------------------------------------------------------------

st.set_page_config(page_title="오늘 우리 집", page_icon="🏠", layout="centered")

LOGO_B64 = "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"
TZ = ZoneInfo("Asia/Seoul")
TODAY = datetime.now(TZ).date()

st.markdown("""
<style>
:root { --cream:#fbf7eb; --cream2:#fffdf6; --yellow:#f4ce3e; --mint:#dff2e8; --peach:#f8e1d5; --ink:#292923; --muted:#77766e; }
.stApp { background:var(--cream); color:var(--ink); }
.block-container { max-width:850px; padding-top:1.4rem; padding-bottom:3rem; }
[data-testid="stHeader"] { background:transparent; }
.hero { text-align:center; background:var(--cream2); border:1px solid #eee6d4; border-radius:26px; padding:18px 18px 14px; margin-bottom:16px; box-shadow:0 7px 24px #695b2410; }
.hero img { width:min(100%,390px); max-height:230px; object-fit:contain; border-radius:18px; }
.hero h1 { font-size:clamp(1.7rem,5vw,2.3rem); margin:.35rem 0 .15rem; color:#25251f; }
.hero p { margin:0; color:var(--muted); }
section[data-testid="stSidebar"] { background:#f6efd9; }
div[data-testid="stVerticalBlockBorderWrapper"] { background:var(--cream2); border-radius:18px; border-color:#eee6d4; }
.stButton>button, .stFormSubmitButton>button { border-radius:12px; border:0; background:var(--yellow); color:#28251b; font-weight:700; min-height:2.7rem; }
.stButton>button:hover, .stFormSubmitButton>button:hover { border:0; background:#ebc52b; color:#222; }
input, textarea, [data-baseweb="select"] { border-radius:10px !important; }
.kpi { display:flex; gap:10px; flex-wrap:wrap; margin:12px 0 18px; }
.kpi span { display:inline-block; background:#fffdf6; border:1px solid #eee6d4; border-radius:999px; padding:9px 14px; font-weight:700; }
.small-muted { color:#77766e; font-size:.88rem; }
hr { border-color:#e9e1d0; }
</style>
""", unsafe_allow_html=True)


def hero(title: str, subtitle: str = "우리 가족, 오늘은 어디에?") -> None:
    st.markdown(
        f'<div class="hero"><img src="data:image/jpeg;base64,{LOGO_B64}" alt="웃는 집 로고">'
        f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def get_config():
    try:
        cfg = st.secrets["supabase"]
        family_cfg = st.secrets["family"]
        url = str(cfg["url"]).strip()
        key = str(cfg["service_role_key"]).strip()
        codes = {str(k): str(v) for k, v in family_cfg["codes"].items()}
        title = str(family_cfg.get("title", "오늘 우리 집"))
        if not url or not key or not codes or any(not value for value in codes.values()):
            raise ValueError("필수 설정값이 비어 있습니다.")
        return url, key, codes, title
    except Exception as exc:
        # 설정이 없더라도 사용자가 브랜드 화면을 볼 수 있도록 로고/앱명을 먼저 보여줍니다.
        hero("오늘 우리 집", "가족 코드로 입장할 수 있도록 앱 설정을 마무리해 주세요")
        st.error("앱 설정이 아직 완료되지 않았어요. 아래 값을 Streamlit의 Secrets에 등록해 주세요.")
        st.code('''[supabase]
url = "https://YOUR_PROJECT.supabase.co"
service_role_key = "YOUR_SERVICE_ROLE_KEY"

[family]
title = "오늘 우리 집"

[family.codes]
엄마 = "엄마용_개별코드"
아빠 = "아빠용_개별코드"
"언니 1" = "언니1용_개별코드"
나 = "내_개별코드"''', language="toml")
        st.caption("Supabase 테이블 생성 SQL과 전체 설정 안내는 app.py 상단 주석에 있어요. 설정 오류: " + str(exc))
        st.stop()


def initial_payload(names):
    return {
        "members": {
            name: {"home": "미정", "arrival": "", "meal": "미정", "updated_at": ""}
            for name in names
        },
        "memo": "",
        "memo_by": "",
        "memo_at": "",
    }


def load_payload(client, names):
    result = client.table("family_board").select("payload").eq("day", TODAY.isoformat()).execute()
    rows = result.data or []
    if rows and isinstance(rows[0].get("payload"), dict):
        payload = rows[0]["payload"]
    else:
        payload = initial_payload(names)
        save_payload(client, payload)
    payload.setdefault("members", {})
    for name in names:
        payload["members"].setdefault(name, {"home": "미정", "arrival": "", "meal": "미정", "updated_at": ""})
    payload.setdefault("memo", "")
    payload.setdefault("memo_by", "")
    payload.setdefault("memo_at", "")
    return payload


def save_payload(client, payload):
    client.table("family_board").upsert(
        {"day": TODAY.isoformat(), "payload": payload, "updated_at": datetime.now(TZ).isoformat()},
        on_conflict="day",
    ).execute()


url, service_key, member_codes, APP_TITLE = get_config()
MEMBERS = list(member_codes.keys())
try:
    supabase = create_client(url, service_key)
except Exception as exc:
    st.error("공유 저장소에 연결하지 못했어요. Supabase 설정을 확인해 주세요.")
    st.caption(str(exc))
    st.stop()

# Entrance: one personal code for each family member.
if "member_name" not in st.session_state:
    hero(APP_TITLE, "가족 코드로 들어와 오늘의 귀가와 식사를 공유해요")
    with st.container(border=True):
        st.subheader("가족 코드로 입장")
        with st.form("login_form", clear_on_submit=False):
            chosen = st.selectbox("누구세요?", MEMBERS)
            entered = st.text_input("가족별 입장 코드", type="password", placeholder="가족에게 받은 코드를 입력하세요")
            submitted = st.form_submit_button("우리 집 입장", use_container_width=True)
        if submitted:
            if hmac.compare_digest(entered, member_codes.get(chosen, "")):
                st.session_state.member_name = chosen
                st.rerun()
            else:
                st.error("코드가 맞지 않아요. 다시 확인해 주세요.")
    st.caption("가족별 코드는 각자 따로 설정하세요. 위치를 추적하지 않고, 직접 입력한 계획만 공유합니다.")
    st.stop()

current = st.session_state.member_name
try:
    board = load_payload(supabase, MEMBERS)
except Exception as exc:
    st.error("오늘 가족 현황을 불러오지 못했어요. Supabase 테이블과 연결 설정을 확인해 주세요.")
    st.caption(str(exc))
    st.stop()

hero(APP_TITLE, f"{TODAY.strftime('%Y년 %m월 %d일')} · 우리 가족, 오늘은 어디에?")
head_left, head_right = st.columns([4, 1])
with head_left:
    st.markdown(f"**{escape(current)}님, 안녕하세요!**")
with head_right:
    if st.button("나가기", use_container_width=True):
        del st.session_state.member_name
        st.rerun()

# Overview summary. Unsubmitted values are always shown as '미정'.
coming = sum(1 for name in MEMBERS if board["members"][name].get("home") in ("집에 있어요", "귀가 예정"))
dinner = sum(1 for name in MEMBERS if board["members"][name].get("meal") == "같이 먹어요")
at_home = sum(1 for name in MEMBERS if board["members"][name].get("home") == "집에 있어요")
st.markdown(
    f'<div class="kpi"><span>🏠 집에 있어요 <b>{at_home}</b>명</span>'
    f'<span>🌙 오늘 귀가 예정 <b>{coming}</b>명</span>'
    f'<span>🍚 같이 저녁 <b>{dinner}</b>명</span></div>',
    unsafe_allow_html=True,
)

st.subheader("우리 가족 오늘 현황")
cols = st.columns(2)
for idx, name in enumerate(MEMBERS):
    info = board["members"][name]
    with cols[idx % 2]:
        with st.container(border=True):
            st.markdown(f"### {escape(name)}" + (" · 나" if name == current else ""))
            home = info.get("home", "미정")
            arrival = info.get("arrival", "")
            home_text = f"⏰ {arrival}쯤 귀가" if home == "귀가 예정" and arrival else home
            st.write(f"**귀가**　{home_text}")
            st.write(f"**저녁**　{info.get('meal', '미정')}")
            if info.get("updated_at"):
                st.caption("마지막 수정 " + info["updated_at"])

st.divider()
st.subheader(f"{current}님의 오늘 계획")
my = board["members"][current]
home_options = ["미정", "집에 있어요", "귀가 예정", "오늘 안 와요"]
meal_options = ["미정", "같이 먹어요", "밖에서 먹어요"]
with st.form("status_form"):
    new_home = st.selectbox("귀가", home_options, index=home_options.index(my.get("home", "미정")) if my.get("home", "미정") in home_options else 0,
                            help="아직 입력하지 않은 상태는 '미정'으로 표시돼요.")
    if new_home == "귀가 예정":
        old_time = my.get("arrival", "")
        try:
            init_time = time.fromisoformat(old_time) if old_time else time(18, 0)
        except ValueError:
            init_time = time(18, 0)
        new_time = st.time_input("대략 몇 시쯤 도착하나요?", value=init_time, step=900, format="HH:mm")
        new_arrival = new_time.strftime("%H:%M")
    else:
        new_arrival = ""
    old_meal = my.get("meal", "미정")
    new_meal = st.selectbox("저녁 식사", meal_options, index=meal_options.index(old_meal) if old_meal in meal_options else 0)
    save_status = st.form_submit_button("내 상태 저장", use_container_width=True)
if save_status:
    board["members"][current] = {
        "home": new_home,
        "arrival": new_arrival,
        "meal": new_meal,
        "updated_at": datetime.now(TZ).strftime("%H:%M"),
    }
    try:
        save_payload(supabase, board)
        st.success("오늘 계획을 가족에게 공유했어요!")
        st.rerun()
    except Exception as exc:
        st.error("저장에 실패했어요. 연결 상태를 확인해 주세요.")
        st.caption(str(exc))

st.divider()
st.subheader("가족 메모")
st.caption("오늘 함께 볼 짧은 메모를 남겨요.")
with st.form("memo_form"):
    memo_text = st.text_area("메모", value=board.get("memo", ""), max_chars=500,
                             placeholder="예: 저녁 7시에 같이 먹자!", label_visibility="collapsed", height=90)
    save_memo = st.form_submit_button("메모 저장", use_container_width=True)
if save_memo:
    board["memo"] = memo_text.strip()
    board["memo_by"] = current
    board["memo_at"] = datetime.now(TZ).strftime("%H:%M")
    try:
        save_payload(supabase, board)
        st.success("가족 메모를 저장했어요.")
        st.rerun()
    except Exception as exc:
        st.error("메모 저장에 실패했어요. 연결 상태를 확인해 주세요.")
        st.caption(str(exc))
if board.get("memo"):
    st.info("💬　" + board["memo"])
    if board.get("memo_by"):
        st.caption(f"작성: {board['memo_by']} · {board.get('memo_at', '')}")
else:
    st.caption("아직 오늘의 메모가 없어요.")

st.caption("계획은 언제든 바꿀 수 있어요. 입력하지 않은 항목은 '미정'이며, 자동 위치 추적은 하지 않습니다.")
