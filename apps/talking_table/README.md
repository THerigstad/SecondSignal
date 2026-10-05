# Talking Table

A prototype for the operator and adults the operator knows. Not a crisis service.

The table is a local browser interface to the repository's policy layer and
voice harness. It uses Python's standard library and plain browser JavaScript.
The policy and harness are the ones in `src/`, unchanged, including their
documented gaps. A crisis card appears only when the policy escalates; the app
never changes that decision.

Built by Codex (the ChatGPT desktop app's coding mode) on 29 and 30 September
2026 from the operator's build orders, reviewed and merged on 4 October 2026;
the decisions it carries are in the register (ADR-0026, ADR-0029) and in the
operator's rulings of 28 September and 3 October 2026.

## Start

Clone the repository; the table needs the `src/`, profiles, packs and codex
documents beside it and runs from the repository root. On Windows, open
`apps/talking_table` and double-click **Start SecondSignal.bat**. It checks
the Python launcher, then `python`, for Python 3.10 or newer, starts the local
server, and opens the default browser. If Python is missing or too old, it opens
the official download page and explains what is needed. Install Python, then
double-click the launcher again. Keep its window open while using the table;
closing it stops the server.

The default address is `http://127.0.0.1:8765/`. If the browser does not open,
open the address printed in the launcher window. The pretend model works without
a key or a paid account. No package installation or browser build step is needed.
On any system with Python 3.10 or newer, `python -m apps.talking_table` from the
repository root does the same as the launcher.

## Use the table

Type a message, then press **Send**. The policy selects the seated character and
any assist; the page lights their plates. House lines remain separate from
character replies. A crisis turn shows only the card and stops voice playback.
The **why** drawer shows the policy's explanation and the harness's audit verdict.
On crisis turns it shows a nameless summary of the safety action; the
card and safety action are unchanged, but character-routing details are omitted
from both the response and its audit row. Other turns retain the policy explanation.

You can send another message while a model is waiting. Each turn runs the policy
before key or message-content checks. Model work runs outside the session lock;
a new accepted turn cancels pending replies, and late replies cannot replace a
crisis card. Model requests have a 15-second app deadline and at most four may
remain active. A vendor call that cannot be stopped occupies a slot until it exits;
full slots withhold ordinary replies and do not prevent crisis cards.

Settings choose the model family, model identifier, character presentation,
the voice (see **Voice** below), operator-circle mode, and the country for the
crisis card's resource line (none by default, which reads the directory line;
declared United States reads 988 and 911; declared, never inferred, and saved
only with **Remember**; the operator's answer 10 of 12, 4 October 2026). The character
presentation and name choices last for the visit, and a visit is the server
session: they hold until **New session** or a restart, a reload or a paired
phone joining does not reset them, and **Remember** never saves them (the
operator's answer of 4 October 2026). Operator-circle mode starts off. It permits an otherwise
eligible reply only when the cultural audit is unlocked and only for the operator
and known adults; it never overrides the crisis gate or other audit failures.
The screen and settings dialog continuously show the active mode, including on
card and pairing screens. Other open tabs and phones refresh this status every
second and when brought back into view. A lost connection retains the last
confirmed status until the server can be reached again.

Model replies cannot supply house lines or crisis cards. The app checks output
before the harness can store, audit, display or voice it, with the same checks
in both operator-circle modes. It rejects detected house identity, source and
authority claims, card/handoff labels, and character-to-human takeover language,
including normalized case, punctuation and Unicode variants. It also rejects
house-line labels and claims about the reply itself, and second-person house
identity claims such as "you are the house", including contractions and plural
forms. Executable `javascript:`, `vbscript:` and `data:` URL schemes are rejected
as bare text when a non-whitespace character immediately follows the colon;
colon-space prose remains allowed. Before these checks, the detection copy folds
look-alike letters through the project's `SKELETON` map without rewriting an
accepted reply. A rejected reply
uses the existing fixed failure message; the rejected text is discarded. The
policy alone supplies the real card and house lines. These are deterministic
language checks with regression coverage, not a proof of recognition of every
possible paraphrase or language.

Real models may cost money. The pretend model is free.

A free Gemini key from Google AI Studio works for testing. On the free tier Google
may use what you type, so use test messages only.

Select the correct vendor and enter that vendor's model identifier and key.
For **Other compatible host**, enter the vendor's own compatible endpoint. Keys
are sent only to the selected vendor address. The page never displays a saved key.

**New session** clears the conversation on screen and resets the policy session.
It also clears a key that was not remembered; the selected model can stay the
same, so enter its key again when needed. It does not erase existing audit
records. Changing settings preserves the policy session and its safety latch.
Closing the server clears in-memory session state. Conversations are not restored
when the server starts again.

## Storage and keys

By default, audit records and remembered settings are stored outside the repository, in
`~/.secondsignal/talking-table/`, where `~` means the current user's home folder.
The page shows the actual storage location. The audit log includes submitted
messages, accepted model output including replies withheld by the harness audit,
decisions, and audit verdicts. The app discards oversized output, markup, detected
house/character impersonation, credential echoes, and model exception text before
the harness can store them. Known credentials in free-text fields are redacted;
crisis records omit character-routing details. Fixed policy cards and schema
constants remain verbatim. Superseded pending replies are not appended after
cancellation. Anyone with access to that folder can read those audit records.

Keys stay in memory unless **remember on this computer** is selected. On Windows,
remembered settings are written to `settings.json` in that same folder, with the
key encrypted using the current account's Windows data protection service.
Remembered credentials are not written in plaintext and are not portable to
another account. Unchecking remembrance removes the saved credential. Keys never
appear in audit records, server logs, responses, or page source.

## Phone access

The default listener is only `127.0.0.1`. Turn on **Let my phone on this Wi-Fi use
the table** from the computer's settings to enable local network access. The
computer shows a six-digit pairing code and a phone address. Open that address
on the phone and enter the code once. Settings remain controlled from the
computer; the phone can send turns and start a new session.

Use only trusted Wi-Fi: the local connection uses HTTP, so pairing does not
encrypt messages in transit. Access from another website is refused. Turn phone
access off to return to access from this computer only.

## Voice

The table can speak a character's reply through ElevenLabs, called by the
server and never by the page. The voice key is entered in Settings next to the
model key and follows its own remember and forget rules; it stays on the server
and never reaches the browser, a log, a response, or the audit. There are 28
voice slots, one for each character and each presentation (as written, woman,
man, neither), all empty until the operator enters voice IDs; none is invented.
Voice stays off until a key and a slot for the current presentation are set,
and a mute control is visible whenever voice is on, pinned to the top of the
page with the mode banner.

**What speaks.** A reply speaks only after it has passed every check the table
already applies, and only through a single-use token the server issues for that
exact audited text: the browser never sends text, a character, or a voice ID,
and the token dies on a new turn, a Settings change, a key rotation, **New
session**, or a crisis card, including for a reply still waiting at the vendor.
A reply the audit ships speaks. An operator-circle release speaks while the
mode is on, and the voice carries the label the screen already shows on it
(ruling 6 of 3 October 2026). On the turn right after a crisis card the whole
reply is spoken once, in the seated character's voice: the character's text,
then the attached safety lines in the order the screen shows them, the
acknowledgment and then the resource line (ruling 24 of 3 October 2026).

**What never speaks.** The crisis card, withheld replies, failure lines, the
house's own turns, and high-risk turns are silent, and the card stops any voice
playing in the same tab. Later turns in the aftermath speak the character's
text alone; the screen keeps the quiet resource reminder, and the voice never
reads it a second time (ruling 16 of 3 October 2026). With the cultural audit
layer unlocked, the audit withholds the turn after a card as high risk, in
operator-circle mode too, so that turn is silent until the rubric is locked.

**Limits.** No reply is lost to a limit. The server accepts up to 20 MB of
audio, about seventeen minutes at the vendor's 128 kbps, where the longest reply
the table can release is under 5,600 characters, about eight and a half minutes
read slowly; it waits up to a minute for the vendor. The browser bounds only the
wait for the audio (75 seconds) and never the playback. A cancelled request may
still run and be billed at the vendor; that is recorded as open work. Before
pairing, a phone on the Wi-Fi learns only the operator-circle mode and its
revision, never the voice state or anything else that moves with a turn.

## Optional voice and lights

Voice and room lights are optional, and the lights module and
`static/sigils.html` are now in the tree. Lights start in pretend mode: they
choose the scene without sending anything to bulbs. Enter a Govee key only in
the computer's Settings panel, **Lights key**, then turn on **Lights on real
bulbs**; **Remember lights on this computer** protects it with this Windows
account, otherwise **New session** or shutdown clears it. The key never belongs
in a chat, a file in the tree, or a packet. The lights follow whoever the policy
seats, and the crisis card is always white. A light failure never changes or
delays a turn. The lights view opens at `/static/sigils.html`; the Stream Deck
addresses in `LIGHTS.md` work too. Voice uses only checked replies and the
server's single-use token, and a card stops it; there is no microphone or
browser speech recognition. The table still works if either optional module
is missing.

## Local checks

From the repository root, `python -m apps.talking_table --no-browser --port 0`
chooses a free port, or supply `--data-dir` pointing outside the repository for
isolated tests. The launcher sets `PYTHONUTF8=1` and
`PYTHONDONTWRITEBYTECODE=1`. No key belongs in a command line.

The app endpoints include `POST /api/turn` with `{"text": "..."}` and
`GET /api/state`. The returned decision and safety action reflect the real
harness. The browser and paired clients must meet the server's same-origin and
pairing checks.

The outer HTTP limit is 65,536 bytes. Within that boundary, the complete text goes
through the policy layer before the ordinary 16,000-character message limit.
The policy's documented gaps and its processing time on unusually long tokens
remain unchanged. No real model, key, microphone, light, or phone is needed for
the local scripted regression checks.
