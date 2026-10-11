"""Render a Plan into a dict of {relative path: file text}. Pure and deterministic."""

from __future__ import annotations

from .spec import Entity, Plan

SAMPLES = {
    "str": ("Sample {name} A", "Sample {name} B"),
    "int": (3, 7),
    "float": (2.5, 4.75),
    "bool": (True, False),
    "date": ("2026-01-15", "2026-02-20"),
}
INVALID = {"str": "   ", "int": "not-a-number", "float": "abc", "bool": "maybe", "date": "15/01/2026"}


def pylit(obj: object, indent: int = 0, width: int = 88) -> str:
    """Python literal with stable formatting (multi-line when long, trailing commas)."""
    one = repr(obj) if not isinstance(obj, (dict, list)) else _one_line(obj)
    if len(one) + indent <= width or not isinstance(obj, (dict, list)) or not obj:
        return one
    pad = " " * (indent + 4)
    if isinstance(obj, dict):
        items = [f"{pad}{k!r}: {pylit(v, indent + 4, width)}," for k, v in obj.items()]
        return "{\n" + "\n".join(items) + "\n" + " " * indent + "}"
    items = [f"{pad}{pylit(v, indent + 4, width)}," for v in obj]
    return "[\n" + "\n".join(items) + "\n" + " " * indent + "]"


def _one_line(obj: object) -> str:
    if isinstance(obj, dict):
        return "{" + ", ".join(f"{k!r}: {_one_line(v)}" for k, v in obj.items()) + "}"
    if isinstance(obj, list):
        return "[" + ", ".join(_one_line(v) for v in obj) + "]"
    return repr(obj)


def sample(entity: Entity, variant: int) -> dict:
    out: dict = {}
    for f in entity.fields:
        value = SAMPLES[f.type][variant]
        if f.type == "str":
            value = value.format(name=f.name.replace("_", " "))
        out[f.name] = value
    return out


def cli_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def schema_literal(plan: Plan) -> dict:
    return {
        e.name: {
            "plural": e.plural,
            "fields": [{"name": f.name, "type": f.type, "required": f.required} for f in e.fields],
        }
        for e in plan.entities
    }


def render(plan: Plan) -> dict[str, str]:
    from .templates import TEMPLATE_RENDERERS, common

    files = common.render_common(plan)
    files.update(TEMPLATE_RENDERERS[plan.template](plan))
    return dict(sorted(files.items()))
