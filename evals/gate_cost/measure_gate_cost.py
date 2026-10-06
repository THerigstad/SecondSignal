"""M1 gate and audit measurements; unchanged policy, FakeAdapter only, no network.

Run from the repository root: python evals/gate_cost/measure_gate_cost.py
The heavy-week audit is temporary and is removed before returning the report.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import inspect
import json
import os
import platform
import queue
import socket
import statistics
import sys
import tempfile
import textwrap
import threading
import time
from collections import Counter
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from apps.talking_table import server  # noqa: E402
from secondsignal import SessionState, load_roster, route  # noqa: E402
from secondsignal.safety import crisis_screen  # noqa: E402
from secondsignal_harness.adapters import FakeAdapter  # noqa: E402
from secondsignal_harness.audit_log import AuditLog, canonical_row  # noqa: E402

HERE = ROOT / "evals/gate_cost"
EVERYDAY = (
    "I would like help planning my week. I have groceries to buy, library books "
    "to return, a garden to water, and a cupboard to organize. I can start with "
    "one small task after breakfast, then make time for a walk in the park. "
)
REPLY = (
    "You could put the groceries on a list, choose a time for the library, "
    "and leave a little room for a walk. Which small task would be useful first?"
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def no_network(*args, **kwargs):
    raise RuntimeError("M1 measurement forbids network access")


@contextmanager
def offline():
    with ExitStack() as stack:
        for name in ("connect", "connect_ex", "bind", "listen", "sendto"):
            stack.enter_context(patch.object(socket.socket, name, no_network))
        for name in ("create_connection", "getaddrinfo"):
            stack.enter_context(patch.object(socket, name, no_network))
        yield


def table_message_limit():
    """Extract the actual len(text) > constant check instead of copying a ceiling."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(server.TableApp.turn)))
    limits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        left = node.left
        if (isinstance(node.ops[0], ast.Gt) and isinstance(left, ast.Call)
                and isinstance(left.func, ast.Name) and left.func.id == "len"
                and len(left.args) == 1 and isinstance(left.args[0], ast.Name)
                and left.args[0].id == "text"
                and isinstance(node.comparators[0], ast.Constant)
                and isinstance(node.comparators[0].value, int)):
            limits.append(node.comparators[0].value)
    require(len(set(limits)) <= 1, "Multiple text-length checks require review")
    return limits[0] if limits else None


def everyday_text(length):
    return (EVERYDAY * (length // len(EVERYDAY) + 1))[:length]


def labelled_inputs():
    """Match existing runners' policy/deferred split, including every trajectory turn."""
    manifest = json.loads((ROOT / "evals/case-manifest.json").read_text(encoding="utf-8"))
    dispositions = {row["id"]: row["disposition"] for row in manifest["cases"]}
    result = []
    case_dir = ROOT / "evals/cases"
    for path in sorted(case_dir.rglob("*.json")):
        if "deferred" in path.relative_to(case_dir).parts:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("plane", "policy") != "policy":
            continue
        source = path.relative_to(ROOT).as_posix()
        if doc.get("kind") == "trajectory":
            prior = []
            disposition = next((key for key in ("known_gap", "disputed", "contract_adjusted")
                                if doc.get(key)), "accepted")
            for number, turn in enumerate(doc["turns"], 1):
                result.append({"id": doc["id"], "turn": number, "kind": "trajectory",
                               "source": source, "text": turn["text"], "prior": list(prior),
                               "session": doc.get("session"), "locale": doc.get("locale"),
                               "disposition": disposition, "expect": turn.get("expect", {})})
                prior.append(turn["text"])
        else:
            for case in doc["cases"]:
                prior = [p["text"] if isinstance(p, dict) else p
                         for p in case.get("prior_turns", [])]
                result.append({"id": case["id"], "turn": None, "kind": "single",
                               "source": source, "text": case["text"], "prior": prior,
                               "session": case.get("session"), "locale": case.get("locale"),
                               "disposition": dispositions[case["id"]], "expect": case["expect"]})
    return result


def original_session(case, roster):
    """Same declared fields as test_eval_cases.make_session; replay own prior turns."""
    block = case.get("session") or {}
    session = SessionState(locale=case.get("locale"),
                           declared_language=block.get("declared_language"),
                           declared_age_band=block.get("declared_age_band", "unknown"),
                           affinities=tuple(block.get("affinities", ())),
                           preferences=dict(block.get("preferences", {})))
    for text in case.get("prior", []):
        route(text, roster, session=session)
    return session


def reference(case):
    return {key: case[key] for key in ("id", "turn", "kind", "source", "disposition")} | {
        "characters": len(case["text"]), "utf8_bytes": len(case["text"].encode("utf-8")),
        "text_sha256": hashlib.sha256(case["text"].encode("utf-8")).hexdigest(),
        "prior_turns": len(case.get("prior", [])),
    }


def machine():
    cpu = platform.processor() or platform.machine()
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
    return {"cpu": cpu, "logical_cpus": os.cpu_count(), "python": platform.python_version(),
            "implementation": platform.python_implementation(), "os": platform.platform(),
            "line": f"{cpu}; {platform.python_implementation()} {platform.python_version()}; "
                    f"{os.cpu_count()} logical CPUs; {platform.platform()}"}


def summary(samples):
    return {"repetitions": len(samples), "median_ms": round(statistics.median(samples), 6),
            "worst_ms": round(max(samples), 6), "best_ms": round(min(samples), 6),
            "samples_ms": [round(v, 6) for v in samples]}


def measure(operation, repeats, check):
    samples = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        value = operation()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
        check(value)
        del value
    return summary(samples)


def capacity(app):
    count = 0
    while app.model_slots.acquire(blocking=False):
        count += 1
    for _ in range(count):
        app.model_slots.release()
    return count


def require_busy(app):
    acquired = app.model_slots.acquire(blocking=False)
    if acquired:
        app.model_slots.release()
    require(not acquired, "The occupied condition lost a model slot")


@contextmanager
def occupied_table(app):
    """Hold real Table model permits by entering a stalled callable FakeAdapter."""
    release = threading.Event()
    entered, finished = queue.Queue(), queue.Queue()
    errors = []

    def stall(system, messages):
        entered.put(threading.current_thread().name)
        release.wait()
        finished.put(True)
        return REPLY

    adapter = FakeAdapter(script=stall)
    app.harness.adapter = adapter
    slots = capacity(app)
    require(slots > 0, "No free slots before measurement")
    callers = []

    def turn():
        try:
            app.turn(EVERYDAY)
        except Exception as exc:
            errors.append(type(exc).__name__)

    try:
        for _ in range(slots):
            caller = threading.Thread(target=turn, daemon=True, name="m1-table-caller")
            callers.append(caller)
            caller.start()
            require(entered.get(timeout=15) == "table-model", "Not a real Table model worker")
        require_busy(app)
        proof = {"actual_slots": slots, "fake_calls_started": len(adapter.calls),
                 "all_permits_occupied_before": True, "all_permits_occupied_after": False,
                 "entry_path": "TableApp.turn -> Harness.speak -> _GuardedAdapter.complete -> FakeAdapter.complete",
                 "stall": "FakeAdapter waits on an Event; no CPU spin, key or network.",
                 "supersession": "Later turns cancel prior jobs; in-flight model workers retain permits until released."}
        yield proof
        require_busy(app)
        proof["all_permits_occupied_after"] = True
        proof["fake_calls_after_measurement"] = len(adapter.calls)
    finally:
        app._cancel_jobs()
        release.set()
        for caller in callers:
            caller.join(timeout=15)
        require(all(not caller.is_alive() for caller in callers), "A Table caller did not finish")
        for _ in range(len(adapter.calls)):
            finished.get(timeout=15)
        deadline = time.monotonic() + 5
        while capacity(app) != slots and time.monotonic() < deadline:
            time.sleep(0.001)
        require(capacity(app) == slots, "Model permits were not restored")
        require(not errors, f"Table caller errors: {errors}")


def gate_times(inputs, roster, repeats, occupied_app=None):
    rows = []
    for case, session in inputs:
        text = case["text"]
        expected_screen = crisis_screen(text)
        expected_route = route(text, roster, session=copy.deepcopy(session)).to_dict()
        samples = {"crisis_screen": [], "route": []}
        for iteration in range(repeats):
            operations = ("crisis_screen", "route") if iteration % 2 == 0 else ("route", "crisis_screen")
            for operation in operations:
                if occupied_app is not None:
                    require_busy(occupied_app)
                fresh = copy.deepcopy(session)
                started = time.perf_counter_ns()
                result = crisis_screen(text) if operation == "crisis_screen" else route(text, roster, session=fresh)
                samples[operation].append((time.perf_counter_ns() - started) / 1_000_000)
                require(result == expected_screen if operation == "crisis_screen"
                        else result.to_dict() == expected_route, "Decision changed during timing")
        timings = {name: summary(v) for name, v in samples.items()}
        for name, values in timings.items():
            condition = "all Table model slots occupied" if occupied_app else "no model work in flight"
            values["plain_sentence"] = (
                f"With {condition}, {name} on this {len(text):,}-character message takes "
                f"{values['median_ms']:.1f} ms at the median and at most {values['worst_ms']:.1f} ms "
                f"in {repeats} calls, before any optional character reply."
            )
        rows.append({"input": reference(case), **timings,
                     "crisis_read": expected_screen.read, "screen_folds": list(expected_screen.screen_folds),
                     "safety_action": expected_route["safety"]["action"], "outcome": expected_route["outcome"],
                     "decision_sha256": hashlib.sha256(canonical_row(expected_route).encode()).hexdigest(),
                     "identical_decisions_every_repeat": True})
    return rows


def prepare_table(app, session):
    app.harness.session = copy.deepcopy(session)
    app.harness.transcript = []
    app.harness.turns = []


def table_probe(app, case, session):
    prepare_table(app, session)
    calls = len(app.harness.adapter.calls)
    started = time.perf_counter_ns()
    result = app.turn(case["text"])
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    return {"input": reference(case), "elapsed_ms": round(elapsed, 6), "kind": result["kind"],
            "action": result["action"], "actual_fake_calls": len(app.harness.adapter.calls) - calls}


def card_times(app, case, session, repeats, occupied=False):
    """Real Table.turn, resetting its small disk audit before each measured call."""
    samples, sizes = [], []
    for _ in range(repeats):
        if occupied:
            require_busy(app)
        # Setup is untimed. The real Table writes and rereads one actual card row.
        app.audit_path.write_text("", encoding="utf-8")
        app.harness.audit_log = AuditLog(app.audit_path)
        result = table_probe(app, case, session)
        require(result["kind"] == "card" and result["actual_fake_calls"] == 0,
                "The Table card path called a model or failed to return the card")
        require(len(app.harness.audit_log) == 1, "Table card audit did not contain exactly one row")
        samples.append(result["elapsed_ms"])
        sizes.append(app.audit_path.stat().st_size)
    return {"input": reference(case), **summary(samples), "card_returns": repeats,
            "actual_fake_calls": 0, "audit_rows_after_each_call": 1, "audit_bytes_max": max(sizes),
            "note": "Actual Table.turn including threads, admission, one disk append/receipt; session and empty-audit reset excluded. Heavy-week read cost is measured separately."}


def audit_week(directory, turns_per_day, repeats):
    """Cycle complete real everyday Table rows, changing time and canonical row id."""
    app = server.TableApp(directory)
    app.harness.adapter = FakeAdapter(script=(REPLY,))
    try:
        for length in (160, 640, 1600):
            text = everyday_text(length)
            require(crisis_screen(text).read == "MISS", "Everyday audit text failed its control")
            app.turn(text)
        templates = app.harness.audit_log.rows()
        require(len(templates) == 3 and all(row["kind"] == "seated" for row in templates),
                "Audit templates must be real seated Table rows")
        require(all(row["action"] != "HUMAN_ESCALATION" for row in templates), "Only everyday audit rows")
        count = turns_per_day * 7
        ids, digest = [], hashlib.sha256()
        with app.audit_path.open("wb") as handle:
            for index in range(count):
                row = dict(templates[index % len(templates)])
                row.pop("row_id")
                row["at"] = 1_791_158_400.0 + (index // turns_per_day) * 86400 + (
                    index % turns_per_day) * (12 * 3600 / turns_per_day)
                row_id = hashlib.sha256(canonical_row(row).encode("utf-8")).hexdigest()
                row["row_id"] = row_id
                payload = (canonical_row(row) + "\n").encode("utf-8")
                handle.write(payload)
                digest.update(payload)
                ids.append(row_id)
        size = app.audit_path.stat().st_size

        def correct_length(log):
            require(len(log) == count, "Audit opener lost rows")

        first_open = measure(lambda: AuditLog(app.audit_path), 1, correct_length)
        loaded = AuditLog(app.audit_path)
        measurements = {
            "auditlog_open_parse": measure(lambda: AuditLog(app.audit_path), repeats, correct_length),
            "table_build_harness_reopen": measure(app._build_harness, repeats, lambda h: correct_length(h.audit_log)),
        }
        missing = hashlib.sha256(b"M1 absent audit receipt").hexdigest()
        for name, row_id in (("first", ids[0]), ("last", ids[-1]), ("missing", missing)):
            measurements[f"read_{name}"] = measure(
                lambda row_id=row_id: loaded.read(row_id), repeats,
                lambda row, name=name, row_id=row_id: require(
                    row is None if name == "missing" else row is not None and row["row_id"] == row_id,
                    "Audit receipt returned the wrong row"))
        measurements["rows_in_memory_copy"] = measure(
            loaded.rows, repeats, lambda rows: require(len(rows) == count, "rows() lost data"))
        for name, values in measurements.items():
            values["plain_sentence"] = (
                f"For this {count:,}-turn week, {name} takes {values['median_ms']:.1f} ms "
                f"at the median and at most {values['worst_ms']:.1f} ms in {repeats} reads."
            )
        return {"turns_per_day": turns_per_day, "days": 7, "turns": count,
                "estimate": f"{turns_per_day:,} turns/day across seven days; the full run uses 1,000/day, about 83/hour across 12 hours, as a deliberately heavy shared-Table sizing scenario, not observed traffic.",
                "file_bytes": size, "file_mib": round(size / 1024**2, 3),
                "bytes_per_turn": round(size / count, 3), "sha256": digest.hexdigest(),
                "template_rows": len(templates), "template_message_lengths": [160, 640, 1600],
                "template_schema": templates[0]["schema"], "template_top_level_fields": sorted(templates[0]),
                "template_actions": sorted({r["action"] for r in templates}),
                "generation": "Three everyday messages through TableApp.turn -> _TableAudit -> AuditLog.append; cycle complete real rows, vary at and recompute canonical SHA-256 row_id; bulk creation avoids timing unrelated repeated writes.",
                "session_model": "Repeating independent three-turn conversations; session, decision, prompt digest and other fields remain those of each real template. Everyday text only.",
                "cache": "OS cache not flushed; first open follows file creation; these are warm-cache local-filesystem observations.",
                "first_open_after_generation": first_open, "measurements": measurements,
                "read_paths": {
                    "startup_reset_settings": "TableApp._build_harness creates AuditLog(path), eagerly reading/parsing every row; reset and update_settings call it.",
                    "append_receipt": "AuditLog.append calls read(new_row_id); read loads all text, splits lines and parses sequentially until the id; a new receipt follows the last-row path.",
                    "rows": "rows() copies dictionaries already in memory and is supplemental; no separate audit-view HTTP endpoint exists.",
                }, "temporary_file_retained": False}
    finally:
        app.close()


def run_report(*, repetitions=100, audit_repetitions=7, turns_per_day=1000,
               case_limit=None, synthetic_length=None):
    """Limits are provided for the one report-shape smoke test, not full results."""
    require(min(repetitions, audit_repetitions, turns_per_day) > 0, "Counts must be positive")
    full = (repetitions, audit_repetitions, turns_per_day, case_limit, synthetic_length) == (100, 7, 1000, None, None)
    with offline(), tempfile.TemporaryDirectory(prefix="secondsignal-m1-") as temporary:
        directory, roster = Path(temporary), load_roster()
        all_cases = labelled_inputs()
        inventory = Counter(case["kind"] for case in all_cases)
        cases = sorted(all_cases, key=lambda c: (-len(c["text"]), c["source"], c["id"], c["turn"] or 0))
        if case_limit is not None:
            cases = cases[:case_limit]
        limit = table_message_limit()
        length = synthetic_length if synthetic_length is not None else limit or 20_000
        require(length > 0 and (limit is None or length <= limit), "Invalid synthetic size")
        app = server.TableApp(directory / "gate")
        app.harness.adapter = FakeAdapter(script=(REPLY,))
        try:
            selected, rejected = None, []
            for case in cases:
                body_size = len(json.dumps({"text": case["text"]}, ensure_ascii=False).encode("utf-8"))
                if body_size > server.MAX_BODY:
                    rejected.append({**reference(case), "reason": "HTTP body ceiling"})
                    continue
                try:
                    acceptance = table_probe(app, case, original_session(case, roster))
                except server.InputError:
                    rejected.append({**reference(case), "reason": "TableApp.turn refused"})
                    continue
                selected = case
                break
            require(selected is not None, "No accepted labelled message")
            synthetic = {"id": "everyday_at_table_limit", "turn": None, "kind": "synthetic",
                         "source": "deterministic EVERYDAY repetition in this script", "disposition": "synthetic_control",
                         "text": everyday_text(length), "prior": []}
            require(crisis_screen(synthetic["text"]).read == "MISS", "Synthetic control screened")
            synthetic_acceptance = table_probe(app, synthetic, SessionState())
            inputs = [(selected, original_session(selected, roster)), (synthetic, SessionState())]
            idle = gate_times(inputs, roster, repetitions)
            card = next(c for c in all_cases if c["expect"].get("safety") == "HUMAN_ESCALATION"
                        and not c.get("prior") and crisis_screen(c["text"]).read != "MISS")
            card_session = original_session(card, roster)
            idle_card = card_times(app, card, card_session, repetitions)
            with occupied_table(app) as occupation:
                busy = gate_times(inputs, roster, repetitions, app)
                busy_card = card_times(app, card, card_session, repetitions, occupied=True)
                ordinary_probe = table_probe(app, synthetic, SessionState())
                require(ordinary_probe["actual_fake_calls"] == 0
                        and ordinary_probe["kind"] == "withheld"
                        and ordinary_probe["action"] != "HUMAN_ESCALATION",
                        "A saturated Table failed its everyday no-model control")
            comparisons = []
            for before, after in zip(idle, busy):
                require(before["decision_sha256"] == after["decision_sha256"], "Slots changed routing")
                for operation in ("crisis_screen", "route"):
                    a, b = before[operation], after[operation]
                    comparisons.append({"input_id": before["input"]["id"], "operation": operation,
                                        "median_delta_ms": round(b["median_ms"] - a["median_ms"], 6),
                                        "median_ratio_busy_over_idle": round(b["median_ms"] / a["median_ms"], 4)})
        finally:
            app.close()
        audit = audit_week(directory / "week", turns_per_day, audit_repetitions)
        gate_worst = max(row[op]["worst_ms"] for group in (idle, busy) for row in group
                         for op in ("crisis_screen", "route"))
        table_worst = max(idle_card["worst_ms"], busy_card["worst_ms"])
        audit_worst = max(row["worst_ms"] for row in audit["measurements"].values())
        receipt = audit["measurements"]["read_last"]
        receipt_matters = receipt["worst_ms"] > 250
        after_sentence = (
            f"The slowest screen/route was {gate_worst:.1f} ms "
            f"({'above' if gate_worst > 250 else 'below'} about a quarter second); "
            f"the slowest actual Table card return with a one-row audit was {table_worst:.1f} ms. "
            f"The slowest standalone audit read/open was {audit_worst / 1000:.2f} seconds "
            f"({'above' if audit_worst > 3000 else 'below'} the declared three-second meaning of 'a few seconds'). "
        )
        after_sentence += (
            f"The week's last-row receipt read took {receipt['median_ms']:.1f} ms at the median and "
            f"{receipt['worst_ms']:.1f} ms at worst. Source-based inference: AuditLog.append reads this "
            "receipt synchronously, and TableApp.turn waits for that job even on a card; "
            + ("this scan alone can delay a week's card return beyond a quarter second, despite fast "
               "one-row card samples. " if receipt_matters else
               "the one-row card samples still do not measure combined full-week card latency. ")
        )
        if max(gate_worst, table_worst) > 250:
            after_sentence += ("The cheapest honest gate next step is to profile repeated full-text normalization "
                               "and folds, then measure semantics-preserving reuse of that complete analysis; "
                               "never truncate the tail or omit the screen. ")
        if audit_worst > 3000 or receipt_matters:
            after_sentence += ("The cheapest honest receipt fix to test is reading back the just-appended "
                               "canonical row at its recorded byte offset and checking its id, preserving "
                               "on-disk receipt proof without rescanning the week. ")
            if audit_worst > 3000:
                after_sentence += "Measure streaming/indexed historical reads if whole-file opens still matter. "
        if max(gate_worst, table_worst) <= 250 and audit_worst <= 3000 and not receipt_matters:
            after_sentence += "No measured path requires a speed fix at these sizes on this machine. "
        after_sentence += "No fix is applied; finite warm runs do not establish a universal latency bound."
        policy_accepted = next(c for c in cases if c["disposition"] in {"accepted", "contract_adjusted"})
        return {"schema_version": 1, "date": "2026-10-05", "measurement_only": True,
                "scope": "full" if full else "smoke/limited", "machine": machine(),
                "method": {
                    "network": "Socket connect/connect_ex/bind/listen/sendto/create_connection/getaddrinfo blocked; no listener; FakeAdapter only.",
                    "timing": "perf_counter_ns wall time; one untimed warm-up per direct operation; alternating screen/route order; session cloning, prior replay, roster loading and result equality checks untimed.",
                    "sessions": "Deepcopy the original session after its own prior turns for every route; trajectory prior turns preserved.",
                    "folds": "Unmodified crisis_screen includes screen_fold; no mock screen, shortcut or candidate transform.",
                    "acceptance": "Largest by characters across all Table-accepted labelled policy turns, including gaps/dissents/trajectories; TableApp.turn acceptance checked.",
                    "concurrency": "All actual Table permits held by stalled FakeAdapter calls; models simulate waiting I/O, not CPU saturation. Direct functions plus 100 real Table card returns per condition.",
                    "gate_threshold_ms": 250, "audit_threshold_ms": 3000,
                },
                "input_inventory": {"single_turn_cases": inventory["single"], "trajectory_turns": inventory["trajectory"],
                                    "considered_for_largest": len(cases), "rejected_larger_inputs": rejected,
                                    "largest_accepted_or_contract_adjusted": reference(policy_accepted)},
                "table_limits": {"everyday_characters": limit, "synthetic_characters": length,
                                 "http_body_bytes": server.MAX_BODY, "source": "AST of TableApp.turn; Handler.do_POST MAX_BODY",
                                 "caveat": "The gate runs before the 16,000-character check; card turns bypass this check, but HTTP still limits the JSON body to 65,536 bytes. Everyday synthetic input uses the text ceiling.",
                                 "fallback": "If no text limit is found, use 20,000 everyday characters."},
                "acceptance_controls": [acceptance, synthetic_acceptance],
                "gate": {"idle": idle, "all_slots_occupied": busy, "occupation": occupation,
                         "comparisons": comparisons, "table_card_idle": idle_card,
                         "table_card_all_slots_occupied": busy_card, "table_everyday_under_occupation": ordinary_probe},
                "audit_week": audit, "after_sentence": after_sentence, "questions_for_operator": [],
                "sources_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                   for name in ("src/secondsignal/safety.py", "src/secondsignal/normalize.py",
                                                "src/secondsignal/router.py", "src/secondsignal_harness/audit_log.py",
                                                "apps/talking_table/server.py", "evals/case-manifest.json")}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "measurements/gate_cost_2026-10-05.json")
    args = parser.parse_args(argv)
    report = run_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report["machine"]["line"])
    for condition in ("idle", "all_slots_occupied"):
        for row in report["gate"][condition]:
            for operation in ("crisis_screen", "route"):
                timing = row[operation]
                print(f"{condition}, {row['input']['id']}, {operation}: "
                      f"median {timing['median_ms']:.3f} ms; worst {timing['worst_ms']:.3f} ms")
    for name in ("table_card_idle", "table_card_all_slots_occupied"):
        row = report["gate"][name]
        print(f"{name}: median {row['median_ms']:.3f} ms; worst {row['worst_ms']:.3f} ms; zero model calls")
    print(f"Heavy week: {report['audit_week']['turns']} turns, {report['audit_week']['file_bytes']} bytes")
    for measurement in report["audit_week"]["measurements"].values():
        print(measurement["plain_sentence"])
    print(report["after_sentence"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
