// Order T3: real browser code driven through an offline DOM and server events.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {page, snapshot, receipt, flush, pending, CARD} from './t3_dom.js';

const sitting = (version, extra = {}) => snapshot({session_version: version, state: 'idle', turn_count: 0, turns: [], ...extra});
const turn = (version, extra = {}) => ({kind: 'reply', turn_id: 'one:1', page_version: version,
  text: 'One small task.', user_text: 'A remote ordinary request', persona: 'nikki', display_name: 'Nikki',
  assist: null, house_lines: [], receipt: receipt(), verdict: {status: 'SHIP'}, decision: {obligations: []},
  state: sitting(version, {state: 'seated', seated: 'nikki', turn_count: 1}), ...extra});
const completed = (version, extra = {}) => {const t = turn(version, extra); return sitting(version, {state: 'seated', seated: 'nikki', turn_count: 1, turns: [t]});};
const card = version => {const state = sitting(version, {state: 'card', card: CARD, card_revision: 2, revision: 2, turn_count: 2}); state.turns = [{kind: 'card', card: CARD, turn_id: 'one:2', page_version: version, state: {...state}, decision: {}, receipt: {crisis_gate: true}}]; return state;};
const button = (p, text) => p.document.querySelectorAll('button').find(node => node.textContent === text);

test('T3 Table polls across planned reconnects without silencing speech or losing a newer card', async () => {
  const p = await page({initial: completed(2)}), stream = p.streams[0];
  const status = p.ids.get('stream-status');
  let stops = 0; p.sandbox.SecondSignalVoice.stopAll = () => { stops++; };
  stream.emit(completed(2));
  const before = p.calls.filter(c => c.url === '/api/state').length;
  stream.listeners.reconnect({data: '{}'}); stream.drop();
  assert.equal(status.textContent, ''); await flush();
  assert.equal(p.calls.filter(c => c.url === '/api/state').length, before + 1);
  assert.equal(stops, 0); assert.equal(p.streams.length, 1);
  const delayedPoll = pending(); p.handlers.set('/api/state', () => delayedPoll.promise);
  stream.emit(completed(3)); stream.listeners.reconnect({data: '{}'}); stream.drop();
  stream.emit(card(5)); delayedPoll.resolve(completed(4)); await flush();
  assert.equal(p.ids.get('crisis').hidden, false);
  assert.equal(p.speech.length, 0); assert.equal(p.streams.length, 1);
  stream.drop(); assert.equal(status.textContent, 'The table is out of reach. Reconnecting.');
});

test('T3 phone polls every second without a stream and an older poll cannot replace a newer card', async () => {
  const p = await page({phone: true, initial: {error: 'offline'}});
  const status = p.ids.get('phone-stream-status');
  assert.equal(p.streams.length, 0);
  assert.equal(status.textContent, 'The table is out of reach. Reconnecting.');
  assert.equal(p.timers.at(-1).milliseconds, 1000);
  p.setPoll(completed(2)); await p.sandbox.poll();
  assert.equal(status.textContent, ''); assert.equal(p.document.body.dataset.state, 'seated');
  const delayedPoll = pending(); let calls = 0;
  p.handlers.set('/api/state', () => ++calls === 1 ? delayedPoll.promise : card(5));
  const older = p.sandbox.poll(); await flush();
  await p.sandbox.poll();
  assert.equal(p.document.body.dataset.state, 'card');
  delayedPoll.resolve(completed(4)); await older;
  assert.equal(p.document.body.dataset.state, 'card');
  assert.equal(p.ids.get('card-words').textContent, CARD);
  assert.equal(p.streams.length, 0); assert.equal(p.speech.length, 0);
  const timers = p.timers.filter(timer => timer.fn === p.sandbox.poll && !timer.cleared);
  assert.equal(timers.length, 1); assert.equal(timers[0].milliseconds, 1000);
});

test('T3 review polls during native reconnect and a late poll cannot cover the current card', async () => {
  const ids = new Map(['live-card', 'record-body', 'connection-status'].map(id => [id, {hidden: false, textContent: ''}]));
  const streams = [], handlers = {}, delayed = pending(); let pollResult = sitting(1), calls = 0;
  const sandbox = {document: {getElementById: id => ids.get(id)}, location: {search: ''}, URLSearchParams,
    EventSource: class {constructor() {streams.push(this);} addEventListener(name, fn) {handlers[name] = fn;}},
    setInterval() {}, fetch: async () => {calls++; const value = await pollResult; return {ok: true, json: async () => value};}};
  vm.runInNewContext(readFileSync(new URL('../static/review.js', import.meta.url), 'utf8'), sandbox);
  await flush(); const emit = value => handlers.state({data: JSON.stringify(value)});
  emit(sitting(1)); pollResult = delayed.promise;
  handlers.reconnect({data: '{}'}); handlers.error({});
  assert.equal(ids.get('connection-status').textContent, ''); assert.equal(calls, 2);
  emit(card(5)); delayed.resolve(completed(4)); await flush();
  assert.equal(ids.get('live-card').hidden, false); assert.equal(ids.get('live-card').textContent, CARD);
  assert.equal(ids.get('record-body').hidden, true); assert.equal(streams.length, 1);
  handlers.error({}); assert.equal(ids.get('connection-status').textContent, 'The table is out of reach. Reconnecting.');
});

for (const kind of ['reply', 'withheld']) test(`T3 remote ${kind} is rendered on both clients and reload with one turn number`, async () => {
  const first = await page({initial: sitting(1)}), second = await page({initial: sitting(1), local: false});
  const posted = sitting(2, {turn_count: 1, pending_turn: {user_text: 'A remote ordinary request'}});
  const ready = completed(3, {kind});
  for (const p of [first, second]) {
    assert.equal(p.streams.length, 1); p.streams[0].emit(posted); p.streams[0].emit(ready);
    assert.match(p.ids.get('transcript').textContent, /One small task/);
    assert.match(p.ids.get('transcript').textContent, /TURN 01/);
    assert.doesNotMatch(p.ids.get('transcript').textContent, /TURN 02/);
    p.streams[0].emit(ready); assert.equal(p.document.querySelectorAll('.turn').length, 1);
    assert.equal(p.speech.length, 0);
  }
  const reload = await page({initial: ready});
  assert.equal(reload.ids.get('transcript').textContent, first.ids.get('transcript').textContent);
});

test('T3 a reload restores the exact card and no first-version dialog covers it', async () => {
  const p = await page({initial: card(4)});
  assert.equal(p.ids.get('crisis').hidden, false); assert.match(p.ids.get('crisis').textContent, /What you just wrote/);
  assert.equal(p.ids.get('limitations-dialog').open, false); assert.equal(p.ids.get('table-panel').hidden, true);
  assert.equal(p.speech.length, 0);
});

test('T3 a stream card wins a paused view and rejects old poll and POST replies', async () => {
  const p = await page({initial: sitting(1)}); await p.send('ordinary draft');
  await p.ids.get('pause-view').click(); p.streams[0].emit(card(5));
  p.turns[0].resolve(turn(3, {speech_token: 'fixture-capability'})); await flush();
  p.streams[0].drop(); p.setPoll(completed(2)); await p.polls[0]();
  assert.equal(p.ids.get('crisis').hidden, false); assert.equal(p.ids.get('transcript').hidden, true);
  assert.equal(p.speech.length, 0); assert.equal(p.ids.get('limitations-dialog').open, false);
});

test('T3 remote reset clears a card and restores the table without an extra turn', async () => {
  const p = await page({initial: card(5)});
  p.streams[0].emit(sitting(6, {session_id: 'two'}));
  assert.equal(p.ids.get('crisis').hidden, true); assert.equal(p.ids.get('table-panel').hidden, false);
  assert.equal(p.ids.get('transcript').textContent, '');
  p.streams[0].emit(card(5)); assert.equal(p.ids.get('crisis').hidden, true);
});

test('T3 config after remote reset cannot preserve the prior transcript', async () => {
  const p = await page({initial: completed(2)});
  p.handlers.set('/api/settings', () => ({...p.config, state: sitting(5, {session_id: 'two'})}));
  await p.ids.get('save-presentation').click(); await flush();
  assert.equal(p.ids.get('transcript').textContent, '');
});

test('T3 lost stream names the problem and fallback polling recovers the current turn', async () => {
  const p = await page({initial: sitting(1)}); p.streams[0].emit(sitting(1));
  const before = p.calls.filter(c => c.url === '/api/state').length;
  await p.polls[0](); assert.equal(p.calls.filter(c => c.url === '/api/state').length, before);
  p.streams[0].drop(); assert.equal(p.ids.get('stream-status').textContent, 'The table is out of reach. Reconnecting.');
  p.setPoll(completed(3)); await p.polls[0]();
  assert.match(p.ids.get('transcript').textContent, /One small task/);
  assert.equal(p.ids.get('stream-status').textContent, ''); assert.equal(p.streams.length, 1);
});

for (const outcome of ['cancel', 'timeout']) test(`T3 a late POST after ${outcome} cannot restart voice`, async () => {
  const p = await page({initial: sitting(1)}); await p.send('ordinary draft');
  if (outcome === 'cancel') await button(p, 'Stop waiting').click();
  else p.timers.find(t => t.milliseconds === 90000).fn();
  p.turns[0].resolve(turn(3, {speech_token: 'fixture-capability'})); await flush();
  assert.equal(p.speech.length, 0);
});

test('T3 local release speaks once even when its stream arrives first', async () => {
  const p = await page({initial: sitting(1)}); await p.send('ordinary draft');
  p.streams[0].emit(completed(3)); p.turns[0].resolve(turn(3, {speech_token: 'fixture-capability'})); await flush();
  assert.equal(p.speech.length, 1); assert.equal(p.document.querySelectorAll('.turn').length, 1);
  p.streams[0].emit(completed(3)); assert.equal(p.speech.length, 1);
});

test('T3 limitations appear once per package version and reopen from settings', async () => {
  const p = await page({initial: sitting(1)}); assert.equal(p.ids.get('limitations-dialog').open, true);
  await p.ids.get('limitations-close').click();
  const reload = await page({initial: sitting(1), saved: p.storage});
  assert.equal(reload.ids.get('limitations-dialog').open, false);
  await reload.ids.get('limitations-open').click(); assert.equal(reload.ids.get('limitations-dialog').open, true);
  assert.match(reload.ids.get('limitations-content').textContent, /149 documented gaps/);
  const escape = await page({initial: sitting(1)}); escape.ids.get('limitations-dialog').close();
  const afterEscape = await page({initial: sitting(1), saved: escape.storage});
  assert.equal(afterEscape.ids.get('limitations-dialog').open, false);
});

test('T3 token absence disables the switch and phone hides computer tools', async () => {
  const p = await page({initial: sitting(1)}), phone = await page({initial: sitting(1), local: false});
  assert.equal(p.ids.get('operator-circle').disabled, true);
  assert.equal(p.ids.get('operator-token-note').textContent, "Operator-circle mode needs the operator's token on this computer.");
  assert.equal(phone.ids.get('operator-tools').hidden, true); assert.equal(phone.ids.get('lights-check').disabled, true);
  p.streams[0].emit(sitting(2, {operator_circle: true, mode_revision: 2}));
  assert.match(p.ids.get('operator-circle-status').textContent, /prototype for the operator's circle/);
});

test('T3 Wi-Fi is not enabled until the exact blocking warning is dismissed affirmatively', async () => {
  const p = await page({initial: sitting(1)}); p.ids.get('phone-mode').checked = true;
  const change = p.ids.get('phone-mode').fire('change'); await flush();
  assert.equal(p.ids.get('network-warning-dialog').open, true);
  assert.equal(p.calls.filter(c => c.url === '/api/network').length, 0);
  assert.equal(p.ids.get('network-warning-copy').textContent, p.config.honesty.network_warning);
  await p.ids.get('network-warning-cancel').click(); await change;
  assert.equal(p.calls.filter(c => c.url === '/api/network').length, 0);
  p.ids.get('phone-mode').checked = true; const enabled = p.ids.get('phone-mode').fire('change'); await flush();
  await p.ids.get('network-warning-accept').click(); await enabled;
  assert.equal(p.calls.filter(c => c.url === '/api/network').length, 1);
});

test('T3 a crisis cancels a pending Wi-Fi enable warning', async () => {
  const p = await page({initial: sitting(1)}); p.ids.get('phone-mode').checked = true;
  const change = p.ids.get('phone-mode').fire('change'); await flush(); p.streams[0].emit(card(3)); await change;
  assert.equal(p.ids.get('network-warning-dialog').open, false);
  assert.equal(p.calls.filter(c => c.url === '/api/network').length, 0);
});

test('T3 the terms dialog shows both attestations and restores the rejected draft', async () => {
  const p = await page({initial: sitting(1)});
  assert.equal(p.ids.get('terms-dialog').open, false);
  const terms = {title: 'Fixture vendor', summary: 'A fixed summary.', vendor: 'openai', revision: 'fixture', attestation: "This key is not used to train the vendor's models, as far as I know."};
  p.handlers.set('/api/turn', () => ({error: 'Read vendor terms', terms_required: true, terms}));
  p.handlers.set('/api/terms/confirm', options => {const body = JSON.parse(options.body); return body.accepted && body.attested ? {confirmed: true} : {error: 'Confirm both statements'};});
  await p.send('ordinary draft'); assert.equal(p.ids.get('terms-dialog').open, true);
  assert.equal(p.ids.get('message').value, 'ordinary draft'); assert.equal(p.ids.get('terms-attestation-label').textContent, terms.attestation);
  await p.ids.get('terms-form').fire('submit'); assert.equal(p.ids.get('terms-dialog').open, true);
  p.ids.get('terms-accepted').checked = true; p.ids.get('terms-attested').checked = true;
  await p.ids.get('terms-form').fire('submit'); assert.equal(p.ids.get('terms-dialog').open, false);
  assert.equal(p.calls.filter(c => c.url === '/api/turn').length, 1);
});

test('T3 flag snapshot uses the visible version and late save cannot cover a card', async () => {
  const p = await page({initial: completed(2, {kind: 'withheld'})});
  const labels = p.document.querySelectorAll('.review-controls button').map(b => b.textContent);
  assert.deepEqual(labels, ['this was read wrong', 'this missed me']);
  const save = pending(); p.handlers.set('/api/review/flag', () => save.promise);
  const click = button(p, labels[0]).click(); await flush();
  const request = JSON.parse(p.calls.find(c => c.url === '/api/review/flag').options.body);
  assert.deepEqual(request, {turn_id: 'one:1', page_version: 2, label: labels[0]});
  p.streams[0].emit(card(4)); save.resolve({saved: true}); await click;
  assert.equal(p.ids.get('crisis').hidden, false); assert.equal(p.ids.get('transcript').hidden, true);
});

test('T3 remote presentation changes refresh names but preserve an open settings draft', async () => {
  const p = await page({initial: completed(2)}); p.ids.get('settings-dialog').showModal(); p.ids.get('house-name').value = 'An unsaved draft';
  p.streams[0].emit({...completed(3), view_settings: {adapter: 'openai', presentation: 'neither', chosen_names: {nikki: 'New name'}}});
  assert.match(p.document.querySelector('.character-name').textContent, /New name/);
  assert.equal(p.ids.get('model-label').textContent, 'OpenAI'); assert.equal(p.ids.get('house-name').value, 'An unsaved draft');
});

test('T3 lights check shows the no-op message without posting a conversation', async () => {
  const p = await page({initial: sitting(1)}); await p.ids.get('lights-check').click();
  assert.equal(p.ids.get('lights-check-status').textContent, 'Lights are off or not set up; nothing to show.');
  assert.equal(p.calls.filter(c => c.url === '/api/turn').length, 0);
});

test('T3 phone polling displays and reloads the actual card, rejects stale state and recovers after reset', async () => {
  const p = await page({phone: true, initial: sitting(1)});
  assert.equal(p.streams.length, 0);
  p.setPoll(card(4)); await p.sandbox.poll();
  assert.equal(p.document.body.dataset.state, 'card');
  assert.match(p.ids.get('card-words').textContent, /What you just wrote/);
  assert.equal(p.ids.get('asks').hidden, true); assert.equal(p.ids.get('view-seated').hidden, true);
  p.setPoll(completed(3)); await p.sandbox.poll(); assert.equal(p.document.body.dataset.state, 'card');
  const reloaded = await page({phone: true, initial: card(4)});
  assert.equal(reloaded.document.body.dataset.state, 'card');
  assert.equal(reloaded.ids.get('card-words').textContent, CARD); assert.equal(reloaded.streams.length, 0);
  p.handlers.set('/api/state', () => { throw new Error('offline'); }); await p.sandbox.poll();
  assert.equal(p.ids.get('phone-stream-status').textContent, 'The table is out of reach. Reconnecting.');
  assert.equal(p.document.body.dataset.state, 'card');
  p.handlers.delete('/api/state');
  p.setPoll(sitting(5, {session_id: 'two'})); await p.sandbox.poll();
  assert.equal(p.document.body.dataset.state, 'idle'); assert.equal(p.ids.get('asks').hidden, false);
  assert.equal(p.ids.get('phone-stream-status').textContent, ''); assert.equal(p.streams.length, 0);
});

test('T3 paused stream completion survives an equal-version POST then resumes without another event', async () => {
  const p = await page({initial: sitting(1)}); await p.send('ordinary draft');
  await p.ids.get('pause-view').click(); p.streams[0].emit(completed(3));
  p.turns[0].resolve(turn(3, {speech_token: 'fixture-capability'})); await flush();
  assert.equal(p.ids.get('transcript').textContent, '');
  await p.ids.get('pause-view').click();
  assert.match(p.ids.get('transcript').textContent, /One small task/); assert.equal(p.speech.length, 0);
});

test('T3 reload retains the current object rather than the turn-era object', async () => {
  const saved = completed(3); saved.object_text = 'The current object';
  saved.turns[0].state.object_text = 'An old object';
  const p = await page({initial: saved});
  assert.match(p.ids.get('plates').textContent, /The current object/);
  assert.doesNotMatch(p.ids.get('plates').textContent, /An old object/);
});

test('T3 a held turn reserves two optional contextual actions for review labels', async () => {
  const p = await page({initial: sitting(1)});
  const offers = {handback: {persona: 'willow', label: 'Hand back', text: 'Could I talk to Willow?'}, assist_offer: {persona: 'ellis', label: 'Ask assist', text: 'Could I talk to Ellis?'}};
  const saved = completed(3, {persona: 'cody', receipt: receipt({holds: [{domain: 'grief'}]}),
    cultural_only: true, second_opinions: [{persona: 'seren',label: 'Another view',text: 'What would Seren add?'}], ...offers});
  Object.assign(saved, offers); p.streams[0].emit(saved);
  assert.equal(p.document.querySelectorAll('.review-controls button').length, 2);
  assert.equal(p.document.querySelectorAll('.table-shortcut, .sprint-start, .sprint-shutter button, .reply-controls button').length, 0);
  assert.equal(p.ids.get('handback-offer').hidden, true); assert.equal(p.ids.get('composer-extras').hidden, true);
});

test('T3 a reset while paused cannot restore queued turns from the old sitting', async () => {
  const p = await page({initial: sitting(1)}); await p.ids.get('pause-view').click();
  p.streams[0].emit(completed(2)); p.streams[0].emit(sitting(4, {session_id: 'two'}));
  await p.ids.get('pause-view').click();
  assert.equal(p.ids.get('transcript').textContent, ''); assert.equal(p.ids.get('turn-count').textContent, 'No turns yet');
});

test('T3 paused POST before a full stream snapshot keeps server chronological order', async () => {
  const p = await page({initial: sitting(1)}); await p.ids.get('pause-view').click(); await p.send('latest draft');
  const latest = turn(4, {turn_id: 'one:2', text: 'Latest reply'});
  latest.state.turn_count = 2;
  p.turns[0].resolve(latest); await flush();
  p.streams[0].emit(sitting(4, {state: 'seated', seated: 'nikki', turn_count: 2,
    turns: [turn(2, {text: 'Earlier reply'}), latest]}));
  await p.ids.get('pause-view').click();
  const rows = p.document.querySelectorAll('.turn');
  assert.equal(rows.length, 2); assert.match(rows[0].textContent, /Earlier reply/);
  assert.match(rows[1].textContent, /Latest reply/); assert.equal(rows[1].classList.contains('current-turn'), true);
});
