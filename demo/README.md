# The demonstration page

`index.html` runs this repository's real package inside the visitor's browser: Python compiled to WebAssembly (Pyodide, from one pinned address), the package's own files fetched from beside the page and verified by SHA-256 against `manifest.json` before anything runs, and the page's network access turned off once it has booted. A visitor types a message and watches the decision; one button runs the labelled-case suite (`tests/test_eval_cases.py`, the file CI runs) through pytest in the browser; another runs the three external review sets and shows every disagreement. Every number on the page comes from that run. Nothing typed leaves the page.

The seat plates show each persona's two name forms with their labels, and a presentation setting (as written, women, men, neither) changes what the plates show and how the seat is named, never the decision (ADR-0026 (Proposed), amendment 1); the page's acceptance run checks that the decision record is byte-identical under all four.

Build the site locally from the repository root with `python demo/build_site.py --out _site`, which copies the runtime files beside the page and writes the manifest from the tree as it stands; serve `_site` with any static server. `tests/test_demo_site.py` checks the manifest against the tree. The workflow `.github/workflows/pages.yml` builds and publishes the same site on every push to `main` that touches it.

The page was built by OpenAI Codex (GPT-6) from a written order of the Primary Design Agent, to a design by ChatGPT-6 Astra, in two rounds on 10 and 11 September 2026; the order, the acceptance evidence and the two defects the builder caught in the order are on record in [`docs/notes/demo-build-2026-09-11.md`](../docs/notes/demo-build-2026-09-11.md).
