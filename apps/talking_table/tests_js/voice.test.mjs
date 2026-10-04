// Offline browser contract tests. Every fetch and audio device below is a fake.
// Run: node --test apps/talking_table/tests_js/voice.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const source = readFileSync(new URL('../static/voice.js', import.meta.url), 'utf8');
const token = 'approved-turn-'.repeat(4);
const tick = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
}

class Element {
  constructor() { this.hidden = false; this.disabled = false; this.textContent = ''; this.attributes = {}; this.listeners = {}; this.dataset = {}; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  getAttribute(name) { return this.attributes[name] ?? null; }
  addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
  click() { for (const callback of this.listeners.click || []) callback({target: this}); }
}

function response({status = 200, type = 'audio/mpeg', body, blobType = 'audio/mpeg'} = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {get: name => name.toLowerCase() === 'content-type' ? type : null},
    blob: async () => body === undefined ? new Blob(['ID3 fake audio'], {type: blobType}) : body,
  };
}

function makePage({fetchImpl, audioPlay, fakeTimers = false} = {}) {
  const nodes = Object.fromEntries(['mute', 'status', 'badge', 'controls'].map(name => [name, [new Element(), new Element()]]));
  const documentListeners = {};
  const windowListeners = {};
  const calls = [], audios = [], created = [], revoked = [], logs = [], scheduled = [];
  let timerSeq = 0;
  const timers = fakeTimers ? {
    setTimeout: (fn, delay) => { const id = ++timerSeq; scheduled.push({id, fn, delay}); return id; },
    clearTimeout: id => { const index = scheduled.findIndex(item => item.id === id); if (index >= 0) scheduled.splice(index, 1); },
  } : {setTimeout, clearTimeout};
  const document = {
    readyState: 'complete',
    querySelectorAll: selector => nodes[selector.match(/^\[data-voice-(\w+)\]$/)?.[1]] || [],
    addEventListener: (name, callback) => { (documentListeners[name] ||= []).push(callback); },
  };
  class Audio {
    constructor(url) { this.src = url; this.paused = true; this.pauseCalls = 0; this.listeners = {}; audios.push(this); }
    addEventListener(name, callback) { (this.listeners[name] ||= []).push(callback); }
    removeEventListener(name, callback) { this.listeners[name] = (this.listeners[name] || []).filter(item => item !== callback); }
    emit(name) { this['on' + name]?.({type: name}); for (const callback of this.listeners[name] || []) callback({type: name}); }
    play() { this.paused = false; this.emit('play'); this.emit('playing'); return audioPlay ? audioPlay(this) : Promise.resolve(); }
    pause() { this.paused = true; this.pauseCalls += 1; this.emit('pause'); }
    removeAttribute(name) { if (name === 'src') this.src = ''; }
    load() {}
    end() { this.paused = true; this.emit('ended'); }
  }
  const sandbox = {
    document, Audio, Blob, AbortController,
    URL: {createObjectURL: blob => { const url = 'blob:test-' + created.length; created.push({url, blob}); return url; }, revokeObjectURL: url => revoked.push(url)},
    fetch: async (url, init) => { calls.push({url, init}); return fetchImpl ? fetchImpl(url, init) : response(); },
    console: Object.fromEntries(['log', 'warn', 'error', 'info'].map(name => [name, (...args) => logs.push(args.join(' '))])),
    ...timers,
    addEventListener: (name, callback) => { (windowListeners[name] ||= []).push(callback); },
  };
  // Any accidental fallback or credential persistence fails at its first use.
  for (const property of ['localStorage', 'sessionStorage', 'speechSynthesis', 'SpeechSynthesisUtterance', 'SpeechRecognition']) {
    Object.defineProperty(sandbox, property, {get() { throw new Error('Forbidden browser capability: ' + property); }});
  }
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, {filename: 'voice.js'});
  for (const callback of documentListeners.DOMContentLoaded || []) callback();
  const voice = sandbox.SecondSignalVoice;
  const snapshot = (extra = {}) => ({voice_ready: true, voice_enabled: true, voice_revision: 1, operator_circle: false, session_id: 'session-one', state: 'seated', ...extra});
  const update = (extra = {}) => voice.updateState(snapshot(extra));
  const speak = (extra = {}) => voice.speak({kind: 'reply', speech_token: token, state: snapshot(), ...extra});
  return {voice, nodes, calls, audios, created, revoked, logs, scheduled, snapshot, update, speak,
    fire: () => { for (const item of scheduled.splice(0)) item.fn(); },
    hide: () => { for (const callback of windowListeners.pagehide || []) callback(); }};
}

test('voice exposes the table hook without enabling browser recognition or storage', async () => {
  const page = makePage();
  for (const name of ['speak', 'stopAll', 'updateState', 'setMuted', 'isMuted', 'isSpeaking', 'canListen', 'listen']) assert.equal(typeof page.voice[name], 'function', name);
  assert.equal(page.voice.canListen(), false);
  await page.voice.listen(() => {});
  assert.equal(page.voice.isSpeaking(), false);
  assert.equal(page.calls.length, 0);
});

test('voice starts off and has no request until server confirms key and a slot', async () => {
  const page = makePage();
  await page.speak();
  assert.equal(page.calls.length, 0);
  assert.ok(page.nodes.controls.every(node => node.hidden));
  page.update();
  assert.ok(page.nodes.controls.every(node => !node.hidden));
});

test('only a reply with an approved token and matching revision can request audio', async () => {
  const page = makePage();
  page.update();
  for (const kind of ['card', 'house', 'withheld', 'failure', 'operator_circle', '', undefined]) await page.speak({kind});
  for (const speech_token of ['', undefined, null, 17]) await page.speak({speech_token});
  await page.speak({state: page.snapshot({voice_revision: 0})});
  await page.speak({state: page.snapshot({session_id: 'previous-session'})});
  assert.equal(page.calls.length, 0);
  assert.equal(page.audios.length, 0);
});

test('approved reply posts only the opaque token to the same-origin endpoint', async () => {
  const page = makePage();
  page.update();
  await page.speak({text: 'Never send caller text', persona: 'caller-choice', key: 'sk_test_not_a_real_secret'});
  assert.equal(page.calls.length, 1);
  const {url, init} = page.calls[0];
  assert.equal(url, '/api/voice');
  assert.equal(init.method, 'POST');
  assert.equal(init.credentials, 'same-origin');
  assert.deepEqual(JSON.parse(init.body), {speech_token: token});
  assert.equal(page.audios.length, 1);
  assert.equal(page.audios[0].paused, false);
  assert.equal(page.voice.isSpeaking(), true);
  assert.ok(page.nodes.badge.every(node => !node.hidden));
  page.audios[0].end();
  assert.equal(page.voice.isSpeaking(), false);
  assert.ok(page.nodes.badge.every(node => node.hidden));
  assert.deepEqual(page.revoked, [page.created[0].url]);
});

test('card stops current speech and never requests its text', async () => {
  const page = makePage();
  page.update();
  await page.speak();
  await page.speak({kind: 'card', text: 'fixture placeholder; never synthesized'});
  assert.equal(page.calls.length, 1);
  assert.equal(page.audios[0].paused, true);
  assert.equal(page.voice.isSpeaking(), false);
  assert.ok(page.nodes.badge.every(node => node.hidden));
});

test('mute stops playback, leaves controls visible and prevents new requests', async () => {
  const page = makePage();
  page.update();
  await page.speak();
  page.voice.setMuted(true);
  assert.equal(page.voice.isMuted(), true);
  assert.equal(page.audios[0].paused, true);
  assert.ok(page.nodes.controls.every(node => !node.hidden));
  assert.ok(page.nodes.mute.every(node => node.getAttribute('aria-pressed') === 'true'));
  await page.speak();
  assert.equal(page.calls.length, 1);
  page.voice.setMuted(false);
  await page.speak();
  assert.equal(page.calls.length, 2);
  page.voice.stopAll();
});

test('both visible mute buttons control the same in-memory mute state', () => {
  const page = makePage();
  page.update();
  page.nodes.mute[0].click();
  assert.equal(page.voice.isMuted(), true);
  page.nodes.mute[1].click();
  assert.equal(page.voice.isMuted(), false);
  assert.equal(makePage().voice.isMuted(), false);
});

// Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
// This test used to assert that operator-circle state prevented audio even for a
// reply with a token.
test('an operator-circle release with a token speaks and carries the label the screen shows', async () => {
  const page = makePage();
  page.update({operator_circle: true});
  assert.ok(page.nodes.controls.every(node => !node.hidden));
  await page.speak({state: page.snapshot({operator_circle: true}), release_reason: 'operator_circle'});
  assert.equal(page.calls.length, 1);
  assert.deepEqual(JSON.parse(page.calls[0].init.body), {speech_token: token});
  assert.equal(page.voice.isSpeaking(), true);
  assert.ok(page.nodes.status.every(node => node.textContent === 'AI voice playing · operator circle'));
  assert.ok(page.nodes.badge.every(node => !node.hidden && node.textContent === 'AI voice · operator circle'));
  page.audios[0].end();
  assert.ok(page.nodes.status.every(node => node.textContent === 'Voice on'));
  assert.ok(page.nodes.badge.every(node => node.hidden && node.textContent === 'AI voice'));
  // A shipped reply carries no extra label.
  await page.speak({release_reason: 'ship'});
  assert.ok(page.nodes.status.every(node => node.textContent === 'AI voice playing'));
  assert.ok(page.nodes.badge.every(node => node.textContent === 'AI voice'));
  page.voice.stopAll();
});

// Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
// The mode flag alone no longer stops audio; the server moves the voice revision
// on every Settings change, and that is what stops it.
test('a newer card, a disabled voice or a moved revision stops active audio; the mode flag alone does not', async () => {
  for (const extra of [{state: 'card'}, {voice_ready: false}, {voice_enabled: false}, {}]) {
    const page = makePage();
    page.update();
    await page.speak();
    page.update({voice_revision: 2, ...extra});
    assert.equal(page.audios[0].paused, true, JSON.stringify(extra));
    assert.equal(page.voice.isSpeaking(), false);
  }
  const page = makePage();
  page.update();
  await page.speak();
  page.update({operator_circle: true});
  assert.equal(page.audios[0].paused, false);
  assert.equal(page.voice.isSpeaking(), true);
  page.voice.stopAll();
});

test('stale state cannot re-enable speech after a newer disabling state', async () => {
  const page = makePage();
  page.update({voice_revision: 3, voice_ready: false, voice_enabled: false});
  page.update({voice_revision: 1});
  await page.speak();
  assert.equal(page.calls.length, 0);
  assert.ok(page.nodes.controls.every(node => node.hidden));
});

test('stale turn revision and prior session cannot request audio', async () => {
  const page = makePage();
  page.update({voice_revision: 2, session_id: 'session-two'});
  await page.speak();
  await page.speak({state: page.snapshot({voice_revision: 2})});
  assert.equal(page.calls.length, 0);
});

test('stopAll aborts pending fetch and ignores its late successful response', async () => {
  const pending = deferred();
  const page = makePage({fetchImpl: () => pending.promise});
  page.update();
  const speaking = page.speak();
  await tick();
  assert.equal(page.calls.length, 1);
  page.voice.stopAll();
  assert.equal(page.calls[0].init.signal.aborted, true);
  pending.resolve(response());
  await speaking;
  assert.equal(page.audios.length, 0);
  assert.equal(page.voice.isSpeaking(), false);
});

test('stopAll while the audio body loads cannot resurrect audio', async () => {
  const pending = deferred();
  const page = makePage({fetchImpl: async () => ({...response(), blob: () => pending.promise})});
  page.update();
  const speaking = page.speak();
  await tick();
  page.voice.stopAll();
  pending.resolve(new Blob(['ID3 fake audio'], {type: 'audio/mpeg'}));
  await speaking;
  assert.equal(page.audios.length, 0);
  assert.equal(page.voice.isSpeaking(), false);
  assert.ok(page.nodes.badge.every(node => node.hidden));
});

test('a late audio.play completion after stop cannot relight the badge', async () => {
  const pending = deferred();
  const page = makePage({audioPlay: () => pending.promise});
  page.update();
  const speaking = page.speak();
  await tick();
  assert.equal(page.audios.length, 1);
  page.voice.stopAll();
  pending.resolve();
  await speaking;
  assert.equal(page.audios[0].paused, true);
  assert.equal(page.voice.isSpeaking(), false);
  assert.ok(page.nodes.badge.every(node => node.hidden));
});

test('HTTP errors, invalid content and empty audio fail silently without fallback', async () => {
  const variants = [
    () => response({status: 403}),
    () => response({status: 500}),
    () => response({type: 'text/html'}),
    () => response({body: new Blob([], {type: 'audio/mpeg'})}),
    // The size cap is the server's MAX_AUDIO, 20 MB since the Night Builds Review's
    // required fix 2 (4 October 2026); it was 8 MB here and 2 MB on the server.
    () => response({body: new Blob([new Uint8Array(20_000_001)], {type: 'audio/mpeg'})}),
    () => { throw new Error('sk_test_network_error_must_not_be_exposed'); },
  ];
  for (const fetchImpl of variants) {
    const page = makePage({fetchImpl});
    page.update();
    try {
      await page.speak();
      assert.equal(page.audios.length, 0);
      assert.equal(page.voice.isSpeaking(), false);
      assert.ok(!page.logs.join('\n').includes('sk_test_'));
      assert.ok(!page.nodes.status.some(node => node.textContent.includes('sk_test_')));
    } finally { page.voice.stopAll(); }
  }
});

test('blocked playback has no fallback and releases the object URL', async () => {
  const page = makePage({audioPlay: () => Promise.reject(new Error('sk_test_play_error_must_not_be_exposed'))});
  page.update();
  await page.speak();
  assert.equal(page.calls.length, 1);
  assert.equal(page.audios.length, 1);
  assert.equal(page.audios[0].paused, true);
  assert.equal(page.voice.isSpeaking(), false);
  assert.deepEqual(page.revoked, [page.created[0].url]);
  assert.ok(!page.logs.join('\n').includes('sk_test_'));
});

test('pagehide stops playback and releases its object URL', async () => {
  const page = makePage();
  page.update();
  await page.speak();
  page.hide();
  assert.equal(page.audios[0].paused, true);
  assert.equal(page.voice.isSpeaking(), false);
  assert.deepEqual(page.revoked, [page.created[0].url]);
});

// Night Builds Review of 30 September 2026, required fix 2 on Codex job 2: a long
// reply is never cut off. The old 90-second watchdog and 8 MB cap are gone.
test('the wait for audio is bounded, playback is not: a long reply plays to its own end', async () => {
  const pending = deferred();
  const page = makePage({fetchImpl: () => pending.promise, fakeTimers: true});
  page.update();
  const speaking = page.speak();
  await tick();
  assert.equal(page.scheduled.length, 1, 'one timer, for the wait');
  assert.equal(page.scheduled[0].delay, 75000);
  // Audio for a reply at the longest the table can release: about eight MB.
  pending.resolve(response({body: new Blob([new Uint8Array(8_200_000)], {type: 'audio/mpeg'})}));
  await speaking;
  assert.equal(page.audios.length, 1);
  assert.equal(page.voice.isSpeaking(), true);
  assert.equal(page.scheduled.length, 0, 'the wait timer is cleared once the audio arrives');
  page.fire();  // however much time passes, nothing stops the playback
  assert.equal(page.audios[0].paused, false);
  assert.equal(page.voice.isSpeaking(), true);
  page.audios[0].end();
  assert.equal(page.voice.isSpeaking(), false);
  assert.deepEqual(page.revoked, [page.created[0].url]);
});

test('a vendor that never answers is given up on when the wait ends, silently', async () => {
  const pending = deferred();
  const page = makePage({fetchImpl: () => pending.promise, fakeTimers: true});
  page.update();
  const speaking = page.speak();
  await tick();
  page.fire();
  assert.equal(page.calls[0].init.signal.aborted, true);
  pending.resolve(response());
  await speaking;
  assert.equal(page.audios.length, 0);
  assert.equal(page.voice.isSpeaking(), false);
  assert.ok(page.nodes.status.every(node => node.textContent === 'Voice on'));
});
