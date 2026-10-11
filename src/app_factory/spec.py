"""Deterministic spec parser: a spec paragraph (or file) becomes a normalized plan.

The parser is rule based on purpose. The same input text always yields the same
plan, so the same generated files and the same tree hash. No model calls.

Grammar (case-insensitive):

* ``title: <name>`` or ``name: <name>`` or a ``# Heading`` sets the app name.
* ``template: rest-api`` or ``template: cli`` picks the template explicitly.
  Otherwise keywords decide: "cli", "command line", "terminal" pick ``cli``;
  "api", "rest", "http", "endpoint", "service", "server" pick ``rest-api``;
  with no keyword the default is ``rest-api`` (recorded as an assumption).
* Entities come from sentences like
  ``Each task has a title (text), a due date, done (bool) and an optional note.``
  or from directive lines like ``entity: task(title: text, priority: int)``.
* Field types: text/str/string, int/integer, float/decimal/number/money,
  bool/boolean/flag, date. A missing type is inferred from the field name and the
  inference is recorded in ``assumptions``. ``optional`` marks a field optional.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field

from . import __version__

TYPE_ALIASES = {
    "text": "str",
    "str": "str",
    "string": "str",
    "word": "str",
    "int": "int",
    "integer": "int",
    "whole": "int",
    "count": "int",
    "float": "float",
    "decimal": "float",
    "number": "float",
    "numeric": "float",
    "money": "float",
    "currency": "float",
    "bool": "bool",
    "boolean": "bool",
    "flag": "bool",
    "yes/no": "bool",
    "date": "date",
}
FLAG_WORDS = {"optional", "required"}
TEMPLATES = ("rest-api", "cli")
RESERVED_FIELDS = {"id", "help"}

BOOL_NAMES = {
    "done", "completed", "complete", "active", "enabled", "archived", "paid", "published",
    "verified", "urgent", "in_stock", "approved", "resolved", "visible", "favorite",
}
INT_NAMES = {
    "count", "quantity", "qty", "priority", "age", "rank", "year", "stock", "pages", "rating",
    "level", "size", "seats", "capacity", "minutes", "points",
}
FLOAT_NAMES = {
    "price", "amount", "cost", "total", "rate", "score", "weight", "balance", "budget",
    "height", "length", "distance", "hours", "percent",
}
DATE_NAMES = {"date", "due", "deadline", "birthday", "due_date", "start_date", "end_date"}

_ENTITY_SENTENCE = re.compile(
    r"\b(?:each|every)\s+(?P<entity>[a-z][a-z0-9]*(?:[ _-][a-z][a-z0-9]*){0,2}?)\s+"
    r"(?:has|have|stores|tracks|records|contains|includes|holds)\s+"
    r"(?:the\s+following\s+)?(?:fields?\s*:?\s*)?(?P<fields>.+)$",
    re.IGNORECASE,
)
_ENTITY_DIRECTIVE = re.compile(r"^\s*entity\s*:\s*(?P<entity>[^(:]+?)\s*(?P<open>[(:])\s*(?P<fields>.*?)\s*\.?$", re.I)
_LEADING_WORDS = re.compile(r"^(?:and|or|plus|also|a|an|the|its|their|his|her|some)\s+")


class SpecError(ValueError):
    """The spec cannot be turned into an app. The message says how to fix it."""


@dataclass
class Field:
    name: str
    type: str
    required: bool = True
    type_source: str = "explicit"


@dataclass
class Entity:
    name: str
    plural: str
    fields: list[Field] = field(default_factory=list)


@dataclass
class Plan:
    name: str
    package: str
    template: str
    template_reason: str
    description: str
    entities: list[Entity]
    assumptions: list[str]
    spec_sha256: str
    factory_version: str = __version__

    def to_dict(self) -> dict:
        return asdict(self)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def snake(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def pluralize(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


def infer_type(name: str) -> str:
    if name.startswith(("is_", "has_", "can_")) or name in BOOL_NAMES:
        return "bool"
    if name in DATE_NAMES or name.endswith(("_date", "_on")):
        return "date"
    if name in INT_NAMES or name.endswith(("_count", "_qty", "_number", "_id")):
        return "int"
    if name in FLOAT_NAMES or name.endswith(("_price", "_amount", "_cost", "_total")):
        return "float"
    return "str"


def _split_top_level(text: str) -> list[str]:
    """Split a field list on commas, semicolons and ' and ' outside parentheses."""
    parts: list[str] = []
    depth = 0
    buf = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and ch in ",;":
            parts.append(buf)
            buf = ""
            i += 1
            continue
        if depth == 0 and text[i:i + 5].lower() == " and ":
            parts.append(buf)
            buf = ""
            i += 5
            continue
        buf += ch
        i += 1
    parts.append(buf)
    return [p.strip() for p in parts if p.strip()]


def _parse_field(token: str, entity: str, assumptions: list[str]) -> Field:
    raw = token.strip().rstrip(".").strip()
    required = True
    type_word: str | None = None

    annotations: list[str] = []
    paren = re.search(r"\(([^)]*)\)", raw)
    if paren:
        annotations = [a for a in re.split(r"[\s,]+", paren.group(1).lower()) if a]
        raw = (raw[: paren.start()] + raw[paren.end():]).strip()
    if ":" in raw:
        raw, _, after = raw.partition(":")
        annotations += [a for a in re.split(r"[\s,]+", after.lower()) if a]

    words = raw.lower().strip()
    while True:
        new = _LEADING_WORDS.sub("", words)
        if new.startswith("optional "):
            required = False
            new = new[len("optional "):]
        elif new.startswith("required "):
            new = new[len("required "):]
        if new == words:
            break
        words = new

    for ann in annotations:
        if ann == "optional":
            required = False
        elif ann == "required":
            required = True
        elif ann in TYPE_ALIASES:
            if type_word and TYPE_ALIASES[ann] != type_word:
                raise SpecError(f"field '{words}' on '{entity}' has two types: {type_word} and {ann}")
            type_word = TYPE_ALIASES[ann]
        else:
            known = ", ".join(sorted(set(TYPE_ALIASES)))
            raise SpecError(f"unknown type '{ann}' for field '{words}' on '{entity}' (known: {known})")

    name = snake(words)
    if not name or not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise SpecError(f"cannot read a field name from '{token.strip()}' on '{entity}'")
    if name in RESERVED_FIELDS:
        raise SpecError(
            f"field '{name}' on '{entity}' is reserved (id is assigned automatically; help is the CLI help flag)"
        )
    source = "explicit"
    if type_word is None:
        type_word = infer_type(name)
        source = "inferred"
        assumptions.append(f"{entity}.{name}: type '{type_word}' inferred from the field name")
    return Field(name=name, type=type_word, required=required, type_source=source)


def _sentences(text: str) -> list[str]:
    """Sentences, with line breaks inside a paragraph treated as spaces."""
    pieces: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        flat = re.sub(r"\s+", " ", para).strip()
        pieces.extend(re.split(r"(?<=[.!?])\s+", flat))
    return [p.strip() for p in pieces if p.strip()]


def _add_entity(entities: dict[str, Entity], name_text: str, fields_text: str, assumptions: list[str]) -> None:
    name = snake(name_text)
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise SpecError(f"cannot use '{name_text}' as an entity name")
    if name in entities:
        raise SpecError(f"entity '{name}' is described twice; describe each entity once")
    fields: list[Field] = []
    seen: set[str] = set()
    for token in _split_top_level(fields_text):
        f = _parse_field(token, name, assumptions)
        if f.name in seen:
            raise SpecError(f"field '{f.name}' appears twice on '{name}'")
        seen.add(f.name)
        fields.append(f)
    if not fields:
        raise SpecError(f"entity '{name}' has no fields")
    if not any(f.required for f in fields):
        raise SpecError(f"entity '{name}' needs at least one required field")
    entities[name] = Entity(name=name, plural=pluralize(name), fields=fields)


def parse_spec(text: str, template_override: str | None = None) -> Plan:
    """Turn spec text into a Plan. Raises SpecError with a fix-it message."""
    if not text.strip():
        raise SpecError("the spec is empty")
    assumptions: list[str] = []
    title: str | None = None
    template: str | None = None
    template_reason = ""
    entities: dict[str, Entity] = {}
    prose: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith(("title:", "name:")) and title is None:
            title = stripped.split(":", 1)[1].strip()
            continue
        if low.startswith("template:"):
            value = slugify(stripped.split(":", 1)[1])
            value = {"api": "rest-api", "rest": "rest-api", "restapi": "rest-api"}.get(value, value)
            if value not in TEMPLATES:
                raise SpecError(f"unknown template '{value}' (choose from: {', '.join(TEMPLATES)})")
            template, template_reason = value, "template: line in the spec"
            continue
        directive = _ENTITY_DIRECTIVE.match(stripped)
        if low.startswith("entity:"):
            if not directive:
                raise SpecError(f"cannot read entity line '{stripped}' (use: entity: task(title: text))")
            fields_text = directive.group("fields")
            if directive.group("open") == "(":
                if not fields_text.endswith(")"):
                    raise SpecError(f"entity line '{stripped}' is missing its closing ')'")
                fields_text = fields_text[:-1]
            _add_entity(entities, directive.group("entity"), fields_text, assumptions)
            continue
        if stripped.startswith("# ") and title is None:
            title = stripped[2:].strip()
            continue
        if stripped.startswith("#"):
            continue
        prose.append(line)

    prose_text = "\n".join(prose)
    for sentence in _sentences(prose_text):
        m = _ENTITY_SENTENCE.search(sentence)
        if m:
            _add_entity(entities, m.group("entity"), m.group("fields"), assumptions)

    if not entities:
        raise SpecError(
            "no entities found. Describe at least one, e.g. "
            "'Each task has a title (text), done (bool) and an optional due date.' "
            "or a line 'entity: task(title: text, done: bool)'"
        )

    if template_override:
        if template_override not in TEMPLATES:
            raise SpecError(f"unknown template '{template_override}' (choose from: {', '.join(TEMPLATES)})")
        template, template_reason = template_override, "--template option"
    if template is None:
        low = prose_text.lower()
        if re.search(r"\b(cli|command[- ]line|terminal|shell)\b", low):
            template, template_reason = "cli", "keyword in spec (cli / command line / terminal)"
        elif re.search(r"\b(api|rest|http|endpoints?|web service|service|server)\b", low):
            template, template_reason = "rest-api", "keyword in spec (api / rest / http / service)"
        else:
            template, template_reason = "rest-api", "default (no template keyword in spec)"
            assumptions.append("template: no keyword found, defaulted to rest-api")

    first = next(iter(entities))
    if title:
        name = slugify(title)
    else:
        name = f"{first.replace('_', '-')}-{'api' if template == 'rest-api' else 'cli'}"
        assumptions.append(f"name: no title given, using '{name}'")
    if not name or not name[0].isalpha():
        name = f"app-{name}".strip("-")
    package = name.replace("-", "_")

    description = ""
    for sentence in _sentences(prose_text):
        if not _ENTITY_SENTENCE.search(sentence):
            description = sentence
            break
    if not description:
        description = f"{name}: generated by app-factory"
    description = description.replace('"', "'").replace("\\", "/")

    return Plan(
        name=name,
        package=package,
        template=template,
        template_reason=template_reason,
        description=description,
        entities=list(entities.values()),
        assumptions=assumptions,
        spec_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
