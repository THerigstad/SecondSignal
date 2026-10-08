// Order T2: real Table and phone controls, with an offline DOM and fake API.
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

async function page({phone = false, settings = {}, initial = null, saved = new Map(), local = true} = {}) {
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
  const config = {local, settings: {adapter: 'fake', model: 'fake-1', presentation: 'as_written', chosen_names: {}, operator_circle: false, voice_enabled: true, voice_slots: {}, declared_preferences: {}, humour_grief: false, language_style: 'match', ...settings}, roster, phone: {}, state: snapshot(), storage: 'fixture storage', presentation_previews: {}, resources: {text: 'Directory', actions: [{label: 'Open directory', url: 'https://findahelpline.com/'}]}};
  if (initial) config.state = initial;
  config.honesty = {limitations: {version: '0.fixture', lines: ['149 documented gaps', '14 recorded dissents']}, session_lines: ['audit.jsonl and receipts.jsonl remain local', 'New session is shared'], operator_token_available: false, token_note: "Operator-circle mode needs the operator's token on this computer.", network_warning: 'The phone page travels over plain HTTP on your Wi-Fi. Anyone on this network who finds the address and the pairing code can read the table. Turn it on only on a network you trust.'};
  const calls = [], turns = [], speech = [], storage = saved, streams = [], handlers = new Map(); let pollState = config.state, objectResult = null;
  class EventSource {
    constructor(url) { this.url = url; this.listeners = {}; streams.push(this); }
    addEventListener(name, fn) { this.listeners[name] = fn; }
    emit(value) { this.listeners.state({data: JSON.stringify(value)}); }
    drop() { this.listeners.error({}); }
    close() { this.closed = true; }
  }
  const sandbox = {document, console, URLSearchParams, EventSource, location: {search: '', pathname: '/'}, navigator: {},
    localStorage: {getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value), removeItem: key => storage.delete(key)},
    fetch: async (url, options) => { calls.push({url, options}); let result;
      if (handlers.has(url)) result = await handlers.get(url)(options);
      else if (url === '/api/config') result = config;
      else if (url === '/api/state') result = pollState;
      else if (url === '/api/turn') { const item = pending(); turns.push(item); result = await item.promise; }
      else if (url === '/api/settings') { Object.assign(config.settings, JSON.parse(options.body)); result = config; }
      else if (url === '/api/object') result = objectResult || {object_text: JSON.parse(options.body).text, object_notice: ''};
      else if (url === '/api/session/reset') { config.state = snapshot({session_id: 'two', state: 'idle'}); config.settings.presentation = 'as_written'; result = config; }
      else if (url === '/api/resources') result = config.resources;
      else if (url === '/api/network') { config.phone = {enabled: JSON.parse(options.body).enabled, urls: [], code: ''}; result = config; }
      else if (url === '/api/review/flag') result = {saved: true};
      else if (url === '/api/lights/check') result = {started: false, message: 'Lights are off or not set up; nothing to show.'};
      else throw new Error('Unexpected endpoint: ' + url);
      return {ok: !result?.error, status: result?.error ? 428 : 200, json: async () => structuredClone(result)};
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
  return {ids, document, calls, turns, speech, config, polls, timers, send, turn, sandbox, streams, storage, handlers, setPoll: value => { pollState = value; }, setObject: value => { objectResult = value; }, rows: () => document.querySelectorAll('.submission')};
}
export {page, snapshot, receipt, flush, pending, CARD};
