"use strict";
(() => {
  const $ = id => document.getElementById(id);
  let sitting = null, version = -1, card = false, streamUp = false;
  const node = (tag, text) => { const result = document.createElement(tag); if (text !== undefined) result.textContent = text; return result; };
  async function api(path, payload) {
    const options = {cache: "no-store", credentials: "same-origin", headers: {Accept: "application/json"}};
    if (payload) { options.method = "POST"; options.headers["Content-Type"] = "application/json"; options.body = JSON.stringify(payload); }
    const response = await fetch(path, options), result = await response.json();
    if (!response.ok) throw new Error(result.error || "This page could not be read.");
    return result;
  }
  function state(snapshot) {
    if (!Number.isSafeInteger(snapshot.session_version) || snapshot.session_version < version) return;
    version = snapshot.session_version; card = snapshot.state === "card";
    $("live-card").hidden = !card; $("record-body").hidden = card;
    $("live-card").textContent = card ? snapshot.card : "";
    $("connection-status").textContent = "";
  }
  async function poll() {
    if (streamUp) return;
    try { state(await api("/api/state")); }
    catch (_) { $("connection-status").textContent = "The table is out of reach. Reconnecting."; }
  }
  function block(title, value) {
    const section = node("li"); section.append(node("h2", title), node("pre", typeof value === "string" ? value : JSON.stringify(value ?? null, null, 2))); return section;
  }
  function drawReplay(logged) {
    const record = logged.record, tree = $("replay-tree"); tree.replaceChildren();
    tree.append(block("Extract in the logged record", record.signals ?? "Not retained in this card record."));
    const ranks = node("li"), candidates = node("ol"); candidates.className = "candidate-grid";
    ranks.append(node("h2", "Candidates in recorded order"));
    for (const candidate of record.ranked || []) {
      const item = node("li"); item.dataset.status = candidate.status;
      item.append(node("h3", candidate.agent_id), node("p", "Eligibility / verdict: " + candidate.status),
        node("p", "Score: " + candidate.score), node("pre", (candidate.rationale || []).join("\n")));
      candidates.append(item);
    }
    if (!candidates.children.length) ranks.append(node("p", "Character-routing details were not retained in this card record."));
    ranks.append(candidates); tree.append(ranks);
    const floor = (record.ranked || []).flatMap(candidate => (candidate.rationale || []).filter(reason => /floor|regulation window|stabiliz/i.test(reason)).map(reason => candidate.agent_id + ": " + reason));
    tree.append(block("Stabilizer floor and route reason", [record.reason || "No route reason retained.", ...floor].join("\n")));
    tree.append(block("Seat and assist", {seat: record.agent_id, assist: record.assist_agent_id, reason: record.assist_reason}));
    tree.append(block("Holds and obligations", {held: record.held || [], obligations: record.obligations || []}));
    tree.append(block("Attached house lines", logged.house_lines));
    tree.append(block("Logged audit verdict", logged.verdict));
    $("replay-status").textContent = "Read from logged row " + logged.row_id + ". No decision was recomputed.";
  }
  async function replay() {
    if (card) return;
    try {
      const logged = await api("/api/replay?row_id=" + encodeURIComponent($("row-id").value.trim()));
      if (!card) drawReplay(logged);
    } catch (error) { $("replay-status").textContent = error.message; }
  }
  async function loadCorrection() {
    try {
      sitting = await api("/api/operator/state");
      $("latch-state").textContent = "Current latch: " + sitting.latch + ". " + sitting.reasons.join("; ");
      $("review-note").textContent = sitting.note;
      $("clear-latch").disabled = sitting.latch === "none";
    } catch (error) { $("operator-status").textContent = error.message; }
  }
  if ($("correction-form")) {
    $("refresh-latch").addEventListener("click", loadCorrection);
    $("correction-form").addEventListener("submit", async event => {
      event.preventDefault(); if (!sitting || card) return;
      $("clear-latch").disabled = true;
      try {
        await api("/api/operator/clear-latch", {reason: $("clear-reason").value, session_id: sitting.session_id, session_version: sitting.session_version});
        $("clear-reason").value = ""; $("operator-status").textContent = "The operator's reason and latch clearing were recorded.";
      } catch (error) { $("operator-status").textContent = error.message; }
      await loadCorrection();
    });
    loadCorrection();
  }
  if ($("replay-form")) {
    $("replay-form").addEventListener("submit", event => { event.preventDefault(); replay(); });
    const id = new URLSearchParams(location.search).get("row_id");
    if (id) { $("row-id").value = id; poll().then(replay); }
  }
  poll();
  if (typeof EventSource === "function") {
    const stream = new EventSource("/api/events");
    let expectedReconnect = false;
    stream.addEventListener("state", event => { expectedReconnect = false; try { state(JSON.parse(event.data)); streamUp = true; } catch (_) {} });
    stream.addEventListener("reconnect", () => { expectedReconnect = true; });
    stream.addEventListener("error", () => {
      streamUp = false;
      if (expectedReconnect) { expectedReconnect = false; poll(); }
      else $("connection-status").textContent = "The table is out of reach. Reconnecting.";
    });
  }
  setInterval(poll, 1000);
})();
