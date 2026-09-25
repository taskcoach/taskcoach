"""Find names left behind by a rename (see docs/PEP8_MIGRATION.md).

A caller missed by a rename fails only when its line runs. Checks:

  R1  attribute use of a mixedCase or _Capitalized name defined
      nowhere, whose snake_case twin is defined: a caller of a renamed
      method
  R2  attribute use of a snake_case name defined nowhere, whose
      mixedCase twin is defined: a rename that went too far
  R3  mixedCase or _Capitalized function referenced nowhere, whose
      snake_case twin is defined: the old definition left behind, an
      override its base no longer calls, or a test double's stale
      method (unittest test* methods excepted)
  R4  getattr/hasattr/setattr/delattr of a name defined nowhere
  R5  keyword argument in a self.method() call that no method of that
      name accepts
  R6  string key spelling a parameter's old mixedCase name: keyword
      arguments passed through a dict
  R7  keyword argument read from **kwargs that no caller passes, while
      callers pass another spelling of it

"Defined" means defined, assigned, imported or a parameter anywhere in
taskcoachlib (and, for tests, in tests). Names from wx and other
libraries are not, so a library name can be a false positive: add it
to ALLOWED with the reason.

Only renames between the mixedCase and snake_case spellings of a name
are seen: a rename to other words (setIcon to set_icon_id) needs a
grep. Names built at run time (getattr with a formatted name, "set" +
name) are not seen either. A file that does not parse fails the check.

usage: python3 tools/check_renames.py [checkout]
"""

import ast
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = "taskcoachlib"
TESTS = "tests"

# (file, check, name): reason
ALLOWED = {
    ("taskcoachlib/widgets/tcsquaremap.py", "R1", "findNodeAtPosition"): (
        "squaremap library method"
    ),
    ("taskcoachlib/config/options.py", "R2", "add_option"): (
        "optparse method"
    ),
    ("taskcoachlib/thirdparty/deltaTime.py", "R2", "day_name"): (
        "calendar.day_name; pyparsing result name"
    ),
    ("taskcoachlib/thirdparty/deltaTime.py", "R2", "time_delta"): (
        "pyparsing result name"
    ),
    ("taskcoachlib/application/application.py", "R2", "get_default"): (
        "Gtk.IconTheme method"
    ),
    ("taskcoachlib/gui/appindicator.py", "R2", "get_status"): (
        "AppIndicator3 method"
    ),
    ("taskcoachlib/config/settings.py", "R4", "frozen"): (
        "sys.frozen, set by bundlers"
    ),
    ("taskcoachlib/filesystem/resourcelock.py", "R4", "st_reparse_tag"): (
        "os.stat_result field on Windows"
    ),
    ("taskcoachlib/gui/mainwindow.py", "R4", "_action"): (
        "AuiManager private attribute"
    ),
    ("taskcoachlib/widgets/frame.py", "R4", "_action"): (
        "AuiManager private attribute"
    ),
    ("taskcoachlib/gui/dialog/editor.py", "R4", "_foregroundColorEntry"): (
        "set with setattr and a format"
    ),
    ("taskcoachlib/gui/dialog/editor.py", "R4", "_backgroundColorEntry"): (
        "set with setattr and a format"
    ),
    ("taskcoachlib/gui/dialog/editor.py", "R4", "effectiveIconDefault"): (
        "optional domain method, not defined yet"
    ),
    ("taskcoachlib/widgets/masked.py", "R3", "_OnKeyDown"): (
        "wx.lib.masked override"
    ),
    ("tests/test.py", "R2", "add_option"): "optparse method",
    ("tests/unittests/ConfigTest.py", "R2", "read_file"): (
        "configparser method"
    ),
}

MIXED = re.compile(r"^_{0,2}[a-z][a-z0-9]*[A-Z]\w*$")
PRIVATE_CAPITALIZED = re.compile(r"^_+[A-Z][A-Za-z0-9]*[a-z][A-Za-z0-9]*$")
SNAKE = re.compile(r"^_*[a-z][a-z0-9]*(_[a-z0-9]+)+$")
KWARGS = {"kwargs", "kwds", "kw"}
WORD = re.compile(r"[A-Za-z_]\w*")


def snake_case(name):
    prefix = re.match(r"^_*", name).group(0)
    body = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name[len(prefix) :])
    body = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", body)
    return prefix + body.lower()


def renamable(name):
    return bool(MIXED.match(name) or PRIVATE_CAPITALIZED.match(name))


def mixed_case(name):
    prefix = re.match(r"^_*", name).group(0)
    first, *rest = name[len(prefix) :].split("_")
    return prefix + first + "".join(part.capitalize() for part in rest)


def python_files(top):
    for directory, subdirectories, files in os.walk(top):
        subdirectories[:] = sorted(
            d for d in subdirectories if not d.startswith((".", "__"))
        )
        for name in sorted(files):
            if name.endswith(".py"):
                yield os.path.join(directory, name)


def parse(top, unparsed):
    trees = {}
    for path in python_files(top):
        with open(path, encoding="utf-8") as source:
            try:
                trees[path] = ast.parse(source.read(), path)
            except SyntaxError as reason:
                unparsed.append(path)
                print("%s: cannot parse: %s" % (path, reason))
    return trees


class Index:
    """What the scanned files define and reference."""

    def __init__(self, trees):
        self.defined = set()
        self.parameters = set()
        self.functions = collections.defaultdict(list)
        self.references = collections.Counter()
        # References from inside functions of that name: super().name()
        self.self_references = collections.Counter()
        self.words_in_strings = set()
        self.passed_keywords = set()
        for tree in trees.values():
            for node in ast.walk(tree):
                self.add(node)

    def add(self, node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.defined.add(node.name)
            self.functions[node.name].append(node)
            self.self_references[node.name] += own_references(node)
            arguments = node.args
            for argument in (
                arguments.posonlyargs
                + arguments.args
                + arguments.kwonlyargs
                + [arguments.vararg, arguments.kwarg]
            ):
                if argument:
                    self.defined.add(argument.arg)
                    self.parameters.add(argument.arg)
        elif isinstance(node, ast.ClassDef):
            self.defined.add(node.name)
        elif isinstance(node, ast.Lambda):
            for argument in node.args.args + node.args.kwonlyargs:
                self.defined.add(argument.arg)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                self.defined.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.Name):
            self.references[node.id] += 1
            if not isinstance(node.ctx, ast.Load):
                self.defined.add(node.id)
        elif isinstance(node, ast.Attribute):
            self.references[node.attr] += 1
            if not isinstance(node.ctx, ast.Load):
                self.defined.add(node.attr)
        elif isinstance(node, ast.keyword) and node.arg:
            self.defined.add(node.arg)
            self.passed_keywords.add(node.arg)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            self.words_in_strings.update(WORD.findall(node.value))
        elif isinstance(node, ast.ExceptHandler) and node.name:
            self.defined.add(node.name)
        # Keyword arguments passed through a dict
        if isinstance(node, ast.Dict) or (
            isinstance(node, ast.Subscript)
            and not isinstance(node.ctx, ast.Load)
        ):
            self.passed_keywords.update(string_keys(node))


def own_references(function):
    return sum(
        1
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute)
        and node.attr == function.name
        or isinstance(node, ast.Name)
        and node.id == function.name
    )


def string_keys(node):
    if isinstance(node, ast.Subscript):
        key = node.slice
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            yield key.value
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                yield key.value


def kwargs_key(node):
    """The key a node reads from a **kwargs dict, or None."""
    if isinstance(node, ast.Call):
        target, name = node.func, None
        if (
            isinstance(target, ast.Attribute)
            and target.attr in ("pop", "get", "setdefault")
            and node.args
        ):
            target, name = target.value, node.args[0]
    elif isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
        target, name = node.value, node.slice
    else:
        return None
    if (
        isinstance(target, ast.Name)
        and target.id in KWARGS
        and isinstance(name, ast.Constant)
        and isinstance(name.value, str)
        and name.value.isidentifier()
    ):
        return name.value
    return None


def check(path, tree, index):
    for node in ast.walk(tree):
        key = kwargs_key(node)
        if key and key not in index.passed_keywords:
            other = mixed_case(key) if SNAKE.match(key) else snake_case(key)
            if other != key and other in index.passed_keywords:
                yield node, "R7", key, "callers pass " + other
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
            name = node.attr
            if name in index.defined:
                pass
            elif renamable(name) and snake_case(name) in index.defined:
                yield node, "R1", name, "renamed to " + snake_case(name)
            elif SNAKE.match(name) and mixed_case(name) in index.defined:
                yield node, "R2", name, "defined as " + mixed_case(name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name, twin = node.name, snake_case(node.name)
            if (
                renamable(name)
                and not name.startswith("test")
                and twin in index.defined
                and index.references[name] <= index.self_references[name]
                and name not in index.words_in_strings
            ):
                yield node, "R3", name, "unused; %s is defined" % twin
        elif isinstance(node, ast.ClassDef):
            yield from check_method_calls(node, index)
        elif isinstance(node, ast.Call):
            yield from check_attribute_call(node, index)
        for key in string_keys(node):
            if (
                MIXED.match(key)
                and key not in index.parameters
                and snake_case(key) in index.parameters
            ):
                yield node, "R6", key, "parameter is " + snake_case(key)


def check_attribute_call(call, index):
    if not (
        isinstance(call.func, ast.Name)
        and call.func.id in ("getattr", "hasattr", "setattr", "delattr")
        and len(call.args) >= 2
    ):
        return
    attribute = call.args[1]
    if (
        isinstance(attribute, ast.Constant)
        and isinstance(attribute.value, str)
        and attribute.value.isidentifier()
        and attribute.value not in index.defined
        and not attribute.value[:1].isupper()
        and not attribute.value.startswith("__")
    ):
        yield call, "R4", attribute.value, "defined nowhere"


def check_method_calls(class_node, index):
    # Only self.method() calls to a method of the same class: a call
    # through any other name may reach an unrelated function.
    methods = {
        node.name
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for call in ast.walk(class_node):
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "self"
            and call.func.attr in methods
        ):
            continue
        definitions = index.functions[call.func.attr]
        if any(definition.args.kwarg for definition in definitions):
            continue
        accepted = {
            argument.arg
            for definition in definitions
            for argument in definition.args.args + definition.args.kwonlyargs
        }
        for keyword in call.keywords:
            if keyword.arg and keyword.arg not in accepted:
                yield call, "R5", keyword.arg, (
                    "not a parameter of " + call.func.attr
                )


def allowed_key(path, code, name):
    path = path.replace(os.sep, "/")
    for key in ALLOWED:
        if path.endswith(key[0]) and key[1:] == (code, name):
            return key
    return None


def main(checkout):
    os.chdir(checkout)
    unparsed = []
    code_trees = parse(CODE, unparsed)
    test_trees = parse(TESTS, unparsed)
    code_index = Index(code_trees)
    test_index = Index({**code_trees, **test_trees})
    scans = [(code_trees, code_index), (test_trees, test_index)]
    used = set()
    findings = set()
    for trees, index in scans:
        for path, tree in trees.items():
            for node, code, name, message in check(path, tree, index):
                key = allowed_key(path, code, name)
                if key:
                    used.add(key)
                else:
                    findings.add((path, node.lineno, code, name, message))
    for finding in sorted(findings):
        print("%s:%d: %s %s: %s" % finding)
    failures = len(findings) + len(unparsed)
    if checkout == ROOT:
        for key in sorted(set(ALLOWED) - used):
            failures += 1
            print("%s: %s %s: ALLOWED entry no longer needed" % key)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(os.path.abspath(sys.argv[1]) if sys.argv[1:] else ROOT))
