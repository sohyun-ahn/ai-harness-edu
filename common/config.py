# 실습 전체 설정 — 모델 이름과 트랙은 여기서만 바꾼다.
# ※ 모든 회사·인물·데이터는 실습용 가상 자료입니다.

# 기본 트랙: "pangyo" (문의 대응 라우팅) | "pohang" (사양서 추출·견적)
# 실행할 때 --track 으로 덮어쓸 수 있다.
TRACK = "pangyo"

# 반복 실행 기본 횟수 (lab1, lab7)
DEFAULT_N = 5

# ---------------------------------------------------------------- 헤드리스 (기본 엔진)
# Claude Code 실행 파일. PATH 에 없으면 전체 경로를 적는다.
CLAUDE_BIN = "claude"

# --model 에 넘기는 값. 별칭(sonnet·haiku·opus)이면 그 계열의 최신 모델을 쓴다.
# None 이면 Claude Code 기본 모델(계정 설정)을 따른다.
HEADLESS_MODEL = "sonnet"
HEADLESS_CHEAP_MODEL = "haiku"   # 채점·분류처럼 싼 작업

# 헤드리스 한 번의 시간 제한(초)
HEADLESS_TIMEOUT = 600

# ---------------------------------------------------------------- SDK (sdk_optional/ 전용, API 키 필요)
MODEL = "claude-sonnet-5-5"        # 메인 Agent
JUDGE_MODEL = "claude-haiku-5-5"   # 채점·분류
MAX_BUDGET_USD = 0.50              # 한 번 실행 상한. 넘으면 SDK 가 멈춘다.
