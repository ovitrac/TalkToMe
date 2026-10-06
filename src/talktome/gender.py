"""Session gender (design §5.1): improvised from the spoken name, as a native speaker would guess it.

Sessions are people, not objects: "he" or "she", never "it". The guess, in order: a leading French article
(la chaise, le moteur; after les/des the plural -s/-x is dropped); a known given or mythological name; a
French noun ending (la nation, la maison; le fromage, le système); a final -a or -e → feminine; a final -o,
-u or consonant → masculine; anything else (acronyms, -i, -y, digits only) → a stable hash, so a name always
keeps the gender it was first given. Claude or the user may override it (`talktome gender`, `--gender`).
Standard library only.

Author: Olivier Vitrac, PhD, HDR — Adservio Innovation Lab — Adservio Group — olivier.vitrac@adservio.fr
License: MIT
"""

from __future__ import annotations

import re
import unicodedata
import zlib

GENDERS = ("f", "m")

FEMALE_NAMES = frozenset(
    """ada agnes alice amy anna anne ariadne ariane athena aurora beatrice carmen chloe claire diane eleanor
    elizabeth emma esther eve grace hera heidi ines iris isabel jane judith julia julie juliet lea lucie lucy
    margaret marie mary maya minerva nadia naomi nina olivia penelope rachel rosa rose rosetta ruth sarah
    sophie venus zoe""".split()
)
MALE_NAMES = frozenset(
    """achille achilles adam alan andy antoine apollo apollon arthur atlas charles dave david etienne gaston
    george georges guillaume harry hector henry hercule hercules hermes hugo jean jerome jerry joe john jose
    jules leo louis loki marc marcus mark mars max maxime merlin michel mike noah odin oscar paul philippe
    pierre remi stephane steve thomas thor ulysse ulysses victor zeus""".split()
)
ARTICLES = {"la": "f", "une": "f", "le": "m", "un": "m"}
SKIPPED = frozenset({"the", "a", "an", "les", "l", "des", "du", "de"})
PLURAL = frozenset({"les", "des"})
FEMININE_ENDINGS = ("tion", "sion", "xion", "aison", "cion", "dad", "dade", "cao")
MASCULINE_ENDINGS = ("age", "isme", "ege", "eme", "scope", "phone")
VOWELS = set("aeiouy")


def _fold(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", word) if not unicodedata.combining(c)).lower()


def _hashed(name: str) -> str:
    return GENDERS[zlib.crc32(name.strip().lower().encode("utf-8")) % 2]


def _cues(lang: str) -> tuple[dict[str, str], frozenset[str], frozenset[str]]:
    """Articles, skipped words and plural articles: French and English always, plus the language's own."""
    articles, skipped, plural = dict(ARTICLES), set(SKIPPED), set(PLURAL)
    if lang not in ("en", "fr"):
        from . import langs

        g = langs.grammar(lang)
        articles.update({_fold(k): v for k, v in g.get("articles", {}).items()})
        skipped |= {_fold(w) for w in g.get("skip", [])}
        plural |= {_fold(w) for w in g.get("plural", [])}
        skipped -= set(articles)  # pt "a" is an article, not the English "a"
    return articles, frozenset(skipped), frozenset(plural)


def guess(name: str, lang: str = "en") -> tuple[str, str]:
    """(gender, reason) for a spoken session name; deterministic."""
    articles, skipped, plurals = _cues(lang)
    words = re.findall(r"[^\W\d_]+", name)
    if words and _fold(words[0]) in articles:
        return articles[_fold(words[0])], f"article {words[0]}"
    plural = False
    while words and _fold(words[0]) in skipped and len(words) > 1:
        plural = plural or _fold(words[0]) in plurals
        words = words[1:]
    if not words:
        return _hashed(name), "improvised (no word)"
    raw = words[0]
    w = _fold(raw)
    if plural and len(w) > 3 and w[-1] in "sx":
        w = w[:-1]
    if w in FEMALE_NAMES:
        return "f", "known name"
    if w in MALE_NAMES:
        return "m", "known name"
    if (raw.isupper() and len(raw) > 1) or not VOWELS & set(w):
        return _hashed(name), "improvised (acronym)"
    for ending in FEMININE_ENDINGS:
        if w.endswith(ending):
            return "f", f"ending -{ending}"
    for ending in MASCULINE_ENDINGS:
        if w.endswith(ending):
            return "m", f"ending -{ending}"
    last = w[-1]
    if last in "ae":
        return "f", f"final -{last}"
    if last in "ou" or last not in VOWELS:
        return "m", f"final -{last}"
    return _hashed(name), f"improvised (final -{last})"


def pronoun(gender: str) -> str:
    """Possessive determiner for {his}: his / her; "their" when no gender is known."""
    return {"m": "his", "f": "her"}.get(gender, "their")
