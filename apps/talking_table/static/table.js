/* The surface displays the harness result. It never decides a safety action. */
"use strict";
(() => {
  // One deterministic formatter for the Table, phone and Stream Deck. The
  // receipt is the same safe object written beside audit.jsonl, never model text.
  function decisionSummary(receipt) {
    if (!receipt || typeof receipt !== "object") return "Decision receipt unavailable.";
    if (receipt.gate_withheld) return "The crisis card holds the floor. No character is seated. The gate withheld speech. No model was called.";
    const names = receipt.display_names || {};
    const name = id => names[id] || id;
    const clauses = [receipt.seat ? name(receipt.seat) + " sat." : "No character was seated."];
    if (receipt.assist) clauses.push(name(receipt.assist) + " assisted.");
    const holds = receipt.holds || [];
    clauses.push(holds.length ? "Held: " + holds.map(hold => hold.domain + " (" + hold.duration + ")").join("; ") + "." : "No holds were active.");
    for (const item of receipt.set_aside || receipt.vetoes || []) clauses.push(name(item.persona) + " was set aside: " + item.reason + ".");
    clauses.push(receipt.audit_withheld ? "The audit withheld speech." : "Neither the gate nor the audit withheld speech.");
    clauses.push(receipt.model_called ? "A model was called." : "No model was called.");
    if (receipt.regulation) clauses.push(receipt.regulation);
    for (const reason of receipt.preference_adjustments || []) clauses.push(reason);
    return clauses.join(" ");
  }
  window.SecondSignalDecisionCard = decisionSummary;
  // The phone imports only the shared formatter above.
  if (!document.getElementById("composer")) return;
  const $ = id => document.getElementById(id);
  const state = {config: null, busy: false, ready: false, count: 0, last: null,
    request: 0, rendered: 0, cardBarrier: 0, epoch: 0, pending: new Set(),
    submissions: new Map(), paused: false, queued: [], lowDemand: false, showTable: false, lastCardRevision: -1, serverSession: null,
    operatorCircle: null, modeRevision: -1, modePolling: false, circleDirty: false};
  const familyLabels = {fake: "Pretend model · free", gemini: "Gemini", openai: "OpenAI", anthropic: "Anthropic", xai: "xAI", compatible: "Compatible host"};

  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  async function api(path, data) {
    const options = {credentials: "same-origin", cache: "no-store", headers: {"Accept": "application/json"}};
    if (data !== undefined) {
      options.method = "POST";
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(data);
    }
    let response;
    try { response = await fetch(path, options); }
    catch (_) { throw new Error("The local server could not be reached. Check that its window is still open."); }
    let result;
    try { result = await response.json(); }
    catch (_) { throw new Error("The server could not return this request. Please try again."); }
    // Mode metadata is also supplied with a pairing-required response. It is
    // independent of turn rendering and never exposes conversation contents.
    applyOperatorMode(result);
    if (!response.ok) {
      const error = new Error(result.error || "The request could not be completed.");
      error.pairingRequired = Boolean(result.pairing_required);
      throw error;
    }
    return result;
  }

  function applyOperatorMode(result) {
    if (!result || typeof result !== "object") return;
    const snapshot = result.state && typeof result.state === "object" ? result.state : result;
    voiceCall("updateState", snapshot);
    const enabled = typeof snapshot.operator_circle === "boolean" ? snapshot.operator_circle : result.settings && result.settings.operator_circle;
    const revision = snapshot.mode_revision === undefined ? result.mode_revision : snapshot.mode_revision;
    if (typeof enabled !== "boolean") return;
    if (Number.isSafeInteger(revision) && revision >= 0) {
      if (revision < state.modeRevision) return;
      state.modeRevision = revision;
    } else if (state.modeRevision >= 0) return;
    state.operatorCircle = enabled;
    if (state.config) state.config.settings.operator_circle = enabled;
    const label = "Operator-circle mode is " + (enabled ? "ON." : "OFF.");
    for (const id of ["operator-circle-status", "settings-operator-circle-status"]) {
      const banner = $(id);
      if (banner.textContent !== label) banner.textContent = label;
      banner.dataset.mode = enabled ? "on" : "off";
    }
    // The checkbox is a local draft while Settings is open; the banners always
    // describe the effective server mode, including changes from another tab.
    if (!$("settings-dialog").open || !state.circleDirty || (state.config && !state.config.local)) {
      $("operator-circle").checked = enabled;
    }
  }

  async function pollOperatorMode() {
    if (state.modePolling) return;
    state.modePolling = true;
    try {
      const snapshot = await api("/api/state");
      adoptSession(snapshot);
      if (snapshot.state === "card" && typeof snapshot.card === "string" &&
          Number.isSafeInteger(snapshot.card_revision) && snapshot.card_revision > state.lastCardRevision) {
        receiveCard({kind: "card", card: snapshot.card, receipt: snapshot.receipt,
          decision: snapshot.decision || {}, verdict: null, state: snapshot});
      }
    }
    catch (_) { voiceCall("stopAll"); /* Silence while server state is unknown. */ }
    finally { state.modePolling = false; }
  }

  function status(id, text, error = false) {
    $(id).textContent = text || "";
    $(id).classList.toggle("error", error);
  }

  function setBusy(busy) {
    state.busy = busy;
    // A pending model must not disable a new message or hold live-region updates.
    $("app").setAttribute("aria-busy", "false");
    for (const id of ["message", "send", "microphone"]) {
      $(id).disabled = busy || !state.ready;
    }
    const updating = busy || state.pending.size > 0;
    for (const id of ["new-session", "settings-open"]) $(id).disabled = updating || !state.ready;
    $("presentation").disabled = updating || !state.ready || !state.config || !state.config.local;
    document.querySelectorAll(".form-choice").forEach(button => { button.disabled = updating || !state.ready || !state.config.local; });
    $("send").firstChild.textContent = "Send ";
    $("stop-waiting").disabled = state.pending.size === 0;
    $("save-presentation").disabled = updating || !state.ready || !state.config || !state.config.local;
  }

  function voiceCall(method, argument) {
    try {
      const voice = window.SecondSignalVoice;
      if (voice && typeof voice[method] === "function") {
        const result = argument === undefined ? voice[method]() : voice[method](argument);
        if (result && typeof result.catch === "function") result.catch(() => {});
      }
    } catch (_) { /* Optional voice errors cannot change the visible turn. */ }
  }

  function refreshMicrophone() {
    let available = false;
    try { available = Boolean(window.SecondSignalVoice && typeof window.SecondSignalVoice.canListen === "function" && window.SecondSignalVoice.canListen()); }
    catch (_) { /* An absent or unavailable microphone is ordinary. */ }
    $("microphone").hidden = !available;
  }

  function namePair(profile) {
    const settings = state.config.settings;
    const choice = settings.presentation || "as_written";
    const pair = profile.names[choice] || profile.names.as_written;
    const chosen = settings.chosen_names && settings.chosen_names[profile.id];
    return choice === "neither" && chosen ? [chosen, "they"] : pair;
  }

  function nameOf(id) {
    const profile = state.config.roster.find(item => item.id === id);
    return profile ? namePair(profile)[0] : "";
  }

  function drawTable() {
    const target = $("plates");
    target.replaceChildren();
    state.config.roster.forEach((profile, index) => {
      const plate = el("div", null, "plate");
      plate.dataset.persona = profile.id;
      plate.dataset.state = "idle";
      plate.setAttribute("role", "group");
      plate.title = profile.one_line;
      const names = el("div", null, "plate-names");
      const pair = namePair(profile);
      const neither = state.config.settings.presentation === "neither";
      profile.plate.forEach(([name, pronoun], formIndex) => {
        const selected = name === pair[0] && (neither || pronoun === pair[1]);
        const form = el(neither ? "button" : "span", name, neither ? "form-choice" : "form-name");
        form.classList.toggle("selected", selected);
        if (neither) {
          form.type = "button";
          form.disabled = state.busy || state.pending.size > 0 || !state.config.local;
          form.setAttribute("aria-pressed", String(selected));
          form.setAttribute("aria-label", "Choose " + name + " with they pronouns");
          form.addEventListener("click", () => chooseName(profile.id, name));
        }
        names.append(form);
        if (formIndex === 0) names.append(el("span", "/"));
      });
      plate.append(names, el("p", "Not seated", "plate-status"));
      target.append(plate);
      if (index === 2) {
        const center = el("div", null, "table-center-band");
        const centerName = el("p", "Waiting for a turn");
        centerName.id = "table-center";
        center.append(centerName, el("span", "THE POLICY HOLDS THE FLOOR"));
        target.append(center);
      }
    });
    paintTable(state.last);
  }

  function paintTable(turn) {
    const card = turn && turn.kind === "card";
    const seated = card ? null : turn && turn.persona;
    const assist = card ? null : turn && turn.assist;
    document.querySelectorAll(".plate").forEach(plate => {
      const id = plate.dataset.persona;
      const mode = id === seated ? "seated" : id === assist ? "assisting" : "idle";
      plate.dataset.state = mode;
      const label = mode === "seated" ? "Seated" : mode === "assisting" ? "Assisting" : "Not seated";
      plate.querySelector(".plate-status").textContent = label;
      const profile = state.config.roster.find(item => item.id === id);
      plate.setAttribute("aria-label", profile.plate.map(pair => pair[0]).join(" / ") + "; " + label);
    });
    if ($("table-center")) $("table-center").textContent = seated ? nameOf(seated) : turn ? "No character seated" : "Waiting for a turn";
    $("table-footnote").textContent = seated ? "The policy seated " + nameOf(seated) + (assist ? "; " + nameOf(assist) + " is assisting." : ".") : "No one is seated until the policy decides.";
    $("turn-count").textContent = state.count ? state.count + (state.count === 1 ? " turn" : " turns") : "No turns yet";
  }

  function refreshPresentationNames() {
    document.querySelectorAll(".character-name").forEach(node => {
      node.textContent = nameOf(node.dataset.persona) + (node.dataset.suffix || "");
    });
  }

  function modelFields() {
    const adapter = $("adapter").value;
    $("gemini-note").hidden = adapter !== "gemini";
    $("compatible-fields").hidden = adapter !== "compatible";
    $("vendor-url").required = adapter === "compatible";
  }

  function applyConfig(config) {
    state.config = config;
    adoptSession(config.state);
    state.circleDirty = false;
    applyOperatorMode(config);
    const settings = config.settings;
    // A late config response must not overwrite a newer mode snapshot.
    if (state.operatorCircle !== null) settings.operator_circle = state.operatorCircle;
    for (const [id, field] of [["adapter", "adapter"], ["model", "model"], ["vendor-url", "url"], ["presentation", "presentation"]]) $(id).value = settings[field] || (field === "presentation" ? "as_written" : "");
    $("remember").checked = Boolean(settings.remember);
    $("locale").value = settings.locale || "";
    applyStyleControls(settings);
    renderPreviews();
    $("voice-enabled").checked = Boolean(settings.voice_enabled);
    $("voice-remember").checked = Boolean(settings.voice_remember);
    $("voice-key").value = "";
    $("voice-key-status").textContent = settings.voice_key_set ? "A voice key is set. Leave blank to keep it; its value is never returned to the page." : "No voice key is set.";
    $("lights-enabled").checked = Boolean(settings.lights_enabled);
    $("lights-remember").checked = Boolean(settings.lights_remember);
    $("lights-key").value = "";
    $("lights-key-status").textContent = settings.lights_key_set ? "A lights key is set. Leave blank to keep it; its value is never returned to the page." : "No lights key is set.";
    drawVoiceSlots(config);
    $("operator-circle").checked = Boolean(settings.operator_circle);
    $("api-key").value = "";
    $("key-status").textContent = settings.key_set ? "A key is set. Leave this field blank to keep it; its value is never returned to the page." : "No key is stored for this session.";
    $("model-label").textContent = familyLabels[settings.adapter] || "Selected model";
    $("connection").textContent = config.local ? "On this computer" : "Paired on Wi-Fi";
    $("storage").textContent = config.storage;
    $("settings-storage").textContent = config.storage;
    $("sigils-link").hidden = !config.sigils_available;
    const remote = !config.local;
    for (const id of ["model-settings", "voice-settings", "lights-settings", "circle-settings", "network-settings", "presentation-settings"]) $(id).disabled = remote;
    $("save-settings").hidden = remote;
    $("remote-settings-note").hidden = !remote;
    const phone = config.phone || {};
    $("phone-mode").checked = Boolean(phone.enabled);
    $("phone-details").hidden = !phone.enabled || remote;
    $("pairing-code").textContent = phone.code || "";
    $("phone-urls").replaceChildren();
    (phone.urls || []).forEach(url => {
      const link = el("a", url, "phone-url");
      link.href = url;
      link.target = "_blank";
      link.rel = "noopener";
      $("phone-urls").append(link);
    });
    modelFields();
    drawTable();
    refreshPresentationNames();
  }

  function drawVoiceSlots(config) {
    const body = $("voice-slots");
    body.replaceChildren();
    const choices = [["as_written", "As written"], ["women", "Woman"], ["men", "Man"], ["neither", "Neither"]];
    config.roster.forEach(profile => {
      const row = el("tr");
      const label = profile.plate.map(pair => pair[0]).filter((value, index, names) => names.indexOf(value) === index).join(" / ");
      const heading = el("th", label);
      heading.scope = "row";
      row.append(heading);
      choices.forEach(([presentation, title]) => {
        const cell = el("td"), input = el("input");
        input.type = "text";
        input.autocomplete = "off";
        input.spellcheck = false;
        input.maxLength = 128;
        input.placeholder = "Voice ID";
        input.dataset.voicePersona = profile.id;
        input.dataset.voicePresentation = presentation;
        input.setAttribute("aria-label", label + " · " + title + " voice ID");
        input.value = (config.settings.voice_slots || {})[profile.id]?.[presentation] || "";
        cell.append(input);
        row.append(cell);
      });
      body.append(row);
    });
  }

  function voiceSlots() {
    const slots = {};
    document.querySelectorAll("[data-voice-persona]").forEach(input => {
      const persona = input.dataset.voicePersona;
      if (!slots[persona]) slots[persona] = {};
      slots[persona][input.dataset.voicePresentation] = input.value.trim();
    });
    return slots;
  }

  function applyStyleControls(settings) {
    const prefs = settings.declared_preferences || {};
    $("one-step").checked = prefs.pace === "one_step";
    $("shorter").checked = prefs.verbosity === "short";
    $("plain-wording").checked = prefs.directness === "plain";
    for (const [id, key] of [["style-directness", "directness"], ["style-delivery", "delivery_order"], ["style-format", "format"], ["style-humour", "humor_tolerance"]]) $(id).value = prefs[key] || "";
    $("humour-grief").checked = Boolean(settings.humour_grief);
    $("language-style").value = settings.language_style || "match";
  }

  function styleValues() {
    const prefs = {};
    if ($("one-step").checked) prefs.pace = "one_step";
    if ($("shorter").checked) prefs.verbosity = "short";
    for (const [id, key] of [["style-directness", "directness"], ["style-delivery", "delivery_order"], ["style-format", "format"], ["style-humour", "humor_tolerance"]]) if ($(id).value) prefs[key] = $(id).value;
    if ($("plain-wording").checked) prefs.directness = "plain";
    return prefs;
  }

  function renderPreviews() {
    const target = $("presentation-previews");
    target.replaceChildren();
    if (!state.config) return;
    const previews = state.config.presentation_previews || {};
    for (const [choice, title] of [["as_written", "As written"], ["women", "Woman"], ["men", "Man"], ["neither", "Neither"]]) {
      const group = el("details", null, "preview-group");
      group.open = choice === $("presentation").value;
      group.append(el("summary", title));
      for (const profile of state.config.roster) {
        const preview = (previews[choice] || {})[profile.id];
        if (!preview || typeof preview.text !== "string") continue;
        const pair = profile.names[choice] || profile.names.as_written;
        const row = el("section", null, "presentation-preview");
        row.append(el("h3", pair[0]), el("p", preview.text), el("p", "From " + preview.source, "small"));
        if (preview.voice_available === true) {
          const play = el("button", "Hear " + pair[0] + " · " + title);
          play.type = "button";
          play.addEventListener("click", async () => {
            play.disabled = true;
            try {
              const sample = await api("/api/presentation/preview", {persona: profile.id, presentation: choice});
              voiceCall("updateState", sample.state);
              voiceCall("speak", sample);
            } catch (error) { status("status", error.message, true); }
            finally { play.disabled = false; }
          });
          row.append(play);
        }
        group.append(row);
      }
      target.append(group);
    }
  }

  function applyView() {
    const card = state.last && state.last.kind === "card";
    $("workspace").classList.toggle("low-demand", state.lowDemand);
    $("low-demand").setAttribute("aria-checked", String(state.lowDemand));
    $("whole-table").hidden = !state.lowDemand || Boolean(card);
    $("whole-table").textContent = state.showTable ? "Hide the whole table" : "Show the whole table";
    $("whole-table").setAttribute("aria-expanded", String(state.showTable));
    $("table-panel").hidden = Boolean(card) || (state.lowDemand && !state.showTable);
    $("submission-history").open = !state.lowDemand;
  }

  async function showResources() {
    if (!$("resources-dialog").open) $("resources-dialog").showModal();
    const target = $("resources-content");
    target.replaceChildren(el("p", "Loading the declared resource line…"));
    try {
      const resource = await api("/api/resources");
      target.replaceChildren(el("p", resource.text));
      for (const action of resource.actions || []) {
        if (!/^(https:\/\/|tel:|sms:)/.test(action.url)) continue;
        const link = el("a", action.label, "resource-action");
        link.href = action.url;
        if (action.url.startsWith("https:")) { link.target = "_blank"; link.rel = "noopener noreferrer"; }
        target.append(link);
      }
    } catch (error) { target.replaceChildren(el("p", error.message)); }
  }

  const copingStyles = {
    jokes: {humor_tolerance: "light", directness: "gentle"},
    quiet: {pace: "one_step", verbosity: "short", humor_tolerance: "none"},
    plan: {pace: "one_step", delivery_order: "summary_first", format: "numbered"},
    person: {directness: "gentle", format: "prose"},
  };
  const copingDescriptions = {
    jokes: "Light humour; gentle directness.",
    quiet: "One step at a time; shorter replies; no humour.",
    plan: "One step at a time; summary first; numbered steps.",
    person: "Gentle directness; prose.",
  };

  function decisionCard(turn) {
    const details = el("details", null, "why decision-card");
    details.open = true;
    const plain = el("p", decisionSummary(turn.receipt), "decision-plain");
    const technical = el("details", null, "technical-record");
    const body = el("div", null, "why-content");
    const trace = turn.decision && turn.decision.explain;
    const isCard = turn.kind === "card";
    body.append(el("h4", isCard ? "Safety summary · card view" : "Decision record · policy output"), el("pre", typeof trace === "string" ? trace : "Decision record unavailable."));
    const note = turn.decision && turn.decision.presentation_note;
    if (typeof note === "string" && note) body.append(el("p", note, "notice"));
    body.append(el("h4", "Audit verdict"), el("pre", turn.verdict === null || turn.verdict === undefined ? "No model reply was audited on this turn." : JSON.stringify(turn.verdict, null, 2)));
    technical.append(el("summary", "Technical record"), body);
    details.append(el("summary", "Decision Card"), plain, technical);
    return details;
  }

  function renderReply(article, turn) {
    const text = String(turn.text || "");
    const obligations = turn.receipt && turn.receipt.obligations || [];
    // Obligations can live in any model paragraph: keep their complete reply
    // visible rather than guessing which sentences fulfil them.
    const effort = Boolean(turn.effort_contract) && !obligations.length;
    let cut = effort ? text.search(/\n\s*\n/) : -1;
    if (effort && cut < 0) {
      const sentence = /[.!?](?:["”']?)(\s+)(?=\S)/.exec(text);
      if (sentence) cut = sentence.index + sentence[0].length - sentence[1].length;
    }
    if (cut > 0 && text.slice(cut).trim()) {
      article.append(el("p", text.slice(0, cut), "reply-text"));
      const rest = el("details", null, "reply-rest");
      rest.append(el("summary", "Show the rest"), el("p", text.slice(cut), "reply-text"));
      article.append(rest);
    } else article.append(el("p", text, "reply-text"));
    if (turn.house_lines && turn.house_lines.length) article.append(el("p", turn.house_lines.join("\n"), "house-text"));
  }

  function showSettings(focusCircle = false) {
    if (!$("settings-dialog").open) {
      state.circleDirty = false;
      $("operator-circle").checked = state.operatorCircle === true;
      $("settings-dialog").showModal();
    }
    pollOperatorMode();
    if (focusCircle) $("operator-circle").focus();
  }

  function renderTurn(turn, input) {
    state.last = turn;
    state.count += 1;
    const isCard = turn.kind === "card";
    // One stop, no speaking path, and no previous character output on a card turn.
    if (isCard) {
      voiceCall("stopAll");
      if ($("settings-dialog").open) $("settings-dialog").close();
      if ($("resources-dialog").open) $("resources-dialog").close();
    }
    paintTable(turn);
    applyView();
    $("workspace").classList.toggle("card-mode", isCard);
    $("table-panel").hidden = isCard || (state.lowDemand && !state.showTable);
    $("transcript").hidden = isCard;
    $("empty-state").hidden = true;
    $("crisis").hidden = !isCard;
    $("crisis").replaceChildren();
    if (isCard) {
      $("crisis").append(el("p", turn.card, "card-text"), decisionCard(turn));
      const archivedCard = el("article", null, "turn past-card");
      archivedCard.dataset.kind = "card";
      archivedCard.append(el("p", turn.card, "house-text"), decisionCard(turn));
      $("transcript").append(archivedCard);
      status("status", "");
      return;
    }
    document.querySelectorAll(".turn").forEach(node => node.classList.toggle("current-turn", false));
    const article = el("article", null, "turn current-turn");
    article.dataset.kind = turn.kind;
    const topline = el("div", null, "turn-topline");
    topline.append(el("span", "TURN " + String(state.count).padStart(2, "0")), el("span", turn.verdict ? "Audit · " + turn.verdict.status : turn.adapter_calls > 0 ? "Model reply unavailable" : "No model called"));
    article.append(topline);
    if (turn.persona) {
      const header = el("div", null, "reply-header");
      const name = el("h3", nameOf(turn.persona), "character-name");
      name.dataset.persona = turn.persona;
      header.append(name, el("span", turn.kind === "withheld" ? "Reply withheld" : "Seated by the policy"));
      article.append(header);
    }
    if (turn.kind === "reply") {
      renderReply(article, turn);
    } else {
      article.append(el("p", turn.text, "house-text"));
    }
    if (turn.assist) {
      const assist = el("p", nameOf(turn.assist) + " is assisting.", "assist-note character-name");
      assist.dataset.persona = turn.assist;
      assist.dataset.suffix = " is assisting.";
      article.append(assist);
    }
    if (turn.notice) article.append(el("p", turn.notice, "notice"));
    if (turn.cultural_only && turn.kind === "withheld") {
      const note = el("p", "Withheld only because the cultural audit layer is not locked. See ", "withheld-note");
      const link = el("button", "Operator-circle mode in Settings");
      link.type = "button";
      link.addEventListener("click", () => showSettings(true));
      note.append(link, document.createTextNode("."));
      article.append(note);
    }
    article.append(decisionCard(turn));
    $("transcript").append(article);
    $("transcript").scrollTop = $("transcript").scrollHeight;
    // Only the server's single-use token reaches the voice, never the text. An
    // operator-circle release speaks while the mode is on, carrying the label the
    // screen already shows on it (ruling 6 of 3 October 2026).
    if (turn.kind === "reply" && turn.speech_token) {
      voiceCall("speak", {speech_token: turn.speech_token, kind: "reply", state: turn.state, release_reason: turn.release_reason});
    } else voiceCall("stopAll");
    status("status", "");
  }

  function finishSubmission(request, outcome, detail = "") {
    const submission = state.submissions.get(request);
    if (!submission || submission.outcome !== "pending") return false;
    submission.outcome = outcome;
    submission.node.dataset.state = outcome;
    submission.label.textContent = outcome[0].toUpperCase() + outcome.slice(1) + (detail ? " · " + detail : "");
    if (submission.timer && typeof window.clearTimeout === "function") window.clearTimeout(submission.timer);
    state.pending.delete(request);
    setBusy(state.busy);
    return true;
  }

  function adoptSession(snapshot, currentRequest) {
    if (!snapshot || !snapshot.session_id || snapshot.session_id === state.serverSession) return;
    const previous = state.serverSession;
    state.serverSession = snapshot.session_id;
    state.lastCardRevision = -1;
    if (previous !== null) {
      state.epoch += 1;
      for (const pending of [...state.pending]) if (pending !== currentRequest) finishSubmission(pending, "superseded", "The server session changed; your writing is recoverable.");
      state.cardBarrier = currentRequest === undefined ? state.request : currentRequest - 1;
      state.queued = [];
    }
  }

  function addSubmission(request, input) {
    const node = el("article", null, "submission");
    node.dataset.state = "pending";
    node.dataset.request = String(request);
    const label = el("p", "Pending", "submission-status");
    label.setAttribute("role", "status");
    const restore = el("button", "Restore to editor");
    restore.type = "button";
    restore.addEventListener("click", () => {
      // Preserve a newer draft too: restoration appends with a blank line.
      const draft = $("message").value;
      $("message").value = draft ? draft + "\n\n" + input : input;
      $("message").focus();
      status("status", draft ? "Submitted writing added after your current draft." : "Submitted writing restored to the editor.");
    });
    node.append(el("p", input, "user-message"), label, restore);
    $("submissions").append(node);
    $("submission-history").open = true;
    const submission = {node, label, input, outcome: "pending", timer: null};
    state.submissions.set(request, submission);
    if (typeof window.setTimeout === "function") submission.timer = window.setTimeout(() => {
      finishSubmission(request, "failed", "The wait timed out; your writing is recoverable.");
    }, 90000);
  }

  function receiveCard(turn, request) {
    const cardRevision = turn.state && turn.state.card_revision;
    // A poll can show a card before its POST returns. A repeated snapshot must
    // neither add a second turn nor supersede a later follow-up to that card.
    if (Number.isSafeInteger(cardRevision) && cardRevision <= state.lastCardRevision) return;
    state.cardBarrier = state.request;
    state.lastCardRevision = Math.max(state.lastCardRevision,
      Number.isSafeInteger(turn.state && turn.state.card_revision) ? turn.state.card_revision : -1);
    for (const pending of [...state.pending]) finishSubmission(pending, pending === request ? "completed" : "superseded", "The crisis card holds the floor.");
    state.queued = [];
    if (state.paused) $("view-status").textContent = "View paused. The crisis card is shown immediately.";
    renderTurn(turn, "");
  }

  async function send() {
    const input = $("message").value;
    if (state.busy || !state.ready || !input.trim()) return;
    voiceCall("stopAll");
    const request = ++state.request;
    const epoch = state.epoch;
    state.pending.add(request);
    addSubmission(request, input);
    // Only submission clears the editor: completion cannot erase a newer draft.
    $("message").value = "";
    setBusy(state.busy);
    status("status", "The policy is reading this turn…");
    try {
      const turn = await api("/api/turn", {text: input});
      if (epoch !== state.epoch) { finishSubmission(request, "superseded"); return; }
      adoptSession(turn.state, request);
      // Even a cancelled wait or paused view must immediately admit a card.
      if (turn.kind === "card") { receiveCard(turn, request); return; }
      const submission = state.submissions.get(request);
      if (!submission || submission.outcome !== "pending") return;
      if (turn.superseded || request <= state.cardBarrier || request < state.rendered) {
        finishSubmission(request, "superseded"); return;
      }
      state.rendered = Math.max(state.rendered, request);
      const outcome = turn.release_reason === "failure" || turn.kind === "failure" ? "failed" : turn.kind === "withheld" ? "withheld" : "completed";
      finishSubmission(request, outcome, state.paused ? "Ready when you resume this view." : "");
      if (state.paused) {
        state.queued = [{turn, input, request}];
        $("view-status").textContent = "View paused. A reply is ready.";
      } else renderTurn(turn, input);
    } catch (error) {
      if (finishSubmission(request, "failed", error.message)) status("status", error.message, true);
    } finally {
      state.pending.delete(request);
      setBusy(state.busy);
      refreshMicrophone();
    }
  }

  async function chooseName(id, name) {
    if (state.busy) return;
    setBusy(true);
    try {
      const chosen = Object.assign({}, state.config.settings.chosen_names, {[id]: name});
      applyConfig(await api("/api/settings", {chosen_names: chosen}));
      status("status", "Presentation updated. The policy rules are unchanged.");
    } catch (error) { status("status", error.message, true); }
    finally { setBusy(false); }
  }

  async function boot() {
    try {
      const config = await api("/api/config");
      applyConfig(config);
      state.ready = true;
      $("pair-panel").hidden = true;
      $("app").hidden = false;
      setBusy(false);
      refreshMicrophone();
      status("status", "Ready.");
    } catch (error) {
      if (error.pairingRequired) {
        $("app").hidden = true;
        $("pair-panel").hidden = false;
        $("connection").textContent = "Pairing needed";
        $("storage").textContent = "Pair with the computer to read its storage location before starting a conversation.";
        $("pair-code").focus();
      } else status("status", error.message, true);
    }
  }

  $("stop-waiting").addEventListener("click", () => {
    voiceCall("stopAll");
    for (const request of [...state.pending]) finishSubmission(request, "cancelled", "Stopped waiting in this view; the session is unchanged.");
    status("status", "Stopped waiting. Your writing is recoverable. A crisis card can still appear.");
  });
  $("pause-view").addEventListener("click", () => {
    state.paused = !state.paused;
    voiceCall("stopAll");
    $("pause-view").setAttribute("aria-pressed", String(state.paused));
    $("pause-view").textContent = state.paused ? "Resume this view" : "Pause this view";
    $("view-status").textContent = state.paused ? "View paused. The session continues; crisis cards still appear." : "";
    if (!state.paused) {
      const queued = state.queued;
      state.queued = [];
      for (const entry of queued) if (entry.request > state.cardBarrier) renderTurn(entry.turn, entry.input);
    }
  });
  $("low-demand").addEventListener("change", () => { state.lowDemand = $("low-demand").checked; applyView(); });
  $("whole-table").addEventListener("click", () => { state.showTable = !state.showTable; applyView(); });
  $("resources-open").addEventListener("click", showResources);
  $("resources-close").addEventListener("click", () => $("resources-dialog").close());
  $("plain-wording").addEventListener("change", () => { $("style-directness").value = $("plain-wording").checked ? "plain" : ""; });
  $("style-directness").addEventListener("change", () => { $("plain-wording").checked = $("style-directness").value === "plain"; });
  $("onboarding-open").addEventListener("click", () => {
    $("onboarding-panel").hidden = false;
    $("onboarding-choice").value = "";
    $("onboarding-confirm").disabled = true;
    $("onboarding-preview").textContent = "Nothing is saved until you confirm.";
    $("onboarding-choice").focus();
  });
  $("onboarding-choice").addEventListener("change", () => {
    const choice = $("onboarding-choice").value;
    $("onboarding-preview").textContent = copingDescriptions[choice] ? copingDescriptions[choice] + " Confirm to store these declared choices. They replace the six current style choices; other settings stay as they are." : "Nothing is saved until you confirm.";
    $("onboarding-confirm").disabled = !copingStyles[choice];
  });
  $("onboarding-skip").addEventListener("click", () => {
    $("onboarding-panel").hidden = true;
    $("onboarding-choice").value = "";
    $("onboarding-confirm").disabled = true;
    $("onboarding-preview").textContent = "Nothing is saved until you confirm.";
    $("onboarding-open").focus();
  });
  $("onboarding-confirm").addEventListener("click", async () => {
    const preferences = copingStyles[$("onboarding-choice").value];
    if (!preferences || !state.config.local) return;
    $("onboarding-confirm").disabled = true;
    try {
      applyConfig(await api("/api/settings", {declared_preferences: preferences, remember: $("remember").checked}));
      $("onboarding-panel").hidden = true;
      status("settings-status", "Your declared style choices are confirmed and saved.");
    } catch (error) { status("settings-status", error.message, true); }
    finally { $("onboarding-confirm").disabled = false; }
  });
  $("composer").addEventListener("submit", event => { event.preventDefault(); send(); });
  $("message").addEventListener("keydown", event => { if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.isComposing) { event.preventDefault(); send(); } });
  $("settings-open").addEventListener("click", () => showSettings());
  $("settings-close").addEventListener("click", () => $("settings-dialog").close());
  $("settings-dialog").addEventListener("close", () => { $("api-key").value = ""; $("voice-key").value = ""; $("lights-key").value = ""; });
  $("operator-circle").addEventListener("change", () => { state.circleDirty = true; });
  $("adapter").addEventListener("change", () => { modelFields(); if ($("adapter").value === "fake") $("model").value = "fake-1"; else if ($("model").value === "fake-1") $("model").value = ""; });
  $("settings-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.config.local) return;
    const data = {adapter: $("adapter").value, model: $("model").value, url: $("vendor-url").value, remember: $("remember").checked, operator_circle: $("operator-circle").checked, locale: $("locale").value};
    data.declared_preferences = styleValues();
    data.humour_grief = $("humour-grief").checked;
    data.language_style = $("language-style").value;
    data.voice_enabled = $("voice-enabled").checked;
    data.voice_remember = $("voice-remember").checked;
    data.voice_slots = voiceSlots();
    if ($("voice-key").value) data.voice_key = $("voice-key").value;
    $("voice-key").value = "";
    data.lights_enabled = $("lights-enabled").checked;
    data.lights_remember = $("lights-remember").checked;
    if ($("lights-key").value) data.lights_key = $("lights-key").value;
    $("lights-key").value = "";
    voiceCall("stopAll");
    if ($("api-key").value) data.key = $("api-key").value;
    $("api-key").value = "";
    $("save-settings").disabled = true;
    try {
      applyConfig(await api("/api/settings", data));
      status("settings-status", "Settings saved.");
      status("status", "Settings saved.");
    }
    catch (error) { status("settings-status", error.message, true); }
    finally { delete data.key; delete data.voice_key; delete data.lights_key; $("save-settings").disabled = false; }
  });
  $("clear-lights-key").addEventListener("click", async () => {
    $("lights-key").value = "";
    try { applyConfig(await api("/api/settings", {clear_lights_key: true, lights_remember: false})); status("settings-status", "The saved and session lights key have been forgotten."); }
    catch (error) { status("settings-status", error.message, true); }
  });
  $("clear-voice-key").addEventListener("click", async () => {
    $("voice-key").value = "";
    voiceCall("stopAll");
    try { applyConfig(await api("/api/settings", {clear_voice_key: true, voice_remember: false})); status("settings-status", "The saved and session voice key have been forgotten."); }
    catch (error) { status("settings-status", error.message, true); }
  });
  $("clear-key").addEventListener("click", async () => {
    $("api-key").value = "";
    try { applyConfig(await api("/api/settings", {clear_key: true, remember: false})); status("settings-status", "The saved and session key have been forgotten."); }
    catch (error) { status("settings-status", error.message, true); }
  });
  $("presentation").addEventListener("change", () => { renderPreviews(); $("presentation-previews").hidden = false; });
  $("presentation-preview-open").addEventListener("click", () => {
    renderPreviews(); $("presentation-previews").hidden = !$("presentation-previews").hidden;
  });
  $("save-presentation").addEventListener("click", async () => {
    if (!state.config.local) return;
    voiceCall("stopAll");
    const presentation = $("presentation").value;
    setBusy(true);
    try { applyConfig(await api("/api/settings", {presentation, chosen_names: {}})); status("status", "Presentation updated. The policy rules are unchanged."); }
    catch (error) { $("presentation").value = state.config.settings.presentation; status("status", error.message, true); }
    finally { setBusy(false); }
  });
  $("phone-mode").addEventListener("change", async () => {
    const enabled = $("phone-mode").checked;
    $("phone-mode").disabled = true;
    try { applyConfig(await api("/api/network", {enabled})); status("network-status", enabled ? "Phone access is on. Pair with the code above." : "Phone access is off."); }
    catch (error) { $("phone-mode").checked = Boolean(state.config.phone.enabled); status("network-status", error.message, true); }
    finally { $("phone-mode").disabled = false; }
  });
  $("new-session").addEventListener("click", async () => {
    if (state.busy || state.pending.size) return;
    voiceCall("stopAll");
    setBusy(true);
    const epoch = ++state.epoch;
    const request = state.request;
    try {
      const config = await api("/api/session/reset", {});
      // Ignore a response belonging to an obsolete reset operation.
      if (epoch !== state.epoch) return;
      if (request !== state.request) { applyConfig(config); return; }
      voiceCall("stopAll");
      state.last = null;
      state.count = 0;
      state.lastCardRevision = -1;
      state.queued = [];
      state.submissions.clear();
      $("submissions").replaceChildren();
      $("transcript").replaceChildren();
      $("transcript").hidden = false;
      $("crisis").replaceChildren();
      $("crisis").hidden = true;
      $("table-panel").hidden = state.lowDemand && !state.showTable;
      $("workspace").classList.remove("card-mode");
      $("empty-state").hidden = false;
      $("message").value = "";
      applyConfig(config);
      status("status", "New session. The screen and session have been cleared; existing audit rows remain on disk.");
    } catch (error) { status("status", error.message, true); }
    finally { setBusy(false); $("message").focus({preventScroll: true}); }
  });
  $("pair-form").addEventListener("submit", async event => {
    event.preventDefault();
    const button = $("pair-form").querySelector("button");
    button.disabled = true;
    try { await api("/api/pair", {code: $("pair-code").value}); $("pair-code").value = ""; await boot(); }
    catch (error) { status("pair-status", error.message, true); }
    finally { button.disabled = false; }
  });
  $("microphone").addEventListener("click", () => {
    voiceCall("listen", words => {
      if (typeof words === "string") { $("message").value = words; $("message").focus(); }
    });
  });
  window.addEventListener("load", refreshMicrophone);
  window.addEventListener("focus", pollOperatorMode);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) pollOperatorMode(); });
  window.setInterval(pollOperatorMode, 1000);
  boot();
})();
