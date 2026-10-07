// Order T2: real Table and phone controls, with an offline DOM and fake API.
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

async function page({phone = false, settings = {}} = {}) {
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
  const roster = ['cody', 'ellis', 'nikki', 'rowan', 'seren', 'vandal', 'willow'].map(id => ({id, one_line: id + ' profile description', domains: ['creative_block'], modes: ['reflection'], contraindications: ['somatic_distress'], handoffs: {analysis: 'seren'}, plate: [[id, 'he'], [id, 'she']], names: {as_written: [id, 'he'], women: [id, 'she'], men: [id, 'he'], neither: [id, 'they']}}));
  const config = {local: true, settings: {adapter: 'fake', model: 'fake-1', presentation: 'as_written', chosen_names: {}, operator_circle: false, voice_enabled: true, voice_slots: {}, declared_preferences: {}, humour_grief: false, language_style: 'match', ...settings}, roster, phone: {}, state: snapshot(), storage: 'fixture storage', presentation_previews: {}, resources: {text: 'Directory', actions: [{label: 'Open directory', url: 'https://findahelpline.com/'}]}};
  const calls = [], turns = [], speech = [], storage = new Map(); let pollState = snapshot(), objectResult = null;
  const sandbox = {document, console, URLSearchParams, location: {search: '', pathname: '/'}, navigator: {},
    localStorage: {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key)},
    fetch: async (url, options) => { calls.push({url, options}); let result;
      if (url === '/api/config') result = config;
      else if (url === '/api/state') result = pollState;
      else if (url === '/api/turn') { const item = pending(); turns.push(item); result = await item.promise; }
      else if (url === '/api/settings') { Object.assign(config.settings, JSON.parse(options.body)); result = config; }
      else if (url === '/api/object') result = objectResult || {object_text: JSON.parse(options.body).text, object_notice: ''};
      else if (url === '/api/session/reset') { config.state = snapshot({session_id: 'two', state: 'idle'}); config.settings.presentation = 'as_written'; result = config; }
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
  return {ids, document, calls, turns, speech, config, polls, timers, send, turn, sandbox, setPoll: value => { pollState = value; }, setObject: value => { objectResult = value; }, rows: () => document.querySelectorAll('.submission')};
}


const offered = (persona, label, text) => ({persona, label, text});
const getButton = (node, text) => node.querySelectorAll('button').find(button => button.textContent === text);
const release = async (p, extra = {}) => { await p.send('help me plan the launch'); p.turns.at(-1).resolve(p.turn(extra)); await flush(); };

test('T2 biography comes from profiles and uses the individual name override', async () => {
  const p = await page({settings: {presentation: 'women', presentation_overrides: {nikki: 'men'}}});
  const profile = p.config.roster.find(item => item.id === 'nikki');
  profile.names.men = ['Nik', 'he'];
  await p.ids.get('save-presentation').click(); await flush();
  const plate = p.document.querySelectorAll('.plate').find(node => node.dataset.persona === 'nikki');
  await plate.querySelector('.biography-name').click(); await flush();
  assert.equal(p.ids.get('biography-dialog').open, true);
  assert.equal(p.ids.get('biography-title').textContent, 'Nik');
  assert.match(p.ids.get('biography-content').textContent, /creative block/);
  assert.match(p.ids.get('biography-content').textContent, /somatic distress/);
  assert.match(p.ids.get('biography-content').textContent, /analysis: seren/);
  assert.equal(p.calls.filter(call => call.url === '/api/turn').length, 0);
});

test('T2 handback marks the saved plate and submits exact offer text while preserving a draft', async () => {
  const p = await page();
  await release(p, {deferred_ask: 'willow', handback: offered('willow', 'Want Willow back now?', 'Could I talk to Willow?')});
  const plate = p.document.querySelectorAll('.plate').find(node => node.dataset.persona === 'willow');
  assert.equal(plate.dataset.saved, 'true'); assert.match(plate.textContent, /Seat saved/);
  p.ids.get('message').value = 'unfinished writing';
  await getButton(p.ids.get('handback-offer'), 'Want Willow back now?').click(); await flush();
  const body = JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body);
  assert.deepEqual(body, {text: 'Could I talk to Willow?', action: 'handback', target: 'willow'});
  assert.equal(p.ids.get('message').value, 'unfinished writing');
  assert.equal(p.ids.get('handback-offer').hidden, true);
});

test('T2 assist slip requires record metadata and sends only the exact phone ask on tap', async () => {
  const p = await page(); await release(p, {assist: 'willow'});
  assert.equal(p.document.querySelectorAll('.assist-slip').length, 0);
  await release(p, {assist: 'willow', assist_offer: offered('willow', 'Willow can be asked, too.', 'Could I talk to Willow?')});
  const slip = p.document.querySelector('.assist-slip'); assert.match(slip.textContent, /House/);
  const before = p.calls.filter(call => call.url === '/api/turn').length;
  assert.equal(before, 2);
  await slip.querySelector('button').click(); await flush();
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'Could I talk to Willow?', action: 'assist', target: 'willow'});
});

test('T2 only released replies expose a server page link and up to three second views', async () => {
  const p = await page();
  const extras = {page_url: '/api/pages/session-one/1', second_opinions: ['cody','ellis','seren','willow'].map(id => offered(id, `What would ${id} add?`, `What would ${id} add?`))};
  await release(p, extras);
  assert.equal(p.document.querySelectorAll('.made-page').length, 1);
  assert.equal(p.document.querySelector('.made-page').href, extras.page_url);
  assert.equal(p.document.querySelectorAll('.reply-controls button').length, 3);
  await getButton(p.document.body, 'What would cody add?').click(); await flush();
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'What would cody add?', action: 'second_view', target: 'cody'});
  p.turns.at(-1).resolve(p.turn({second_view: true})); await flush();
  assert.match(p.document.querySelector('.current-turn').textContent, /a second view/);
  await release(p, {...extras, kind: 'withheld'});
  assert.equal(p.document.querySelectorAll('.made-page').length, 1);
});

test('T2 the object is separately checked and a refusal clears its field', async () => {
  const p = await page(); await release(p);
  p.ids.get('table-object').value = 'a brass key';
  await p.ids.get('save-object').click(); await flush();
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/object').at(-1).options.body), {text: 'a brass key'});
  assert.match(p.document.querySelector('.plate[data-persona="nikki"]').textContent, /a brass key/);
  assert.equal(p.calls.filter(call => call.url === '/api/turn').length, 1);
  p.setObject({object_text: '', object_notice: 'That line belongs in the message, not on the table.'});
  p.ids.get('table-object').value = 'refused fixture'; await p.ids.get('save-object').click(); await flush();
  assert.equal(p.ids.get('table-object').value, '');
  assert.equal(p.ids.get('object-notice').textContent, 'That line belongs in the message, not on the table.');
});

test('T2 a declared tag leaves the raw message intact and applies to one submission', async () => {
  const p = await page(); p.ids.get('draft-tag').value = 'letter';
  const raw = '  help me plan the launch\n'; await p.send(raw);
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: raw, tag: 'letter'});
  assert.equal(p.ids.get('draft-tag').value, '');
  p.turns[0].resolve(p.turn({tag: 'letter'})); await flush();
  assert.equal(p.document.querySelector('.turn-tag').textContent, 'letter');
  await p.send('help me plan the meeting');
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'help me plan the meeting'});
});

test('T2 house name is literal text and room and individual overrides are explicit settings', async () => {
  const p = await page({settings: {house_name: '<b>My table</b>'}});
  assert.equal(p.ids.get('idle-house-name').textContent, '<b>My table</b>');
  assert.equal(p.ids.get('idle-house-name').querySelectorAll('b').length, 0);
  assert.equal(p.document.querySelectorAll('[data-override-persona]').length, 7);
  p.ids.get('room').value = 'studio'; p.ids.get('override-willow').value = 'men';
  await p.ids.get('save-presentation').click(); await flush();
  const data = JSON.parse(p.calls.filter(call => call.url === '/api/settings').at(-1).options.body);
  assert.equal(data.room, 'studio'); assert.deepEqual(data.presentation_overrides, {willow: 'men'});
});

test('T2 sprint has quiet pause stop and elapsed-time expiry with no server fields', async () => {
  const p = await page(); await release(p, {persona: 'cody'});
  const before = p.calls.length;
  await p.document.querySelector('.sprint-start').click(); await flush();
  assert.equal(p.document.querySelector('.sprint-clock').textContent, '25:00');
  await getButton(p.document.querySelector('.sprint-shutter'), 'Pause').click();
  assert.ok(getButton(p.document.querySelector('.sprint-shutter'), 'Resume'));
  await getButton(p.document.querySelector('.sprint-shutter'), 'Stop').click();
  assert.equal(p.document.querySelectorAll('.sprint-shutter').length, 0);
  assert.equal(p.calls.length, before);
  let clock = 0; const timer = p.sandbox.SecondSignalT2.createSprint(() => clock);
  timer.start('seren'); clock += 60000; assert.equal(timer.snapshot().remaining, 1440000);
  timer.toggle(); clock += 60000; assert.equal(timer.snapshot().remaining, 1440000);
  timer.toggle(); clock += 1440000; assert.equal(timer.snapshot().persona, null);
  await p.send('help me plan the meeting');
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'help me plan the meeting'});
});

test('T2 a card closes the biography and hides all Table extras including an active sprint', async () => {
  const p = await page(); await release(p, {persona: 'cody', deferred_ask: 'willow', handback: offered('willow','Want Willow back now?','Could I talk to Willow?')});
  await p.document.querySelector('.sprint-start').click();
  await p.document.querySelector('.biography-name').click();
  await release(p, {kind: 'card', persona: null, card: CARD, state: snapshot({state: 'card', card_revision: 3}), receipt: receipt({gate_withheld: true, aftermath: 'The house held the floor. No character saw this message.'})});
  assert.equal(p.ids.get('biography-dialog').open, false);
  assert.equal(p.ids.get('composer-extras').hidden, true); assert.equal(p.ids.get('handback-offer').hidden, true);
  assert.equal(p.document.querySelectorAll('.sprint-shutter').length, 0);
  assert.match(p.ids.get('crisis').textContent, /The house held the floor. No character saw this message./);
});

test('T2 ask acknowledgement appears before the reply and only once', async () => {
  const p = await page(); const line = "You asked for Vandal. Willow is taking this one, because loss is Willow's ground. Vandal hasn't gone anywhere.";
  await release(p, {ask_acknowledgement: line, house_lines: [line]});
  const current = p.document.querySelector('.current-turn').textContent;
  assert.ok(current.indexOf(line) < current.indexOf('Take the next step.'));
  assert.equal(current.split(line).length, 2);
});

test('T2 phone applies individual names and sends the exact declared phone ask', async () => {
  const p = await page({phone: true});
  p.sandbox.render(snapshot({seated: 'nikki', presentation: 'women', presentation_overrides: {nikki: 'men'}, house_name: '<b>My table</b>'}));
  assert.equal(p.ids.get('phone-house-name').textContent, '<b>My table</b>');
  assert.match(p.ids.get('seated-plate').getAttribute('aria-label'), /Nik/);
  const button = getButton(p.ids.get('ask-grid'), 'Ask for Nik');
  button.click(); await flush();
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'Could I talk to Nik?', action: 'ask', target: 'nikki'});
  const legacy = await page({phone: true});
  legacy.sandbox.render(snapshot({state: 'idle', presentation: 'as_written'}));
  assert.ok(getButton(legacy.ids.get('ask-grid'), 'Ask for Ellis'));
  legacy.ids.get('ask-grid').querySelectorAll('button').find(node => node.dataset.persona === 'ellis').click(); await flush();
  assert.deepEqual(JSON.parse(legacy.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'Could I talk to Ellis?'});
});

test('T2 phone name plate opens source biography and a card removes it and offers', async () => {
  const p = await page({phone: true});
  p.sandbox.render(snapshot({seated: 'nikki', handback: offered('willow','Want Willow back now?','Could I talk to Willow?')}));
  await p.ids.get('seated-plate').querySelector('.form-name').click(); await flush();
  assert.equal(p.ids.get('phone-biography').open, true);
  assert.match(p.ids.get('phone-biography-content').textContent, /creative block/);
  assert.equal(p.calls.filter(call => call.url === '/api/turn').length, 0);
  p.sandbox.render(snapshot({state: 'card'}));
  assert.equal(p.ids.get('phone-biography').open, false); assert.equal(p.ids.get('phone-handback').hidden, true);
});

test('T2 a historical second view carries its released source identity and original wording', async () => {
  const p = await page();
  await release(p, {second_opinions: [{...offered('willow', 'What would Will add?', 'What would Will add?'), source_session: 'one', source_revision: 1}]});
  await release(p, {state: snapshot({revision: 2})});
  await getButton(p.document.body, 'What would Will add?').click(); await flush();
  assert.deepEqual(JSON.parse(p.calls.filter(call => call.url === '/api/turn').at(-1).options.body), {text: 'What would Will add?', action: 'second_view', target: 'willow', source_session: 'one', source_revision: 1});
});
