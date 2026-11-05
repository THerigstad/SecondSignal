"""Write the harness specification page and its picture from the recorded sitting.

ADR-0035 (Proposed) records the harness as a versioned part of the system, in
the format of Gertler, Novelli and Floridi: one model pairing, eight
components and five records. The machine-readable record is JSON, and the
record said its human-readable rendering would be generated from that JSON so
that two separately maintained descriptions cannot drift. This script is that
rendering for one recorded sitting, ``examples/harness-five-turn.json``. It
writes ``examples/harness-five-turn.md`` and the eight-component picture in a
light and a dark version, and ``tests/test_harness_spec_page.py`` fails when
any of the three differs from what this script writes from the record.

Every status, reason, evidence path, version, count and hash on the page is
read from the record, and the decision record's own decision word is read from
the register, ``docs/adr/index.json``, and printed beside every citation of it.
The fixed sentences are the plain-word
descriptions of the components the record marks implemented, which carry no
reason of their own. The page lives beside its record, outside ``docs/``, so
the typo guard's word list (built from the README and ``docs/``) does not
change and no hash moves.

Like the public-number refreshers, it never writes by default. It prints what
is stale and exits non-zero, and writes only when asked:

    python evals/render_harness_spec.py            # show what is stale
    python evals/render_harness_spec.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "examples" / "harness-five-turn.json"
REGISTER = ROOT / "docs" / "adr" / "index.json"
PAGE = ROOT / "examples" / "harness-five-turn.md"
PICTURES = {
    "light": ROOT / "examples" / "harness-five-turn-light.svg",
    "dark": ROOT / "examples" / "harness-five-turn-dark.svg",
}
PAPER = "https://arxiv.org/abs/2610.40917"
ADR_NUMBER = "0035"
ADR_FILE = f"{ADR_NUMBER}-the-harness-is-a-versioned-part-of-the-system.md"
# The register's own decision word is printed beside each citation on the page.
ADR_LABEL = "ADR-" + ADR_NUMBER

NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
STATUS_WORDS = {"implemented": "implemented", "partial": "partial", "not-implemented": "not implemented"}

# The paper's three bands, over the component order the record fixes.
BANDS = (
    ("What it can do", "Cognitive band", 0, 4),
    ("What it is allowed to do", "Control band", 4, 6),
    ("What checks it", "Assurance band", 6, 8),
)

# Display text per component. "plain" describes a component the record marks
# implemented (such a component carries no reason); "detail" adds a value read
# from the component's own configuration; "lines" and "note" are the picture's.
COMPONENTS: dict[str, dict[str, Any]] = {
    "orchestration and planning": {
        "title": "Orchestration and planning",
        "lines": ("Orchestration", "and planning"),
        "note": "Router picks who speaks",
        "plain": "The router decides who speaks, whether anyone speaks at all, and which of the "
                 "{personas} personas may answer.",
    },
    "context and memory": {
        "title": "Context and memory",
        "lines": ("Context", "and memory"),
        "note": "One sitting, {max_turns} prior turns",
        "plain": "A sitting keeps its state and its prior turns.",
        "detail": "In this record, up to {max_turns} prior turns go into each prompt.",
    },
    "tool and action interfaces": {
        "title": "Tool and action interfaces",
        "lines": ("Tool and action", "interfaces"),
        "note": "Text in, text out, no tools",
        "plain": "Adapters accept text and return text.",
    },
    "operational knowledge": {
        "title": "Operational knowledge",
        "lines": ("Operational", "knowledge"),
        "note": "Codexes and the house block",
        "plain": "Each persona's codex, the shared house block and the persona profiles are text "
                 "the model sees. Guidance a model can read is advice, not enforcement, so every "
                 "safety check lives in code instead.",
    },
    "sandboxing": {
        "title": "Sandboxing",
        "lines": ("Sandboxing",),
        "note": "No agent-run code to contain",
        "plain": "Model output is text only.",
    },
    "permission model": {
        "title": "Permission model",
        "lines": ("Permission", "model"),
        "note": "Gate, latch, holds in code",
        "plain": "The crisis gate, the latch and holds decide in code before any model is called. "
                 "When the gate fires, the crisis card goes out and no model answers. Each operator "
                 "control names who may use it and what authorizes it (record 2 below).",
    },
    "verification, evaluation and observability": {
        "title": "Verification, evaluation and observability",
        "lines": ("Verification, evaluation", "and observability"),
        "note": "Audit row on every turn",
        "plain": "Every turn writes an audit row judged by {layers} layers ({layer_names}), and the "
                 "worst layer wins.",
    },
    "execution runtime and lifecycle management": {
        "title": "Execution runtime and lifecycle management",
        "lines": ("Execution runtime and", "lifecycle management"),
        "note": "No checkpoint or resume",
        "plain": "The sitting has its lifecycle records.",
        "detail": "In this record, a failed model call is retried {retries}, with a "
                  "{timeout}-second transport timeout.",
    },
}

THEMES = {
    "light": {"bg": "#ffffff", "band": "#f6f8fa", "ink": "#1f2328", "quiet": "#59636e",
              "axis": "#818b98", "good": "#1a7f37", "warn": "#9a6700", "tint": "0.12"},
    "dark": {"bg": "#0d1117", "band": "#151b23", "ink": "#f0f6fc", "quiet": "#9198a1",
             "axis": "#656c76", "good": "#3fb950", "warn": "#d29922", "tint": "0.15"},
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"


def number_word(count: int) -> str:
    return NUMBER_WORDS[count] if 0 <= count < len(NUMBER_WORDS) else f"{count:,}"


def joined(items: list[str]) -> str:
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def load(path: Path = RECORD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def decision_word(register_path: Path = REGISTER) -> str:
    register = json.loads(register_path.read_text(encoding="utf-8"))
    for record in register["records"]:
        if record["file"] == ADR_FILE:
            return str(record["decision"])
    raise KeyError(f"{ADR_FILE} is not in the register")


def _components(record: dict[str, Any]) -> list[dict[str, Any]]:
    components = record["active_specification"]["records"]["release"]["components"]
    names = [component["name"] for component in components]
    if names != list(COMPONENTS):
        raise ValueError("the record's components differ from the eight this page describes")
    return list(components)


def _values(record: dict[str, Any]) -> dict[str, Any]:
    spec = record["active_specification"]
    components = {component["name"]: component for component in _components(record)}
    generation = components["execution runtime and lifecycle management"]["configuration"]["generation"]
    rows = record["audit_rows"]
    layers = sorted(rows[0]["verdict"]["layers"]) if rows else []
    retries = int(generation["retries"])
    timeout = float(components["execution runtime and lifecycle management"]["configuration"]
                    ["adapter_transport_timeout_seconds"])
    return {
        "personas": number_word(len(spec["records"]["release"]["loaded_roster_source_hashes"])),
        "max_turns": components["context and memory"]["configuration"]["max_turns"],
        "layers": number_word(len(layers)),
        "layer_names": joined(layers),
        "retries": {0: "never", 1: "once", 2: "twice"}.get(retries, f"{number_word(retries)} times"),
        "timeout": f"{timeout:g}",
    }


def _status_counts(components: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"implemented": 0, "partial": 0, "not-implemented": 0}
    for component in components:
        counts[component["status"]] += 1
    return counts


def headline(components: list[dict[str, Any]]) -> str:
    counts = _status_counts(components)
    total = number_word(len(components)).capitalize()
    return (f"{number_word(counts['implemented']).capitalize()} of {number_word(len(components))} "
            f"implemented, {number_word(counts['partial'])} partial, "
            f"{number_word(counts['not-implemented'])} declared not implemented"
            if counts["partial"] or counts["not-implemented"] else f"All {total} implemented")


def _component_bullet(component: dict[str, Any], values: dict[str, Any]) -> str:
    text = COMPONENTS[component["name"]]
    status = STATUS_WORDS[component["status"]]
    reason = component.get("reason", "")
    parts = [f"**{text['title']}: {status}.**"]
    if reason:
        parts.append(f"The record's reason: \"{reason}\"")
    else:
        parts.append(text["plain"].format(**values))
    if "detail" in text:
        parts.append(text["detail"].format(**values))
    evidence = ", ".join(f"[`{path}`](../{path})" for path in component["evidence"])
    parts.append(f"Evidence: {evidence}.")
    return "- " + " ".join(parts)


def render_page(record: dict[str, Any], decision: str) -> str:
    spec = record["active_specification"]
    closed = record["closed_specification"]
    rows = record["audit_rows"]
    components = _components(record)
    values = _values(record)
    counts = _status_counts(components)
    active_hash = record["header"]["specification_hash"]
    closing_hash = closed["specification_hash"]
    pairing = spec["records"]["run_start"]["model_pairing"]
    requested, reported = pairing["requested"], pairing["host_reported"]
    recorder = spec["startup_attestation"]["recorder"]
    release = spec["records"]["release"]
    versions = release["components"][0]["versions"]
    declared = spec["records"]["declared_changeable"]
    events = spec["records"]["material_change_events"]
    run_end = closed["records"]["run_end"]
    outcome = run_end["outcome"]
    turns = run_end["final_turn_ordinal"]
    ordinals = [row["sitting_turn_ordinal"] for row in rows]
    stamped = [row["specification_hash"] for row in rows]
    stamps_match = bool(rows) and all(value == active_hash for value in stamped)
    null_events = all(row["material_change_event_id"] is None for row in rows)

    def version(key: str) -> str:
        return versions[key]

    packs = [f"{key.split(':', 1)[1]} {value}" for key, value in versions.items() if key.startswith("pack:")]
    controls = ", ".join(f"`{control['field']}`" for control in declared["operator"])
    releases = outcome.get("release_counts", {})
    if len(releases) == 1 and next(iter(releases.values())) == outcome["accepted_turns"]:
        release_text = (f"all {number_word(int(outcome['accepted_turns']))} released under "
                        f"`{next(iter(releases))}`")
    else:
        release_text = "released " + (joined([f"{count:,} under `{reason}`" for reason, count in
                                              releases.items()]) or "none")
    statuses = {row["verdict"]["status"] for row in rows}
    holding = {tuple(sorted((name, verdict) for name, verdict in row["verdict"]["layers"].items()
                            if verdict != "PASS")) for row in rows}
    verdict_line = ""
    if len(statuses) == 1 and len(holding) == 1 and next(iter(holding)):
        layers_held = next(iter(holding))
        said = joined([f"the {name} layer returned `{verdict}`" for name, verdict in layers_held])
        verdict_line = f" In this sitting every audit verdict was `{next(iter(statuses))}`, because {said}."

    lines: list[str] = []
    add = lines.append
    add("<!-- Generated by evals/render_harness_spec.py from examples/harness-five-turn.json; "
        "do not edit by hand. tests/test_harness_spec_page.py fails when this page and its "
        "record disagree. -->")
    add("")
    add("# SecondSignal harness specification")
    add("")
    add(f"This page writes down SecondSignal's harness in the format proposed by Gertler, Novelli "
        f"and Floridi ([Towards Portable Specification of the Agent Harness]({PAPER}), Digital "
        f"Ethics Center, Yale University): one model pairing, eight components and five records. "
        f"Every value on it is read from the recorded sitting beside it, "
        f"[`harness-five-turn.json`](harness-five-turn.json), specification hash "
        f"`{active_hash[:12]}`, and a test fails if the page and the record disagree.")
    add("")
    add("## What this is")
    add("")
    add("A harness is everything around a model that is not the model, and it looks different "
        "from one system to the next. In the case of SecondSignal, the harness makes the decisions, "
        "so the model isn't expected to. It decides who speaks and whether it is safe to; the "
        "model only writes the words.")
    add("")
    add("Where many teams work to make models better at making decisions, Tyler Herigstad, who "
        "built SecondSignal, took the decision out of the model's hands.")
    add("")
    add(f"The record is a {number_word(turns)}-turn demonstration sitting on a scripted test "
        f"model, `{requested['model_id']}` version {requested['model_version']}, written by "
        f"`{recorder['name']}` {recorder['version']}.")
    add("")
    add("## The eight parts")
    add("")
    add("<picture>")
    add('  <source media="(prefers-color-scheme: dark)" srcset="harness-five-turn-dark.svg">')
    add(f'  <img src="harness-five-turn-light.svg" alt="{escape(headline(components))}: the eight '
        f'components in the paper\'s three bands, with their status in this record" width="760">')
    add("</picture>")
    add("")
    gaps = counts["partial"] + counts["not-implemented"]
    add(f"{number_word(counts['implemented']).capitalize()} of the eight components are "
        f"implemented, {number_word(counts['partial'])} are partial and "
        f"{number_word(counts['not-implemented'])} are declared not implemented. "
        + ("Every gap carries its reason in the record, as the paper asks." if gaps else ""))
    for band, _term, start, stop in BANDS:
        add("")
        add(f"### {band}")
        add("")
        for component in components[start:stop]:
            bullet = _component_bullet(component, values)
            if component["name"] == "verification, evaluation and observability":
                bullet = bullet.replace(" Evidence: ", verdict_line + " Evidence: ", 1)
            add(bullet)
    add("")
    add("## The five records")
    add("")
    add("The paper asks for five records, not one, and all five are present here, including the "
        "empty ones.")
    add("")
    add(f"1. **Release: what ships.** The eight components with their versions: harness "
        f"{version('harness')}, policy {version('policy')}, crisis card {version('crisis_card')}, "
        f"language packs {joined(packs)}. It also holds SHA-256 hashes of "
        f"{len(release['governing_files'])} governing files and of the "
        f"{number_word(len(release['loaded_roster_source_hashes']))} loaded personas.")
    add(f"2. **Declared changeable: what may change.** "
        f"{number_word(len(declared['operator'])).capitalize()} operator controls, each with its "
        f"actor, authorization and evidence: {controls}. The list for personas and model calls "
        + ("is empty." if not declared["personas_and_model_calls"] else "is not empty."))
    add(f"3. **Run start: what is present when the sitting begins.** The components, the model "
        f"pairing and the {len(spec['records']['run_start']['initial_state'])}-field initial "
        f"state, attested by the recorder. The requested model, `{requested['model_id']}` version "
        f"{requested['model_version']}, and the model the host reported, "
        f"`{reported['model_id']}` version {reported['model_version']}, are separate fields.")
    add("4. **Material change events: what changed during the sitting.** "
        + ("None in this sitting." if not events else f"{len(events):,} in this sitting.")
        + " A change keeps its old and new values, who asked, what authorized it, the turns it "
          "was in force and whether it was reversed, in a log that is append-only, chained by "
          "SHA-256 and checked on read.")
    add(f"5. **Run end: the configuration and outcome at the close.** "
        f"{number_word(int(outcome['accepted_turns'])).capitalize()} turns accepted "
        f"(`{outcome['reason']}`), {release_text}, with closing hash "
        f"`{closing_hash[:12]}`.")
    add("")
    add("The paper's sharpest worry, an agent editing its own harness, is answered by record 2: "
        "no persona and no model call can change anything.")
    add("")
    add("## The stamp on every turn")
    add("")
    span = (f"turns {ordinals[0]} to {ordinals[-1]}" if ordinals == list(range(1, len(ordinals) + 1))
            else "turns " + joined([str(value) for value in ordinals]))
    add(f"Every audit row names the exact harness that produced it, with three stamps: the active "
        f"specification hash, the turn's number in the sitting, and the material change in force. "
        f"In this sitting all {number_word(len(rows))} rows carry `{active_hash[:12]}`, {span}, "
        + ("and an explicit null for the change" if null_events else "and the change in force")
        + (", matching the record's header." if stamps_match else "; not every row matches the header."))
    add("")
    add("The specification hash is SHA-256 over the record's sorted JSON, leaving out only its "
        "own field. Change one byte of a governing file, a version or a control, and the hash "
        "changes. A row whose stamps disagree with the active specification raises an error.")
    add("")
    add("## What it does not claim")
    add("")
    add("- **Tamper-evident, not tamper-proof.** The program that writes the event log can still "
        "rewrite its files. A coordinated rewrite of the log and its local receipts needs an "
        "independently kept anchor to expose it.")
    add("- **Not self-enforcing.** The code and its tests enforce the controls. The record says "
        "which controls were in force.")
    add("- **Runtime is partial,** as the execution runtime component above says.")
    review = ("built and tested, and not yet independently reviewed"
              if decision == "Proposed" else "the decision recorded in the register")
    add(f"- **{decision}.** The decision record, [{ADR_LABEL}](../docs/adr/{ADR_FILE}), is "
        f"{decision}: {review}.")
    add("")
    add("## Check it yourself")
    add("")
    add(f"- **The record:** [`harness-five-turn.json`](harness-five-turn.json) holds the header, "
        f"both snapshots and the {number_word(len(rows))} audit rows.")
    add("- **The code:** [`spec.py`](../src/secondsignal_harness/spec.py) builds and validates "
        "the record, and [`event_log.py`](../src/secondsignal_harness/event_log.py) keeps the "
        "chained change log.")
    add(f"- **The hashes:** in full, the active hash is `{active_hash}` and the closing hash is "
        f"`{closing_hash}`. `validate_specification` in spec.py recomputes each from the record's "
        f"contents and raises if they differ.")
    add("- **This page:** `python evals/render_harness_spec.py` reports whether the page and its "
        "pictures still match the record, and "
        "[`tests/test_harness_spec_page.py`](../tests/test_harness_spec_page.py) runs that check "
        "with the rest of the suite.")
    add("")
    add("## Sources")
    add("")
    add(f"- Nicolas Gertler, Claudio Novelli and Luciano Floridi, [Towards Portable Specification "
        f"of the Agent Harness]({PAPER}), Digital Ethics Center, Yale University, arXiv "
        f"2610.40917, 29 October 2026.")
    add(f"- [{ADR_LABEL} ({decision}): the harness is a versioned part of the system]"
        f"(../docs/adr/{ADR_FILE}).")
    add("")
    return "\n".join(lines)


def render_picture(record: dict[str, Any], theme: str) -> str:
    colours = THEMES[theme]
    components = _components(record)
    values = _values(record)
    active_hash = record["header"]["specification_hash"]
    title = headline(components)
    width, column, gap, top = 226, 226, 16, 76
    box_width, box_height, box_gap = 206, 88, 12

    def text(x: float, y: float, words: str, size: float = 13, weight: int = 400,
             fill: str = "ink") -> str:
        return (f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" font-weight="{weight}" '
                f'fill="{colours[fill]}">{escape(words, quote=False)}</text>')

    def box(x: float, y: float, status: str) -> str:
        if status == "not-implemented":
            return (f'<rect x="{x:g}" y="{y:g}" width="{box_width}" height="{box_height}" rx="8" '
                    f'fill="none" stroke="{colours["axis"]}" stroke-width="1.25" '
                    f'stroke-dasharray="4 4"/>')
        colour = colours["good"] if status == "implemented" else colours["warn"]
        return (f'<rect x="{x:g}" y="{y:g}" width="{box_width}" height="{box_height}" rx="8" '
                f'fill="{colour}" fill-opacity="{colours["tint"]}" stroke="{colour}" '
                f'stroke-width="1.5"/>')

    def swatch(x: float, status: str) -> str:
        if status == "not-implemented":
            return (f'<rect x="{x:g}" y="550" width="16" height="12" rx="3" fill="none" '
                    f'stroke="{colours["axis"]}" stroke-width="1.25" stroke-dasharray="3 3"/>')
        colour = colours["good"] if status == "implemented" else colours["warn"]
        return (f'<rect x="{x:g}" y="550" width="16" height="12" rx="3" fill="{colour}" '
                f'fill-opacity="{colours["tint"]}" stroke="{colour}" stroke-width="1.25"/>')

    height = top + 56 + 4 * box_height + 3 * box_gap + 12 + 52
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 {height}" width="760" '
        f'height="{height}" role="img" font-family="{FONT}">',
        f"<title>{escape(title, quote=False)}</title>",
        f'<rect width="760" height="{height}" rx="12" fill="{colours["bg"]}"/>',
        text(24, 32, title, 15, 600),
        text(24, 54, f"The paper's three bands, each component's status as recorded in "
                     f"{active_hash[:12]}", 11.5, 400, "quiet"),
    ]
    for index, (band, term, start, stop) in enumerate(BANDS):
        x = 24 + index * (column + gap)
        members = components[start:stop]
        band_height = 56 + len(members) * box_height + (len(members) - 1) * box_gap + 12
        parts.append(f'<rect x="{x}" y="{top}" width="{width}" height="{band_height}" rx="8" '
                     f'fill="{colours["band"]}"/>')
        parts.append(text(x + 12, top + 24, band, 13, 600))
        parts.append(text(x + 12, top + 40, term, 11.5, 400, "quiet"))
        for row, component in enumerate(members):
            y = top + 56 + row * (box_height + box_gap)
            shown = COMPONENTS[component["name"]]
            parts.append(box(x + 10, y, component["status"]))
            for line, words in enumerate(shown["lines"]):
                parts.append(text(x + 22, y + 24 + 16 * line, words, 13, 600))
            parts.append(text(x + 22, y + 58, STATUS_WORDS[component["status"]].capitalize(),
                              11.5, 400, "quiet"))
            parts.append(text(x + 22, y + 74, shown["note"].format(**values), 11.5))
    parts.extend([
        swatch(24, "implemented"), text(46, 560, "Implemented", 11.5),
        swatch(134, "partial"), text(156, 560, "Partial", 11.5),
        swatch(219, "not-implemented"), text(241, 560, "Not implemented, with its reason in the record", 11.5),
        "</svg>",
    ])
    return "\n".join(parts) + "\n"


def outputs(record: dict[str, Any] | None = None, decision: str | None = None) -> dict[Path, str]:
    record = load() if record is None else record
    decision = decision_word() if decision is None else decision
    result = {PAGE: render_page(record, decision)}
    for theme, path in PICTURES.items():
        result[path] = render_picture(record, theme)
    return result


def stale(rendered: dict[Path, str]) -> list[Path]:
    return [path for path, contents in rendered.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != contents]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the harness specification page from its record.")
    parser.add_argument("--write", action="store_true", help="write the page and both pictures")
    args = parser.parse_args(argv)
    rendered = outputs()
    if args.write:
        for path, contents in rendered.items():
            path.write_text(contents, encoding="utf-8", newline="\n")
        print(f"wrote {len(rendered)} files")
        return 0
    behind = stale(rendered)
    for path in behind:
        print(f"stale: {path.relative_to(ROOT).as_posix()}")
    if not behind:
        print("the page and both pictures match the record")
    return 1 if behind else 0


if __name__ == "__main__":
    sys.exit(main())
