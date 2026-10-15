"""사내 문의 분류·배정 (실습용 가상 앱)."""

RULES = [
    ("보안", ["해킹", "피싱", "유출", "보안"]),
    ("IT", ["비밀번호", "노트북", "VPN", "메일"]),
    ("구매", ["구매", "납품", "견적", "환불"]),
    ("인사", ["휴가", "급여", "연차"]),
]
TEAMS = {"보안": "정보보안팀", "IT": "IT 헬프데스크", "구매": "구매팀", "인사": "인사팀", "기타": "총무팀"}
HUMAN_WORDS = ["환불", "징계", "사고"]


def classify(text):
    """규칙 순서대로 처음 맞는 분야. 대소문자는 가리지 않는다."""
    t = text.lower()
    for label, words in RULES:
        if any(w in t for w in words):
            return label
    return "기타"


def route(text):
    intent = classify(text)
    return {"intent": intent, "team": TEAMS[intent],
            "needs_human": any(w in text for w in HUMAN_WORDS)}
