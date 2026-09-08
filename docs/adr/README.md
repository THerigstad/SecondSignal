# Architecture decision records

One file per decision, numbered in the order they were written. A record is
never edited into a different decision: it is amended by a later record that
says so, or superseded by one, and both directions are written down.

## The register

`index.json` lists every record with two statuses that are kept apart on
purpose:

- **decision** — `Proposed` (written, not yet adopted; a citation of it must
  say so), `Accepted` (adopted; may still have no code behind it) or
  `Superseded`.
- **implementation** — `not-code` (a principle, nothing to build), `none`
  (nothing in the tree honors it yet), `partial`, `reference-unwired` (code
  exists in the tree and nothing calls it) or `built`.

`tests/test_adr_index.py` enforces the register, so a status is a fact the
tree can check rather than a line someone remembered to update:

- every record file is registered and every entry has a file;
- the status line inside each record agrees with the register;
- a record with code behind it names evidence tests that exist and modules
  that exist; a record with none names no module;
- every `ADR-NNNN` cited from `src/`, `tests/` or `evals/` resolves to an
  entry, a citation of a Proposed record carries `(Proposed)` beside it on
  the same line, and a stale marker on an Accepted record fails;
- `amends` and `supersedes` point both ways;
- every Proposed record, and every record whose implementation is `none` or
  `reference-unwired`, is named in the README, so the public claim can never
  run ahead of the tree;
- a number listed under `reserved` has no file, no entry and no citation.

Flipping a status is a human act. The checks refuse a flip the tree cannot
show: `Accepted` with an implementation other than `none` or `not-code`
needs a test that exists, and a Proposed record cited from code needs the
marker until the day it is accepted.

## Why the register exists

On 2 September 2026 ADR-0014 was written with the status "planned, no
implementation". On 6 September a reference port of the function it
describes entered the tree. The status line stayed as it was for a week and
nothing could notice, because a status line is prose. Review round 1 (five
model families, 7 to 8 September) asked, in five vocabularies, for status to
be machine-enforced; the register and its test were built the same day the
new records landed.

## Reading order

New readers: ADR-0010 (the crisis screen is a floor and fails closed),
ADR-0015 (the two-tier latch), ADR-0016 (seat versus hold), ADR-0018
(normalize before every lexicon). Then ADR-0014 and the Security Division
records that hang from it (ADR-0019, ADR-0020, ADR-0022, ADR-0023), all of
which are Proposed and say so.
