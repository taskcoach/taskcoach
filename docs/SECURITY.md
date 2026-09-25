# Security: Dynamic Dispatch Policy

## Table of Contents

1. [No Dynamic Function Dispatch](#no-dynamic-function-dispatch)
2. [Audit Results](#audit-results)
3. [General Principles](#general-principles)

---

## No Dynamic Function Dispatch

**Rule:** No `getattr(obj, string)(...)` dispatch where the string selects
which function to call. Use explicit `if/elif` blocks or direct function
references instead.

**Rationale:**

- **Grepability:** `_status_filter_overlay` appears as a direct call, not hidden
  inside a string. `grep _status_filter_overlay` finds all callers.
- **IDE support:** "Find usages" and "Go to definition" work on direct calls.
  They do not work on `getattr(self, method_name)`.
- **Security:** A string-based dispatcher can be tricked into calling
  unintended methods if the string comes from external input. Explicit
  `if/elif` limits dispatch to the exact methods listed.
- **Readability:** Reading `get_bitmap()` shows exactly what can happen —
  two branches, two methods. No need to trace what strings are in the table.

**Bad:** `getattr(self, method)(route, size)` — string selects function.

**Good:** Explicit `if/elif` on method name — see `synthetic_icon_generator.py:render_bitmap()`.

---

## Audit Results

Full audit of `taskcoachlib/` for dynamic function calls (2026-02-16).

### Category 1: getattr-as-dispatch (string to function call)

| File | Line | Pattern | Risk | Status |
|------|------|---------|------|--------|
| `gui/icons/synthetic_icon_generator.py` | 55-65 | `if/elif` on `method_name` | None | **Fixed** — explicit if/elif |
| `changes/monitor.py` | 59,112 | `getattr(klass, "%sChangedEventType" % name)()` | Low | Internal: name from hardcoded list |
| `changes/sync.py` | 208+ | `getattr(memOwner, "add%s" % className)(obj)` | Low | Internal: className from sync protocol |
| `patches/hypertreelist.py` | 5508 | `getattr(self._main_win, method)(*a, **k)` | Low | Internal: widget method proxy |
| `viewer/task.py` | 730 | `getattr(task.Task, "%sChangedEventType" % choice)()` | Low | Internal: choice from settings |
| `editor.py` | 808 | `getattr(self.items[0], "%sColor" % colorType)()` | Low | Internal: colorType is "fg"/"bg" |

### Category 2: eval/exec

No `eval` or `exec`. Text from a task file is parsed, never run:

| File | Pattern | Status |
|------|---------|--------|
| `persistence/xml/reader.py` | `ast.literal_eval` of colour and expanded-context tuples | **Fixed**: was `eval` |
| `persistence/xml/reader.py` | `safe_eval_date_expr()` of date expressions in templates saved before tskversion 32 | **Fixed**: names limited to `OLD_TEMPLATE_NAMES` (was the whole `date` module); `_` attributes and modules refused |

### Category 3: Dynamic imports

| File | Line | Pattern | Status |
|------|------|---------|--------|
| `application.py` | 137 | `__import__(import_name)` | OK — version checking, hardcoded names |
| `gui/icons/icon_library.py` | 390 | `importlib.import_module(module_name)` | OK — theme name from catalog JSON |

---

## General Principles

1. **No user-controlled strings in `getattr`/`eval`/`exec` paths.** If a
   string comes from user input, file data, or network data, it must never
   be used to select which function to call.

2. **Prefer explicit dispatch.** When a routing decision depends on a string,
   use `if/elif` or a dict mapping strings to direct function references
   (not strings).

3. **Audit new patterns.** When adding new `getattr` calls, verify:
   - The attribute name is hardcoded or from a trusted internal source.
   - The target object only has safe methods.
   - The call is documented in this file.

4. **Dynamic imports are acceptable** when the module name comes from a
   trusted source (hardcoded list, catalog JSON under developer control).
