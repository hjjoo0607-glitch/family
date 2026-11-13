"""우리 가족 플랜 B | 실행: streamlit run app.py
GitHub에는 이 파일과 requirements.txt만 올리세요. 비밀 키는 Streamlit Secrets에만 저장합니다.
처음 실행한 앱의 '설정 안내'에서 Supabase SQL과 Secrets 예시를 확인하세요.
"""
import hashlib
import hmac
import itertools
import math
import secrets
from datetime import date
from urllib.parse import quote

import requests
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="우리 가족 플랜 B", page_icon="🍀", layout="wide")
st.markdown("""<style>
.stApp{background:#faf9f5} h1,h2,h3{color:#294b40}
div.stButton>button{border-radius:14px;min-height:48px;width:100%}
[data-testid="stTextInput"] input{min-height:48px;font-size:16px}
[data-testid="stRadio"] label{padding:10px 12px;border:1px solid #cbd9cd;border-radius:12px;margin:4px 0;min-height:48px}
.family-hero{background:#eaf3e8;border:1px solid #cddfcb;border-radius:24px;padding:26px 22px;margin-bottom:18px}
.family-logo{font-size:44px}.family-hero h1{font-size:clamp(26px,7vw,40px);margin:8px 0;line-height:1.3}
.family-hero p{color:#345646;font-size:16px;line-height:1.7;margin:8px 0}
@media(max-width:640px){
[data-testid="stMainBlockContainer"]{padding:1.5rem 1rem 3rem}
[data-baseweb="tab-list"]{flex-wrap:wrap;gap:6px}
[data-baseweb="tab"]{flex:1 1 44%;min-height:48px;background:#eef4ed;border-radius:12px;padding:8px}
} [data-testid='stMetric']{background:#eef4ed;padding:16px;border-radius:18px}
</style>""", unsafe_allow_html=True)
st.markdown("""<section class="family-hero" aria-label="우리 가족 플랜 B 소개">
<div class="family-logo" aria-hidden="true">🍀</div>
<h1>우리 가족 플랜 B</h1>
<p><strong>함께 놀고, 지치면 쉬어가는 가족 나들이 도우미</strong></p>
<p>일정과 자동차 동선 · 익명 체력 투표 · 가까운 대안 찾기 · 고마운 마음 전하기</p>
<p>아빠 · 엄마 · 오빠 · 언니1 · 언니2 · 나<br>계획이 바뀌어도 괜찮아. 여섯 명이 편한 하루를 만들어요.</p>
</section>""", unsafe_allow_html=True)

SQL = """-- Supabase 프로젝트 → SQL Editor → New query에 전체 붙여넣고 실행
create table if not exists public.family_plans (
 room text primary key, payload jsonb not null,
 updated_at timestamptz not null default now()
);
create table if not exists public.family_votes (
 room text not null, poll text not null, voter text not null,
 tired boolean not null, updated_at timestamptz not null default now(),
 primary key(room,poll,voter)
);
create table if not exists public.family_praise (
 id bigint generated always as identity primary key,
 room text not null, nickname text not null, body text not null,
 created_at timestamptz not null default now()
);
alter table public.family_plans enable row level security;
alter table public.family_votes enable row level security;
alter table public.family_praise enable row level security;
-- 브라우저/anon 사용자는 접근 불가. 앱 서버의 service_role만 사용합니다.
revoke all on public.family_plans, public.family_votes, public.family_praise from anon, authenticated;
grant all on public.family_plans, public.family_votes, public.family_praise to service_role;
grant usage, select on sequence public.family_praise_id_seq to service_role;
"""

def cfg(key, default=""):
    try:
        return str(st.secrets.get(key, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default

with st.expander("🔧 처음이라면: 설정 안내 / 개인정보 안내"):
    st.markdown("""
**1. GitHub / Streamlit**
- GitHub 저장소에 `app.py`, `requirements.txt` 두 파일을 올립니다.
- Streamlit Community Cloud에서 저장소를 선택하고 Main file path를 `app.py`로 배포합니다.
- 앱 관리 화면의 Settings → Secrets에 아래 설정을 붙여 넣습니다. 키를 GitHub에 올리지 마세요.

**2. 카카오 연결**
- [Kakao Developers](https://developers.kakao.com)에서 앱을 만들고 REST API 키를 확인합니다.
- [로컬 API 안내](https://developers.kakao.com/docs/latest/ko/local/dev-guide)의 사용 조건·권한을 확인합니다.
- [카카오모빌리티](https://developers.kakaomobility.com)에서 자동차 길찾기 API 이용 설정·쿼터를 확인합니다.
- 장소 검색 키와 길찾기 키를 각각 입력합니다. 같은 앱의 키를 쓸 수 있는 환경이라면 같은 값을 넣어도 됩니다.
- 검색 실패/권한 오류 시 실제 오류를 표시하며 시간을 임의로 생성하지 않습니다.

**3. 무료 공유 DB**
- [Supabase](https://supabase.com)에서 프로젝트를 만듭니다. SQL Editor에서 아래 SQL을 실행합니다.
- 프로젝트 URL과 서버 전용 `service_role` 키(legacy API key)를 Secrets에 입력합니다.
- 무료 요금제에도 사용량 제한·비활성 프로젝트 일시 중지가 있을 수 있습니다.

**4. 익명 투표와 가족 방**
- 아래에서 무작위 투표 코드 6개를 생성해 Secrets의 VOTE_CODES에 넣습니다.
- 코드는 가족들이 이름을 기록하지 않고 하나씩 가져가세요. 코드와 이름의 대응표는 만들지 마세요.
- 이름 대신 비가역 토큰만 DB에 저장합니다. 화면에는 개별 표가 아닌 합계만 표시합니다.
- 이는 코드 기반 가명 처리입니다. 서버 관리자에 대한 완전한 익명성은 보장하지 않습니다.
- 코드 공유 시 대리 투표를 막을 수 없습니다. 6개 코드는 모든 가족 방에서 공통 사용됩니다.
- FAMILY_PEPPER와 투표 코드는 운영 중 바꾸지 마세요. 기존 방/투표에 영향을 줍니다.
- 가족만 아는 긴 방 암호를 사용하세요. 방 암호를 아는 사람은 일정·댓글 열람과 일정 수정이 가능합니다.
- 주소·댓글·일정은 DB 운영자가 볼 수 있습니다. 민감한 집 주소 대신 근처 공공장소를 권장합니다.
""")
    st.code('''KAKAO_REST_KEY = "카카오_장소검색_REST키"
KAKAO_MOBILITY_KEY = "자동차_길찾기_REST키"
SUPABASE_URL = "https://내프로젝트.supabase.co"
SUPABASE_SERVICE_ROLE_KEY = "서버전용_service_role키"
FAMILY_PEPPER = "충분히_긴_무작위_비밀문자열"
VOTE_CODES = ["코드1", "코드2", "코드3", "코드4", "코드5", "코드6"]''', language="toml")
    if st.button("설정용 무작위 코드 6개와 비밀문자열 만들기"):
        st.code('VOTE_CODES = ' + str([secrets.token_hex(5) for _ in range(6)]).replace("'", '"') + '\nFAMILY_PEPPER = "' + secrets.token_hex(32) + '"', language="toml")
        st.warning("화면을 공유하지 말고 Secrets에 보관하세요. 코드는 가족에게 하나씩만 배포하세요.")
    st.code(SQL, language="sql")
    st.caption("자동차 API: https://apis-navi.kakaomobility.com/v1/directions · 장소 API: https://dapi.kakao.com/v2/local/search/keyword.json")

@st.cache_resource
def database(url, key):
    return create_client(url, key)

@st.cache_data(ttl=600, show_spinner=False)
def api_get(url, key, params):
    try:
        res = requests.get(url, headers={"Authorization": f"KakaoAK {key}"}, params=params, timeout=20)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as exc:
        raise RuntimeError("카카오 요청 실패: 권한·키·쿼터 또는 네트워크를 확인하세요. " + (f"HTTP {exc.response.status_code}" if exc.response is not None else "연결 오류")) from None

def search_place(query, x=None, y=None, radius=2000):
    params = {"query": query, "size": 10}
    if x is not None:
        params.update(x=x, y=y, radius=radius, sort="distance")
    return api_get("https://dapi.kakao.com/v2/local/search/keyword.json", cfg("KAKAO_REST_KEY"), params).get("documents", [])

def driving(a, b):
    if a["id"] == b["id"]:
        return {"duration": 0, "distance": 0}
    data = api_get("https://apis-navi.kakaomobility.com/v1/directions", cfg("KAKAO_MOBILITY_KEY"),
                   {"origin": f'{a["x"]},{a["y"]}', "destination": f'{b["x"]},{b["y"]}', "priority": "RECOMMEND"})
    routes = data.get("routes", [])
    if not routes or routes[0].get("result_code") != 0:
        raise RuntimeError("자동차 경로를 찾지 못했습니다: " + str(routes[0].get("result_msg", "경로 없음") if routes else "응답 없음"))
    return routes[0]["summary"]

def total_route(points):
    legs = [driving(a, b) for a, b in zip(points, points[1:])]
    return sum(v["duration"] for v in legs), sum(v["distance"] for v in legs), legs

def dist(a, b):
    lat1, lat2 = math.radians(float(a["y"])), math.radians(float(b["y"]))
    dlat = lat2-lat1
    dlng = math.radians(float(b["x"])-float(a["x"]))
    return 6371*2*math.asin(min(1, math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlng/2)**2)))

def best_spatial_order(points, fixed_end):
    if len(points) <= 2:
        return points
    middle = points[1:-1] if fixed_end else points[1:]
    end = [points[-1]] if fixed_end else []
    # 최대 6곳: 직선거리 기준 전수 비교 후, 실제 자동차 경로로 원안과 비교합니다.
    candidates = ([points[0]] + list(p) + end for p in itertools.permutations(middle))
    return min(candidates, key=lambda p: sum(dist(a,b) for a,b in zip(p,p[1:])))

def map_link(p):
    return f'https://map.kakao.com/link/map/{p["id"]}'

def draw_points(points):
    import pandas as pd
    st.map(pd.DataFrame([{"lat":float(p["y"]), "lon":float(p["x"])} for p in points]))
    st.caption("지도는 위치 확인용입니다. 상세 정보와 길찾기는 각 장소의 카카오맵 링크를 이용하세요.")

# DB 미설정이어도 안내와 예시를 볼 수 있습니다.
ready = bool(cfg("SUPABASE_URL") and cfg("SUPABASE_SERVICE_ROLE_KEY") and len(cfg("FAMILY_PEPPER")) >= 20)
db = None
if ready:
    try:
        db = database(cfg("SUPABASE_URL"), cfg("SUPABASE_SERVICE_ROLE_KEY"))
    except Exception:
        st.error("공유 DB 연결 설정을 확인해주세요. 키나 상세 내부 오류는 화면에 표시하지 않습니다.")
with st.expander("🏡 가족 비밀방 — 여기를 눌러 입장", expanded=True):
    st.subheader("가족끼리 같은 방 이름과 암호를 입력해요")
    room_name = st.text_input("방 이름", value="우리 가족")
    password = st.text_input("가족만 아는 방 암호 (12자 이상)", type="password")
    st.caption("6명: 아빠 · 엄마 · 오빠 · 언니1 · 언니2 · 나")
    st.info("새로고침 버튼으로 다른 가족의 투표·댓글을 불러와요.")
    st.button("🔄 새로고침")

if not db or len(password) < 12 or not room_name.strip():
    st.info("설정 안내를 마친 뒤 위의 가족 비밀방에 방 이름과 12자 이상 방 암호를 입력하세요.")
    st.subheader("✨ 이렇게 사용해요")
    st.markdown("**일정 만들기 → 자동차 이동 비교 → 익명 체력 투표 → 근처 플랜 B → 계획자 칭찬**")
    st.warning("현재는 안내 화면입니다. 실제 장소·이동 시간·투표 결과를 예시 숫자로 대신 표시하지 않습니다.")
    st.stop()

room = hmac.new(cfg("FAMILY_PEPPER").encode(), (room_name.strip()+"\0"+password).encode(), hashlib.sha256).hexdigest()

def token(code):
    return hmac.new(cfg("FAMILY_PEPPER").encode(), (room+"\0"+code).encode(), hashlib.sha256).hexdigest()

def load_plan():
    result = db.table("family_plans").select("payload").eq("room", room).execute().data
    return result[0]["payload"] if result else None

try:
    plan = load_plan()
except Exception:
    st.error("DB를 읽지 못했어요. SQL 실행 여부, 키와 프로젝트 활성 상태를 확인하세요.")
    st.stop()

t1,t2,t3,t4 = st.tabs(["🗓 일정·동선", "🪁 근처 플랜 B", "🗳 익명 체력 투표", "💌 칭찬 우체통"])
with t1:
    st.subheader("오늘의 여행을 함께 정해요")
    st.caption("출발지 포함 최대 6곳. 첫 장소는 고정하고 나머지 순서의 개선안을 비교합니다.")
    day = st.date_input("여행 날짜", date.fromisoformat(plan["date"]) if plan else date.today())
    planner = st.text_input("이번 계획을 짠 사람", value=plan.get("planner", "아빠") if plan else "아빠", max_chars=30)
    if "draft_room" not in st.session_state or st.session_state.draft_room != room:
        st.session_state.draft_room = room
        st.session_state.draft_points = list(plan.get("points", [])) if plan else []
    if cfg("KAKAO_REST_KEY"):
        query = st.text_input("지역+장소 이름 검색", placeholder="예: 수원 화성행궁")
        if st.button("장소 검색", disabled=not query.strip()):
            try:
                st.session_state.search_results = search_place(query.strip())
                if not st.session_state.search_results:
                    st.warning("검색 결과가 없어요. 지역명을 함께 입력해보세요.")
            except RuntimeError as e:
                st.error(str(e))
        results = st.session_state.get("search_results", [])
        if results:
            idx = st.selectbox("검색 결과 — 주소를 꼭 확인하세요", range(len(results)), format_func=lambda i: results[i]["place_name"]+" · "+results[i].get("road_address_name", results[i].get("address_name", "")))
            if st.button("일정에 추가", disabled=len(st.session_state.draft_points)>=6):
                p = results[idx]
                if any(v["id"]==p["id"] for v in st.session_state.draft_points):
                    st.warning("이미 추가한 장소예요.")
                else:
                    st.session_state.draft_points.append(p)
    else:
        st.warning("장소 검색을 사용하려면 KAKAO_REST_KEY를 설정하세요.")
    points = st.session_state.draft_points
    for i,p in enumerate(points):
        cols = st.columns([6,1])
        cols[0].markdown(f'**{i+1}. {p["place_name"]}** · [카카오맵]({map_link(p)})')
        if cols[1].button("삭제", key=f"del_{i}"):
            points.pop(i)
            st.rerun()
    end_mode = st.radio("마지막 장소는 어떻게 할까요?", ["🏠 마지막 장소 고정 — 귀가 지점 등", "🔀 마지막 장소도 순서 변경 가능"], index=0)
    fixed_end = end_mode.startswith("🏠")
    st.caption("식사 예약처럼 시간이 정해진 중간 일정이 있다면 개선 순서를 바로 적용하지 말고 직접 확인하세요. 체류 시간은 이동 시간에 포함되지 않습니다.")
    if st.button("💾 가족 일정 저장", disabled=not points):
        payload = {"date":str(day),"planner":planner.strip() or "계획자", "points":points}
        try:
            db.table("family_plans").upsert({"room":room,"payload":payload}, on_conflict="room").execute()
            st.success("공유 일정이 저장됐어요. 다른 가족은 새로고침하면 볼 수 있어요.")
            plan=payload
        except Exception:
            st.error("일정 저장에 실패했어요. DB 상태를 확인하고 다시 시도하세요.")
    if len(points)>=2 and st.button("🚗 원래 동선과 개선 동선 비교"):
        if not cfg("KAKAO_MOBILITY_KEY"):
            st.warning("KAKAO_MOBILITY_KEY를 설정해야 실제 자동차 시간을 조회할 수 있어요.")
        else:
            try:
                with st.spinner("자동차 경로를 조회하고 있어요…"):
                    original = total_route(points)
                    candidate = best_spatial_order(points, fixed_end)
                    improved = total_route(candidate)
                chosen, stats = (candidate, improved) if improved[0]<original[0] else (points, original)
                c1,c2,c3=st.columns(3)
                c1.metric("원안 이동 시간", f"{math.ceil(original[0]/60)}분")
                c2.metric("제안 이동 시간", f"{math.ceil(stats[0]/60)}분")
                c3.metric("총 주행거리", f"{stats[1]/1000:.1f} km")
                st.markdown(" → ".join(p["place_name"] for p in chosen))
                for a,b,leg in zip(chosen,chosen[1:],stats[2]):
                    st.write(f'{a["place_name"]} → {b["place_name"]}: 약 {math.ceil(leg["duration"]/60)}분 / {leg["distance"]/1000:.1f}km')
                draw_points(chosen)
                st.caption("직선거리로 순서 후보를 만든 뒤 카카오 자동차 예상 시간으로 원안과 비교한 휴리스틱입니다. 전역 최적 경로는 보장하지 않습니다. 실시간 조회 기준이며 여행 날짜의 교통 예측·주차·도보·체류 시간은 제외합니다. 응답은 10분간 캐시됩니다.")
            except RuntimeError as e:
                st.error(str(e))

with t2:
    st.subheader("🪁 지치면 가까운 곳에서 가볍게")
    if not plan or not plan.get("points"):
        st.info("먼저 가족 일정을 저장해주세요.")
    else:
        ps=plan["points"]
        anchor=st.selectbox("현재 있는 장소", ps, format_func=lambda p:p["place_name"])
        mood=st.radio("어떤 플랜 B가 좋을까요?",["앉아서 쉬기", "실내에서 놀기", "가볍게 산책"],horizontal=False)
        radius=st.slider("검색 반경 (직선거리)",500,5000,2000,500)
        st.caption("영업시간·주차·계단·요금·실제 좌석 여부는 카카오맵이나 전화로 확인하세요. 가까운 곳도 걷는 거리가 길 수 있어요.")
        if st.button("근처 플랜 B 찾기"):
            if not cfg("KAKAO_REST_KEY"):
                st.error("카카오 장소 검색 키가 필요해요.")
            else:
                keywords={"앉아서 쉬기":["카페","보드게임카페"],"실내에서 놀기":["보드게임카페","오락실"],"가볍게 산책":["공원","산책"]}[mood]
                try:
                    found={}
                    for kw in keywords:
                        for p in search_place(kw,anchor["x"],anchor["y"],radius):
                            if p["id"] != anchor["id"]:
                                found[p["id"]]=p
                    candidates=sorted(found.values(),key=lambda p:float(p.get("distance") or 1e9))[:5]
                    if not candidates:
                        st.info("검색 결과가 없어요. 반경이나 활동을 바꿔보세요.")
                    for p in candidates:
                        with st.container(border=True):
                            st.markdown(f'### {p["place_name"]}')
                            st.write(p.get("road_address_name") or p.get("address_name"))
                            st.write(f'직선거리 약 {p.get("distance", "?")}m · {p.get("category_name", "")}')
                            if cfg("KAKAO_MOBILITY_KEY"):
                                try:
                                    leg=driving(anchor,p)
                                    st.write(f'🚗 약 {math.ceil(leg["duration"]/60)}분 · {leg["distance"]/1000:.1f}km')
                                except RuntimeError as e:
                                    st.warning(str(e))
                            st.link_button("카카오맵에서 확인",map_link(p))
                    st.info("🎲 가족 미션: 카페에서는 ‘오늘 고마웠던 순간’ 한 가지씩 말하기, 보드게임은 20분 한 판, 산책은 사진 세 장만 찍고 돌아오기!")
                except RuntimeError as e:
                    st.error(str(e))

with t3:
    st.subheader("🗳 이름 없이 지금 체력 알려주기")
    st.caption("4명 이상 ‘지쳤어요’면 플랜 B 전환 신호! 미투표는 피로 표에 포함하지 않습니다.")
    if not plan:
        st.info("먼저 일정을 저장해주세요.")
    else:
        round_name=st.selectbox("투표 시점 — 가족 모두 같은 시점을 선택하세요",["출발 전","식사 후","오후 활동 후","저녁 전"])
        poll=plan["date"]+"|"+round_name
        try:
            rows=db.table("family_votes").select("tired").eq("room",room).eq("poll",poll).execute().data
            tired=sum(1 for r in rows if r["tired"])
            a,b=st.columns(2)
            a.metric("참여",f"{len(rows)} / 6명")
            b.metric("지쳤어요",f"{tired}명")
            st.progress(min(tired/6,1))
            if tired>=4:
                st.warning("🍀 과반수가 지쳤어요. 원래 계획을 강행하기보다 ‘근처 플랜 B’에서 편한 대안을 골라보세요!")
            else:
                st.info("아직 4명 미만이에요. 투표와 별개로 한 명이라도 힘들면 쉬어가도 괜찮아요.")
        except Exception:
            st.error("투표 결과를 불러오지 못했어요. DB 설정을 확인하세요.")
        try:
            codes=[str(v) for v in st.secrets.get("VOTE_CODES",[])]
        except Exception:
            codes=[]
        valid_codes=len(codes)==6 and len(set(codes))==6 and all(len(v)>=8 for v in codes)
        if not valid_codes:
            st.warning("서로 다른 8자 이상 투표 코드 6개를 Secrets에 설정해야 투표할 수 있어요.")
        with st.form("vote", clear_on_submit=True):
            code=st.text_input("나만의 익명 투표 코드",type="password")
            choice=st.radio("지금 체력은?",["😴 지쳤어요 — 쉬고 싶어요","🙂 아직 괜찮아요"])
            submitted=st.form_submit_button("익명으로 투표 / 내 표 변경",disabled=not valid_codes)
        if submitted:
            if not any(hmac.compare_digest(code,v) for v in codes):
                st.error("투표 코드를 확인해주세요.")
            else:
                try:
                    db.table("family_votes").upsert({"room":room,"poll":poll,"voter":token(code),"tired":choice.startswith("😴")},on_conflict="room,poll,voter").execute()
                    st.rerun()
                except Exception:
                    st.error("투표 저장에 실패했어요. 다시 시도해주세요.")
        st.caption("같은 날짜·투표 시점에서는 코드당 한 표만 저장됩니다. 다시 투표하면 이전 표를 변경합니다. 새 투표를 시작하려면 다른 시점을 선택하세요. 투표 시점을 바꾸면 집계도 바뀝니다.")

with t4:
    st.subheader("💌 계획해준 마음에 고마움을")
    if plan:
        st.info(f'이번 계획자: {plan.get("planner", "우리 가족")} · “같이 갈 곳을 고민해줘서 고마워!”')
    with st.form("praise",clear_on_submit=True):
        nickname=st.text_input("보내는 이름 / 별명 (익명도 가능)",value="익명의 가족",max_chars=30)
        body=st.text_area("고마운 마음 한 줄",placeholder="아빠, 우리가 좋아할 곳 찾아줘서 고마워!",max_chars=500)
        send=st.form_submit_button("칭찬 보내기 💚")
    if send:
        if not body.strip():
            st.warning("칭찬을 한 줄 적어주세요.")
        else:
            try:
                db.table("family_praise").insert({"room":room,"nickname":nickname.strip() or "익명의 가족","body":body.strip()}).execute()
                st.success("마음이 전달됐어요!")
            except Exception:
                st.error("댓글 저장에 실패했어요. DB 상태를 확인하세요.")
    try:
        comments=db.table("family_praise").select("nickname,body,created_at").eq("room",room).order("created_at",desc=True).limit(50).execute().data
        for comment in comments:
            with st.container(border=True):
                st.text(comment["nickname"]+" · "+comment["created_at"][:10])
                st.text(comment["body"])
        if not comments:
            st.caption("첫 번째 칭찬을 남겨보세요.")
    except Exception:
        st.error("칭찬을 불러오지 못했어요.")
    st.caption("최근 50개를 표시합니다. 삭제·전체 정리는 Supabase Table Editor에서 운영자가 할 수 있어요.")
