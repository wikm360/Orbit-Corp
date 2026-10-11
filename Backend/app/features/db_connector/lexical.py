"""Small dependency-free BM25 over Persian word tokens + character 4-grams (typos, ZWNJ and Arabic/Persian letter variants tolerated).
Used next to the vector search so exact business words ("صورت وضعیت", "حسن انجام کار", view names) always count."""

import collections
import math
import re

_STOP = set("از در به با که را این آن یا و تا برای است شد شده هست بود می چه چقدر چند کدام کدوم الان امسال ما ایم شرکت میشه هستن داریم کن".split())


def normalize(text: str) -> str:
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه").replace("‌", " ")
    text = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), text)
    text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
    return re.sub(r"[^\w\s]", " ", text.lower())


def tokens(text: str) -> list[str]:
    words = [w for w in normalize(text).split() if w not in _STOP and len(w) > 1]
    grams: list[str] = []
    for w in words:
        if len(w) >= 3:
            padded = f"#{w}#"
            grams += [padded[i : i + 4] for i in range(max(1, len(padded) - 3))]
    return words + grams


class Bm25Index:
    def __init__(self, documents: list[str], boosts: list[str] | None = None):
        boosts = boosts or [""] * len(documents)
        self._docs = [tokens(d) + tokens(b) * 2 for d, b in zip(documents, boosts)]
        self._n = len(self._docs)
        self._avgdl = (sum(map(len, self._docs)) / self._n) if self._n else 1.0
        self._df = collections.Counter(t for d in self._docs for t in set(d))
        self._tf = [collections.Counter(d) for d in self._docs]

    def scores(self, query: str, k1: float = 1.4, b: float = 0.6) -> list[float]:
        q = set(tokens(query))
        out = []
        for i in range(self._n):
            score = 0.0
            for t in q:
                f = self._tf[i].get(t)
                if not f:
                    continue
                idf = math.log(1 + (self._n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(self._docs[i]) / self._avgdl))
            out.append(score)
        return out

    def top(self, query: str, k: int) -> list[int]:
        sc = self.scores(query)
        order = sorted(range(self._n), key=lambda i: sc[i], reverse=True)
        return [i for i in order[:k] if sc[i] > 0]
