# The room lights

1. Get a key: in the Govee Home app open Profile, then Settings, then Apply for API Key, and submit the form; Govee sends you the key (asking for a new key switches off the old one).
2. Start the Talking Table: it starts in pretend mode, which chooses the scene but sends nothing to bulbs.
3. Put the key only in the Table's Settings panel, **Lights key**, and turn on **Lights on real bulbs**; use **Remember lights on this computer** if you want it kept, and never put it in a file or a chat.

The lights take the colour of whoever the house seats, white for the crisis card, dim amber when nobody is seated. Turning **Lights on real bulbs** off or forgetting the key returns to pretend mode. Without the remember switch, **New session** or shutdown clears the key; with it, Windows protects the saved key for this account.

Stream Deck: give each key the Website action with one of these addresses, replacing TABLE with the address the Talking Table shows when it starts.

- Cody: `http://TABLE/sigils.html?ask=cody`
- Ellis: `http://TABLE/sigils.html?ask=ellis`
- Nikki: `http://TABLE/sigils.html?ask=nikki`
- Rowan: `http://TABLE/sigils.html?ask=rowan`
- Seren: `http://TABLE/sigils.html?ask=seren`
- Vandal: `http://TABLE/sigils.html?ask=vandal`
- Willow: `http://TABLE/sigils.html?ask=willow`

Each press of a Website key opens a new browser tab, so tabs stack up over a session; close them now and then, or use one tab the deck re-uses if the deck software offers it.

Keep the deck's **GET request in background** option OFF for these keys: the page's script sends the ask, so with that box ticked nothing is sent and nothing says so.

There is no Govee plugin on the deck for SecondSignal, because it would set colours behind the policy and could show a character colour during the crisis card.

Each key sends "Could I talk to NAME?" as an ordinary message; the house decides who sits. The colours live in `sigil_colors.json`; after changing them, run `python apps/talking_table/lights.py --sync-page` so the phone page matches.

This is a prototype for the operator and adults the operator knows. It is not a crisis service.


## Test lights without a turn — order T3

Settings has a **Test lights** button. On the computer it posts to
`/api/lights/check`: each roster colour, about two seconds per scene, then card
white and idle, through the same worker and saved lamp settings. Lights off or
no key gives: “Lights are off or not set up; nothing to show.” A real turn cancels
the sequence and a crisis card holds the floor. Paired phones cannot start the
check. It adds no turn, decision, receipt or audit row. The project manager can
point the reserved Stream Deck Lights check key at this path later.
