"""Lotin <-> kirill transliteratsiya va qidiruv uchun normalizatsiya."""
import re

# o‘ / g‘ uchun ʻ, tutuq belgisi uchun ʼ
_APOS = "‘’ʻʼ`´'"


def normalize_apostrophes(text: str) -> str:
    out = []
    for i, ch in enumerate(text):
        if ch in _APOS:
            prev = text[i - 1].lower() if i else ""
            out.append("ʻ" if prev in ("o", "g") else "ʼ")
        else:
            out.append(ch)
    return "".join(out)


_LAT2CYR_2 = {
    "oʻ": "ў", "gʻ": "ғ", "sh": "ш", "ch": "ч", "zh": "ж", "kh": "х",
    "ya": "я", "yu": "ю", "yo": "ё", "ye": "е",
}
_LAT2CYR_1 = {
    "a": "а", "b": "б", "c": "ц", "d": "д", "e": "е", "f": "ф", "g": "г",
    "h": "ҳ", "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н",
    "o": "о", "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у",
    "v": "в", "w": "в", "x": "х", "y": "й", "z": "з", "ʼ": "ъ",
}


def lat2cyr(text: str) -> str:
    text = normalize_apostrophes(text)
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        two = text[i:i + 2].lower()
        if two in _LAT2CYR_2:
            m, step = _LAT2CYR_2[two], 2
        elif ch.lower() in _LAT2CYR_1:
            m, step = _LAT2CYR_1[ch.lower()], 1
            word_start = i == 0 or not text[i - 1].isalpha()
            if ch.lower() == "e" and word_start:
                m = "э"
        else:
            m, step = ch, 1
        out.append(m.upper() if ch.isupper() else m)
        i += step
    return "".join(out)


def has_latin(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]", text))


_CYR2LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "",
    "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q",
    "ғ": "g", "ҳ": "h",
}
# Bir xil tovushning turlicha yozilishini bitta shaklga keltiramiz
_FUZZY = [
    ("kh", "h"), ("x", "h"), ("q", "k"), ("dj", "j"), ("zh", "j"),
    ("ye", "e"), ("yo", "o"), ("iy", "i"), ("w", "v"),
]


def search_key(text: str) -> str:
    """Lotin va kirillda yozilgan matnni bir xil kalitga aylantiradi.

    "Хамраев", "Xamrayev", "hamraev" -> "hamraev"
    """
    s = "".join(_CYR2LAT.get(c, c) for c in text.lower())
    s = re.sub(r"[^a-z ]", "", s)
    for a, b in _FUZZY:
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    return " ".join(s.split())


def matches(query: str, key: str) -> bool:
    words = search_key(query).split()
    return bool(words) and all(w in key for w in words)
