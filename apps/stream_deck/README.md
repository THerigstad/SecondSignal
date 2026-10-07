# The Stream Deck kit

This kit makes three profiles for a 15-key Stream Deck: TESTING SECONDSIGNAL,
BUILDING, and MUSIC. A plain JSON list holds each profile's pages and keys.
Change a list, run the generator, and import the new files. The deck is
regenerated from its lists and is never rebuilt by hand.

## The lists and the command

The three starting examples are in `apps/stream_deck/profiles/`: `TESTING.json`,
`BUILDING.json`, and `MUSIC.json`. Copy all three beside the repository and edit
those copies. Keep personal addresses, program paths, and artwork outside the
repository. The examples deliberately use `PLACEHOLDER:` targets.

From the repository root, run:

```text
python -m apps.stream_deck.make_profile --keys "../TESTING.json" --out "../DECK OUTPUT" --record-icons --offline
```

Each list names its two companions, so this one command makes all three
profiles. A list without companions makes just its own profile; repeat
`--keys` to supply other profiles in the same run. Python 3.10 or newer is
needed. Pillow supplies PNG images; without it, the generator explains once
that it will write SVG images only. `--offline` skips website requests while
still extracting icons from local programs.

The output folder holds the three `.streamDeckProfile` files, their icon sets,
the small ask and reset scripts, a `custom` folder for artwork, `KEY CARD.txt`,
`FETCH REAL ICONS.bat`, a short `README.txt`, and the generation report.
The key card lists every position, including empty
spots, and ends with NEEDS ART and PLACEHOLDERS lists. The report records each
icon's source and any fallback. `--record-icons` also records the chosen icon
source in the copied input lists. Do not use it on the repository's examples.

## Fetch real website icons later

The supplied profiles are built offline. Website tiles have a dark slate
background, the site's name in white, and its first letter large. Local program
icons are still extracted; personal pictures and `reserved.png` still win.

When wanted, double-click `FETCH REAL ICONS.bat` in DECK OUTPUT with internet
access. It runs the same generator on the same three lists, fetches site
favicons, and regenerates the three profiles. It needs Python 3.10 or newer
and Pillow and installs nothing automatically. The window reports any missing
prerequisite. Import the refreshed profile files again afterward.

## Import and use

Double-click each `.streamDeckProfile` file. The Stream Deck app asks to import
it; accept the import for each of the three files. Select the first profile
in the app. Its switch keys connect the three profiles; MUSIC's switch back
to TESTING is on its More page. Folder pages receive a Back key at the top
left automatically. When replacing a previous import, keep one active copy
of each profile and check the app's profile names before removing an old copy.

Keep DECK OUTPUT in place: the ask and New session keys open scripts stored
there. The ask keys need the Talking Table running. Start the Table first;
its existing launcher opens the browser. Ask keys send an ordinary message
such as `Could I talk to Vandal?`; the Table decides who sits. New session
uses the Table's existing reset action. The scripts need a working Windows
Python `.pyw` association to open without a console window. The Table launcher
explains how to install Python if it cannot find it.

The Table address defaults to port 8765. For another port, set
`SECONDSIGNAL_TABLE_PORT` before opening Stream Deck, and update the Table page
address in the list. The standalone ask script also accepts a character name
and then a port; reset accepts a port. A stopped Table makes either script exit
quietly. A key does not start or change the model, voice, or room lights.

STOP types `Stop. Hold.` and Enter into the window that has focus. It's in
types the operator's approved standing request and Enter into that window.
Focus the intended chat before pressing either key.

## Change a key

Positions are `[column, row]`: columns 0 through 4 go left to right, and rows
0 through 2 go top to bottom. Keep one key per position. The generator checks
the position, key kind, known character, folder destination, and profile
switch destination, and names the key if the list is wrong.

Key kinds are `website`, `open`, `text`, `hotkey`, `folder`, `switch`, `ask`,
`reserved`, and `empty`. A key has an `id`, `title`, `position`, and `kind`.
Its `target` is an address, local path, fixed text, shortcut such as
`Windows+H`, page ID, or profile ID as appropriate. Ask keys use `character`.
Text keys use `enter: true` when Enter should follow. New session uses the
special open target `@reset`. Leave position `[0, 0]` out of sub-page lists;
the generator adds Back. `home` identifies the first page.

The three generated profiles use stable UUIDs so their switch keys agree.
The purchased music profile is an explicit `external_profiles` entry; enter
the UUID from that profile's export. An unresolved external UUID, or any
target beginning `PLACEHOLDER:`, gets an inactive reserved tile instead of a
dead link. Reserved keys have no active shortcut.

## Icons and personal artwork

Artwork is chosen in this order:

1. A matching custom file wins. Put `<key id>.png` or `<key id>.svg` in
   DECK OUTPUT/custom, or in an Icons folder beside the key lists. A custom
   file in `custom` takes priority. Keep the optional `<key id>@2x.png` beside
   it; the supplied profile format uses the 144-pixel version, so the
   288-pixel original is preserved without being substituted.
2. Program and website keys use the real program icon or a fetched website
   icon. The generator tries the site's touch icon or favicon, then Google's
   favicon service. It never draws a replacement logo. Offline mode skips
   website requests but keeps local program extraction. An unavailable icon
   uses an original labelled tile and records the fallback.
3. Other keys use original simple tiles: the seven character colours and
   names, amber for Start the Table, white with dark text for STOP, and dark
   slate for navigation and work keys. Reserved tiles have warning stripes
   along their bottom third unless custom `reserved.png` or `reserved.svg`
   is present.

Personal artwork uses these IDs: `velour_youtube`,
`velour_core_international`, `bandcamp`, `soundcloud`, `fourthwall`,
`vandal_bot`, `calen_bot`, and `music_ground`. A missing personal image gets
a bright magenta NEEDS ART tile, with the key's title beneath that warning.
Filenames must match the key ID and extension exactly, including letter case,
even on Windows: `stop.png` matches `stop`; `Stop.png` does not. Unrelated
pictures are ignored.

Generated tiles and raster artwork are written as 144 by 144 PNG and SVG
versions when Pillow is available. The SVG version of raster art embeds the
image, so it needs no outside file. For custom SVG artwork, supply a matching
PNG too if both formats are wanted: Pillow cannot rasterize arbitrary SVG,
and a lone SVG is preserved as SVG with that limitation recorded.

No light control, smart-light plugin, or credential belongs in a key list or
on this deck. The room lights remain the Table's, and their key stays only
in the Table's encrypted settings. Keep account information and personal
paths in the operator's copies, never in this folder's examples or README.
