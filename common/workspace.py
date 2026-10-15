"""실험용 작업 폴더 만들기 — 내 PC 의 다른 CLAUDE.md·git 정보가 섞이지 않게 임시 폴더에서 돌린다.

폴더는 <임시 폴더>/labs-ws/<이름> 에 매번 새로 만든다. 경로가 출력되므로 직접 들어가서
`claude` 를 켜고 /context 로 들여다볼 수 있다.
"""
import shutil
import tempfile
from pathlib import Path

from common.data import DATA

BASE = Path(tempfile.gettempdir()) / "labs-ws"


def build(name, *, copy=None, write=None, track=None):
    """copy: {폴더 안 경로: 원본 파일·폴더}, write: {폴더 안 경로: 내용}, track: 근거 자료를 data/ 로 복사.

    근거 자료는 정답이 없는 것만 넣는다 — 판교는 kb/, 포항은 price_table.csv.
    """
    ws = BASE / name
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    for rel, src in (copy or {}).items():
        dst, src = ws / rel, Path(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy(src, dst)
    for rel, text in (write or {}).items():
        dst = ws / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
    if track == "pangyo":
        shutil.copytree(DATA / "pangyo" / "kb", ws / "data" / "kb")
    elif track == "pohang":
        (ws / "data").mkdir(exist_ok=True)
        shutil.copy(DATA / "pohang" / "price_table.csv", ws / "data" / "price_table.csv")
    return ws
