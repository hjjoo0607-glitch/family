"""우리 사이, 번역기 💌 — 외부 API 없는 한 기기 공동 사용 버전
실행: pip install -r requirements.txt → streamlit run app.py
Python 3.11 이상 권장. Secrets, 로그인, 데이터베이스는 필요하지 않습니다.
이 프로그램은 외부 AI/이미지/폰트/저장 서비스에 요청하지 않습니다.
Streamlit Cloud 배포 시 코드는 Streamlit 서버에서 실행됩니다.
'세션 저장'은 현재 브라우저 연결에 대응하는 서버 메모리를 뜻합니다.
"""
import html
import re
import unicodedata
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

st.set_page_config(page_title="우리 사이, 번역기 💌", page_icon="💌", layout="centered")
MAX_CHARS = 500
EMOJIS = ["🐱", "🐶", "🐰", "🐻", "🦊", "🐼", "🐸", "🐧", "🐣", "🍓", "🍑", "🍊", "🍎", "🥝", "🍇"]
# 가족을 따로 등록하지 않고 아래 여섯 명을 항상 사용합니다.
FIXED_FAMILY = [
    {"id": "dad", "name": "아빠", "emoji": "🐻"},
    {"id": "mom", "name": "엄마", "emoji": "🌷"},
    {"id": "brother", "name": "오빠", "emoji": "🐶"},
    {"id": "sister1", "name": "언니 1", "emoji": "🐰"},
    {"id": "sister2", "name": "언니 2", "emoji": "🐱"},
    {"id": "jooyoung", "name": "주영", "emoji": "🐣"},
]
ALL = "__all__"
REACTIONS = [("read", "👀 읽었어요"), ("understand", "💛 이해해요"), ("talk", "💬 이야기해요")]
AI_NOTICE = "AI가 아닌 규칙 기반 표현 도우미입니다. 보내기 전에 뜻이 맞는지 확인해 주세요."
SESSION_NOTICE = "기록은 현재 사용 중인 세션에서만 유지되며, 새로고침이나 접속 종료 등으로 사라질 수 있어요."
SHARED_NOTICE = "가족이 한 기기를 함께 사용하는 앱이므로 작성 화면의 원문을 다른 사람이 볼 수 있어요. 전송 후 편지함 화면을 보여 주세요."
UNSUPPORTED = "이 문장은 자동으로 바꾸기 어려워요. 아래 틀로 직접 다듬어 보세요."
SAFETY_NOTICE = ("위협이나 폭력 관련 표현은 다정한 말로 포장하지 않아요. 자동 변환을 중단했어요. "
                 "지금 위험하다면 먼저 안전한 곳으로 이동하고 믿을 만한 어른이나 112·119에 도움을 요청하세요. "
                 "이 앱의 규칙만으로 모든 위험 표현을 판별할 수는 없어요.")

# 구체적인 문장 전체부터 확인합니다. re.fullmatch를 사용하므로 일부 단어가
# 우연히 들어 있다는 이유로 나머지 요청·거절·이유를 지워 버리지 않습니다.
# 여기에 (상황 이름, 정규식, 결과 문장)을 추가하면 표현 사전을 확장할 수 있습니다.
RULES = [
    ("설거지", r"설거지(?:를)?\s*(?:좀\s*)?(?:해|해줘|해\s*줘|해라)", "설거지 좀 도와줄 수 있어?"),
    ("쓰레기", r"쓰레기(?:를)?\s*(?:좀\s*)?(?:버려|버려줘|버려\s*줘|버려라)", "쓰레기 버리는 것 좀 부탁해도 될까?"),
    ("청소", r"청소(?:를)?\s*(?:좀\s*)?(?:해|해줘|해\s*줘|해라)", "청소 좀 해줄 수 있어?"),
    ("빨래 널기", r"빨래(?:를)?\s*(?:좀\s*)?(?:널어|널어줘|널어\s*줘|널어라)", "빨래 좀 널어줄 수 있어?"),
    ("빨래 개기", r"빨래(?:를)?\s*(?:좀\s*)?(?:개|개줘|개\s*줘|개라)", "빨래 좀 개줄 수 있어?"),
    ("식탁", r"식탁(?:을)?\s*(?:좀\s*)?(?:닦아|닦아줘|닦아\s*줘|닦아라)", "식탁 좀 닦아줄 수 있어?"),
    ("TV 소리", r"(?:tv|티비|텔레비전)\s*소리(?:를)?\s*(?:좀\s*)?(?:줄여|줄여줘|줄여\s*줘|줄여라)", "TV 소리를 조금만 줄여줄 수 있어?"),
    ("음악 소리", r"음악\s*소리(?:를)?\s*(?:좀\s*)?(?:줄여|줄여줘|줄여\s*줘|줄여라)", "음악 소리를 조금만 줄여줄 수 있어?"),
    ("목소리", r"목소리(?:를)?\s*(?:좀\s*)?(?:낮춰|낮춰줘|낮춰\s*줘|낮춰라)", "목소리를 조금만 낮춰줄 수 있어?"),
    ("소음", r"(?:시끄럽게\s*하지\s*마|조용히\s*(?:좀\s*)?해)", "조금만 조용히 해줄 수 있어?"),
    # '마음대로'가 있는 대표 상황은 요청한 예시대로 노크 요청으로 바꿉니다.
    # 무조건 출입 금지를 뜻하는 다음 규칙과는 구분하여 경계를 유지합니다.
    ("개인 공간: 무단 출입", r"내\s*방에\s*마음대로\s*들어오지\s*마", "내 방에 들어오기 전에 먼저 노크해 줬으면 좋겠어."),
    ("개인 공간: 출입 거절", r"내\s*방에\s*들어오지\s*마", "내 방에는 들어오지 말아 줘."),
    ("노크", r"(?:내\s*방에\s*)?들어오기\s*전에\s*(?:먼저\s*)?노크(?:\s*좀)?\s*(?:해|해줘|해\s*줘)", "들어오기 전에 먼저 노크해 줬으면 좋겠어."),
    ("물건: 허락", r"내\s*물건(?:을)?\s*(?:마음대로|허락\s*없이)\s*(?:쓰지|사용하지)\s*마", "내 물건을 허락 없이 쓰지 말아 줘."),
    ("물건: 무단 접촉 거절", r"내\s*물건(?:을)?\s*마음대로\s*만지지\s*마", "내 물건은 마음대로 만지지 말아 줘."),
    ("물건: 만지기 거절", r"내\s*물건(?:을)?\s*만지지\s*마", "내 물건은 만지지 말아 줘."),
    ("물건: 무단 가져가기 거절", r"내\s*물건(?:을)?\s*마음대로\s*가져가지\s*마", "내 물건은 마음대로 가져가지 말아 줘."),
    ("물건: 가져가기 거절", r"내\s*물건(?:을)?\s*가져가지\s*마", "내 물건은 가져가지 말아 줘."),
    ("물건: 사용 거절", r"내\s*물건(?:을)?\s*쓰지\s*마", "내 물건은 쓰지 말아 줘."),
    ("물건 빌리기", r"충전기(?:를)?\s*(?:좀\s*)?(?:빌려줘|빌려\s*줘)", "충전기 좀 빌려줄 수 있어?"),
    ("물건 빌리기", r"우산(?:을)?\s*(?:좀\s*)?(?:빌려줘|빌려\s*줘)", "우산 좀 빌려줄 수 있어?"),
    ("물건 돌려받기", r"내\s*물건(?:을)?\s*(?:좀\s*)?(?:돌려줘|돌려\s*줘)", "내 물건 좀 돌려줄 수 있어?"),
    ("정리 정돈", r"네\s*물건(?:을)?\s*(?:좀\s*)?(?:치워|치워줘|치워\s*줘|치워라)", "네 물건 좀 정리해 줄 수 있어?"),
    ("정리 정돈", r"네\s*방(?:을)?\s*(?:좀\s*)?(?:치워|치워줘|치워\s*줘|치워라)", "네 방 정리 좀 해줄 수 있어?"),
    ("정리 정돈", r"방(?:을)?\s*(?:좀\s*)?(?:치워|치워줘|치워\s*줘|치워라)", "방 정리 좀 해줄 수 있어?"),
    ("정리 정돈", r"장난감(?:을)?\s*(?:좀\s*)?(?:치워|치워줘|치워\s*줘|치워라)", "장난감 좀 정리해 줄 수 있어?"),
    ("정리 정돈", r"신발(?:을)?\s*(?:좀\s*)?(?:정리해|정리해줘|정리해\s*줘)", "신발 좀 정리해 줄 수 있어?"),
    ("약속 시간", r"(?:약속\s*시간에\s*)?늦지\s*마", "늦지 않게 와 줬으면 좋겠어."),
    ("약속 시간", r"(?:약속\s*)?시간(?:을|은)?\s*(?:좀\s*)?(?:지켜|지켜줘|지켜\s*줘|지켜라)", "약속 시간을 지켜줬으면 좋겠어."),
    ("말 끊기", r"(?:내가\s*말할\s*때\s*)?(?:내\s*)?말(?:을)?\s*끊지\s*마", "내 말을 끊지 말아 줘."),
    ("대화 중 듣기", r"내\s*말(?:을)?\s*(?:좀\s*)?(?:들어|들어줘|들어\s*줘)", "내 말을 좀 들어줄 수 있어?"),
    ("쉬고 싶을 때", r"나\s*(?:좀\s*)?혼자\s*(?:있게\s*해|있게\s*해줘|있게\s*해\s*줘|있을래)", "나 혼자 있게 해 줬으면 좋겠어."),
    ("거절", r"(?:그건\s*)?싫어", "나는 그건 원하지 않아."),
]
COMPILED_RULES = [(label, re.compile(pattern, re.IGNORECASE), result) for label, pattern, result in RULES]

# 이 목록은 안전망의 일부일 뿐입니다. 탐지를 우회하는 표현이나 문맥의 위험을
# 완벽히 알아낼 수 없습니다. 원문·미리 보기·직접 작성 결과·전송 직전 모두 확인합니다.
DANGER_PATTERNS = [
    r"죽(?:여|일|이|고\s*싶|을래|어|었)", r"때리", r"때려", r"때릴", r"때렸", r"때린", r"맞아\s*죽", r"패\s*버", r"패고", r"팬다",
    r"패겠", r"가만(?:히)?\s*안\s*(?:둬|둘)", r"해치", r"해칠", r"폭력", r"폭행", r"협박",
    r"칼로", r"칼(?:을)?\s*(?:들|휘|찌)", r"찌르", r"찌를", r"불(?:을)?\s*질", r"목(?:을)?\s*조",
    r"부숴\s*버", r"자살", r"자해", r"극단적\s*선택", r"성폭력", r"성폭행", r"강간", r"학대",
    r"목숨", r"손찌검", r"발로\s*차", r"주먹", r"맞았", r"맞고\s*있", r"맞을까\s*무서",
]
DANGER_RE = re.compile("|".join(DANGER_PATTERNS), re.IGNORECASE)
HARSH_RE = re.compile(r"씨발|시발|씨빨|ㅅㅂ|병신|ㅂㅅ|개새끼|멍청|바보|닥쳐|꺼져|짜증|한심|미쳤|미친|네\s*탓|니\s*탓|너\s*때문|왜\s*맨날|제발\s*좀")
# 무례한 접두어를 지운 뒤에도 문장 전체가 사전과 맞을 때만 바꿉니다.
PREFIX_RE = re.compile(r"^(?:(?:야|씨발|시발|ㅅㅂ|병신|ㅂㅅ|개새끼|바보야|멍청아)[\s,!，]+)+")


def normalize(text):
    """검색할 때만 띄어쓰기·유니코드를 정규화합니다. 사용자의 원문 자체는 바꾸지 않습니다."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip()


def nickname_key(text):
    return normalize(text).casefold()


def is_danger(text):
    return bool(DANGER_RE.search(normalize(text)))


def soften_text(text):
    """순수 함수: 저장/전송 없이 (상태, 결과, 설명)만 반환해 테스트하기 쉽습니다."""
    if not text.strip():
        return "empty", "", "하고 싶은 말을 먼저 입력해 주세요."
    if len(text) > MAX_CHARS:
        return "unsupported", "", "입력은 500자까지 가능해요."
    if is_danger(text):
        return "danger", "", SAFETY_NOTICE
    # 긴 문장의 일부를 멋대로 바꾸지 않도록 문장 전체를 검사합니다.
    canonical = normalize(text).rstrip(".!?。！？~ ")
    candidate = PREFIX_RE.sub("", canonical)
    for label, pattern, result in COMPILED_RULES:
        if pattern.fullmatch(candidate):
            return "converted", result, f"‘{label}’ 상황의 표현 규칙을 적용했어요."
    # '거절'을 기계적으로 부드럽게 바꾸면 뜻이 뒤집히는 경우가 많으므로
    # 일반적인 문장 어미 치환은 하지 않습니다. 공손한 문장도 명시된 패턴만 유지합니다.
    polite = [
        r".+(?:해|아|어|여|려|춰|워|내|개|봐|줘|줘도|려도|아도|어도)\s*(?:줄\s*수\s*있어|도\s*될까|될까)",
        r".+(?:부탁해|부탁할게|고마워|고마워요|고맙습니다)",
        r".+(?:해|아|어|여|려|줘)\s*줬으면\s*좋겠어",
        r".+지\s*말아\s*줘", r".+말아\s*줬으면\s*좋겠어",
    ]
    if not HARSH_RE.search(canonical) and any(re.fullmatch(p, canonical) for p in polite):
        return "kept", text.strip(), "이미 부드러운 표현이라 그대로 두었어요. 그래도 뜻은 직접 확인해 주세요."
    # 문맥을 추측하지 않고 문장별로 알려진 규칙만 적용합니다.
    # 처리하지 못한 부분은 그대로 유지했다고 명확히 알립니다.
    pieces = re.split(r"(?<=[.!?。！？])\s+|\n+", text.strip())
    changed = False
    outputs = []
    for piece in pieces:
        core = normalize(piece).rstrip(".!?。！？~ ")
        candidate = PREFIX_RE.sub("", core)
        output = piece
        for _label, pattern, result in COMPILED_RULES:
            if pattern.fullmatch(candidate):
                output = result
                changed = True
                break
        outputs.append(output)
    result = " ".join(outputs)
    if len(result) > MAX_CHARS:
        result = text.strip()
        changed = False
    return "converted", result, (
        "알고 있는 표현만 다듬었어요. 처리하지 못한 부분은 그대로 두었으니 뜻을 확인해 주세요."
        if changed else "이 표현은 규칙으로 안전하게 다듬기 어려워 원문을 유지했어요. 아래에서 수정한 뒤 보내 주세요."
    )


def combine_manual(situation, feeling, request):
    """사용자가 실제 적은 문장만 이어 붙입니다. 감정/사과/약속을 만들어 넣지 않습니다."""
    parts = [part.strip() for part in (situation, feeling, request) if part.strip()]
    return "\n".join(parts)


# ------------------------ 사용자별 현재 세션 상태 ------------------------
S = st.session_state


def init_state():
    defaults = {
        "members": [dict(m) for m in FIXED_FAMILY], "messages": [], "original": "", "preview": "", "author": None,
        "recipient": ALL, "draft_source": None, "draft_status": "idle", "draft_note": "",
        "draft_token": str(uuid.uuid4()), "sent_tokens": set(), "reviewed": False,
        "situation": "", "feeling": "", "request": "", "flash": "", "notice": "",
        "delete_id": None, "reset_confirm": False, "processing": False,
        "welcome_done": False,
    }
    for key, value in defaults.items():
        if key not in S:
            S[key] = value


init_state()


def invalidate_preview():
    S.preview = ""
    S.draft_source = None
    S.draft_status = "idle"
    S.draft_note = ""
    S.reviewed = False
    S.draft_token = str(uuid.uuid4())


def source_changed():
    invalidate_preview()
    S.situation = S.feeling = S.request = ""
    S.notice = "원문이 바뀌었어요. 다시 변환해 주세요."


def writer_changed():
    # 공동 기기에서 작성자를 바꾸면 이전 작성자의 작업 내용부터 지웁니다.
    S.original = ""
    S.situation = S.feeling = S.request = ""
    invalidate_preview()
    S.notice = "작성자를 바꿨어요. 새 마음을 적어 주세요."


def recipient_changed():
    # 같은 글이라도 받는 사람이 바뀌면 다시 확인하도록 합니다.
    S.reviewed = False


def preview_changed():
    S.reviewed = False


def manual_changed():
    # 틀의 재료를 고쳤다면 옛 조합을 그대로 보내지 못하게 합니다.
    if S.draft_status == "manual":
        S.preview = ""
        S.draft_source = None
        S.reviewed = False
        S.draft_status = "unsupported"
        S.draft_note = "입력 틀이 바뀌었어요. 다시 문장으로 모아 주세요."


def clear_draft():
    S.original = ""
    S.situation = S.feeling = S.request = ""
    invalidate_preview()
    S.notice = "작성 중인 원문과 미리 보기를 지웠어요."


def convert():
    if S.processing:
        return
    S.processing = True
    try:
        status, result, note = soften_text(S.original)
        S.preview = result
        S.draft_status = status
        S.draft_note = note
        S.draft_source = S.original if result else None
        S.reviewed = False
        S.draft_token = str(uuid.uuid4())
        S.notice = ""
    finally:
        S.processing = False


def make_manual():
    if is_danger(S.original) or any(is_danger(S[k]) for k in ("situation", "feeling", "request")):
        S.preview = ""
        S.draft_status = "danger"
        S.draft_note = SAFETY_NOTICE
        S.draft_source = None
        S.reviewed = False
        return
    result = combine_manual(S.situation, S.feeling, S.request)
    if not result:
        S.notice = "입력 틀 중 하나 이상에 내 문장을 적어 주세요."
        return
    if len(result) > MAX_CHARS:
        S.notice = "합친 문장은 줄바꿈을 포함해 500자까지 가능해요. 조금 줄여 주세요."
        return
    S.preview = result
    S.draft_status = "manual"
    S.draft_note = "직접 적은 내용만 줄바꿈으로 모았어요. 아래에서 자연스럽게 수정해 주세요."
    S.draft_source = S.original
    S.draft_token = str(uuid.uuid4())
    S.reviewed = False
    S.notice = ""


def send_message():
    """최종 문장만 기록합니다. 원문/중간 결과/상황·감정 입력은 저장하지 않습니다."""
    if S.processing:
        return
    S.processing = True
    try:
        final = S.preview.strip()
        member_ids = {m["id"] for m in S.members}
        if S.author not in member_ids or (S.recipient != ALL and S.recipient not in member_ids):
            S.notice = "작성자와 받는 사람을 다시 확인해 주세요."
            return
        if S.draft_source is None or S.draft_source != S.original:
            S.notice = "원문이 바뀌었어요. 먼저 다시 변환해 주세요."
            return
        if not final or len(final) > MAX_CHARS:
            S.notice = "빈 문장은 보낼 수 없어요. 500자 이내의 최종 문장을 확인해 주세요."
            return
        # 수정하면서 위협 표현을 추가하는 경우도 여기서 다시 검사합니다.
        if is_danger(S.original) or is_danger(final):
            S.notice = SAFETY_NOTICE
            return
        if S.draft_token in S.sent_tokens:
            S.notice = "이미 등록한 편지예요."
            return
        author = next(m for m in S.members if m["id"] == S.author)
        recipient = next((m for m in S.members if m["id"] == S.recipient), None)
        token = S.draft_token
        # 메시지 스키마에 원문 필드가 없습니다. 최종 텍스트와 최소 표시 정보만 저장합니다.
        S.messages.append({
            "id": token, "author_id": author["id"], "author_name": author["name"],
            "author_emoji": author["emoji"], "recipient_id": S.recipient,
            "recipient_name": recipient["name"] if recipient else "가족 모두",
            "recipient_emoji": recipient["emoji"] if recipient else "🏡",
            "text": final, "sent_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "reactions": {kind: set() for kind, _ in REACTIONS},
        })
        S.sent_tokens.add(token)
        clear_draft()
        S.notice = ""
        S.flash = "마음이 배달됐어요 💌"
    finally:
        S.processing = False


def react(message_id, kind, member_id):
    if member_id not in {m["id"] for m in S.members}:
        return
    for message in S.messages:
        if message["id"] == message_id and kind in message["reactions"]:
            # 집합(set)은 동일한 가족 ID를 한 번만 저장합니다.
            users = message["reactions"][kind]
            if member_id in users:
                users.remove(member_id)
            else:
                users.add(member_id)
            return


def delete_message(message_id):
    if S.delete_id == message_id:
        S.messages = [m for m in S.messages if m["id"] != message_id]
        S.delete_id = None
        S.notice = "편지를 삭제했어요."


def reset_everything():
    if S.get("reset_confirm"):
        S.clear()
        init_state()
        S.notice = "편지와 작성 내용을 초기화했어요. 가족 여섯 명은 그대로예요."


CSS = """
<style>
:root{color-scheme:light;}
.stApp{background:#FFF9EF;color:#49372F;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
.block-container{max-width:540px;padding:1rem .9rem 3rem;}
[data-testid="stAppViewContainer"]{overflow-x:hidden;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stMainBlockContainer"]{width:100%;}
[data-testid="stRadio"] [role="radiogroup"]{display:flex;flex-wrap:wrap;gap:.45rem;}
[data-testid="stRadio"] [role="radiogroup"]>label{flex:1;min-width:85px;padding:.65rem .35rem;background:#EDF3E6;border-radius:14px;margin:0;justify-content:center;}
h1,h2,h3,p,label,[data-testid="stMarkdownContainer"]{color:#49372F;}
[data-testid="stCaptionContainer"]{color:#69564B;}
.hero{text-align:center;background:#FBE8EA;border-radius:26px;padding:1.2rem .5rem;margin-bottom:1rem;}
.hero h1{font-size:clamp(1.6rem,5vw,2.3rem);margin:.3rem 0;}
.hero p{margin:.5rem 0;}.envelope{font-size:2.6rem;}
.stButton>button,.stFormSubmitButton>button{border-radius:16px;min-height:48px;font-size:1rem;
 background:#FBE3E7;color:#49372F;border:1px solid #B9968D;white-space:normal;}
.stButton>button:hover,.stFormSubmitButton>button:hover{border-color:#78544C;color:#49372F;}
textarea,input{font-size:1rem!important;color:#49372F!important;background:#FFFDFA!important;border-radius:14px!important;}
[data-baseweb="select"]>div{border-radius:14px;background:#FFFDFA;color:#49372F;min-height:46px;}
[data-baseweb="tab-list"]{gap:.3rem;flex-wrap:wrap;height:auto;}
button[data-baseweb="tab"]{white-space:normal;height:auto;min-height:52px;font-size:1rem;flex:1;padding:.5rem;border-radius:14px;}
button[data-baseweb="tab"][aria-selected="true"]{background:#E9F0E2;color:#49372F;}
.bubble{border-radius:22px;background:#EAF1E3;padding:1rem 1.1rem;margin:.6rem 4% .4rem 0;
 border:1px solid #CBD8BE;overflow-wrap:anywhere;}
.bubble.pink{background:#FBE4E8;border-color:#E2BCC5;margin-left:4%;margin-right:0;}
.meta{font-size:.92rem;color:#674E43;margin-bottom:.6rem;}
.message-text{font-size:1.08rem;line-height:1.7;white-space:pre-wrap;}
.family-card{background:#EDF3E6;border-radius:16px;padding:.8rem 1rem;margin:.5rem 0;font-size:1.05rem;}
.step{background:#EDF3E6;border-radius:14px;padding:.8rem;margin:.8rem 0;font-weight:600;}
@media(max-width:480px){.block-container{padding:.8rem .7rem 3rem;}.bubble,.bubble.pink{margin-left:0;margin-right:0;}
button[data-baseweb="tab"]{font-size:.9rem;padding:.5rem .15rem;}.stButton>button{font-size:.92rem;padding:.4rem .3rem;}}
*{animation:none!important;transition:none!important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)
# 시작 화면에서만 본문 영역을 세로·가로 중앙에 배치합니다.
if not S.welcome_done:
    st.markdown("""<style>
    [data-testid="stMain"]{display:flex;flex-direction:column;justify-content:center;min-height:100svh;}
    .block-container{margin:auto;max-width:480px;padding:1.5rem 1rem;}
    .hero{background:transparent;padding:1rem 0;}
    .hero .envelope{font-size:5rem;}
    </style>""", unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="envelope" aria-hidden="true">💌</div>' 
            '<h1>우리 사이, 번역기 💌</h1><p>솔직한 마음은 그대로, 표현은 다정하게</p></div>',
            unsafe_allow_html=True)
# 환영 화면은 현재 세션에서 한 번만 보여 줍니다.
# 시작 버튼을 누르기 전에는 st.stop()으로 아래 가족 설정·작성·편지함을 그리지 않습니다.
# 실제 작업이 없는 가짜 로딩이나 기다림, 외부 이미지, 애니메이션은 넣지 않습니다.
if not S.welcome_done:
    # 첫 화면에는 앱 제목·소개와 시작 버튼만 남깁니다.
    # 필요한 사용·개인정보 안내는 시작 후 본 화면에서 표시합니다.
    st.button("시작하기 💌", key="welcome_start", type="primary",
              use_container_width=True, on_click=lambda:S.update(welcome_done=True))
    st.stop()

# fragment는 본문만 다시 실행합니다. 페이지 전체 재구성을 줄이고 선택 화면을 유지합니다.
# 화면을 옮겨도 작성 위젯의 임시 상태가 정리되지 않도록 키를 유지합니다.
@st.fragment
def main_screen():
    for key in ("original", "preview", "author", "recipient", "reviewed", "situation", "feeling", "request"):
        S[key] = S[key]
    with st.expander("사용 전 안내 · 기록과 개인정보"):
        st.info(AI_NOTICE)
        st.caption("🌱 " + SESSION_NOTICE)
        st.warning(SHARED_NOTICE)
    if S.flash:
        st.success(S.flash)
        S.flash = ""
    if S.notice:
        st.info(S.notice)
        S.notice = ""

    # 선택 화면을 세션에 보관해 버튼을 눌러도 다른 화면으로 돌아가지 않습니다.
    page = st.radio("화면 선택", ["마음 쓰기 ✍️", "가족 편지함 💌", "우리 가족"],
                    key="current_page", horizontal=True, label_visibility="collapsed")

    if page == "우리 가족":
        st.subheader("우리 가족")
        st.caption("우리 가족 여섯 명이에요. 마음 쓰기에서 보내는 가족과 받는 가족을 선택해 주세요.")
        for member in S.members:
            st.markdown(f'<div class="family-card">{html.escape(member["name"])}</div>', unsafe_allow_html=True)
        with st.expander("🧹 전체 기록 초기화"):
            st.warning("보낸 편지, 반응, 작성 중인 원문을 모두 지워요. 가족 여섯 명은 그대로 유지돼요. 되돌릴 수 없어요.")
            st.checkbox("모든 편지와 작성 중인 내용을 삭제한다는 것을 확인했어요.", key="reset_confirm")
            st.button("전체 기록 초기화", disabled=not S.reset_confirm, on_click=reset_everything, use_container_width=True)

    if page == "마음 쓰기 ✍️":
        st.subheader("✍️ 내 마음을 편지로")
        st.caption(AI_NOTICE)
        st.caption("① 입력 → ② 다듬기 → ③ 확인 후 전송")
        st.caption("공동 기기용이에요. 작성자·받는 사람 선택은 표시용이며, 받는 사람이 아닌 가족도 편지함을 볼 수 있어요.")
        if not S.members:
            st.info("가족 목록을 불러오지 못했어요. 전체 기록 초기화를 사용해 주세요.")
        else:
            member_map = {m["id"]: m for m in S.members}
            ids = list(member_map)
            if S.author not in member_map:
                S.author = ids[0]
            if S.recipient != ALL and S.recipient not in member_map:
                S.recipient = ALL

            def member_label(mid):
                return "가족 모두" if mid == ALL else member_map[mid]["name"]

            left, right = st.columns(2)
            left.selectbox("보내는 가족", ids, format_func=member_label, key="author", on_change=writer_changed)
            right.selectbox("받는 가족", [ALL] + ids, format_func=member_label, key="recipient", on_change=recipient_changed)
            st.markdown('<div class="step">① 하고 싶은 말을 적어 주세요</div>',unsafe_allow_html=True)
            st.text_area("원문 · 아직 전송되지 않았어요", key="original", max_chars=MAX_CHARS, height=140,
                         on_change=source_changed, placeholder="예: TV 소리 좀 줄여.")
            st.caption(f"원문 {len(S.original)} / {MAX_CHARS}자")
            st.button("다정하게 바꾸기 🪄", on_click=convert,
                      disabled=not S.original.strip() or S.processing, use_container_width=True)

            if S.draft_status == "danger":
                st.error(SAFETY_NOTICE)
            elif S.draft_status in ("converted", "kept", "manual"):
                st.info(S.draft_note)
            elif S.draft_status == "empty":
                st.warning(S.draft_note)
            elif S.draft_status == "unsupported":
                st.warning(UNSUPPORTED)
                st.caption("일부 단어만 바꾸면 뜻이 달라질 수 있어, 모르는 문장은 자동 변환하지 않아요.")
                if S.draft_note != UNSUPPORTED:
                    st.caption(S.draft_note)

            # 미리 보기가 비어도 직접 수정 칸을 유지하여 지웠다가 다시 쓸 수 있습니다.
            if S.draft_status in ("converted", "kept", "manual") and S.draft_source is not None:
                st.markdown('<div class="step">② 원문과 비교하고, 최종 문장을 고쳐 주세요</div>',unsafe_allow_html=True)
                st.caption("위의 원문과 아래 문장을 비교해 주세요. 앱이 내 뜻을 판단해 주지는 않아요.")
                st.text_area("가족에게 보여 줄 최종 문장 · 직접 수정 가능", key="preview", max_chars=MAX_CHARS,
                             height=140, on_change=preview_changed)
                st.caption(f"최종 문장 {len(S.preview)} / {MAX_CHARS}자")
                current = S.draft_source == S.original
                dangerous = is_danger(S.preview) or is_danger(S.original)
                if not current:
                    st.warning("원문이 바뀌었어요. 다시 변환해 주세요.")
                if dangerous:
                    st.error(SAFETY_NOTICE)
                st.caption("뜻이 맞는지 확인하고, 아래 보내기 버튼을 눌러 주세요.")
                st.markdown('<div class="step">③ 확인한 문장만 보내요</div>',unsafe_allow_html=True)
                st.button("이 마음 보내기 💌", key="send_final", on_click=send_message, use_container_width=True,
                          disabled=S.processing or not current or dangerous or not S.preview.strip())
            st.button("작성 중인 원문·미리 보기 지우기", on_click=clear_draft, use_container_width=True,
                      disabled=not bool(S.original or S.preview or S.situation or S.feeling or S.request))
            st.caption("전송 후 원문과 미리 보기는 초기화돼요. 아래 탭에서 ‘가족 편지함 💌’을 눌러 보여 주세요.")

    if page == "가족 편지함 💌":
        st.subheader("📬 가족에게 도착한 마음")
        st.caption("확인하고 전송한 최종 문장만 표시해요. 원문과 중간 변환 결과는 편지 기록에 넣지 않아요.")
        st.caption("인증 없는 공동 기기용이에요. 누구나 반응할 가족을 선택하거나, 확인 후 편지를 삭제할 수 있어요.")
        if not S.messages:
            st.info("아직 도착한 마음이 없어요. 첫 번째 편지를 보내볼까요? 🐣")
        else:
            member_map = {m["id"]: m for m in S.members}
            reaction_person = st.selectbox("반응할 가족 (본인 인증 아님)", list(member_map),
                                           format_func=lambda mid:member_map[mid]["name"],
                                           key="reaction_person")
            st.caption("같은 가족의 같은 반응은 한 번만 세어요. 선택한 반응을 다시 누르면 취소돼요. ✓는 선택된 반응이에요.")
            # 순서가 같은 시각에도 append 순서를 유지하는 안정 정렬입니다.
            for index, message in enumerate(sorted(S.messages, key=lambda m:m["sent_at"])):
                mid = message["id"]
                sent = datetime.fromisoformat(message["sent_at"]).astimezone(ZoneInfo("Asia/Seoul")).strftime("%Y.%m.%d %H:%M:%S")
                meta = (f'{message["author_name"]} → '
                        f'{message["recipient_name"]}\n{sent} · 한국 시간')
                # 사용자가 입력한 HTML 태그는 실행하지 않고 글자 그대로 보여줍니다.
                st.markdown(f'<div class="bubble {"pink" if index % 2 else ""}">'
                            f'<div class="meta">{html.escape(meta).replace(chr(10), "<br>")}</div>'
                            f'<div class="message-text">{html.escape(message["text"])}</div></div>',unsafe_allow_html=True)
                columns = st.columns(3)
                for column, (kind, label) in zip(columns, REACTIONS):
                    users = message["reactions"][kind]
                    active = reaction_person in users
                    column.button(f'{label} {len(users)}' + (" ✓" if active else ""), key=f"react_{mid}_{kind}",
                                  on_click=react, args=(mid,kind,reaction_person), use_container_width=True)
                st.button("🗑️ 이 편지 삭제", key="ask_delete_" + mid,
                          on_click=lambda target=mid:S.update(delete_id=target))
                if S.delete_id == mid:
                    st.warning("이 편지와 반응을 정말 삭제할까요? 삭제하면 되돌릴 수 없어요.")
                    yes, no = st.columns(2)
                    yes.button("네, 삭제할게요", key="delete_yes_"+mid, on_click=delete_message, args=(mid,), use_container_width=True)
                    no.button("취소", key="delete_no_"+mid, on_click=lambda:S.update(delete_id=None), use_container_width=True)


main_screen()
