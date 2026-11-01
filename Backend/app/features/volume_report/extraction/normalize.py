"""Description normalization, lexicon tokenization and the non-binding hints (role, surcharge word, group key).

Text goes through `core.text_normalization.normalize` -- the same function the lexical search paths use -- so stored
`description_norm` values stay searchable with the existing trigram/BM25 machinery. Tokenizing is done on whole words
(longest phrase first): that is what keeps "زیر اساس" (SUBBASE) from also yielding BASE. Never write rules on raw
substrings."""

import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.core.text_normalization import normalize
from app.features.volume_report.seed_data import HARD_EXCLUSION_REASONS, LEXICON_SEED

QUANTITY_PLACES = Decimal("0.0001")

_PERSIAN_MONTHS = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)


def normalize_text(text: object) -> str:
    """`normalize` plus whitespace collapsing (it leaves "\\n", NBSP and runs of spaces alone)."""
    if text is None:
        return ""
    return re.sub(r"\s+", " ", normalize(str(text))).strip()


def light_clean(text: object) -> str:
    """Letter/digit unification only (no punctuation stripping) -- used where punctuation carries structure."""
    value = str(text).replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    value = re.sub(r"[۰-۹]", lambda m: str(ord(m.group()) - 0x06F0), value)
    value = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), value)
    return re.sub(r"\s+", " ", value).strip()


def parse_quantity(value: object) -> Decimal | None:
    """Number or numeric string (Persian/Arabic digits, thousands separators, "(12)" as negative) -> Decimal rounded to
    4 places; anything else -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
        except InvalidOperation:
            return None
    else:
        text = light_clean(value).replace("٫", ".").replace("٬", "").replace(",", "").replace("−", "-").replace(" ", "")
        negative = False
        if text.startswith("(") and text.endswith(")"):
            negative, text = True, text[1:-1]
        if not re.fullmatch(r"-?\d+(\.\d+)?", text):
            return None
        number = Decimal(text)
        if negative:
            number = -abs(number)
    if not number.is_finite():
        return None
    return number.quantize(QUANTITY_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class LexiconEntry:
    token: str
    kind: str  # item_hint | role | hard_exclusion | noise
    phrases: tuple[str, ...]


class Lexicon:
    """Phrase -> token matcher over normalized words."""

    def __init__(self, entries: Iterable[LexiconEntry]):
        self._kind: dict[str, str] = {}
        by_first_word: dict[str, list[tuple[tuple[str, ...], str]]] = {}
        for entry in entries:
            self._kind[entry.token] = entry.kind
            for phrase in entry.phrases:
                words = tuple(normalize_text(phrase).split())
                if words:
                    by_first_word.setdefault(words[0], []).append((words, entry.token))
        for candidates in by_first_word.values():
            candidates.sort(key=lambda item: len(item[0]), reverse=True)
        self._by_first_word = by_first_word

    @classmethod
    def from_seed(cls) -> "Lexicon":
        return cls(LexiconEntry(token, kind, tuple(phrases)) for token, kind, phrases in LEXICON_SEED)

    def kind_of(self, token: str) -> str | None:
        return self._kind.get(token)

    def tokenize(self, description_norm: str) -> list[str]:
        """Tokens in order of appearance, de-duplicated. Unmatched words are simply not tokens."""
        words = description_norm.split()
        tokens: list[str] = []
        i = 0
        while i < len(words):
            for phrase, token in self._by_first_word.get(words[i], ()):
                if tuple(words[i : i + len(phrase)]) == phrase:
                    if token not in tokens:
                        tokens.append(token)
                    i += len(phrase)
                    break
            else:
                i += 1
        return tokens

    def hard_exclusion_reason(self, tokens: Iterable[str]) -> str | None:
        for token in tokens:
            if self._kind.get(token) == "hard_exclusion":
                return HARD_EXCLUSION_REASONS.get(token, "other")
        return None


def role_hint(tokens: Iterable[str]) -> str:
    """supply / execute / combined / na. A hint only -- the final role is the agent's or a human's call."""
    token_set = set(tokens)
    supply, execute = "SUPPLY" in token_set, "EXEC" in token_set
    if supply and execute:
        return "combined"
    if supply:
        return "supply"
    if execute:
        return "execute"
    return "na"


def group_key(description_norm: str, unit_norm: str, site_kind: str) -> str:
    """Identity of a unique (description, unit, site kind) group; same formula as `vr_decisions.key_hash`."""
    return hashlib.sha256(f"{description_norm}|{unit_norm}|{site_kind}".encode()).hexdigest()


def persian_months_in(text: object) -> set[str]:
    words = set(normalize_text(text).split())
    return {month for month in _PERSIAN_MONTHS if normalize_text(month) in words or (month == "آبان" and "ابان" in words)}
