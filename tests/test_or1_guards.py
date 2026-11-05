"""Measurement stays outside the policy and harness request paths."""
from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT = "evals.or1"
LEXICON = "evals.or1_lexicon"
RESULTS = "secondsignal_harness.results"


def _module_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    parts = list(relative.with_suffix("").parts)
    if parts[0] == "src":
        parts.pop(0)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _literal(node: ast.AST, constants: dict[str, str] | None = None) -> str | None:
    if isinstance(node, ast.Name) and constants is not None:
        return constants.get(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _literal(node.left, constants), _literal(node.right, constants)
        if left is not None and right is not None:
            return left + right
    return None


def _called(node: ast.AST, aliases: dict[str, str]) -> str:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        return _called(node.value, aliases) + "." + node.attr
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "getattr" and len(node.args) >= 2:
            attribute = _literal(node.args[1])
            if attribute is not None:
                return _called(node.args[0], aliases) + "." + attribute
    return "<unresolved>"


def _edges(path: Path, root: Path) -> set[str]:
    """Resolve imports, aliases and literal dynamic imports; reject opaque loaders."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module = _module_name(path, root)
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    aliases: dict[str, str] = {}
    constants = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            value = _literal(statement.value)
            if isinstance(target, ast.Name) and value is not None:
                constants[target.id] = value
    edges: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                edges.add(name.name)
                aliases[name.asname or name.name.split(".")[0]] = (
                    name.name if name.asname else name.name.split(".")[0]
                )
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = importlib.util.resolve_name("." * node.level + base, package)
            edges.add(base)
            for name in node.names:
                target = base + "." + name.name
                edges.add(target)
                aliases[name.asname or name.name] = target
    # Import functions assigned to aliases retain their identity.
    for _ in range(3):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                value = _called(node.value, aliases)
                if value != "<unresolved>":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            aliases[target.id] = value
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _called(node.func, aliases)
        if name in {"importlib.import_module", "__import__", "builtins.__import__"}:
            target = _literal(node.args[0], constants) if node.args else None
            assert target is not None, f"{path}: unresolved dynamic import"
            if target.startswith("."):
                anchor = (_literal(node.args[1]) if len(node.args) > 1 else None)
                if anchor is None:
                    anchor = next((_literal(k.value) for k in node.keywords
                                   if k.arg == "package"), None)
                assert anchor is not None, f"{path}: unresolved relative dynamic import"
                target = importlib.util.resolve_name(target, anchor)
            edges.add(target)
            if name.endswith("__import__"):
                fromlist = next((k.value for k in node.keywords if k.arg == "fromlist"), None)
                if fromlist is None and len(node.args) > 3:
                    fromlist = node.args[3]
                if isinstance(fromlist, (ast.List, ast.Tuple)):
                    for item in fromlist.elts:
                        member = _literal(item)
                        assert member is not None, f"{path}: unresolved import fromlist"
                        edges.add(target + "." + member)
        elif name in {"exec", "eval", "builtins.exec", "builtins.eval"}:
            raise AssertionError(f"{path}: opaque executable import path")
        elif name.endswith((".spec_from_file_location", ".module_from_spec", ".exec_module",
                            ".SourceFileLoader", ".load_module", ".run_path", ".run_module")):
            assert module == "evals.or1.provenance", f"{path}: unaudited source loader"
    return edges


def _source(name: str, root: Path) -> Path | None:
    # The lexicon's private namespace deliberately omits the eager policy __init__.
    if name == "_or1_policy":
        return None
    if name.startswith("_or1_policy."):
        name = "secondsignal." + name[len("_or1_policy."):]
    relative = Path(*name.split("."))
    for base in (root / "src", root):
        for candidate in ((base / relative).with_suffix(".py"), base / relative / "__init__.py"):
            if candidate.is_file():
                return candidate
    return None


def _reachable(starts: list[Path], root: Path) -> set[str]:
    pending = starts[:]
    seen: set[Path] = set()
    edges: set[str] = set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        for edge in _edges(path, root):
            edges.add(edge)
            target = _source(edge, root)
            if target is not None and target not in seen:
                pending.append(target)
    return edges


def _is_measurement(name: str) -> bool:
    return name == LEXICON or name == INSTRUMENT or name.startswith(INSTRUMENT + ".")


def _assert_request_boundary(starts: list[Path], root: Path) -> None:
    forbidden = sorted(name for name in _reachable(starts, root) if _is_measurement(name))
    assert not forbidden, f"request path imports measurement: {forbidden}"


def test_instrument_imports_only_stdlib_itself_and_the_results_leaf():
    files = sorted((ROOT / "evals/or1").rglob("*.py"))
    assert files, "the measurement package is missing"
    for path in files:
        for name in _edges(path, ROOT):
            assert not (name == "secondsignal" or name.startswith("secondsignal.")), name
            assert not name.startswith("secondsignal_harness"), (
                "normal harness imports execute the eager parent; use the audited leaf adapter", name
            )
            assert (name == INSTRUMENT or name.startswith(INSTRUMENT + ".")
                    or name.split(".")[0] in sys.stdlib_module_names), (path, name)
    # The source loader is one explicit exception, pinned to the unchanged leaf.
    from evals.or1 import provenance
    assert Path(provenance._results.__file__).resolve() == ROOT / "src/secondsignal_harness/results.py"
    assert provenance._results.__name__ == RESULTS
    assert provenance.write_json_result is provenance._results.write_json_result
    source = (ROOT / "evals/or1/provenance.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    loads = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "spec_from_file_location"]
    assert len(loads) == 1 and _literal(loads[0].args[0]) == RESULTS


def test_lexicon_cannot_import_router_even_through_another_local_module():
    imports = _reachable([ROOT / "evals/or1_lexicon.py"], ROOT)
    assert not any(name == "secondsignal" or name.endswith(".router")
                   or ".router." in name for name in imports), sorted(imports)
    assert {"_or1_policy.signals", "_or1_policy.safety"} <= imports


def test_router_safety_harness_and_table_cannot_import_measurement():
    starts = [path for directory in ("src/secondsignal", "src/secondsignal_harness",
                                     "apps/talking_table")
              for path in (ROOT / directory).rglob("*.py")]
    assert starts
    _assert_request_boundary(starts, ROOT)


def test_import_guard_rejects_direct_relative_dynamic_and_indirect_wiring(tmp_path):
    module = tmp_path / "evals/request.py"
    module.parent.mkdir()
    examples = [
        "import evals.or1\n",
        "from evals.or1 import runner\n",
        "from evals import or1_lexicon\n",
        "from . import or1\n",
        "from .or1 import runner\n",
        "import importlib as loader\nloader.import_module('evals.or1')\n",
        "from importlib import import_module as load\nload('evals.or1.runner')\n",
        "import importlib\nload = importlib.import_module\nload('evals.or1')\n",
        "__import__('evals.' + 'or1')\n",
        "import importlib\nMODULE = 'evals.or1'\nimportlib.import_module(MODULE)\n",
        "__import__('evals', fromlist=['or1'])\n",
        "import importlib\ngetattr(importlib, 'import_module')('evals.or1')\n",
        "import importlib\nimportlib.import_module('.or1', 'evals')\n",
        "import importlib\nimportlib.import_module(name_from_configuration)\n",
        "exec(code_from_configuration)\n",
    ]
    for source in examples:
        module.write_text(source, encoding="utf-8", newline="\n")
        try:
            _assert_request_boundary([module], tmp_path)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"guard missed forbidden import: {source}")
    helper = tmp_path / "bridge.py"
    helper.write_text("from evals import or1\n", encoding="utf-8", newline="\n")
    module.write_text("import bridge\n", encoding="utf-8", newline="\n")
    try:
        _assert_request_boundary([module], tmp_path)
    except AssertionError:
        pass
    else:
        raise AssertionError("guard missed transitive request-path wiring")
    helper.write_text("import json\n", encoding="utf-8", newline="\n")
    _assert_request_boundary([module], tmp_path)


def _isolated(code: str, destination: Path) -> None:
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, str(ROOT), str(destination)],
        capture_output=True, text=True, cwd=ROOT, env=environment, timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_importing_and_writing_the_instrument_loads_no_policy_or_harness_runtime(tmp_path):
    _isolated(r"""
import importlib
import importlib.abc
import pathlib
import pkgutil
import sys
root = pathlib.Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / 'src')]
class BlockRuntime(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'secondsignal' or fullname.startswith('secondsignal.'):
            raise AssertionError('instrument imported policy: ' + fullname)
        if fullname == 'secondsignal_harness' or fullname.startswith('secondsignal_harness.'):
            raise AssertionError('instrument imported harness runtime: ' + fullname)
sys.meta_path.insert(0, BlockRuntime())
package = importlib.import_module('evals.or1')
for module in pkgutil.walk_packages(package.__path__, 'evals.or1.'):
    importlib.import_module(module.name)
from evals.or1 import provenance
path = pathlib.Path(sys.argv[2]) / 'leaf-result.json'
document = provenance.result_document({'rows': []}, specification_hash='absent')
provenance.write_json_result(path, document)
assert provenance.read_json_result(path)['header']['reproducibility'] == 'not-reproducible'
assert not any(n == 'secondsignal' or n.startswith('secondsignal.')
               or n == 'secondsignal_harness' or n.startswith('secondsignal_harness.')
               for n in sys.modules)
""", tmp_path)


def test_lexicon_source_loading_never_executes_the_router(tmp_path):
    _isolated(r"""
import importlib.abc
import pathlib
import sys
root = pathlib.Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / 'src')]
class BlockRouter(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'secondsignal' or fullname.endswith('.router'):
            raise AssertionError('lexicon loaded eager policy or router: ' + fullname)
sys.meta_path.insert(0, BlockRouter())
from evals.or1_lexicon import load_policy_modules
signals, safety = load_policy_modules(root)
assert signals.__name__ == '_or1_policy.signals'
assert safety.__name__ == '_or1_policy.safety'
assert pathlib.Path(signals.__file__).resolve() == root / 'src/secondsignal/signals.py'
assert pathlib.Path(safety.__file__).resolve() == root / 'src/secondsignal/safety.py'
assert not any(name == 'secondsignal' or name.endswith('.router') for name in sys.modules)
""", tmp_path)
