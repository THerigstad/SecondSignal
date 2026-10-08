# Talking Table

A prototype for the operator and adults the operator knows. Not a crisis service.

The table is a local browser interface to the repository's policy layer and
voice harness. It uses Python's standard library and plain browser JavaScript.
The policy and harness are the ones in `src/`; the policy decisions and their
documented gaps are unchanged. A crisis card appears only when the policy escalates; the app
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
The **Decision Card** opens with plain words from the same receipt object saved
beside the audit: who sat, the holds and their current-turn duration, who was set
aside and why, whether the gate or audit withheld speech, and whether a model was
called. A dysregulation cap adds: “Challenge voices were ineligible because this
turn read as dysregulated.” Any reduction of declared humour is explained here.
The second layer, **Technical record**, keeps the previous raw evidence. Both
layers are nameless on a crisis turn; character-routing details remain omitted
from the response and crisis audit row. Neither layer is written by a model.

Submitted writing appears immediately and stays recoverable through **Restore to
editor**. Restoring preserves any newer draft. Each submission visibly ends as
completed, withheld, failed, superseded or cancelled. **Stop waiting** ends the
local wait; **Pause this view** holds ordinary display updates without resetting
the policy session. A crisis card bypasses pause, supersedes pending replies and
stays above any late response. Enter inserts a line; Ctrl+Enter, Command+Enter or
**Send** submits. This is the first honest slice of Hang On, built where the Table
already controls it.

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
presentation and name choices are saved separately in `preferences.json` with
**Remember on this computer** in this version. They survive a server restart
without being stored beside a key. Without Remember they last for the visit
only. **New session** resets the active presentation and name choices, while
the last remembered choice stays saved for the next restart; saving a new
choice replaces it and turning Remember off removes it. A reload or a paired
phone joining does not reset the active choice. Operator-circle mode starts off. It permits an otherwise
eligible reply only when the cultural audit is unlocked and only for the operator
and known adults; it never overrides the crisis gate or other audit failures.
The screen and settings dialog continuously show the active mode, including on
card and pairing screens. Other open Table tabs follow the server event
stream, with polling when that stream is unavailable. The phone page polls the
shared sitting every second and never opens a stream. A lost connection retains the last
confirmed status until the server can be reached again.

### How replies are presented

The settings surface starts with **One step at a time**, **Shorter replies** and
**Plain wording first**. **More** exposes directness, delivery order, format and
the humour dial from none to gallows. These are the six existing style keys;
saving the setting is the person's confirmation. Message text never stores them.
With **Remember**, these choices, the grief-humour opt-in and language style live
in `preferences.json`, separately from keys; without Remember they are in memory.
The harness reads confirmed preferences through `effective_preferences` and
applies the turn's register caps before adding the **Declared preferences:** line
to the house's this-turn block. No declared style changes routing or house lines.

One step at a time asks for one next action, with the remaining model reply under
**Show the rest**. House lines, hold obligations and the crisis card stay outside
that budget. **Humour helps me grieve** changes an instruction only: humour can
reach a grief turn through the seated specialist's voice and protocols, never by
putting the humorist on the grief seat; the policy's no-joke obligations still bind.

Language style offers the language just used, English for Spanish writing, or
technical words kept in English. The Spanish pack is unreviewed and its native
review is in progress. These instructions make no new language-coverage claim.

The skippable coping-style setup asks, “When life hits hard, do you reach for
jokes, quiet, a plan, or a person?” It previews declared keys and requires an
explicit confirmation before adopting them. Skipping stores nothing.

Before applying character presentation, text previews show a line from each
character's existing codex in each presentation. A voice preview appears only
when its presentation has a configured voice ID and voice access is ready; it
uses the existing protected voice path. No preview text is generated.

Presentation and chosen names are remembered across restarts under the Remember
switch, like the other remembered settings, and never beside a key (idea-list
item 13, ruled 5 October 2026).

### Table kit two

The presentation control carries the operator's onboarding sentence: “You can
pick how everyone sounds. Who speaks is picked for your safety, and you'll
always be told why.” Each character also has an override: as written, women,
men, neither, or follow the table. Overrides use the existing profile name and
presentation forms for prompts, plates, Decision Cards and biographies, and are
remembered with the table setting under **Remember**. With no override the
existing presentation lifecycle stays the same.

Tap a name plate on the Table or phone page for its **Seat biography**: domains,
modes, contraindications and the handoffs explicitly recorded in that profile.
These words come from the loaded profile, never a model. Both name forms remain
on the plate; the panel uses the active presentation's name.

The ask acknowledgement has a strict evidence boundary: it attaches before a
seated reply only if the returned record identifies the asked character and a
different seated character. Its reason comes from the record alone. The supplied
policy has no named-character-ask field, so ordinary message text cannot produce
this line today; the missing field is recorded in the limitations and build log.
Explicit character-request controls can save a deferred ask for this sitting.
On a later turn, **Want {Asked} back now?** appears only when that character is
eligible and has not been seated; its plate has a quiet saved mark. Tapping it
sends **Could I talk to {Asked}?** through the ordinary pipeline. The offer clears
on tap, when the character sits, or on **New session**. A typed name is never
silently converted into this declared control state.

**What do you call your table?** accepts one plain-text line of at most forty
characters. It is the idle and phone-page heading and is remembered only under
**Remember**. It never enters a model prompt, receipt or audit row. **Which room
are you in?** offers none, Workshop, Parlor, Studio and Yard, with “You picked the
room; the house still picks the chair.” The selected room is remembered under
the same switch and adds its fixed working-style instruction to seated prompts.

An assist already named by the decision record produces the house's narrow
**{Assist} can be asked, too.** slip under the seated plate. Tapping it sends the
same phone-page ask text as a new turn; merely showing the slip adds nothing to
the prompt and calls no second model. The policy still decides the next seat.

**Object on the table** accepts one line of at most sixty characters for the
sitting. The policy's public crisis screen checks the object on its own before
acceptance. A line that alarms is cleared with “That line belongs in the message,
not on the table.” Accepted text appears below the seated name and in one prompt
line, never in the routed message, remembered settings or sanitized receipt.
**New session** clears it. A composer tag—plan, letter, verse, list, unsent or
none—applies to the next submitted message only, appears on that turn, and adds
one fixed prompt line. Rooms, tags and the object change how a seated character
works, never who sits.

When Cody or Seren is seated, **Start a 25-minute sprint** opens a quiet shutter
with remaining time, **Pause** and **Stop**. The clock lives in the browser;
no request carries it. The object field stays visible while messages continue
through normal routing. A sidetrack can seat another character. The sprint ends
without a sound, alarm, streak or points.

Every released character reply has **Open as a page**. It opens a printable,
saveable page containing only that released character text, its presentation
name as byline and the house footer “Written with a seated companion, not a
professional.” The server reads the released turn; the browser never posts the
reply text back. Up to three **What would {Name} add?** controls are drawn from
other eligible candidates on that turn. Held turns reserve their two optional controls for the review labels below;
hand-back, assist and second-view controls are suppressed on those turns. Earlier replies retain their own
eligibility and presentation names. They submit exactly those words as a
new turn, labelled **a second view**, with one policy-selected voice per reply.

A crisis card suppresses these extras. The only T2 addition on a card turn is
the nameless first-layer Decision Card receipt: “The house held the floor. No
character saw this message.” The model is never called for that turn.

### Low-demand view and Resources

**Low-demand view** asks for no diagnosis. It puts the current reply, its speaker
and the composer first, with the seven plates behind **Show the whole table**.
The Decision Card's plain layer stays first. The switch is labelled and announced,
and focus follows the displayed reading order. The view is entirely local: no
request carries it, and switching it does not change a session or decision.
It adds no sound or animation.

The **Resources** button stays pinned in the top toolbar in both views, including when the
card is showing. It opens the existing resource line for the declared country,
with link or call actions; without a declared country it shows the directory.
Opening it never spends or repeats the character's spoken-once resource line.

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

Live keys must satisfy the vendor terms and no-training attestation below.
The pretend model is available for testing without a vendor key.

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
The page shows the actual storage location. `audit.jsonl` keeps audit rows;
`receipts.jsonl` keeps a separate sanitized receipt for each non-crisis turn:
seat, holds and obligations, veto reasons, roster hash, audit verdicts, release
rule, fold receipt and the declared preferences actually applied. It contains
no message text, raw stems or crisis patterns. The page reads that same receipt
object; crisis turns have a nameless in-memory summary and no receipt file row.
`preferences.json` stores presentation/name choices and confirmed reply-style settings only when
Remember is selected and contains no credential. The audit log includes submitted
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
delays a turn. The lights view opens at `/static/sigils.html`; its separate **Explain this turn**
switch is off by default and adds no new explanation until enabled. When enabled,
it uses the same receipt-to-plain-words formatter as the Table's Decision Card; the Stream Deck
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

## Table kit three — 7 October 2026

**Known gaps and limitations** is generated from the case manifest, package
`__version__`, English and Spanish pack status, and ADR-0029 in the decision
register. It states the documented gap and dissent counts, unreviewed lexicons,
operator-circle exception and prototype scope. It appears once per package
version in each browser; Settings reopens it. The version acknowledgment uses
browser local storage and holds no conversation or credential.

The composer explains the shared sitting before a message is sent. Closing the
**server window** ends that sitting; closing or reloading a browser page leaves
it available to the other paired screens until **New session** or server shutdown.
The audit is durable, but it does not restore a sitting after a server restart.
No transcript-storage switch is added. A turn or New session on any paired screen
changes the same sitting on all screens.

Each change has one increasing server session version. `/api/events` sends full
current snapshots. Each stream closes after one second, even during activity;
EventSource reconnects after its advertised one-second retry. Table and review pages poll during
the gap, without treating a planned closure as an outage or stopping speech.
The phone page uses `/api/state` every second and never opens an event stream,
so virtual-time screenshots cannot stall on an in-flight stream fetch.
Unversioned legacy Table responses retain their original two-second interval.
The event endpoint remains available to paired phones. A failed phone poll
shows “The table is out of reach. Reconnecting.” and retries after one second.
Reload restores released
and withheld replies or the current card. Remote turns, including the Stream
Deck's existing ask POST, appear through the same path as locally submitted turns.
Saved snapshots never replay speech. A card bypasses paused views, closes optional
dialogs and wins over stale replies, polls and prior sessions. A lost stream says:
“The table is out of reach. Reconnecting.” No second routing state is maintained.

Before the first seated send to each live vendor, the Table displays the fixed
summary in `vendor_terms.json` and requires both summary confirmation and:
“This key is not used to train the vendor's models, as far as I know.” The summaries
are PM drafts, name each vendor's own terms page as the authority, and do not
verify account settings. Compatible hosts have separate confirmations by host;
their own terms page must be checked because no universal terms URL exists.
The pretend model needs no confirmation, and a crisis card never consults this
gate. Rejected consent leaves the policy session unchanged. `terms.json` stores
only vendor/revision acknowledgments when Remember is on; otherwise acknowledgment
lasts for this sitting. It never sits beside an API key. Turning Remember off
removes that file in the same settings transaction.

Operator-circle starts off and the Settings switch requires `operator.token` in
the Table's data folder. Generate it locally, without printing its value:

```console
python -m apps.talking_table --make-operator-token
```

For a custom data folder, pass the same `--data-dir` to this command and the server.
The command refuses a folder inside the repository, does not overwrite an existing
token, and starts no server. No token ships in the tree or appears on a page.
Without it the disabled control says: “Operator-circle mode needs the operator's
token on this computer.” The enabled banner says it is a prototype for the
operator's circle. Direct test harness construction retains its explicit mode.

Pairing records carry `phone` scope; loopback computer access carries `computer`
scope. The central authorization boundary checks all settings, presentation,
network, operator, replay, receipts-export and lights paths. A phone can send,
reset and flag turns, but cannot change those computer settings or open the
operator/replay pages, including through encoded static aliases. Turning phone
access on requires dismissing this blocking warning:

> The phone page travels over plain HTTP on your Wi-Fi. Anyone on this network who finds the address and the pairing code can read the table. Turn it on only on a network you trust.

Each released or withheld turn has two optional labels: **this was read wrong**
and **this missed me**. A tap saves the original decision, receipt, displayed text
and actual house lines, visible page version and caller scope in
`review_queue.jsonl`, privately on the computer. It changes no label, fixture or
policy state. The project manager can turn queue items into fixtures by hand.
A slow queue write cannot delay a card or put old content back over it.

**Review a careful-side read** opens `/operator.html` on the computer. The operator
reads the latch, enters a reason and invokes the existing
`clear_latch(reason, actor="operator")`. A durable request row precedes the clear;
a distinct result row records either completion or a superseded review. A changed
sitting rejects an old review. Message text gains no way to clear the latch.
The latch surface says: “A careful-side read is reviewed by the person who runs
this table. The review looks at the turn, not at you.”

**Voices set aside this week** counts recorded vetoes in the local Monday-to-Sunday
week. It displays voice/reason counts only, without message text, message dates or
streaks. **Save this week's receipt bundle** explicitly downloads those receipts
and the roster hash; the browser's normal save/download control chooses the file.
Older receipts use their linked audit timestamp; new receipts carry a timestamp.
Nothing is uploaded or exported automatically.

**Replay a logged decision** opens `/replay.html`; the Decision Card's technical
layer links the current audit row. An audit or receipt row id opens the saved
extract, ranked eligibility/score/verdict, recorded stabilizer rationale, assist,
holds, house lines and audit verdict. It reads the logged record and never routes
again. Crisis logs retain their existing nameless projection; omitted routing
fields are explicitly marked unavailable, not reconstructed.

**Test lights** calls `POST /api/lights/check`. When the configured lights switch
and key are present, the existing worker shows roster colours in order, about two
seconds after each scene completes, then card white, then idle. With lights off
or missing a key it says: “Lights are off or not set up; nothing to show.” A real
turn, reset or settings change cancels the remaining check; a card keeps the floor.
The check adds no conversation, receipt, audit row or session-version change.

The complete durable data-folder inventory is `audit.jsonl` (messages, accepted
output, decisions and operator correction records), `receipts.jsonl` (sanitized
non-crisis decision receipts), `review_queue.jsonl` (explicitly flagged snapshots),
`settings.json` (remembered settings with encrypted credentials), `preferences.json`
(remembered presentation/style choices), `terms.json` (remembered vendor consent),
and the locally generated `operator.token`. Temporary `.tmp` files exist only
while staging settings writes. No new surface stores an API key. The separate
voice and lights remember switches retain their existing behavior.
