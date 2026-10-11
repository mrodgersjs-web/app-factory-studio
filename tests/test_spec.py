import pytest

from app_factory.spec import SpecError, infer_type, parse_spec, pluralize

TODO = """# Team Todo

A small offline todo API. Each task has a title (text), done (bool),
a priority (int), a due date and optional notes (text).
"""


def fields_of(plan, entity=0):
    return [(f.name, f.type, f.required, f.type_source) for f in plan.entities[entity].fields]


def test_paragraph_with_line_breaks_is_one_sentence():
    plan = parse_spec(TODO)
    assert plan.name == "team-todo"
    assert plan.package == "team_todo"
    assert plan.template == "rest-api"
    assert [e.name for e in plan.entities] == ["task"]
    assert plan.entities[0].plural == "tasks"
    assert fields_of(plan) == [
        ("title", "str", True, "explicit"),
        ("done", "bool", True, "explicit"),
        ("priority", "int", True, "explicit"),
        ("due_date", "date", True, "inferred"),
        ("notes", "str", False, "explicit"),
    ]
    assert plan.assumptions == ["task.due_date: type 'date' inferred from the field name"]
    assert plan.description == "A small offline todo API."


def test_same_text_gives_same_plan_and_hash():
    assert parse_spec(TODO).to_dict() == parse_spec(TODO).to_dict()
    assert parse_spec(TODO).spec_sha256 != parse_spec(TODO + " ").spec_sha256


def test_cli_keyword_and_multiple_entities():
    plan = parse_spec(
        "A command line tool for a shop. Each product has a name, quantity and price. "
        "Every supplier has a name (text) and an optional phone (text)."
    )
    assert plan.template == "cli"
    assert plan.name == "product-cli"
    assert [e.name for e in plan.entities] == ["product", "supplier"]
    assert [(f.name, f.type) for f in plan.entities[0].fields] == [
        ("name", "str"), ("quantity", "int"), ("price", "float"),
    ]
    assert plan.entities[1].fields[1].required is False


def test_entity_directive_lines_and_template_line():
    plan = parse_spec(
        "title: Clinic Booking\n"
        "template: api\n"
        "entity: appointment(patient name: text, start date: date, paid: bool, fee: decimal)\n"
        "entity: room: label (text), capacity (int)\n"
    )
    assert plan.name == "clinic-booking"
    assert plan.template == "rest-api"
    assert plan.template_reason == "template: line in the spec"
    assert [(f.name, f.type) for f in plan.entities[0].fields] == [
        ("patient_name", "str"), ("start_date", "date"), ("paid", "bool"), ("fee", "float"),
    ]
    assert [(f.name, f.type) for f in plan.entities[1].fields] == [("label", "str"), ("capacity", "int")]


def test_multiword_entity_and_override():
    plan = parse_spec("Each inventory item has a name and a reorder level (int).", template_override="cli")
    assert plan.entities[0].name == "inventory_item"
    assert plan.entities[0].plural == "inventory_items"
    assert plan.template == "cli"
    assert plan.template_reason == "--template option"


def test_default_template_is_recorded_as_assumption():
    plan = parse_spec("Each note has a body.")
    assert plan.template == "rest-api"
    assert "template: no keyword found, defaulted to rest-api" in plan.assumptions


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "empty"),
        ("A todo app with nothing described.", "no entities found"),
        ("Each task has a title (colour).", "unknown type 'colour'"),
        ("Each task has a title and a title.", "appears twice"),
        ("Each task has an id (int) and a title.", "reserved"),
        ("Each task has optional notes (text).", "at least one required field"),
        ("template: desktop\nEach task has a title.", "unknown template"),
        ("entity: task(title: text", "missing its closing"),
        ("Each task has a title (int, text).", "two types"),
        ("Each task has a title. Each task has a body.", "described twice"),
    ],
)
def test_bad_specs_are_refused_with_a_reason(text, message):
    with pytest.raises(SpecError, match=message):
        parse_spec(text)


def test_inference_and_plurals():
    assert infer_type("is_active") == "bool"
    assert infer_type("order_count") == "int"
    assert infer_type("unit_price") == "float"
    assert infer_type("shipped_on") == "date"
    assert infer_type("nickname") == "str"
    assert [pluralize(w) for w in ("task", "category", "box", "day", "batch")] == [
        "tasks", "categories", "boxes", "days", "batches",
    ]
