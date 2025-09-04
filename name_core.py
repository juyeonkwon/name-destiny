from __future__ import annotations
from functools import lru_cache
from typing import List, Tuple

__all__ = [
    "hangul_syllables",
    "name_to_strokes",
    "expand_reduction_steps",
    "fortune_from_last_digit",
    "syllable_stroke_count",
    "interleave_names",
]

# ---------------- Korean decomposition ----------------
CHO = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
JUNG = ["ㅏ","ㅐ","ㅑ","ㅒ","ㅓ","ㅔ","ㅕ","ㅖ","ㅗ","ㅘ","ㅙ","ㅚ","ㅛ","ㅜ","ㅝ","ㅞ","ㅟ","ㅠ","ㅡ","ㅢ","ㅣ"]
JONG = ["","ㄱ","ㄲ","ㄳ","ㄴ","ㄵ","ㄶ","ㄷ","ㄹ","ㄺ","ㄻ","ㄼ","ㄽ","ㄾ","ㄿ","ㅀ","ㅁ","ㅂ","ㅄ","ㅅ","ㅆ","ㅇ","ㅈ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]
JONG_SPLIT = {
    ""   : [], "ㄱ":["ㄱ"], "ㄲ":["ㄲ"], "ㄳ":["ㄱ","ㅅ"], "ㄴ":["ㄴ"], "ㄵ":["ㄴ","ㅈ"], "ㄶ":["ㄴ","ㅎ"],
    "ㄷ":["ㄷ"], "ㄹ":["ㄹ"], "ㄺ":["ㄹ","ㄱ"], "ㄻ":["ㄹ","ㅁ"], "ㄼ":["ㄹ","ㅂ"], "ㄽ":["ㄹ","ㅅ"], "ㄾ":["ㄹ","ㅌ"],
    "ㄿ":["ㄹ","ㅍ"], "ㅀ":["ㄹ","ㅎ"], "ㅁ":["ㅁ"], "ㅂ":["ㅂ"], "ㅄ":["ㅂ","ㅅ"], "ㅅ":["ㅅ"], "ㅆ":["ㅆ"],
    "ㅇ":["ㅇ"], "ㅈ":["ㅈ"], "ㅊ":["ㅊ"], "ㅋ":["ㅋ"], "ㅌ":["ㅌ"], "ㅍ":["ㅍ"], "ㅎ":["ㅎ"]
}

def _is_hangul_syllable(ch: str) -> bool:
    return 0xAC00 <= ord(ch) <= 0xD7A3

def hangul_syllables(text: str) -> List[str]:
    """원문에서 한글 음절만 추출."""
    return [ch for ch in text if _is_hangul_syllable(ch)]

def _decompose_korean_char(ch: str):
    code = ord(ch)
    if not (0xAC00 <= code <= 0xD7A3):
        return "", "", []
    s = code - 0xAC00
    cho  = CHO[s // 588]
    jung = JUNG[(s % 588)//28]
    jong = JONG[s % 28]
    return cho, jung, JONG_SPLIT[jong]

# ---------------- Stroke (획수) ----------------
STROKE_CHO = {
    "ㄱ":2,"ㄲ":4,"ㄴ":2,"ㄷ":3,"ㄸ":6,"ㄹ":5,"ㅁ":4,"ㅂ":4,"ㅃ":8,
    "ㅅ":2,"ㅆ":4,"ㅇ":1,"ㅈ":3,"ㅉ":6,"ㅊ":4,"ㅋ":3,"ㅌ":4,"ㅍ":4,"ㅎ":3
}
STROKE_JUNG = {
    "ㅏ":2,"ㅐ":3,"ㅑ":3,"ㅒ":4,"ㅓ":2,"ㅔ":3,"ㅕ":3,"ㅖ":4,
    "ㅗ":2,"ㅘ":3,"ㅙ":4,"ㅚ":3,"ㅛ":3,"ㅜ":2,"ㅝ":3,"ㅞ":4,"ㅟ":3,
    "ㅠ":3,"ㅡ":1,"ㅢ":2,"ㅣ":1
}
STROKE_JONG = STROKE_CHO  # 종성도 동일 적용

@lru_cache(maxsize=4096)
def syllable_stroke_count(ch: str) -> int:
    """음절의 획수 = 초성+중성(+종성) 합."""
    cho, jung, jongs = _decompose_korean_char(ch)
    if not cho:
        return 0
    s = STROKE_CHO.get(cho, 0) + STROKE_JUNG.get(jung, 0)
    if jongs:
        s += sum(STROKE_JONG.get(j, 0) for j in jongs)
    return s

def name_to_strokes(name: str) -> List[int]:
    """이름의 각 음절을 획수로 변환."""
    syls = hangul_syllables(name)
    return [syllable_stroke_count(ch) for ch in syls]

# ---------------- Sequence reduction ----------------
def interleave_names(name1: str, name2: str) -> str:
    """두 이름을 번갈아가며 합친 문자열."""
    syls1 = hangul_syllables(name1)
    syls2 = hangul_syllables(name2)
    result = []
    for a, b in zip(syls1, syls2):
        result.append(a)
        result.append(b)
    if len(syls1) > len(syls2):
        result.extend(syls1[len(syls2):])
    elif len(syls2) > len(syls1):
        result.extend(syls2[len(syls1):])
    return "".join(result)

def expand_reduction_steps(seq: List[int]) -> List[List[int]]:
    """인접 합을 1의 자리로 줄여 길이 2가 될 때까지 반복."""
    if not seq or len(seq) < 2:
        return [list(seq)] if seq else []
    steps: List[List[int]] = [list(seq)]
    cur = steps[0]
    while len(cur) > 2:
        cur = [ (cur[i] + cur[i+1]) % 10 for i in range(len(cur)-1) ]
        steps.append(cur)
    return steps

# ---------------- Fortune ----------------
def fortune_from_last_digit(d: int) -> Tuple[str, str]:
    """마지막 1자리 숫자 해석 (재미용)."""
    mapping = {
        0: ("A+", "합이 잘 맞는 편. 안정감/루틴 강점."),
        1: ("B",  "에너지 강. 추진력 vs 마찰 관리 필요."),
        2: ("A",  "균형/협업 적합. 상호 배려가 강점."),
        3: ("B+", "아이디어 풍부. 실행 규칙이 관건."),
        4: ("C+", "성향 차 크면 평행선. 규칙 합의 필수."),
        5: ("B",  "변화/활력. 합의된 변화 관리가 핵심."),
        6: ("A",  "성실/책임 조합. 장기전 강함."),
        7: ("B",  "독립성 강. 역할경계 명확히."),
        8: ("A",  "성과지향. 목표 일치 시 상승."),
        9: ("S",  "시너지 최상. 빠른 결속/확장.")
    }
    return mapping.get(int(d) % 10, ("-", "해석 불가"))
