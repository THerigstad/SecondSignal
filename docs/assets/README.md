# Assets

Every image in this directory is generated or drawn, and every one carries
its provenance here and, in full, in [`generation-prompts.json`](generation-prompts.json):
the tool, the family, the door, the date, the prompt as far as it is on
record, the operator's steering verbatim, and the attempts that were
rejected. Where a prompt was not written down at the time, the record says
so; nothing is reconstructed. The record is checked: `tests/test_assets.py`
holds every recorded hash to the committed file and every alt text a page
uses to the alt text recorded here.

The rules for pictures in this repository, as ruled by the operator on 10
September 2026: no portraits anywhere near a crisis line; no lock and no
shield, ever; no labels, names or capabilities inside an image (those belong
in real text beside it); the hero keeps its seven rooms, its shared light
and its empty courtyard; and a third-party image is never committed, whatever
the reason it was looked at.

## The files

- **`secondsignal-house.png`** (1774 × 887). The seven-room house at dusk,
  the repository's hero. Generated with ChatGPT's built-in image generation,
  through the Codex desktop app, by the operator on 8 September 2026 and
  chosen by him from five variants; byte-identical to the copy in the
  strategy packet it arrived in. The prompt was not saved with the packet;
  the generator's own literal description of the image is kept in the
  prompts file in its place. Alt text, on record: *Seven open rooms in a
  shallow concrete arc, each lit the same warm amber, facing an empty gravel
  courtyard with one stone bench at dusk. Nobody is seated: which room
  lights up is decided outside the rooms.*
- **`secondsignal-mark.svg`**, **`secondsignal-mark-dark.svg`**. The doorway
  mark: two nested open doorways on one baseline, charcoal and rust (ivory
  and rust on the dark ground). Drawn as SVG by the Primary Design Agent on
  9 September 2026 from the concept geometry ChatGPT-6 Astra proposed the
  same day; the four concept prompts are in the prompts file verbatim; the
  raster concepts they produced are in the operator's archive and are not
  committed. The mark carries no letters and survives a rename.
- **`confessions-train.png`** (1774 × 887). The picture at the top of
  [`docs/confessions.md`](../confessions.md): a small rust-and-grey toy
  train, a single long railcar, lying straight across the oval loop of
  track it was meant to follow, one end on each curve, pointing straight
  ahead where the track bends. Attempt 1, Grok 4.6, 9 September 2026: rejected,
  off-spec on three counts (a caption baked into the image, a pile-up of
  several yellow cars tangled in loops of track, none of the house
  palette); the file is not here and never will be. Attempt 2, ChatGPT
  (Work) 6 Astra, Extra High, 9 September 2026 at 7:52 PM the operator's
  local time: chosen. His steering of both generators is in the prompts
  file verbatim; a third-party meme was shown as a pose reference only,
  with the instruction not to copy it, and the result shares the joke, not
  the frame. The committed file is the operator's file after a lossless
  optimisation (every pixel identical, checked) so it renders on GitHub
  under the two-megabyte line. Caption, as real text beside it: *Passes more
  tests than the last one did.*
- **`routing-tree.svg`**. The seat-versus-hold routing tree of ADR-0016,
  drawn on 10 September 2026 in the four tokens.
- **`review-round.svg`**. How a review round works here, drawn the same
  day; the numbers on it come from the fixture runner and the committed
  result pages.
- **`social-preview.png`** (1280 × 640). The house with the mark in one
  corner, composed on 10 September 2026 for the repository's social preview
  so a link unfurls with the house. Not used in the README.

## Palette

Working tokens, chosen 9 September 2026 and revisitable: ivory `#F5F1E8`,
charcoal `#252823`, rust `#A64527`, sage `#9B9B7F`. Charcoal on ivory
measures about 13.2:1, ivory on rust about 5.3:1; sage is an accent, never
small text on ivory.

## License

The images in this directory, like the character documents under
[`docs/codex/`](../codex/), are licensed under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International
([`LICENSE-CONTENT`](../../LICENSE-CONTENT)), not under the MIT license
that covers the code. The characters and their pictures are the operator's;
the policy layer is open.
