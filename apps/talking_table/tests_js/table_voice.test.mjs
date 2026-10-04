// Exercise the actual table event wiring with a tiny offline DOM and fake API.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const source = readFileSync(new URL('../static/table.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../static/index.html', import.meta.url), 'utf8');
const flush = async () => { for (let i = 0; i < 3; i++) await new Promise(resolve => setImmediate(resolve)); };
const pending = () => { let resolve; const promise = new Promise(done => { resolve = done; }); return {promise, resolve}; };
const snapshot = (extra = {}) => ({voice_ready: true, voice_enabled: true, voice_revision: 1, mode_revision: 1, session_id: 'one', operator_circle: false, state: 'seated', ...extra});

async function page({local = true} = {}) {
  const all = [], ids = new Map();
  class Node {
    constructor(tag = 'div', connected = false) {
      this.tagName = tag.toUpperCase(); this.children = []; this.parent = null; this.root = connected;
      this.dataset = {}; this.attributes = {}; this.listeners = {}; this.className = ''; this.textContent = '';
      this.value = ''; this.checked = false; this.hidden = false; this.open = false;
      this.classList = {toggle: (name, force) => { const classes = new Set(this.className.split(' ').filter(Boolean)); const add = force ?? !classes.has(name); add ? classes.add(name) : classes.delete(name); this.className = [...classes].join(' '); }, remove: name => this.classList.toggle(name, false)};
      all.push(this);
    }
    set id(value) { this._id = value; ids.set(value, this); }
    get id() { return this._id; }
    get firstChild() { return this.children[0] || this; }
    get connected() { return this.root || Boolean(this.parent?.connected); }
    append(...children) { for (const child of children) { child.parent = this; this.children.push(child); } }
    replaceChildren(...children) { for (const child of this.children) child.parent = null; this.children = []; this.append(...children); }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    async fire(name, extra = {}) { await Promise.all((this.listeners[name] || []).map(fn => fn({preventDefault() {}, ...extra}))); }
    querySelector(selector) { return all.find(node => node.parent === this && matches(node, selector)) || new Node(); }
    focus() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.fire('close'); }
  }
  function matches(node, selector) {
    if (selector.startsWith('.')) return node.className.split(' ').includes(selector.slice(1));
    if (selector === '[data-voice-persona]') return Boolean(node.dataset.voicePersona);
    return node.tagName.toLowerCase() === selector;
  }
  for (const match of html.matchAll(/\bid="([^"]+)"/g)) { const node = new Node('div', true); node.id = match[1]; }
  const document = {getElementById: id => ids.get(id), createElement: tag => new Node(tag), createTextNode: text => Object.assign(new Node('#text'), {textContent: text}), querySelectorAll: selector => all.filter(node => node.connected && matches(node, selector)), addEventListener() {}};
  const calls = [], speech = [], states = [], polls = [], turns = [];
  let stops = 0;
  const roster = ['cody', 'ellis', 'nikki', 'rowan', 'seren', 'vandal', 'willow'].map(id => ({id, one_line: id, plate: [[id, 'he'], [id, 'she']], names: {as_written: [id, 'he'], women: [id, 'she'], men: [id, 'he'], neither: [id, 'they']}}));
  const config = {local, settings: {adapter: 'fake', model: 'fake-1', presentation: 'as_written', chosen_names: {}, operator_circle: false, voice_enabled: true, voice_slots: {}}, roster, phone: {}, state: snapshot(), storage: 'test storage'};
  let settingsReply = null, pollState = snapshot();
  const sandbox = {
    document,
    fetch: async (url, options) => {
      calls.push({url, options});
      let result;
      if (url === '/api/config') result = config;
      else if (url === '/api/state') result = pollState;
      else if (url === '/api/turn') { const request = pending(); turns.push(request); result = await request.promise; }
      else if (url === '/api/settings') result = settingsReply ? await settingsReply.promise : config;
      else throw new Error('Unexpected endpoint: ' + url);
      return {ok: true, json: async () => structuredClone(result)};
    },
    SecondSignalVoice: {speak: value => { speech.push(value); }, stopAll: () => { stops += 1; }, updateState: value => { states.push(value); }, canListen: () => false},
    addEventListener() {}, setInterval: fn => { polls.push(fn); }, console,
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, {filename: 'table.js'});
  await flush();
  const send = async text => { ids.get('message').value = text; await ids.get('composer').fire('submit'); await flush(); };
  const turn = (extra = {}) => ({kind: 'reply', text: 'Checked reply', persona: null, assist: null, house_lines: ['Displayed house line'], state: snapshot(), speech_token: 'approved-token', verdict: {status: 'SHIP'}, decision: {}, ...extra});
  return {ids, document, calls, speech, states, turns, polls, config, send, turn, get stops() { return stops; }, setPoll: state => { pollState = state; }, delaySettings: () => { settingsReply = pending(); return settingsReply; }};
}

test('Settings renders 28 empty voice slots covering every offered presentation', async () => {
  const table = await page();
  const slots = table.document.querySelectorAll('[data-voice-persona]');
  assert.equal(slots.length, 28);
  assert.ok(slots.every(node => node.value === ''));
  assert.equal(new Set(slots.map(node => node.dataset.voicePersona)).size, 7);
  assert.deepEqual([...new Set(slots.map(node => node.dataset.voicePresentation))].sort(), ['as_written', 'men', 'neither', 'women']);
});

test('table forwards the token, the state and the release reason for a checked reply, never the text or the house line', async () => {
  const table = await page();
  await table.send('A normal message');
  table.turns[0].resolve(table.turn({release_reason: 'ship'}));
  await flush();
  assert.equal(table.speech.length, 1);
  assert.deepEqual(Object.keys(table.speech[0]).sort(), ['kind', 'release_reason', 'speech_token', 'state']);
  assert.equal(table.speech[0].speech_token, 'approved-token');
  assert.equal(table.speech[0].release_reason, 'ship');
  assert.ok(!JSON.stringify(table.speech[0]).includes('Checked reply'));
  assert.ok(!JSON.stringify(table.speech[0]).includes('Displayed house line'));
});

// Ruling 6 of 3 October 2026: operator-circle replies speak while the mode is on.
// The operator-circle variant used to sit in the silent list below.
test('withheld, house and failure responses never invoke speech', async () => {
  for (const extra of [{kind: 'withheld'}, {kind: 'house'}, {kind: 'failure'}, {kind: 'reply', speech_token: null}]) {
    const table = await page();
    await table.send('A normal message');
    table.turns[0].resolve(table.turn(extra));
    await flush();
    assert.equal(table.speech.length, 0, JSON.stringify(extra));
  }
});

test('an operator-circle release with a token invokes speech and carries its release reason', async () => {
  const table = await page();
  await table.send('A normal message');
  table.turns[0].resolve(table.turn({state: snapshot({operator_circle: true}), release_reason: 'operator_circle', verdict: {status: 'WITHHOLD'}}));
  await flush();
  assert.equal(table.speech.length, 1);
  assert.equal(table.speech[0].release_reason, 'operator_circle');
  assert.equal(table.speech[0].speech_token, 'approved-token');
  assert.equal(table.speech[0].state.operator_circle, true);
});

test('an older reply arriving after a newer card cannot invoke speech', async () => {
  const table = await page();
  await table.send('First ordinary message');
  await table.send('Second ordinary message');
  table.turns[1].resolve(table.turn({kind: 'card', card: '', state: snapshot({voice_revision: 2, state: 'card'})}));
  await flush();
  table.turns[0].resolve(table.turn());
  await flush();
  assert.equal(table.speech.length, 0);
  assert.equal(table.ids.get('crisis').hidden, false);
});

test('an older reply arriving after a newer reply cannot replace its speech', async () => {
  const table = await page();
  await table.send('First ordinary message');
  await table.send('Second ordinary message');
  table.turns[1].resolve(table.turn({speech_token: 'newest-token', state: snapshot({voice_revision: 2})}));
  await flush();
  table.turns[0].resolve(table.turn());
  await flush();
  assert.deepEqual(table.speech.map(item => item.speech_token), ['newest-token']);
});

test('state polling forwards a card from another tab to the voice stop gate', async () => {
  const table = await page();
  table.setPoll(snapshot({voice_revision: 2, state: 'card'}));
  await table.polls[0]();
  assert.equal(table.states.at(-1).state, 'card');
  assert.equal(table.states.at(-1).voice_revision, 2);
});

test('Settings clears both password fields before its request completes and on close', async () => {
  const table = await page();
  const delayed = table.delaySettings();
  table.ids.get('voice-key').value = 'sk_test_voice_key_only_in_test';
  table.ids.get('api-key').value = 'sk_test_model_key_only_in_test';
  const saving = table.ids.get('settings-form').fire('submit');
  await flush();
  assert.equal(table.ids.get('voice-key').value, '');
  assert.equal(table.ids.get('api-key').value, '');
  const sent = JSON.parse(table.calls.at(-1).options.body);
  assert.equal(sent.voice_key, 'sk_test_voice_key_only_in_test');
  assert.equal(sent.key, 'sk_test_model_key_only_in_test');
  delayed.resolve(table.config);
  await saving;
  table.ids.get('voice-key').value = 'sk_test_draft_key_only_in_test';
  table.ids.get('api-key').value = 'sk_test_draft_model_only_in_test';
  await table.ids.get('settings-dialog').fire('close');
  assert.equal(table.ids.get('voice-key').value, '');
  assert.equal(table.ids.get('api-key').value, '');
});

test('paired remote Settings disables voice edits and will not submit them', async () => {
  const table = await page({local: false});
  assert.equal(table.ids.get('voice-settings').disabled, true);
  assert.equal(table.ids.get('save-settings').hidden, true);
  await table.ids.get('settings-form').fire('submit');
  assert.equal(table.calls.filter(call => call.url === '/api/settings').length, 0);
});
