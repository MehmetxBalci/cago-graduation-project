"""Translation lookup, interpolation and display <-> internal value mapping (presentation only).

    tr = get_translator("tr")
    tr.t("form.generate")                       -> "Önerileri üret"
    tr.t("status.hard_valid", n=12)             -> "12 aday zorunlu kısıtları sağlıyor"
    tr.label("material", "cotton")              -> "pamuk"
    tr.option_labels("fit", ["slim", "relaxed"]) -> {"slim": "Dar kesim", "relaxed": "Rahat kesim"}   (unique, reversible)
    tr.to_internal("fit", "Rahat kesim", [...]) -> "relaxed"

Design rules
* Internal identifiers are never translated in place: widgets keep the internal values as options and only format them for
  display, so the request passed to the frozen research engine is identical in every language.
* A missing message key in the active catalog is an error in strict mode (`CAGO_I18N_STRICT=1`, used by the tests) and
  otherwise falls back to English while being recorded in `Translator.missing` and logged. The automated tests guarantee
  that both catalogs have identical keys and placeholders, so the fallback is never needed in a released build.
* Interpolation is strict: a placeholder without a value raises `TranslationError` instead of rendering "{name}".
"""
from __future__ import annotations

import logging
import os
import re
import string
from functools import lru_cache
from typing import Any, Iterable

from app.i18n import en, tr

LOG = logging.getLogger("cago.i18n")
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = ("en", "tr")
LANGUAGE_BUTTONS = {"en": "EN", "tr": "TR"}
CATALOGS = {"en": en, "tr": tr}
VOCAB_DOMAINS = ("segment", "category", "material", "colour", "fit", "length_cut", "stretch", "thermal_warmth", "breathability",
                 "durability_wear", "component", "component_class", "rejection", "text_tag")
_UNDERSCORE_DOMAINS = ("category", "component", "component_class", "rejection", "text_tag")
_COLOUR_SPLIT = re.compile(r"(/| - )")
_CAPITALISED_OPTION_DOMAINS = ("material", "colour")


def capitalise(text: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Upper-case the first letter (Turkish: i -> İ, ı -> I)."""
    if not text:
        return text
    first = {"i": "İ", "ı": "I"}.get(text[0], text[0].upper()) if lang == "tr" else text[0].upper()
    return first + text[1:]


class TranslationError(KeyError):
    """Unknown key, missing key in strict mode, or a placeholder without a value."""


def placeholders(template: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(template) if f}


class Translator:
    def __init__(self, lang: str = DEFAULT_LANGUAGE, strict: bool | None = None):
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language {lang!r}; choose one of {SUPPORTED_LANGUAGES}")
        self.lang = lang
        self.catalog = CATALOGS[lang]
        self.messages: dict[str, str] = self.catalog.MESSAGES
        self.vocab: dict[str, dict[str, str]] = self.catalog.VOCAB
        self.strict = (os.environ.get("CAGO_I18N_STRICT") == "1") if strict is None else strict
        self.missing: set[str] = set()

    def __repr__(self) -> str:
        return f"Translator({self.lang!r})"

    # ------------------------------------------------------------ messages
    def has(self, key: str) -> bool:
        return key in self.messages

    def t(self, key: str, **params: Any) -> str:
        tpl = self.messages.get(key)
        if tpl is None:
            if self.strict or key not in en.MESSAGES:
                raise TranslationError(f"missing translation key {key!r} for language {self.lang!r}")
            self.missing.add(key)
            LOG.warning("missing translation key %r for language %r; using English", key, self.lang)
            tpl = en.MESSAGES[key]
        try:
            return tpl.format_map(params) if placeholders(tpl) else tpl
        except (KeyError, IndexError) as exc:
            raise TranslationError(f"placeholder {exc} of key {key!r} ({self.lang}) has no value") from exc

    # ------------------------------------------------------------ numbers (Turkish: decimal comma, percent sign first)
    def num(self, x: float, spec: str = "g") -> str:
        s = format(x, spec)
        return s.replace(".", ",") if self.lang == "tr" else s

    def pct(self, p: float) -> str:
        """Percentage of a material (V1 rule: integer when whole, else one decimal)."""
        s = f"{p:.0f}" if abs(p - round(p)) < 1e-6 else f"{p:.1f}"
        return f"%{s.replace('.', ',')}" if self.lang == "tr" else f"{s}%"

    def pct_token(self, value: str) -> str:
        """A frozen evidence value like '3.5%' rendered in the active language (unparseable values unchanged)."""
        try:
            return self.pct(float(value.rstrip("%"))) if value.endswith("%") else self.num(float(value))
        except ValueError:
            return value

    # ------------------------------------------------------------ vocabulary
    def label(self, domain: str, value: Any) -> str:
        """Display label of an internal identifier. English = the identifier itself (categories / components: spaces for
        underscores). Turkish = catalog label; identifiers without a reliable translation are shown unchanged."""
        if value is None:
            return ""
        v = str(value)
        if self.lang == "en":
            return v.replace("_", " ") if domain in _UNDERSCORE_DOMAINS else v
        if domain == "colour":
            return translate_colour(v)
        if domain == "rejection" and v not in self.vocab["rejection"] and v.startswith("hard_validation:"):
            return v.replace("_", " ")
        hit = self.vocab.get(domain, {}).get(v)
        if hit is not None:
            return hit
        return v.replace("_", " ") if domain in _UNDERSCORE_DOMAINS else v

    def is_translated(self, domain: str, value: str) -> bool:
        """True when the Turkish catalog defines a label (or the identifier is deliberately retained)."""
        if self.lang == "en":
            return True
        if domain == "colour":
            return colour_fully_translated(value)
        return value in self.vocab.get(domain, {}) or value in self.catalog.RETAINED.get(domain, set())

    def option_labels(self, domain: str, values: Iterable[Any], capitalize: bool | None = None) -> dict[Any, str]:
        """Unique display label per internal value (reversible). Colliding labels get the identifier appended.
        Turkish option lists start materials and colours with a capital letter (Pamuk, Siyah); sentences use `label`."""
        vals = list(dict.fromkeys(values))
        cap = (self.lang == "tr" and domain in _CAPITALISED_OPTION_DOMAINS) if capitalize is None else capitalize
        base = {v: (capitalise(self.label(domain, v), self.lang) if cap else self.label(domain, v)) for v in vals}
        counts: dict[str, int] = {}
        for lab in base.values():
            counts[lab] = counts.get(lab, 0) + 1
        out = {}
        for v in vals:
            lab = base[v]
            out[v] = f"{lab} ({v})" if counts[lab] > 1 and lab != str(v) else lab
        if len(set(out.values())) != len(out):                     # identical identifiers cannot collide; defensive
            raise TranslationError(f"display labels of {domain!r} are not unique: {out}")
        return out

    def to_internal(self, domain: str, label: str, values: Iterable[Any], capitalize: bool | None = None) -> Any:
        """Reverse mapping display label -> internal value within the given option set."""
        rev = {lab: v for v, lab in self.option_labels(domain, values, capitalize).items()}
        if label not in rev:
            raise TranslationError(f"{label!r} is not a {domain} label of the current options")
        return rev[label]

    # ------------------------------------------------------------ convenience
    def field(self, ui_field: str) -> str:
        return self.t(f"field.{ui_field}")

    def field_lc(self, ui_field: str) -> str:
        return self.t(f"field_lc.{ui_field}")

    def role(self, role: str) -> str:
        return self.t(f"role.{role}")

    def sr_name(self, rule: str) -> str:
        return self.t(f"sr.{rule}.name")


# ---------------------------------------------------------------- colours (Turkish only; English shows the identifier)
def _translate_words(words: list[str]) -> str | None:
    out, i = [], 0
    while i < len(words):
        for n in (3, 2, 1):                                       # longest known phrase first
            chunk = " ".join(words[i:i + n])
            if len(words[i:i + n]) == n and (chunk in tr.COLOUR_PHRASES or (n == 1 and chunk in tr.COLOUR_WORDS)):
                out.append(tr.COLOUR_PHRASES.get(chunk) or tr.COLOUR_WORDS[chunk])
                i += n
                break
        else:
            return None
    return " ".join(out)


def _colour_segments(colour: str) -> list[tuple[str, str | None]]:
    """[(segment or separator, translation or None)]."""
    parts = _COLOUR_SPLIT.split(colour)
    out = []
    for p in parts:
        if p in ("/", " - "):
            out.append((p, p))
        else:
            words = p.strip().split()
            out.append((p, _translate_words(words) if words else p))
    return out


@lru_cache(maxsize=4096)
def translate_colour(colour: str) -> str:
    return "".join(t if t is not None else s for s, t in _colour_segments(colour))


def colour_fully_translated(colour: str) -> bool:
    return all(t is not None for _, t in _colour_segments(colour))


@lru_cache(maxsize=None)
def get_translator(lang: str = DEFAULT_LANGUAGE) -> Translator:
    return Translator(lang)


EN = get_translator("en")
