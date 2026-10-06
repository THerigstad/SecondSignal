// Order T1: exercise the real page with an independent offline DOM and API.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const source = readFileSync(new URL('../static/table.js', import.meta.url), 'utf8');
const html = readFileSync(new URL('../static/index.html', import.meta.url), 'utf8');
const phoneHtml = readFileSync(new URL('../static/sigils.html', import.meta.url), 'utf8');
const CARD = 'What you just wrote should be heard by a real person, not a character.';
const flush = async () => { for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve)); };
const pending = () => { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return {promise, resolve, reject}; };
const snapshot = (extra = {}) => ({voice_ready: true, voice_enabled: true, voice_revision: 1, mode_revision: 1, revision: 1, session_id: 'one', operator_circle: false, state: 'seated', ...extra});
const receipt = (extra = {}) => ({seat: 'nikki', assist: null, display_names: {nikki: 'Nikki', willow: 'Willow'}, holds: [], obligations: [], vetoes: [], model_called: true, gate_withheld: false, audit_withheld: false, declared_preferences: {}, preference_adjustments: [], presentation_instructions: {}, ...extra});

async function page({phone = false} = {}) {
  const ids = new Map(), all = [], polls = [], timers = [];
  let active = null;
  const descendants = node => node.children.flatMap(child => [child, ...descendants(child)]);
  function matches(node, selector) {
    if (selector.includes(',')) return selector.split(',').some(part => matches(node, part.trim()));
    const bits = selector.trim().split(/\s+/);
    if (bits.length > 1) {
      if (!matches(node, bits.pop())) return false;
      for (let parent = node.parentNode; parent; parent = parent.parentNode) if (matches(parent, bits.join(' '))) return true;
      return false;
    }
    const attribute = selector.match(/\[([^=\]]+)(?:=["']?([^"'\]]*)["']?)?\]/);
    if (attribute) {
      const value = node.getAttribute(attribute[1]);
      if (value === null || (attribute[2] !== undefined && value !== attribute[2])) return false;
      selector = selector.replace(attribute[0], '');
    }
    const id = selector.match(/#([\w-]+)/);
    if (id && node.id !== id[1]) return false;
    const classes = [...selector.matchAll(/\.([\w-]+)/g)].map(match => match[1]);
    if (classes.some(name => !node.classList.contains(name))) return false;
    const tag = selector.match(/^[\w-]+/);
    return !tag || node.tagName.toLowerCase() === tag[0].toLowerCase();
  }
  class Node {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.parentNode = null; this._text = '';
      this.dataset = {}; this.attributes = {}; this.listeners = {}; this.className = ''; this.style = {};
      this.value = ''; this.checked = false; this.hidden = false; this.open = false; this.disabled = false;
      this.classList = {
        contains: name => this.className.split(/\s+/).includes(name),
        toggle: (name, force) => { const set = new Set(this.className.split(/\s+/).filter(Boolean)); const add = force ?? !set.has(name); add ? set.add(name) : set.delete(name); this.className = [...set].join(' '); return add; },
        add: (...names) => names.forEach(name => this.classList.toggle(name, true)),
        remove: (...names) => names.forEach(name => this.classList.toggle(name, false)),
      };
      all.push(this);
    }
    set id(value) { this._id = value; ids.set(value, this); }
    get id() { return this._id || ''; }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    set textContent(value) { this.replaceChildren(); this._text = String(value ?? ''); }
    get firstChild() { return this.children[0] || (this._text ? this : null); }
    get lastChild() { return this.children.at(-1) || null; }
    get parentElement() { return this.parentNode; }
    get isConnected() { return this === body || Boolean(this.parentNode?.isConnected); }
    append(...children) { for (let child of children) { if (typeof child === 'string') { const text = new Node('#text'); text.textContent = child; child = text; } child.remove(); child.parentNode = this; this.children.push(child); } }
    appendChild(child) { this.append(child); return child; }
    prepend(...children) { for (const child of [...children].reverse()) this.insertBefore(child, this.children[0]); }
    insertBefore(child, before) { child.remove(); const index = this.children.indexOf(before); child.parentNode = this; this.children.splice(index < 0 ? this.children.length : index, 0, child); return child; }
    remove() { if (this.parentNode) { this.parentNode.children = this.parentNode.children.filter(child => child !== this); this.parentNode = null; } }
    replaceChildren(...children) { this._text = ''; for (const child of this.children) child.parentNode = null; this.children = []; this.append(...children); }
    setAttribute(name, value) { this.attributes[name] = String(value); if (name === 'id') this.id = String(value); if (name === 'class') this.className = String(value); if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value); }
    getAttribute(name) { if (name === 'id') return this.id || null; if (name === 'class') return this.className || null; if (name.startsWith('data-')) return this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] ?? null; return this.attributes[name] ?? null; }
    removeAttribute(name) { delete this.attributes[name]; }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    async fire(name, extra = {}) { let prevented = false; await Promise.all((this.listeners[name] || []).map(fn => fn({target: this, currentTarget: this, preventDefault() { prevented = true; }, ...extra}))); return prevented; }
    click() { return this.fire('click'); }
    querySelectorAll(selector) { return descendants(this).filter(node => matches(node, selector)); }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { for (let node = this; node; node = node.parentNode) if (matches(node, selector)) return node; return null; }
    focus() { active = this; }
    scrollIntoView() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.fire('close'); }
  }
  const body = new Node('body'), documentElement = new Node('html');
  const stack = [body];
  const voids = new Set(['input', 'meta', 'link', 'br', 'hr', 'img', 'source']);
  const markup = phone ? phoneHtml.split('<script')[0] : html;
  for (const token of markup.matchAll(/<\/?[a-z][^>]*>|[^<]+/gi)) {
    const part = token[0];
    if (!part.startsWith('<')) { if (part.trim()) { const text = new Node('#text'); text.textContent = part; stack.at(-1).append(text); } continue; }
    const match = part.match(/^<(\/)?([\w-]+)([^>]*)>/); if (!match) continue;
    const [, close, rawTag, attrs] = match, tag = rawTag.toLowerCase();
    if (['html', 'body', 'head', 'script', 'style'].includes(tag)) continue;
    if (close) { for (let i = stack.length - 1; i > 0; i--) if (stack[i].tagName.toLowerCase() === tag) { stack.length = i; break; } continue; }
    const node = new Node(tag);
    for (const attr of attrs.matchAll(/([\w-]+)(?:="([^"]*)"|='([^']*)')?/g)) node.setAttribute(attr[1], attr[2] ?? attr[3] ?? '');
    node.hidden = Object.hasOwn(node.attributes, 'hidden'); node.checked = Object.hasOwn(node.attributes, 'checked'); node.value = node.attributes.value ?? '';
    stack.at(-1).append(node); if (!voids.has(tag)) stack.push(node);
  }
  if (phone) for (const match of phoneHtml.matchAll(/<script type="application\/json" id="([^"]+)">([\s\S]*?)<\/script>/g)) {
    const node = new Node('script'); node.id = match[1]; node.textContent = match[2]; body.append(node);
  }
  const document = {body, documentElement, get activeElement() { return active; }, hidden: false,
    getElementById: id => ids.get(id) || null, createElement: tag => new Node(tag),
    createTextNode: text => { const node = new Node('#text'); node.textContent = text; return node; },
    querySelectorAll: selector => descendants(body).filter(node => matches(node, selector)),
    querySelector: selector => descendants(body).find(node => matches(node, selector)) || null,
    addEventListener() {}};
  const roster = ['cody', 'ellis', 'nikki', 'rowan', 'seren', 'vandal', 'willow'].map(id => ({id, one_line: id, plate: [[id, 'he'], [id, 'she']], names: {as_written: [id, 'he'], women: [id, 'she'], men: [id, 'he'], neither: [id, 'they']}}));
  const config = {local: true, settings: {adapter: 'fake', model: 'fake-1', presentation: 'as_written', chosen_names: {}, operator_circle: false, voice_enabled: true, voice_slots: {}, declared_preferences: {}, humour_grief: false, language_style: 'match'}, roster, phone: {}, state: snapshot(), storage: 'fixture storage', presentation_previews: {}, resources: {text: 'Directory', actions: [{label: 'Open directory', url: 'https://findahelpline.com/'}]}};
  const calls = [], turns = [], speech = [], storage = new Map(); let pollState = snapshot();
  const sandbox = {document, console, URLSearchParams, location: {search: '', pathname: '/'}, navigator: {},
    localStorage: {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key)},
    fetch: async (url, options) => { calls.push({url, options}); let result;
      if (url === '/api/config') result = config;
      else if (url === '/api/state') result = pollState;
      else if (url === '/api/turn') { const item = pending(); turns.push(item); result = await item.promise; }
      else if (url === '/api/settings') { Object.assign(config.settings, JSON.parse(options.body)); result = config; }
      else if (url === '/api/resources') result = config.resources;
      else throw new Error('Unexpected endpoint: ' + url);
      return {ok: true, json: async () => structuredClone(result)};
    },
    SecondSignalVoice: {speak: value => speech.push(value), stopAll() {}, updateState() {}, canListen: () => false},
    addEventListener() {}, setInterval: fn => { polls.push(fn); return polls.length; }, clearInterval() {},
    setTimeout: (fn, milliseconds) => { const timer = {fn, milliseconds, cleared: false}; timers.push(timer); return timer; },
    clearTimeout: timer => { if (timer) timer.cleared = true; }, requestAnimationFrame: fn => fn(),
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox); vm.runInContext(source, sandbox, {filename: 'table.js'});
  if (phone) for (const match of phoneHtml.matchAll(/<script>([\s\S]*?)<\/script>/g)) vm.runInContext(match[1], sandbox, {filename: 'sigils.html'});
  await flush();
  const turn = (extra = {}) => ({kind: 'reply', text: 'Take the next step.\n\nMore optional detail.', persona: 'nikki', display_name: 'Nikki', assist: null, house_lines: [], state: snapshot(), speech_token: null, verdict: {status: 'SHIP'}, decision: {obligations: []}, receipt: receipt(), ...extra});
  const send = async text => { ids.get('message').value = text; ids.get('composer').fire('submit'); await flush(); };
  return {ids, document, calls, turns, speech, config, polls, timers, send, turn, sandbox, setPoll: value => { pollState = value; }, rows: () => document.querySelectorAll('.submission')};
}

test('T1 submitted writing appears immediately and Restore preserves a newer draft', async () => {
  const p = await page(); await p.send('help me plan the launch');
  assert.match(p.ids.get('submissions').textContent, /help me plan the launch/);
  assert.equal(p.rows()[0].dataset.state, 'pending');
  p.ids.get('message').value = 'A newer unfinished draft';
  const restore = p.rows()[0].querySelectorAll('button').find(node => /Restore to editor/.test(node.textContent));
  assert.ok(restore); await restore.click();
  assert.match(p.ids.get('message').value, /help me plan the launch/);
  assert.match(p.ids.get('message').value, /A newer unfinished draft/);
});

test('T1 a second send keeps both submissions and marks the older reply superseded', async () => {
  const p = await page(); await p.send('help me plan the launch'); await p.send('help me plan the meeting');
  assert.equal(p.rows().length, 2);
  p.turns[0].resolve(p.turn({superseded: true, kind: 'withheld'})); await flush();
  p.turns[1].resolve(p.turn({state: snapshot({revision: 2})})); await flush();
  assert.deepEqual(p.rows().map(node => node.dataset.state), ['superseded', 'completed']);
});

for (const [kind, release_reason, expected] of [['reply', 'ship', 'completed'], ['withheld', 'withheld', 'withheld'], ['withheld', 'failure', 'failed']]) {
  test(`T1 a ${release_reason} response reaches its visible terminal state`, async () => {
    const p = await page(); await p.send('help me plan the launch');
    p.turns[0].resolve(p.turn({kind, release_reason})); await flush();
    assert.equal(p.rows()[0].dataset.state, expected);
    assert.match(p.rows()[0].textContent.toLowerCase(), new RegExp(expected));
  });
}

test('T1 a transport failure keeps writing recoverable and visibly failed', async () => {
  const p = await page(); await p.send('help me plan the launch'); p.turns[0].reject(new Error('offline fixture')); await flush();
  assert.equal(p.rows()[0].dataset.state, 'failed');
  assert.match(p.rows()[0].textContent, /help me plan the launch/);
});

test('T1 a reply that never settles reaches a visible timeout without losing writing', async () => {
  const p = await page(); await p.send('help me plan the launch');
  const deadline = p.timers.find(timer => !timer.cleared && timer.milliseconds > 0);
  assert.ok(deadline); deadline.fn(); await flush();
  assert.equal(p.rows()[0].dataset.state, 'failed');
  assert.match(p.rows()[0].textContent, /help me plan the launch/);
  assert.equal(p.ids.get('message').disabled, false);
});

test('T1 Stop waiting cancels only the view and a late card still takes the floor', async () => {
  const p = await page(); await p.send('help me plan the launch'); await p.ids.get('stop-waiting').click();
  assert.equal(p.rows()[0].dataset.state, 'cancelled');
  assert.equal(p.ids.get('message').disabled, false);
  assert.equal(p.calls.filter(call => call.url.includes('reset')).length, 0);
  p.turns[0].resolve(p.turn({kind: 'card', card: CARD, persona: null, state: snapshot({state: 'card', revision: 1, card_revision: 1})})); await flush();
  assert.equal(p.ids.get('crisis').hidden, false); assert.match(p.ids.get('crisis').textContent, /real person/);
});

test('T1 Pause this view cannot suppress a polled card or permit an older voice', async () => {
  const p = await page(); await p.send('help me plan the launch'); await p.ids.get('pause-view').click();
  p.setPoll(snapshot({state: 'card', revision: 2, card_revision: 2, card: CARD, receipt: receipt({seat: null, gate_withheld: true, model_called: false}), decision: {}}));
  await p.polls[0](); await flush();
  assert.equal(p.ids.get('crisis').hidden, false);
  assert.equal(p.rows()[0].dataset.state, 'superseded');
  p.turns[0].resolve(p.turn({speech_token: 'fixture-approved-token'})); await flush();
  assert.equal(p.speech.length, 0); assert.equal(p.ids.get('crisis').hidden, false);
});

test('T1 polling an old card at a newer turn revision does not supersede its follow-up', async () => {
  const p = await page(); await p.send('help me plan the launch');
  p.turns[0].resolve(p.turn({kind: 'card', card: CARD, persona: null, state: snapshot({state: 'card', revision: 1, card_revision: 1})})); await flush();
  await p.send('help me plan the meeting');
  p.setPoll(snapshot({state: 'card', revision: 2, card_revision: 1, card: CARD, receipt: receipt({seat: null, gate_withheld: true}), decision: {}}));
  await p.polls[0](); await flush();
  assert.equal(p.rows()[1].dataset.state, 'pending');
  p.turns[1].resolve(p.turn({state: snapshot({revision: 2, card_revision: null})})); await flush();
  assert.equal(p.rows()[1].dataset.state, 'completed');
});

test('T1 a delayed POST for an already polled card cannot supersede a later follow-up', async () => {
  const p = await page(); await p.send('help me plan the launch');
  const cardState = snapshot({state: 'card', revision: 1, card_revision: 1, card: CARD, receipt: receipt({gate_withheld: true}), decision: {}});
  p.setPoll(cardState); await p.polls[0](); await flush();
  await p.send('help me plan the meeting');
  p.turns[0].resolve(p.turn({kind: 'card', card: CARD, persona: null, state: cardState})); await flush();
  assert.equal(p.rows()[1].dataset.state, 'pending');
  p.turns[1].resolve(p.turn({state: snapshot({revision: 2})})); await flush();
  assert.equal(p.rows()[1].dataset.state, 'completed');
});

test('T1 a new server session card is visible even when its revision is lower', async () => {
  const p = await page();
  p.setPoll(snapshot({state: 'card', revision: 5, card_revision: 5, card: CARD, receipt: receipt({gate_withheld: true}), decision: {}}));
  await p.polls[0](); await flush(); await p.send('help me plan the launch');
  const nextCard = CARD + '\nIf this was read wrong, say so in your own words. Asking is better than assuming.';
  p.setPoll(snapshot({session_id: 'new-session', mode_revision: 2, state: 'card', revision: 1, card_revision: 1, card: nextCard, receipt: receipt({gate_withheld: true}), decision: {}}));
  await p.polls[0](); await flush();
  assert.match(p.ids.get('crisis').textContent, /Asking is better than assuming/);
  assert.equal(p.rows()[0].dataset.state, 'superseded');
  p.turns[0].resolve(p.turn({kind: 'card', card: CARD, persona: null, state: snapshot({state: 'card', revision: 5, card_revision: 5})})); await flush();
  assert.match(p.ids.get('crisis').textContent, /Asking is better than assuming/);
});

test('T1 Enter preserves unfinished writing and a modifier sends', async () => {
  const p = await page(); const editor = p.ids.get('message'); editor.value = 'help me plan the launch';
  await editor.fire('keydown', {key: 'Enter', ctrlKey: false, metaKey: false, shiftKey: false}); await flush();
  assert.equal(p.turns.length, 0); assert.equal(editor.value, 'help me plan the launch');
  await editor.fire('keydown', {key: 'Enter', ctrlKey: true, metaKey: false, shiftKey: false}); await flush();
  assert.equal(p.turns.length, 1);
});

test('T1 low-demand view is announced and never becomes a request parameter', async () => {
  const p = await page(); const toggle = p.ids.get('low-demand'); toggle.checked = true; await toggle.fire('change'); await flush();
  assert.ok(toggle.getAttribute('aria-label') || toggle.getAttribute('aria-labelledby') || html.includes('Low-demand'));
  assert.equal(p.calls.filter(call => call.url === '/api/settings').length, 0);
  await p.send('help me plan the launch');
  const sent = JSON.parse(p.calls.find(call => call.url === '/api/turn').options.body);
  assert.deepEqual(Object.keys(sent), ['text']);
});

test('T1 the Decision Card formatter uses receipt facts and strips all names on cards', async () => {
  const p = await page(); const format = p.sandbox.SecondSignalDecisionCard;
  assert.equal(typeof format, 'function');
  const value = receipt({holds: [{domain: 'grief', duration: 'this turn'}], vetoes: [{persona: 'willow', reason: 'their boundaries do not fit this turn'}], preference_adjustments: ['Humour was lowered to none because this turn carries the no-humour obligation.']});
  const normal = String(format(value)); assert.match(normal, /Nikki/); assert.match(normal, /grief/); assert.match(normal, /this turn/); assert.match(normal, /Humour/);
  const card = String(format({...value, gate_withheld: true, model_called: false}));
  assert.doesNotMatch(card, /Nikki|Willow|nikki|willow/);
});

test('T1 an effort fold never hides house lines or obligation-bearing replies', async () => {
  const p = await page(); await p.send('help me plan the launch');
  p.turns[0].resolve(p.turn({effort_contract: true, house_lines: ['Visible house line.']})); await flush();
  const folds = p.document.querySelectorAll('details').filter(node => /Show the rest/.test(node.textContent));
  assert.ok(folds.length); assert.ok(folds.every(node => !node.textContent.includes('Visible house line.')));
  await p.send('help me plan the meeting');
  p.turns[1].resolve(p.turn({effort_contract: true, decision: {obligations: ['offer_companion:rowan']}, receipt: receipt({obligations: ['offer_companion:rowan']}), state: snapshot({revision: 2})})); await flush();
  assert.equal(p.document.querySelectorAll('details').filter(node => /Show the rest/.test(node.textContent)).length, folds.length);
});

test('T1 skipping the optional coping question saves no settings', async () => {
  const p = await page(); await p.ids.get('onboarding-open').click();
  p.ids.get('onboarding-choice').value = 'jokes'; await p.ids.get('onboarding-choice').fire('change');
  await p.ids.get('onboarding-skip').click(); await flush();
  assert.equal(p.calls.filter(call => call.url === '/api/settings').length, 0);
  assert.equal(p.ids.get('onboarding-panel').hidden, true);
});

test('T1 coping choices are only stored after the person confirms the declared keys', async () => {
  const p = await page(); await p.ids.get('onboarding-open').click();
  p.ids.get('onboarding-choice').value = 'plan'; await p.ids.get('onboarding-choice').fire('change');
  assert.equal(p.calls.filter(call => call.url === '/api/settings').length, 0);
  await p.ids.get('onboarding-confirm').click(); await flush();
  const requests = p.calls.filter(call => call.url === '/api/settings'); assert.equal(requests.length, 1);
  const declared = JSON.parse(requests[0].options.body).declared_preferences;
  assert.ok(declared && Object.keys(declared).length);
  assert.ok(Object.keys(declared).every(key => ['pace', 'verbosity', 'directness', 'delivery_order', 'format', 'humor_tolerance'].includes(key)));
});

test('T1 Resources opens an action link without sending a conversational turn', async () => {
  const p = await page(); await p.ids.get('resources-open').click(); await flush();
  assert.equal(p.ids.get('resources-dialog').open, true);
  assert.ok(p.ids.get('resources-content').querySelectorAll('a').some(node => node.href === 'https://findahelpline.com/'));
  assert.equal(p.calls.filter(call => call.url === '/api/turn').length, 0);
});

test('T1 the phone explanation starts empty and shows the identical optional receipt sentence', async () => {
  const p = await page({phone: true}); const value = receipt({holds: [{domain: 'grief', duration: 'this turn'}]});
  p.sandbox.render(snapshot({state: 'idle', receipt: value}));
  assert.equal(p.ids.get('phone-decision-enabled').checked, false);
  assert.equal(p.ids.get('phone-decision').hidden, true);
  assert.equal(p.ids.get('phone-decision').textContent, '');
  p.ids.get('phone-decision-enabled').checked = true; await p.ids.get('phone-decision-enabled').fire('change');
  assert.equal(p.ids.get('phone-decision').textContent, p.sandbox.SecondSignalDecisionCard(value));
  p.ids.get('phone-decision-enabled').checked = false; await p.ids.get('phone-decision-enabled').fire('change');
  assert.equal(p.ids.get('phone-decision').textContent, '');
});
