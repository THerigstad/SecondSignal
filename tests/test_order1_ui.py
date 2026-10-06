"""Decision 1/3/4 current-push presentation checks; no model or vendor network."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.talking_table import __main__ as launcher
from apps.talking_table import server
from secondsignal.profiles import load_roster

ROOT = Path(__file__).resolve().parents[1]
DOOR = (
    "This describes the characters, not you. For now, your choice lasts for this visit. "
    "We're building it so your characters stay the way you set them, and so you can "
    "shape them to fit what you need."
)
NOTICE = "A prototype for the operator and adults the operator knows. Not a crisis service."


def _function(source, name):
    """Extract a top-level browser function for an offline DOM contract test."""
    match = re.search(r"^([ ]*)function " + name + r"\(", source, re.M)
    assert match, name
    start = match.start()
    end = source.index("\n" + match[1] + "}", match.end()) + len(match[1]) + 2
    return source[start:end]


DOM = r"""
class Node {
  constructor(tag='div', text='') { this.tagName=tag;this.ownText=text;this.children=[];this.attrs={};this.dataset={};this.className='';
    this.classList={add:n=>{this.className+=' '+n;},contains:n=>this.className.split(' ').includes(n),toggle:(n,on)=>{this.className=this.className.split(' ').filter(v=>v!==n).join(' ');if(on)this.className+=' '+n;}}; }
  get textContent(){return this.ownText+this.children.map(c=>c.textContent).join('');}
  set textContent(v){this.ownText=String(v);this.children=[];}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.ownText='';this.children=nodes;}
  setAttribute(k,v){this.attrs[k]=String(v);}
  addEventListener(){}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  querySelectorAll(selector){const all=this.children.flatMap(c=>[c,...c.querySelectorAll('*')]);if(selector==='*')return all;
    const match=selector.match(/^\.([\w-]+)(?:\[data-([\w-]+)="([^"]+)"\])?$/);
    return all.filter(n=>match&&n.classList.contains(match[1])&&(!match[2]||n.dataset[match[2].replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]===match[3]));}
}
const nodes=new Map();const $=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
const document={createElement:tag=>new Node(tag),activeElement:null,querySelectorAll:s=>$('plates').querySelectorAll(s),querySelector:s=>$('plates').querySelector(s)};
function element(tag,text,cls){const n=new Node(tag,text??'');n.className=cls||'';return n;}
const el=element;
function chooseName(){}
const input=JSON.parse(process.argv[1]);const profiles=input.profiles;
const state={config:{roster:profiles,settings:{presentation:input.presentation,chosen_names:input.chosen},local:true},last:null,count:0,pending:new Set(),busy:false,ready:true};
let presentation=input.presentation;const chosenForms=new Map();
for(const p of profiles)if(input.chosen[p.id])chosenForms.set(p.id,p.plate.findIndex(v=>v[0]===input.chosen[p.id]));
const panels=[];let busy=false;
"""


@pytest.mark.parametrize("surface", ["talking_table", "demo"])
@pytest.mark.parametrize("presentation", ["as_written", "women", "men", "neither"])
def test_both_surfaces_render_two_names_without_gender_labels(surface, presentation):
    node = shutil.which("node")
    assert node, "Node is required for the offline browser DOM check (no skipped tests)"
    roster = load_roster()
    profiles = [dict(
        id=p.id, one_line=p.one_line, plate=p.plate,
        names={v: p.name_for(v) for v in ("as_written", "women", "men", "neither")},
        neitherChoices=[p.name_for("neither", chosen=n) for n, _ in p.plate],
    ) for p in roster.values()]
    if surface == "talking_table":
        source = (ROOT / "apps/talking_table/static/table.js").read_text(encoding="utf-8")
        names = ("namePair", "nameOf", "drawTable", "paintTable")
    else:
        source = (ROOT / "demo/index.html").read_text(encoding="utf-8")
        names = ("namePair", "nameOf", "renderPlateNames", "drawTable", "paintTable")
    program = DOM + "\n".join(_function(source, n) for n in names) + r"""
drawTable();
console.log(JSON.stringify({plates:document.querySelectorAll('.plate').map(p=>({
  names:p.querySelector('.plate-names').children.filter(n=>n.tagName==='button'||n.classList.contains('form-name')).map(n=>n.textContent),
  text:p.querySelectorAll('*').map(n=>n.ownText).join(' '),aria:p.attrs['aria-label'],
  childAria:p.querySelectorAll('*').map(n=>n.attrs['aria-label']||'').join(' ')
})),name:nameOf('ellis')}));
"""
    result = subprocess.run([node, "-e", program, json.dumps(dict(
        profiles=profiles, presentation=presentation, chosen={"ellis": "Elli"},
    ))], capture_output=True, text=True, check=True)
    output = json.loads(result.stdout)
    assert len(output["plates"]) == 7
    for plate, profile in zip(output["plates"], profiles):
        assert plate["names"] == [p[0] for p in profile["plate"]]
        assert not re.search(r"\b(she|he)\b", " ".join(
            [plate["text"], plate["aria"], plate["childAria"]]), re.I)
    if presentation == "neither":
        assert output["name"].split(" (")[0] == "Elli"


@pytest.mark.parametrize("path", ["apps/talking_table/static/index.html", "demo/index.html"])
def test_exact_presentation_door_words(path):  # Order T1, 2026-10-05: current_visit -> presentation copy pin.
    source = (ROOT / path).read_text(encoding="utf-8")
    expected = DOOR if path.startswith("demo/") else 'This describes the characters, not you. Remember on this computer saves this choice across restarts. New session resets the current choice.'  # Order T1, 2026-10-05: Table visit-only copy -> remembered; demo unchanged.
    assert expected in source
    assert '<option value="as_written">' in source
    assert '<option value="neither">' in source


def test_name_choice_refreshes_existing_reply_and_assist_labels():
    node = shutil.which("node")
    assert node, "Node is required for the offline browser DOM check (no skipped tests)"
    source = (ROOT / "apps/talking_table/static/table.js").read_text(encoding="utf-8")
    roster = load_roster()
    profiles = [dict(id=p.id, names={v: p.name_for(v)
                for v in ("as_written", "women", "men", "neither")}, plate=p.plate)
                for p in roster.values()]
    program = DOM + "\n".join(_function(source, name) for name in
                              ("namePair", "nameOf", "refreshPresentationNames")) + r"""
const header=el('h3','Ellis','character-name');header.dataset.persona='ellis';
const assist=el('p','Willow is assisting.','character-name');assist.dataset.persona='willow';assist.dataset.suffix=' is assisting.';
$('plates').append(header,assist);refreshPresentationNames();
console.log(JSON.stringify([header.textContent,assist.textContent]));
"""
    result = subprocess.run([node, "-e", program, json.dumps(dict(
        profiles=profiles, presentation="neither", chosen={"ellis": "Elli", "willow": "Will"},
    ))], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout) == ["Elli", "Will is assisting."]


def test_presentation_is_restored_from_remembered_settings(tmp_path, monkeypatch):  # Order T1, 2026-10-05: not_restored -> restored.
    monkeypatch.setattr(server, "_secret_blob", lambda value, **kwargs: value)
    first = server.TableApp(data_dir=tmp_path / "table")
    second = None
    try:
        config = first.update_settings({"remember": True, "presentation": "neither",
                                        "chosen_names": {"ellis": "Elli"}})
        assert config["settings"]["presentation"] == "neither"
        assert config["settings"]["chosen_names"] == {"ellis": "Elli"}
        stored = json.loads(first.settings_path.read_text(encoding="utf-8"))["settings"]
        assert "presentation" not in stored and "chosen_names" not in stored
        second = server.TableApp(data_dir=tmp_path / "table")
        assert second.settings["presentation"] == "neither"  # Order T1, 2026-10-05: as_written -> remembered neither.
        assert second.settings["chosen_names"] == {"ellis": "Elli"}  # Order T1, 2026-10-05: empty -> remembered name choice.
        assert second.settings["remember"] is True
        assert first.reset()["settings"]["presentation"] == "as_written"
        assert first.settings["chosen_names"] == {}
    finally:
        first.close()
        if second:
            second.close()


def test_legacy_remembered_presentation_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "_secret_blob", lambda value, **kwargs: value)
    folder = tmp_path / "table"
    folder.mkdir()
    (folder / "settings.json").write_text(json.dumps({
        "settings": {"presentation": "men", "chosen_names": {"ellis": "Ellis"}},
        "key_blob": "",
    }), encoding="utf-8")
    app = server.TableApp(data_dir=folder)
    try:
        assert app.settings["presentation"] == "as_written"
        assert app.settings["chosen_names"] == {}
    finally:
        app.close()


@pytest.mark.parametrize("surface", ["page", "server", "launcher"])
def test_prototype_notice_has_no_gendered_pronoun(surface):
    if surface == "page":
        source = (ROOT / "apps/talking_table/static/index.html").read_text(encoding="utf-8")
        notices = re.findall(r'<p class="(?:prototype|dialog-prototype)">([^<]+)</p>', source)
        assert len(notices) == 2
    else:
        notices = [server.PROTOTYPE if surface == "server" else launcher.NOTICE]
    for notice in notices:
        assert notice == NOTICE
        assert not re.search(r"\b(?:she|he)\b", notice, re.I)


def test_neither_debug_and_setting_values_do_not_add_character_pronoun_labels(tmp_path):
    app = server.TableApp(data_dir=tmp_path / "table")
    try:
        config = app.update_settings({"presentation": "neither"})
        turn = app.turn("Help me make a plan for my work tomorrow.")
        # These are the actual strings shown by whyDrawer and the settings UI.
        debug = turn["decision"].get("explain", "")
        debug += turn["decision"].get("presentation_note", "")
        debug += json.dumps(turn["verdict"])
        settings = json.dumps(config["settings"])
        assert not re.search(r"\b(?:she|he)\b", debug + settings, re.I)
        assert config["settings"]["adapter"] == "fake"
    finally:
        app.close()
