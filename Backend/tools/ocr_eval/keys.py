"""Scoring keys derived from eval/ground_truth.md (the reviewed ground truth of the four `Dropped Image*.png` scans).

`score_image(name, text)` returns (found, total, detail). Matching is whitespace/ZWNJ-insensitive, digit-script
insensitive (Persian/Arabic/Latin) and treats '.' and '/' as the same separator (decimal marks differ between scans).
"""

import re

_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def norm(text: str) -> str:
    text = text.translate(_DIGITS).replace("٫", ".").replace("٬", "").replace(",", "").replace("،", "")
    text = text.replace("ك", "ک").replace("ي", "ی").replace("ى", "ی").replace("أ", "ا").replace("إ", "ا")
    text = text.replace(".", "/")
    return re.sub(r"[\s‌‏‎ *|`_\-]", "", text)


def _present(keys: list[str], text: str) -> list[str]:
    haystack = norm(text)
    return [k for k in keys if norm(k) in haystack]


def _lcs(a: list[str], b: list[str]) -> int:
    prev = [0] * (len(b) + 1)
    for x in a:
        cur = [0]
        for j, y in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if x == y else max(prev[j], cur[-1]))
        prev = cur
    return prev[-1]


# ---- image 1 (rotated scan, 11-column table)
K1 = ["104800", "39804", "95400", "5564.79", "20701.3", "15720", "5970.6", "14310", "834.7185", "3105.195",
      "39940.5135", "266270.09", "202-004", "1405/06/09", "1405/3597", "1405/2334", "1405/02/22", "1405/02/06",
      "2+100", "7+000", "9+000", "14+200", "2+600", "2+950", "9+500", "10+900", "18+000", "0.15",
      "رایمند", "محور گستر نصر", "بسترسازی", "نماینده"]

# ---- image 2 (33-row table)
SEQ2 = [1180, 1200, 1155, 1168, 1200, 1200, 1197, 1466, 1333, 978, 1333, 1311, 1333, 1222, 1377, 1177, 1311, 1244,
        1333, 1222, 1177, 1111, 1066, 1200, 1044, 1088, 1266, 1155, 1177, 1277, 1200, 1155, 1155]
KM2 = ["00+300", "00+350", "00+400", "00+450", "00+500", "00+550", "00+600", "1+400", "1+450", "1+500", "1+550",
       "1+600", "1+650", "1+700", "1+750", "1+800", "1+850", "1+950", "2+050", "02+050", "02+100", "02+150",
       "02+200", "02+250", "02+300", "02+350", "02+400", "02+500", "02+600", "2+700", "2+800", "2+900", "03+000"]
K2 = ["1405/3597", "1405/2334", "401-001", "1405/06/15", "18+000", "1212.45", "پریمکت", "قیرمحلولMC"]

# ---- image 3 (Persian digits, two-level table)
K3 = ["990302", "990201", "990303", "990202", "990304", "990301", "990306", "990601", "990602", "990603", "990604",
      "990605", "0/87", "0/71", "0/86", "0/69", "0/77", "0/83", "0/78", "0/75", "0/70", "49/00", "70/00",
      "1404", "3597", "رایمند", "زرند", "باندفرودگاه", "از23ریزمتره", "از24ریزمتره", "از25ریزمتره", "از26ریزمتره",
      "از27ریزمتره", "از28ریزمتره", "از29ریزمتره", "از30ریزمتره"]

# ---- image 4 (low-quality letter); only values the reviewer could read
K4 = ["5476472885657", "1405/06/03", "3597", "رایمند", "زرند", "سیریز", "حاجی", "25درصد", "10درصد", "ماده29",
      "ماده48", "ماده28", "ابنیه", "مطهری", "کوچه36", "پلاک47", "7617899596", "7614634698", "32520830",
      "32222124", "32220049", "تبصره2"]


def score_image(name: str, text: str) -> tuple[int, int, str]:
    if name == "Dropped Image":
        got = _present(K1, text)
        return len(got), len(K1), ""
    if name == "Dropped Image (2)":
        nums = [x for x in re.findall(r"(?<![\d./+])\d{3,4}(?![\d./+])", text.translate(_DIGITS))]
        seq = _lcs([str(x) for x in SEQ2], nums)
        km = len(_present(KM2, text))
        head = len(_present(K2, text))
        return seq + km + head, len(SEQ2) + len(KM2) + len(K2), f"seq={seq}/33 km={km}/33 head={head}/{len(K2)}"
    if name == "Dropped Image (3)":
        got = _present(K3, text)
        tamin = text.count("تامین") + text.count("تأمین")
        wrong = text.count("تعیین")
        return len(got), len(K3), f"تامین={tamin} تعیین={wrong}"
    if name == "Dropped Image (4)":
        got = _present(K4, text)
        return len(got), len(K4), ""
    raise KeyError(name)


def has_repetition_loop(text: str) -> bool:
    words = text.split()
    return any(words[i:i + 3] == words[i + 3:i + 6] == words[i + 6:i + 9] == words[i + 9:i + 12]
               for i in range(max(0, len(words) - 12)))
