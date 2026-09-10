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
tree can check rather than a line someone remembered to update. Exactly what
it checks, so the guarantee is read as wide as it is and no wider:

- every record file is registered and every entry has a file;
- the status line inside each record has one grammar,
  `- **Status:** <Decision> — <implementation>; <prose>`, and both words are
  parsed exactly and compared with the register on both axes (not by prefix:
  "Accepted-but-not-adopted" is not Accepted, and "built" in the register
  with "reference-unwired" in the record fails);
- the two vocabularies are frozen inside the test, outside the file under
  test, so the index cannot widen its own schema;
- a record with code behind it names evidence tests and modules that exist,
  and an evidence entry `path::name` must be a real, collected test function
  (a name in a docstring is not a test) that carries no skip, skipif or
  xfail mark and calls neither `pytest.skip` nor `pytest.xfail`;
- every `ADR-NNNN` cited from `src/`, `tests/` or `evals/` in Python, and
  from any JSON fixture under `evals/` or `src/` in the project's own fields
  (a reviewer's verbatim fields are quoted material), resolves to an entry;
  a citation of a Proposed record carries `(Proposed)` beside it, every
  occurrence on the line; a stale marker on an Accepted record fails;
- the heading's title text equals the registered title;
- `amends` and `supersedes` point both ways in the register, and each
  record's own prose names its counterpart; a Superseded record has a
  successor;
- the README's status block is generated from the register by
  `docs/adr/render_status.py` and pinned; a decision word (Accepted,
  Proposed, Superseded) anywhere else on the README fails, so the public
  summary can never be a free sentence; every Proposed or unbuilt record is
  named there;
- a line under `docs/` that names a record in the `ADR-NNNN` form and calls
  it Accepted, Proposed or Superseded must agree with the register, unless
  the sentence is conditional (until, after, flips, becomes);
- a number listed under `reserved` has no file, no entry and no citation.

What it does not guarantee: that an evidence test passes (CI shows that for
the exact commit, and the evaluation page carries the counts from a run);
that `built` means correct; that a status claim written without the
`ADR-NNNN` form is noticed. Review round 2 (ChatGPT, mutations R01 to R14)
found the gaps the list above closes; every mutation is a red regression in
`tests/test_register_mutations.py`, including the six controls.

Flipping a status is a human act. The checks refuse a flip the tree cannot
show: `Accepted` with an implementation other than `none` or `not-code`
needs a test that exists and runs, and a Proposed record cited from code
needs the marker until the day it is accepted.

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
