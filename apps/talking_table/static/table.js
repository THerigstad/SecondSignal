/* The surface displays the harness result. It never decides a safety action. */
"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const state = {config: null, busy: false, ready: false, count: 0, last: null,
    request: 0, rendered: 0, cardBarrier: 0, epoch: 0, pending: new Set(),
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
    try { await api("/api/state"); }
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
    state.circleDirty = false;
    applyOperatorMode(config);
    const settings = config.settings;
    // A late config response must not overwrite a newer mode snapshot.
    if (state.operatorCircle !== null) settings.operator_circle = state.operatorCircle;
    for (const [id, field] of [["adapter", "adapter"], ["model", "model"], ["vendor-url", "url"], ["presentation", "presentation"]]) $(id).value = settings[field] || (field === "presentation" ? "as_written" : "");
    $("remember").checked = Boolean(settings.remember);
    $("locale").value = settings.locale || "";
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
    for (const id of ["model-settings", "voice-settings", "lights-settings", "circle-settings", "network-settings"]) $(id).disabled = remote;
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

  function whyDrawer(turn) {
    const details = el("details", null, "why");
    const body = el("div", null, "why-content");
    const trace = turn.decision && turn.decision.explain;
    const isCard = turn.kind === "card";
    body.append(el("h4", isCard ? "Safety summary · card view" : "Decision record · policy output"), el("pre", typeof trace === "string" ? trace : "Decision record unavailable."));
    const note = turn.decision && turn.decision.presentation_note;
    if (typeof note === "string" && note) body.append(el("p", note, "notice"));
    body.append(el("h4", "Audit verdict"), el("pre", turn.verdict === null || turn.verdict === undefined ? "No model reply was audited on this turn." : JSON.stringify(turn.verdict, null, 2)));
    details.append(el("summary", "Why this turn?"), body);
    return details;
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
    }
    paintTable(turn);
    $("workspace").classList.toggle("card-mode", isCard);
    $("table-panel").hidden = isCard;
    $("transcript").hidden = isCard;
    $("empty-state").hidden = true;
    $("crisis").hidden = !isCard;
    $("crisis").replaceChildren();
    if (isCard) {
      $("crisis").append(el("p", turn.card, "card-text"), whyDrawer(turn));
      const archivedCard = el("article", null, "turn past-card");
      archivedCard.dataset.kind = "card";
      archivedCard.append(el("p", turn.card, "house-text"), whyDrawer(turn));
      $("transcript").append(archivedCard);
      status("status", "");
      return;
    }
    const article = el("article", null, "turn");
    article.dataset.kind = turn.kind;
    const topline = el("div", null, "turn-topline");
    topline.append(el("span", "TURN " + String(state.count).padStart(2, "0")), el("span", turn.verdict ? "Audit · " + turn.verdict.status : turn.adapter_calls > 0 ? "Model reply unavailable" : "No model called"));
    article.append(topline, el("p", input, "user-message"));
    if (turn.persona) {
      const header = el("div", null, "reply-header");
      const name = el("h3", nameOf(turn.persona), "character-name");
      name.dataset.persona = turn.persona;
      header.append(name, el("span", turn.kind === "withheld" ? "Reply withheld" : "Seated by the policy"));
      article.append(header);
    }
    if (turn.kind === "reply") {
      article.append(el("p", turn.text, "reply-text"));
      if (turn.house_lines && turn.house_lines.length) article.append(el("p", turn.house_lines.join("\n"), "house-text"));
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
    article.append(whyDrawer(turn));
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

  async function send() {
    const input = $("message").value;
    if (state.busy || !state.ready || !input.trim()) return;
    voiceCall("stopAll");
    const request = ++state.request;
    const epoch = state.epoch;
    state.pending.add(request);
    // Clear at submission: a late completion must never erase a newer draft.
    $("message").value = "";
    setBusy(state.busy);
    status("status", "The policy is reading this turn…");
    try {
      const turn = await api("/api/turn", {text: input});
      if (epoch !== state.epoch || turn.superseded) return;
      if (turn.kind === "card") {
        // Invalidate every request already in flight, including requests sent
        // after this card request. Only a new submission may replace this card.
        state.cardBarrier = state.request;
      } else if (request <= state.cardBarrier || request < state.rendered) return;
      state.rendered = Math.max(state.rendered, request);
      renderTurn(turn, input);
    } catch (error) {
      if (epoch === state.epoch && request === state.request && request > state.cardBarrier) status("status", error.message, true);
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

  $("composer").addEventListener("submit", event => { event.preventDefault(); send(); });
  $("message").addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); } });
  $("settings-open").addEventListener("click", () => showSettings());
  $("settings-close").addEventListener("click", () => $("settings-dialog").close());
  $("settings-dialog").addEventListener("close", () => { $("api-key").value = ""; $("voice-key").value = ""; $("lights-key").value = ""; });
  $("operator-circle").addEventListener("change", () => { state.circleDirty = true; });
  $("adapter").addEventListener("change", () => { modelFields(); if ($("adapter").value === "fake") $("model").value = "fake-1"; else if ($("model").value === "fake-1") $("model").value = ""; });
  $("settings-form").addEventListener("submit", async event => {
    event.preventDefault();
    if (!state.config.local) return;
    const data = {adapter: $("adapter").value, model: $("model").value, url: $("vendor-url").value, remember: $("remember").checked, operator_circle: $("operator-circle").checked, locale: $("locale").value};
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
  $("presentation").addEventListener("change", async () => {
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
      $("transcript").replaceChildren();
      $("transcript").hidden = false;
      $("crisis").replaceChildren();
      $("crisis").hidden = true;
      $("table-panel").hidden = false;
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
