/* Audio is authorized and synthesized by the table server. No credentials live here. */
"use strict";
(() => {
  // The server waits up to a minute for the vendor (VOICE_TIMEOUT); the wait
  // for the audio is bounded a little beyond that. Playback itself is never
  // bounded: a long reply plays to its end (Night Builds Review of 30
  // September 2026, required fix 2 on Codex job 2). The size limit is the
  // server's MAX_AUDIO; nothing larger is ever sent.
  const AUDIO_WAIT_MS = 75000;
  const MAX_AUDIO_BYTES = 20000000;
  let ready = false, muted = false, speaking = false, generation = 0;
  let revision = -1, session = null, label = "", controller = null;
  let audio = null, objectURL = null, timer = null;
  const nodes = selector => document.querySelectorAll(selector);

  function paint() {
    nodes("[data-voice-controls]").forEach(node => { node.hidden = !ready; });
    nodes("[data-voice-mute]").forEach(node => {
      node.textContent = muted ? "Unmute voice" : "Mute voice";
      node.setAttribute("aria-pressed", String(muted));
    });
    // A spoken operator-circle release carries the label the screen already
    // shows on it (ruling 6 of 3 October 2026).
    const playing = "AI voice playing" + (label ? " · " + label : "");
    nodes("[data-voice-status]").forEach(node => {
      node.textContent = muted ? "Voice muted" : speaking ? playing : "Voice on";
    });
    nodes("[data-voice-badge]").forEach(node => {
      node.hidden = !speaking;
      node.textContent = "AI voice" + (label ? " · " + label : "");
    });
  }

  function clearTimer() {
    if (timer !== null) { clearTimeout(timer); timer = null; }
  }

  function stopAll() {
    generation += 1;
    clearTimer();
    if (controller) { controller.abort(); controller = null; }
    if (audio) {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      audio.removeAttribute("src");
      audio.load();
      audio = null;
    }
    if (objectURL) { URL.revokeObjectURL(objectURL); objectURL = null; }
    speaking = false;
    label = "";
    paint();
  }

  function setMuted(value) {
    muted = Boolean(value);
    if (muted) stopAll();
    paint();
  }

  function updateState(snapshot) {
    if (!snapshot || !Number.isSafeInteger(snapshot.voice_revision)) return;
    if (snapshot.voice_revision < revision) return;
    const nextReady = snapshot.voice_enabled === true && snapshot.voice_ready === true;
    // Operator-circle mode no longer silences the voice (ruling 6 of 3 October
    // 2026). A mode change still stops playback, because the server moves the
    // voice revision with every Settings change.
    if (snapshot.voice_revision !== revision || snapshot.session_id !== session ||
        !nextReady || snapshot.state === "card") stopAll();
    revision = snapshot.voice_revision;
    session = snapshot.session_id;
    ready = nextReady;
    paint();
  }

  async function speak(turn) {
    if (!turn || turn.kind !== "reply") { stopAll(); return; }
    const snapshot = turn.state;
    if (!ready || muted || !snapshot || snapshot.voice_revision !== revision ||
        snapshot.session_id !== session || typeof turn.speech_token !== "string" ||
        !turn.speech_token) return;
    stopAll();
    const job = generation;
    const active = () => job === generation && ready && !muted;
    const nextLabel = turn.release_reason === "operator_circle" ? "operator circle" : "";
    controller = new AbortController();
    timer = setTimeout(() => { if (active()) stopAll(); }, AUDIO_WAIT_MS);
    try {
      const response = await fetch("/api/voice", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: {"Content-Type": "application/json", "Accept": "audio/mpeg"},
        body: JSON.stringify({speech_token: turn.speech_token}), signal: controller.signal
      });
      if (!active()) return;
      if (!response.ok || (response.headers.get("Content-Type") || "").split(";")[0] !== "audio/mpeg") {
        stopAll(); return;
      }
      const blob = await response.blob();
      if (!active()) return;
      // The audio has arrived whole; from here nothing but its own end, the
      // card, a new turn, mute or a state change stops it.
      clearTimer();
      if (!blob.size || blob.size > MAX_AUDIO_BYTES) { stopAll(); return; }
      objectURL = URL.createObjectURL(blob);
      const player = new Audio(objectURL);
      audio = player;
      player.onended = player.onerror = () => { if (active()) stopAll(); };
      await player.play();
      if (!active()) { player.pause(); return; }
      speaking = true;
      label = nextLabel;
      paint();
    } catch (_) {
      // Vendor and browser errors are deliberately neither displayed nor logged.
      if (active()) stopAll();
    }
  }

  nodes("[data-voice-mute]").forEach(node => {
    node.addEventListener("click", () => setMuted(!muted));
  });
  window.addEventListener("pagehide", stopAll);
  window.SecondSignalVoice = Object.freeze({
    speak, stopAll, updateState, setMuted,
    isMuted: () => muted, isSpeaking: () => speaking,
    canListen: () => false, listen: () => {}
  });
  paint();
})();
