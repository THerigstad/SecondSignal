"""Order T3: local display, consent and review surfaces; never routing inputs."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from secondsignal import __version__
from secondsignal.profiles import roster_hash
from secondsignal_harness import AuditLog

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NETWORK_WARNING = (
    "The phone page travels over plain HTTP on your Wi-Fi. Anyone on this network who finds "
    "the address and the pairing code can read the table. Turn it on only on a network you trust."
)
TOKEN_NOTE = "Operator-circle mode needs the operator's token on this computer."
REVIEW_NOTE = (
    "A careful-side read is reviewed by the person who runs this table. "
    "The review looks at the turn, not at you."
)
ATTESTATION = "This key is not used to train the vendor's models, as far as I know."
FLAGS = ("this was read wrong", "this missed me")
COMPUTER_PATHS = (
    "/api/settings", "/api/object", "/api/network", "/api/presentation/", "/api/operator/",
    "/api/replay", "/api/receipts/", "/api/lights/", "/operator.html", "/replay.html",
    "/static/operator.html", "/static/replay.html",
)


def limitations(root=ROOT, prototype="A prototype for the operator and adults the operator knows. Not a crisis service."):
    """Generate from the public-count sources, pack metadata and ADR register."""
    manifest = json.loads((root / "evals/case-manifest.json").read_text(encoding="utf-8"))
    counts = Counter(case["disposition"] for case in manifest["cases"])
    index = json.loads((root / "docs/adr/index.json").read_text(encoding="utf-8"))
    harness = next(row for row in index["records"] if row["number"] == "0029")
    packs = {name: json.loads((root / f"src/secondsignal/packs/{name}.json").read_text(
        encoding="utf-8"))["status"] for name in ("en", "es-419")}
    facts = {"documented_gaps": counts["known_gap"], "recorded_dissents": counts["disputed"],
             "lexicon": packs, "harness_decision": harness["decision"],
             "harness_implementation": harness["implementation"]}
    return {"version": __version__, "facts": facts, "lines": [
        prototype,
        f"The recorded checks still contain {counts['known_gap']} documented gaps and "
        f"{counts['disputed']} recorded dissents.",
        f"The English lexicon is {packs['en']}. The Latin American Spanish pack is {packs['es-419']}.",
        f"The voice harness is {harness['decision']} in the decision register; "
        f"its implementation status is {harness['implementation']}.",
        "Operator-circle mode can release an otherwise passing, normal-risk reply when only "
        "the unlocked cultural check is inconclusive, with the operator reviewing afterward. "
        "The crisis gate and the other checks still apply.",
    ]}


def make_operator_token(data_dir):
    """Local command only. Never return, print, overwrite or ship the token."""
    folder = Path(data_dir).resolve()
    if folder == ROOT or ROOT in folder.parents:
        raise ValueError("The storage folder must be outside the repository.")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "operator.token"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        stream.write(secrets.token_hex(32) + "\n")
    return True


class TableFeatures:
    """Mix into the existing Table; its existing lock owns the sitting."""

    def _init_features(self):
        self.session_version = time.time_ns() // 1_000_000
        self.events = threading.Condition(self.lock)
        self.closed = False
        self.display_turns = {}
        self.current_turn = None
        self.pending_turn = None
        self.review_lock = threading.Lock()
        self.correction_lock = threading.Lock()
        self.terms_lock = threading.RLock()
        self.limitations_sheet = limitations()
        self.token_ready = self.operator_token_available()
        self.review_path = self.data_dir / "review_queue.jsonl"
        self.terms_path = self.data_dir / "terms.json"
        self.confirmations = {}
        raw_terms = (HERE / "vendor_terms.json").read_bytes()
        self.vendor_terms = json.loads(raw_terms)
        self.terms_revision = hashlib.sha256(raw_terms).hexdigest()
        if self.settings["remember"] and self.terms_path.exists():
            try:
                saved = json.loads(self.terms_path.read_text(encoding="utf-8"))
                if isinstance(saved, dict) and not self._contains_key(saved):
                    self.confirmations = {k: v for k, v in saved.items()
                                          if isinstance(k, str) and isinstance(v, str)}
            except (OSError, ValueError):
                pass
        self.state["session_version"] = self.session_version

    def operator_token_available(self):
        try:
            value = (self.data_dir / "operator.token").read_text(encoding="ascii").strip()
            return bool(re.fullmatch(r"[a-f0-9]{64}", value))
        except (OSError, UnicodeError):
            return False

    def _publish(self):
        # Caller owns self.lock; no disk I/O or model operation is performed.
        self.session_version += 1
        self.state["session_version"] = self.session_version
        self.events.notify_all()

    def sitting(self):
        with self.lock:
            snapshot = copy.deepcopy(self.state)
            snapshot["session_version"] = self.session_version
            if self.state["state"] == "card":
                turns = [self.current_turn] if self.current_turn else []
            else:
                turns = list(self.display_turns.values())
                snapshot["pending_turn"] = copy.deepcopy(self.pending_turn)
                snapshot["latch"] = self.harness.session.latch
                snapshot["latch_review_note"] = REVIEW_NOTE
                snapshot["view_settings"] = {key: copy.deepcopy(self.settings[key]) for key in (
                    "adapter", "model", "presentation", "chosen_names", "house_name", "room",
                    "presentation_overrides", "remember")}
            snapshot["turns"] = copy.deepcopy(turns)
            return snapshot if self.state["state"] == "card" else self._redact(snapshot)

    def _posted(self, job):
        self.pending_turn = {"turn_id": f"{self.session_id}:{job.revision}",
                             "user_text": self._redact(job.text), "revision": job.revision}
        self._publish()

    def _displayed(self, job, result):
        self.pending_turn = None
        self._publish()
        result["turn_id"] = f"{self.session_id}:{job.revision}"
        result["page_version"] = self.session_version
        result["audit_row_id"] = getattr(job, "audit_row_id", None)
        result["state"] = copy.deepcopy(self.state)
        displayed = copy.deepcopy(result)
        displayed.pop("speech_token", None)
        if result["kind"] != "card":
            displayed["user_text"] = self._redact(job.text)
            displayed["review_house_lines"] = self._redact(list(job.result.house_lines))
        self.current_turn = displayed
        self.display_turns[result["turn_id"]] = displayed

    def _reset_features(self):
        self.display_turns.clear()
        self.current_turn = self.pending_turn = None
        if not self.settings["remember"]:
            self.confirmations.clear()
        self._publish()

    def terms_summary(self):
        family = self.settings["adapter"]
        if family == "fake":
            return None
        entry = dict(self.vendor_terms[family])
        vendor = family
        if family == "compatible":
            vendor += ":" + (urlsplit(self.settings["url"]).hostname or "")
        revision = self.terms_revision
        return {**entry, "family": family, "vendor": vendor, "revision": revision,
                "attestation": ATTESTATION,
                "confirmed": self.confirmations.get(vendor) == revision}

    def _persist_terms(self, remember=None, confirmations=None):
        remember = self.settings["remember"] if remember is None else remember
        confirmations = self.confirmations if confirmations is None else confirmations
        if remember and confirmations:
            temporary = self.terms_path.with_suffix(".tmp")
            try:
                temporary.write_text(json.dumps(confirmations), encoding="utf-8")
                temporary.replace(self.terms_path)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            self.terms_path.unlink(missing_ok=True)

    def confirm_terms(self, payload):
        # Consent storage is serialized with settings, never with a waiting card.
        with self.terms_lock:
            with self.lock:
                terms = self.terms_summary()
                if (not terms or payload.get("vendor") != terms["vendor"]
                        or payload.get("revision") != terms["revision"]
                        or payload.get("accepted") is not True or payload.get("attested") is not True):
                    raise self.input_error("Read the current vendor summary and confirm both statements.")
                confirmed = {**self.confirmations, terms["vendor"]: terms["revision"]}
                remember, session = self.settings["remember"], self.session_id
            try:
                self._persist_terms(remember=remember, confirmations=confirmed)
            except OSError:
                raise self.input_error("The computer could not save this confirmation. Try again.") from None
            with self.lock:
                if not remember and session != self.session_id:
                    raise self.input_error("The sitting changed. Confirm for the current sitting.")
                self.confirmations = confirmed
                self._publish()
                return {"confirmed": True, "vendor": terms["vendor"]}

    def honesty(self):
        return {
            "limitations": copy.deepcopy(self.limitations_sheet), "terms": self.terms_summary(),
            "operator_token_available": self.token_ready, "token_note": TOKEN_NOTE,
            "network_warning": NETWORK_WARNING,
            "session_lines": [
                "This conversation ends when the table's server window closes. "
                "Reloading or closing this page leaves the shared sitting on the computer "
                "until New session or server shutdown.",
                "audit.jsonl keeps submitted messages, accepted model output including "
                "audit-withheld replies, decisions and operator correction records.",
                "receipts.jsonl keeps non-crisis decisions without message text, raw stems or crisis patterns.",
                "review_queue.jsonl keeps only turns explicitly flagged for the operator's review.",
                "A turn or New session on either paired screen changes the same sitting on every screen; "
                "settings stay under the computer's control.",
            ],
        }

    def flag_turn(self, payload, scope):
        with self.lock:
            turn = self.display_turns.get(payload.get("turn_id"))
            version = payload.get("page_version")
            label = payload.get("label")
            if (not turn or turn["kind"] not in ("reply", "withheld") or label not in FLAGS
                    or type(version) is not int or not turn["page_version"] <= version <= self.session_version):
                raise self.input_error("Choose one of the two review labels on a displayed turn.")
            snapshot = self._redact({"schema": "secondsignal.table.review.v1", "at": time.time(),
                "turn_id": turn["turn_id"], "page_version": version, "label": label, "scope": scope,
                "audit_row_id": turn.get("audit_row_id"), "record": copy.deepcopy(turn["decision"]),
                "receipt": copy.deepcopy(turn["receipt"]), "user_text": turn.get("user_text", ""),
                "shown_text": turn["text"], "house_lines": list(turn.get("review_house_lines", turn.get("house_lines", []))),
                "kind": turn["kind"]})
        # A disk wait for review must never own the sitting or its audit lock.
        with self.review_lock:
            row_id = AuditLog(self.review_path).append(snapshot)
        return {"saved": True, "row_id": row_id}

    def correction_state(self):
        with self.lock:
            session = self.harness.session
            return {"session_id": self.session_id, "session_version": self.session_version,
                    "latch": session.latch, "reasons": list(session.latch_reasons), "note": REVIEW_NOTE}

    def _correction_row(self, row):
        with self.audit_lock:
            return self.harness.audit_log.append(self._redact(row))

    def clear_careful_read(self, payload):
        reason = self._one_line(payload.get("reason"), 500, "Review reason")
        if not reason or self._has_key(reason):
            raise self.input_error("Give a review reason without a key.")
        with self.correction_lock:
            with self.lock:
                before = self.correction_state()
                if (payload.get("session_id") != self.session_id
                        or payload.get("session_version") != self.session_version):
                    raise self.input_error("The sitting changed. Read its current state before clearing.")
                row = {"schema": "secondsignal.table.correction.v1", "kind": "operator_latch_review",
                       "at": time.time(), "reason": reason, "actor": "operator", "before": before}
            request_id = self._correction_row(row)
            with self.lock:
                applied = self.correction_state() == before
                if applied:
                    self._cancel_jobs()
                    self.harness.session.clear_latch(reason, actor="operator")
                    self.pending_turn = None
                    self.state.update(self._mode_state())
                    self._publish()
                after = self.correction_state()
            # The request is durable before clearing; the result distinguishes races.
            self._correction_row({**row, "kind": "operator_latch_clear" if applied else
                                  "operator_latch_review_superseded", "at": time.time(),
                                  "request_row_id": request_id, "applied": applied, "after": after})
            if not applied:
                raise self.input_error("The sitting changed during review; nothing was cleared.")
            return after

    def logged_decision(self, row_id):
        if not isinstance(row_id, str) or not re.fullmatch(r"[a-f0-9]{64}", row_id):
            raise self.input_error("Enter a logged audit or receipt row id.")
        receipt = self.receipts.read(row_id) if self.receipt_path.exists() else None
        audit_id = receipt.get("audit_row_id") if receipt else row_id
        if not audit_id:
            raise self.input_error("This superseded receipt has no logged decision to replay.")
        row = self.harness.audit_log.read(audit_id)
        if row is None and self.audit_path.exists():
            row = AuditLog(self.audit_path).read(audit_id)
        if not row or not isinstance(row.get("decision"), dict):
            raise self.input_error("No logged decision was found for that row id.")
        return self._redact({"row_id": audit_id, "receipt": receipt, "record": row["decision"],
                             "verdict": row.get("verdict"), "house_lines": row.get("house_lines", []),
                             "released": row.get("released"), "release_reason": row.get("release_reason")})

    def receipt_week(self, now=None):
        now = now or datetime.now().astimezone()
        monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end = monday + timedelta(days=7)
        # Read the durable sources, including rows written before this process.
        audit = {row["row_id"]: row for row in AuditLog(self.audit_path).rows()}
        receipts = []
        for row in AuditLog(self.receipt_path).rows():
            stamp = row.get("at", audit.get(row.get("audit_row_id"), {}).get("at"))
            if isinstance(stamp, (int, float)) and monday.timestamp() <= stamp < end.timestamp():
                receipts.append(row)
        return self._redact({"schema": "secondsignal.table.receipt_bundle.v1",
                            "week": monday.date().isoformat(), "roster_hash": roster_hash(self.roster),
                            "receipts": receipts})

    def refused_seats(self, now=None):
        bundle = self.receipt_week(now)
        counts = Counter()
        for row in bundle["receipts"]:
            for veto in row.get("vetoes", []):
                name = row.get("display_names", {}).get(veto["persona"], veto["persona"])
                counts[(name, veto["reason"])] += 1
        words = {1: "once", 2: "twice", 3: "three times"}
        return {"week": bundle["week"], "counts": [
            {"voice": name, "reason": reason, "count": count,
             "line": f"{name} was set aside {words.get(count, str(count) + ' times')} because {reason}."}
            for (name, reason), count in sorted(counts.items())]}

    def check_lights(self):
        with self.lock:
            if not self._lights_key():
                return {"started": False, "message": "Lights are off or not set up; nothing to show."}
            if self.state["state"] == "card":
                return {"started": False, "message": "The crisis card holds the floor."}
            self.lights.check(tuple(self.roster))
            return {"started": True, "message": "The lights will show each colour, then the card colour, then idle."}
