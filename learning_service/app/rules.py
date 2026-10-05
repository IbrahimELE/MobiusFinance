"""Rule layer: turn ratings, tags and free-text notes into a preference profile.

Works offline and deterministically, so the demo never depends on an LLM.

How a note is read: it is split into clauses ("Više o dugu, manje o
proizvodima, kraće."). In each clause we look for topic keywords (Bosnian and
English stems) and a direction cue: "manje", "bez", "previše", "ne zanima" ...
mean *avoid*; anything else ("više", "fali", "fokus na", or a bare mention)
means *focus*. The latest opinion on a topic decides its direction, so a later
"ipak više o proizvodima" overrides an earlier "manje o proizvodima"; repeated
agreeing mentions make a topic rank higher.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# topic key -> (label for people, phrase for the agent prompt, keyword stems)
TOPICS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "debt": ("zaduženost", "zaduženost (debt-to-equity)", ("dug", "duga", "dugu", "duzn", "zaduz", "debt", "leverage", "kredit")),
    "free_cash_flow": ("slobodni novčani tok", "slobodni novčani tok (FCF)", ("fcf", "novcani tok", "novcanom toku", "novcanog toka", "cash flow", "cashflow", "slobodni novac")),
    "valuation": ("valuacija", "valuaciju (P/E, forward P/E)", ("valuacij", "p/e", " pe ", "skup", "jeftin", "multipl", "valuation", "cijena dionice")),
    "growth": ("rast", "rast prihoda", ("rast", "growth", "prihod", "revenue")),
    "margins": ("marže", "marže i profitabilnost", ("marz", "margin", "profitabil", "zarada")),
    "competition": ("konkurencija", "poređenje s konkurencijom", ("konkuren", "competit", "rival", "peer", "poredj", "usporedb")),
    "risks": ("rizici", "ključne rizike iz 10-K", ("rizik", "risk")),
    "dividends": ("dividende", "dividende i povrat kapitala", ("dividend", "otkup dionic", "buyback")),
    "macro": ("makro", "makro okruženje (kamate, inflacija)", ("makro", "kamat", "inflac", "macro", "fed ", "recesij")),
    "product_details": ("opis proizvoda", "opis proizvoda", ("proizvod", "product", "iphone", "uredjaj")),
}

# style key -> (value, label, prompt sentence, stems)
STYLE_RULES: list[tuple[str, str, str, str, tuple[str, ...]]] = [
    ("length", "short", "kraće", "Piši kratko: teza najviše 3 rečenice.", ("krace", "kratk", "sazet", "manje teksta", "previse teksta", "predug", "dugacak", "short", "brief")),
    ("length", "long", "detaljnije", "Piši detaljnije: 5–6 rečenica s više konteksta.", ("detaljn", "duze", "vise detalja", "prekratk", "longer", "detail")),
    ("tone", "simple", "jednostavnije", "Piši jednostavno i objasni stručne pojmove u zagradi.", ("jednostavn", "objasn", "laick", "bez zargona", "ne razumijem", "simple", "explain")),
    ("tone", "numbers", "više brojeva", "Svaku tvrdnju potkrijepi konkretnim brojem.", ("vise brojeva", "konkretn", "brojk", "numbers")),
]

TAG_TO_STYLE = {"short": ("length", "short"), "long": ("length", "long"), "simple": ("tone", "simple")}
ALLOWED_TAGS = set(TOPICS) | set(TAG_TO_STYLE)

AVOID_CUES = ("manje", "bez ", "previse", "ne zanima", "ne treba", "izbaci", "preskoci", "nebitn", "ne spominj",
              "less", "without", "too much", "skip", "don't", "dont")
MAX_FOCUS = 4


def _norm(text: str) -> str:
    """Lowercase, strip diacritics (č->c, đ->dj) so stems match however the user types."""
    t = text.lower().replace("đ", "dj")
    t = unicodedata.normalize("NFKD", t)
    return "".join(c for c in t if not unicodedata.combining(c))


def _clauses(note: str) -> list[str]:
    parts = re.split(r"[,;.!?\n]|\s(?:ali|i|a|but|and)\s", _norm(note))
    return [f" {p.strip()} " for p in parts if p.strip()]


def read_note(note: str) -> tuple[dict[str, float], dict[str, str]]:
    """Topic scores (+1 focus / -1 avoid) and style choices found in one note."""
    topics: dict[str, float] = {}
    style: dict[str, str] = {}
    for clause in _clauses(note):
        avoid = any(cue in clause for cue in AVOID_CUES)
        for key, (_, _, stems) in TOPICS.items():
            if any(s in clause for s in stems):
                topics[key] = -1.0 if avoid else 1.0
        for skey, value, _, _, stems in STYLE_RULES:
            if any(s in clause for s in stems):
                style[skey] = value
    return topics, style


@dataclass
class RuleProfile:
    focus: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    style: dict[str, str | None] = field(default_factory=lambda: {"length": None, "tone": None})

    @property
    def empty(self) -> bool:
        return not (self.focus or self.avoid or any(self.style.values()))

    def instructions(self) -> str:
        if self.empty:
            return ""
        out = []
        for skey, value, _, sentence, _ in STYLE_RULES:
            if self.style.get(skey) == value:
                out.append(sentence)
        if self.focus:
            out.append("Obavezno komentariši: " + ", ".join(TOPICS[k][1] for k in self.focus) + ".")
        if self.avoid:
            out.append("Izbjegavaj ili svedi na minimum: " + ", ".join(TOPICS[k][1] for k in self.avoid) + ".")
        return "Korisnik je kroz ocjene pokazao šta želi. " + " ".join(out)

    def label(self) -> str:
        if self.empty:
            return ""
        parts = []
        if self.focus:
            parts.append("fokus: " + ", ".join(TOPICS[k][0] for k in self.focus))
        for skey, value, lab, _, _ in STYLE_RULES:
            if self.style.get(skey) == value:
                parts.append(lab)
        if self.avoid:
            parts.append("bez: " + ", ".join(TOPICS[k][0] for k in self.avoid))
        return " · ".join(parts)


def build_profile(feedback: list[dict]) -> RuleProfile:
    """`feedback` oldest first, each with rating, note, tags."""
    # topic -> (direction, strength, last position); the latest mention sets the direction.
    state: dict[str, tuple[float, int, int]] = {}
    style: dict[str, str | None] = {"length": None, "tone": None}
    for i, fb in enumerate(feedback):
        topics, note_style = read_note(fb.get("note") or "")
        for tag in fb.get("tags") or []:
            if tag in TOPICS:
                # A tag on a thumbs-down means "this was missing"; on thumbs-up "more of this".
                topics.setdefault(tag, 1.0)
            elif tag in TAG_TO_STYLE:
                skey, value = TAG_TO_STYLE[tag]
                note_style.setdefault(skey, value)
        for key, direction in topics.items():
            prev = state.get(key)
            strength = prev[1] + 1 if prev and prev[0] == direction else 1
            state[key] = (direction, strength, i)
        style.update(note_style)  # oldest first, so the latest choice wins
    rank = lambda k: (-state[k][1], -state[k][2])  # stronger first, then more recent
    focus = sorted((k for k, v in state.items() if v[0] > 0), key=rank)[:MAX_FOCUS]
    avoid = sorted((k for k, v in state.items() if v[0] < 0), key=rank)
    return RuleProfile(focus=focus, avoid=avoid, style=style)
