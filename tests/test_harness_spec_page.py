"""The harness specification page is printed from its record, and this holds it there.

ADR-0035 (Proposed) keeps the harness record as JSON and said its human-readable
rendering would be generated from that JSON, so that two separately maintained
descriptions cannot drift. ``evals/render_harness_spec.py`` writes
``examples/harness-five-turn.md`` and the eight-component picture, light and
dark, from the recorded sitting ``examples/harness-five-turn.json``. One check
holds the chain:

* both snapshots in the record validate, so their hashes match their contents;
* the page and both pictures on disk are exactly what the record renders;
* the page states the record's active and closing hashes in full, and every
  component's status and evidence paths, so a hand edit to the record that the
  page does not show fails here.
"""

from __future__ import annotations

from evals import render_harness_spec as render
from secondsignal_harness.spec import COMPONENT_NAMES, validate_specification


def test_the_page_and_its_pictures_are_what_the_record_renders():
    record = render.load()
    validate_specification(record["active_specification"])
    validate_specification(record["closed_specification"])
    rendered = render.outputs(record)
    assert sorted(path.name for path in rendered) == [
        "harness-five-turn-dark.svg", "harness-five-turn-light.svg", "harness-five-turn.md"]
    assert render.stale(rendered) == [], "run python evals/render_harness_spec.py --write"
    page = rendered[render.PAGE]
    assert record["header"]["specification_hash"] in page
    assert record["closed_specification"]["specification_hash"] in page
    components = record["active_specification"]["records"]["release"]["components"]
    assert [component["name"] for component in components] == list(COMPONENT_NAMES)
    for component in components:
        title = render.COMPONENTS[component["name"]]["title"]
        assert f"**{title}: {render.STATUS_WORDS[component['status']]}.**" in page
        assert all(f"`{path}`" in page for path in component["evidence"])
        if component["reason"]:
            assert component["reason"] in page
