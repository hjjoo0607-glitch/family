import streamlit as st

st.set_page_config(
    page_title="5등급제 → 9등급제 성적 로드맵",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 모바일에서 한 화면에 최대한 많이 보이도록 여백과 글자 크기를 줄입니다.
st.markdown(
    """
    <style>
      .block-container {padding-top: .7rem; padding-bottom: .5rem; padding-left: 1rem; padding-right: 1rem;}
      h1 {font-size: 1.55rem !important; margin-bottom: .15rem !important;}
      h2, h3 {font-size: 1.05rem !important; margin-top: .4rem !important; margin-bottom: .2rem !important;}
      [data-testid="stMetric"] {padding: .25rem .4rem;}
      [data-testid="stMetricValue"] {font-size: 1.35rem;}
      div[data-testid="stVerticalBlock"] > div {gap: .35rem;}
      .plan-card {border: 1px solid #e5e7eb; border-radius: 10px; padding: .55rem .65rem; min-height: 6rem;}
      .plan-title {font-weight: 700; margin-bottom: .25rem;}
      .plan-line {font-size: .88rem; line-height: 1.5;}
      .hint {color: #667085; font-size: .78rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

TERMS = ["1학년 1학기", "1학년 2학기", "2학년 1학기", "2학년 2학기", "3학년 1학기", "3학년 2학기"]


def convert_5_to_9(grade):
    """5등급제 평균을 1·3·5·7·9 대응의 선형 근사값으로 변환."""
    return 1.0 + 2.0 * (float(grade) - 1.0)


def make_pattern(average, count, mode):
    """주어진 평균을 유지하면서 모드별 패턴을 1~9 범위에 배분."""
    if count <= 0:
        return []
    if mode == "균등 분배":
        offsets = [0.0] * count
    else:
        # 성적 숫자는 낮을수록 좋음. 점진 상승은 뒤로 갈수록 숫자가 낮아집니다.
        centered = [i - (count - 1) / 2 for i in range(count)]
        if mode == "점진적 상승":
            offsets = [-0.55 * x for x in centered]
        else:  # 초반에 집중하고 뒤에서 여유: 초반 숫자는 낮고 후반 숫자는 높게
            offsets = [0.55 * x for x in centered]

    # 오프셋을 더한 뒤 1~9 범위에 맞추되 전체 평균은 최대한 보존합니다.
    low, high = -20.0, 20.0
    for _ in range(80):
        shift = (low + high) / 2
        values = [min(9.0, max(1.0, average + off + shift)) for off in offsets]
        if sum(values) < average * count:
            low = shift
        else:
            high = shift
    shift = (low + high) / 2
    return [min(9.0, max(1.0, average + off + shift)) for off in offsets]


st.title("🎓 성적 변환 & 목표 로드맵")
st.caption("학기 평균을 입력하면 5등급제 성적을 9등급제로 근사 변환하고, 3학년 1학기까지의 목표를 계산합니다.")

left, right = st.columns([1.1, 1.0], gap="small")
with left:
    completed = st.selectbox(
        "성적이 나온 학기 수",
        options=[1, 2, 3, 4, 5],
        format_func=lambda n: f"{n}개 학기까지 입력",
        index=1,
        help="순서대로 1학년 1학기부터 입력합니다. 최대 3학년 1학기까지 입력할 수 있습니다.",
    )
with right:
    target = st.number_input(
        "최종 목표 평균 (9등급제)",
        min_value=1.0,
        max_value=9.0,
        value=3.0,
        step=0.1,
        format="%.1f",
        help="1등급이 가장 우수합니다. 목표는 남은 학기까지 포함한 전체 학기 평균입니다.",
    )

st.markdown("**현재 학기 평균 (5등급제)**")
input_cols = st.columns(completed, gap="small")
values_5 = []
for i in range(completed):
    with input_cols[i]:
        value = st.number_input(
            TERMS[i], min_value=1.0, max_value=5.0, value=3.0, step=0.1,
            format="%.1f", key=f"grade_{i}",
        )
        values_5.append(value)

converted = [convert_5_to_9(v) for v in values_5]
current_average = sum(converted) / len(converted)
remaining_terms = TERMS[completed:5]  # 3학년 1학기까지, 총 5학기 기준
remaining = len(remaining_terms)
required_total = target * 5 - sum(converted)
required_average = required_total / remaining if remaining else None

st.markdown("---")
st.markdown("**현재 성적 · 9등급제 환산**")
metric_cols = st.columns([1, 1, 2], gap="small")
metric_cols[0].metric("현재 평균", f"{current_average:.2f}등급")
metric_cols[1].metric("최종 목표", f"{target:.1f}등급")
metric_cols[2].markdown(
    "<div class='hint'>학기별 환산: "
    + "　·　".join(f"{TERMS[i]} <b>{converted[i]:.1f}</b>" for i in range(completed))
    + "</div>",
    unsafe_allow_html=True,
)

if remaining == 0:
    st.info("3학년 1학기까지 모든 학기를 입력했습니다. 현재 평균과 목표 평균을 비교해 보세요.")
    if current_average <= target:
        st.success("입력한 현재 평균이 목표 등급 이내입니다.")
    else:
        st.warning("현재 평균이 목표보다 높습니다. 입력값을 확인하거나 목표를 조정해 보세요.")
else:
    st.markdown("**남은 학기 목표 로드맵 (9등급제 환산 평균)**")
    if required_average < 1.0:
        st.error(
            f"목표 달성이 어렵습니다. 남은 학기 평균이 {required_average:.2f}등급이어야 해 1등급만 받아도 목표 평균에 도달하지 못합니다."
        )
        status = "달성 어려움 · 최선의 경우"
        display_avg = 1.0
    elif required_average > 9.0:
        st.success(
            f"현재 성적 기준으로 목표 여유가 있습니다. 남은 학기 평균이 최대 {required_average:.2f}등급이어도 목표 평균 이내입니다."
        )
        status = "목표 달성 여유 · 참고용"
        display_avg = 9.0
    else:
        st.caption(f"남은 {remaining}개 학기에서 필요한 평균: **{required_average:.2f}등급**")
        status = "학기별 권장 등급"
        display_avg = required_average

    modes = ["균등 분배", "점진적 상승", "초반 집중 · 후반 여유 (알잘딱깔센)"]
    mode_cols = st.columns(3, gap="small")
    for col, mode in zip(mode_cols, modes):
        values = make_pattern(display_avg, remaining, mode)
        rows = "<br>".join(
            f"{term.replace('학년 ', '-')} <b>{grade:.1f}등급</b>"
            for term, grade in zip(remaining_terms, values)
        )
        col.markdown(
            f"<div class='plan-card'><div class='plan-title'>{mode}</div>"
            f"<div class='hint'>{status}</div><div class='plan-line'>{rows}</div></div>",
            unsafe_allow_html=True,
        )

st.markdown(
    "<div class='hint'>계산 가정: 5등급제 평균을 1·3·5·7·9등급으로 선형 근사하며, 전체 평균은 학기별 동일 가중치로 계산합니다. "
    "실제 석차등급 환산은 학교·과목별 분포와 반영비율에 따라 달라질 수 있습니다.</div>",
    unsafe_allow_html=True,
)
