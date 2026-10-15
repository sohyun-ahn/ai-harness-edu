"""모델 답변에서 JSON 꺼내기 — 엔진(headless·SDK)과 상관없이 같이 쓴다."""
import json
import re


def extract_json(text):
    """답변 안의 첫 JSON 객체를 꺼낸다. 없거나 깨졌으면 None."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    try:
        return json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
