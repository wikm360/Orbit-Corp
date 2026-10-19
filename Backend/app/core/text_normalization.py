"""Persian-aware text normalization shared by every lexical search path (hint BM25, document full-text / trigram).

One definition on purpose: the text stored in `document_chunks.search_text` and the query terms must be normalized
identically, otherwise exact matches silently stop matching.
"""

import re

STOPWORDS = frozenset(
    "از در به با که را این آن یا و تا برای است شد شده هست بود می چه چقدر چند کدام کدوم الان امسال ما ایم شرکت میشه هستن داریم کن".split()
)


def normalize(text: str) -> str:
    """Lower-case, unify Arabic/Persian letter variants, ZWNJ -> space, Persian/Arabic digits -> ASCII, punctuation -> space."""
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه").replace("‌", " ")
    text = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), text)
    text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
    return re.sub(r"[^\w\s]", " ", text.lower())


def words(text: str) -> list[str]:
    """Normalized words without stopwords or one-letter tokens, in order of appearance."""
    return [w for w in normalize(text).split() if w not in STOPWORDS and len(w) > 1]
