// Order T1: the phone explanation is optional and Resources is read-only.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

const html = readFileSync(new URL('../static/sigils.html', import.meta.url), 'utf8');
const source = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)]
  .filter(([, attributes]) => !attributes.includes('src=') && !attributes.includes('application/json'))[0][2];
const flush = async () => { for (let i = 0; i < 3; i++) await new Promise(resolve => setImmediate(resolve)); };

async function phone(state) {
  const nodes = new Map(), calls = [], formatted = [];
  class Node {
    constructor() {
      this.children = []; this.listeners = {}; this.attributes = {}; this.dataset = {};
      this.style = {}; this.textContent = ''; this.checked = false; this.hidden = false;
      this.classList = {add() {}};
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(name, value) { this.attributes[name] = value; }
    addEventListener(name, handler) { this.listeners[name] = handler; }
    querySelectorAll() { return this.children; }
    querySelector(name) { return this.parts?.[name] || new Node(); }
    showModal() { this.open = true; }
    close() { this.open = false; }
    focus() { this.focused = true; }
  }
  for (const [, id] of html.matchAll(/\bid="([^"]+)"/g)) nodes.set(id, new Node());
  for (const id of ['roster', 'sigil-colors']) {
    nodes.get(id).textContent = html.match(new RegExp('<script type="application/json" id="' + id + '">([\\s\\S]*?)</script>'))[1];
  }
  nodes.get('phone-decision').hidden = true;
  const document = {getElementById: id => nodes.get(id), createElement: () => new Node(), body: new Node()};
  const resource = {text: 'Declared country resource line.', actions: [{label: 'Find a crisis line', url: 'https://findahelpline.com'}]};
  const sandbox = {
    document, URL, URLSearchParams, location: {search: '', pathname: '/sigils.html'}, history: {replaceState() {}},
    setTimeout() {}, clearTimeout() {},
    fetch: async (url, options) => { calls.push({url, options}); return {ok: true, json: async () => url === '/api/state' ? state : resource}; },
    SecondSignalDecisionCard: receipt => { formatted.push(receipt); return receipt.gate_withheld ? 'The crisis card holds the floor. No model was called.' : 'A voice sat. A model was called.'; },
  };
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, {filename: 'sigils.html'});
  await flush();
  return {nodes, calls, formatted, resource, document};
}

test('phone Decision Card switch starts off and emits no added sentence', async () => {
  const page = await phone({state: 'idle', receipt: {seat: 'seren'}});
  assert.equal(page.nodes.get('phone-decision-enabled').checked, false);
  assert.equal(page.nodes.get('phone-decision').hidden, true);
  assert.equal(page.nodes.get('phone-decision').textContent, '');
  assert.equal(page.formatted.length, 0);
  assert.ok(html.includes('<script src="/static/table.js"></script>'));
});

test('phone uses the shared receipt sentence only after opt-in and clears it when switched off', async () => {
  const receipt = {gate_withheld: true, display_names: {}, seat: null};
  const page = await phone({state: 'card', receipt});
  const control = page.nodes.get('phone-decision-enabled');
  control.checked = true;
  control.listeners.change();
  assert.equal(page.formatted[0], receipt);
  assert.equal(page.nodes.get('phone-decision').textContent, 'The crisis card holds the floor. No model was called.');
  assert.equal(page.nodes.get('phone-decision').hidden, false);
  assert.equal(control.attributes['aria-checked'], 'true');
  assert.equal(page.document.body.dataset.state, 'card');
  assert.equal(page.nodes.get('asks').hidden, true);
  control.checked = false;
  control.listeners.change();
  assert.equal(page.nodes.get('phone-decision').textContent, '');
  assert.equal(page.nodes.get('phone-decision').hidden, true);
});

test('phone Resources opens a labelled dialog with actions and never submits a turn', async () => {
  const page = await phone({state: 'idle'});
  await page.nodes.get('phone-resources-open').listeners.click();
  assert.equal(page.nodes.get('phone-resources').open, true);
  assert.equal(page.nodes.get('phone-resource-line').textContent, page.resource.text);
  assert.equal(page.nodes.get('phone-resource-actions').children[0].href, 'https://findahelpline.com');
  assert.deepEqual(page.calls.map(call => call.url), ['/api/state', '/api/resources']);
  assert.ok(page.calls.every(call => call.options.method !== 'POST'));
  page.nodes.get('phone-resources-close').listeners.click();
  assert.equal(page.nodes.get('phone-resources').open, false);
  assert.equal(page.nodes.get('phone-resources-open').focused, true);
});
