# PEP 8 Migration Guidance

Key guidance for the ongoing PEP 8 migration. Read this before "fixing" style
warnings, especially CamelCase names. This is intentionally short: guidance,
not a changelog.

Standing development standards (style, verification, docs, commits) live in
[DEVELOPMENT.md](DEVELOPMENT.md); this document keeps the migration-specific
details.

## Formatter and line length

- Formatter: **black, line-length 79** (configured in `pyproject.toml`,
  `[tool.black]`). black output is always PEP 8 compliant; it is a stricter,
  opinionated subset (double quotes, a fixed wrapping style, trailing commas).
  Running black is the standard way to fix whitespace and wrapping.
- PEP 8 line length: **79 for code, 72 for comments and docstrings**. black
  wraps code; wrap comments and docstrings by hand.

## Naming: snake_case, with a wx exception

Default: `snake_case` for functions, methods, variables, and arguments.

**Keep CamelCase (do not rename) when the name comes from wx:**

- Methods that **override** wx methods (`Destroy`, `Bind`, `Unbind`,
  `ProcessEvent`, `UpdateWindowUI`, `RemoveIcon`, any `wx.adv.TaskBarIcon`
  override). Renaming an override breaks it: wx then calls the parent version.
  This is correctness, not style.
- Methods or attributes that **duck-type a wx interface** so callers can treat
  the object as a wx widget (e.g. `AppIndicatorTaskBarIcon` mirroring
  `wx.adv.TaskBarIcon`). Renaming breaks those callers.

PEP 8 explicitly allows this: "mixedCase is allowed only in contexts where
that's already the prevailing style ... to retain backwards compatibility."
So flake8 `N802/N803/N812/N813` on wx names are **expected; do not fix them**.

**A name being widely used across the codebase is NOT a keep-reason.** The only
keep-reasons are wx coupling and name-coupling (below). "Used in many files"
only means the rename has more call sites: rename it everywhere, or, if the
blast radius is very large (e.g. a domain-wide parameter name), defer it to its
own dedicated, comprehensive change. Do not leave it CamelCase because it is a
convention.

## Do not blindly rename name-coupled callbacks

Some names are coupled by string, not by reference, so renaming silently breaks
dispatch: event type strings and their handlers, `getattr`-based dispatch, and the
`humanReadable`/`renderXxx` coupling (see `ATTRIBUTE_PATTERN.md` and
`PUBLISHER_OBSERVER.md`).

Before renaming any non-wx CamelCase name:

1. Confirm it is internal (not a wx override or wx-interface method).
2. Find every reference: `registerObserver`, `Bind`, `getattr`, and
   cross-module callers.
3. Rename in lockstep, then run `tools/check_renames.py` and the tests.

## flake8 codes: fix vs expected

- **Fix:** `E501` (except unbreakable URLs/strings), `W505` (comments
  and docstrings over 72), `E1xx`/`E3xx`, `F401`/`F402`, blank-line rules.
- **Expected / ignore:** `N802/N803/N812/N813` on wx names; `W503/W504`
  (black's preferred operator-wrapping style); `W291` inside a
  translatable string (the text is the translation key); `F401` on a
  package `__init__.py` re-export. Bundled library code (`thirdparty/`)
  keeps its own style: no black, its names as they are.

## Finishing the Migration

To Do 26 in [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#to-do):
steps 1 and 2 are in 2.0.3.1; steps 3 to 5 come after that release
(**ruled by designer 2026-10-07**).
Inventory 2026-10-05 (pep8-naming on `taskcoachlib` without
`thirdparty/` and `patches/`, and `tests`): 7,896 findings in 247 of
389 files.

| Code | Names | Code | Tests |
|---|---|---|---|
| N802 | functions and methods | 1,948 | 3,321 |
| N806 | local variables | 921 | 593 |
| N803 | parameters | 501 | 111 |
| N815 | class attributes | 184 | 124 |
| N804 | `class_` for `cls` | 102 | 0 |
| N816 | module globals | 66 | 3 |
| N801, N818 | classes, exceptions | 5 | 10 |

Of the code's 1,334 method names, 163 are wx's (keep); 1,171 are Task
Coach's own, with 10,964 occurrences. 105 of those are in wx style
(`RefreshAllItems`, `OnBeforeShowToolTip`): each checked, as wx may
call it. The tests have 2,370 `testXxx` names (2,816 definitions).

Built from strings, renamed with their builder; the strings stored in
settings and files stay, the builder converts:

- `<key>SortFunction`, `<key>SortEventTypes`: sort keys and column
  names from the settings (`sorter.py`).
- `<field>ChangedEventType`, `effective<Field>ChangedEventType`
  (`scheduler.py`, the task viewer's choices).
- The owner methods made per owned kind (`addNote`,
  `notesChangedEventType`, `setAttachments`: `owner.py`, `merge.py`).
- `%sColor` (`editor.py`), `endOf%s` from the effort aggregation
  (`reducer.py`), `<getter>Source` (`appearance.py`), template fields
  (`templates.py`, the writer's `<name>tmpl`), the export's
  `renderXxx`, the editor tests' `_%sCombo` and `_%sSync`.

Kept, as other code calls them by these names: wx's (overrides,
duck-typed interfaces), unittest's (`setUp`, `tearDown`), squaremap's
and other libraries' callbacks; the list is taken from the libraries'
classes.

Steps, one commit each, each followed by the full suite,
`tools/check_renames.py` and an app check:

1. Locals, `cls`, test method names. Test method names done
   2026-10-05: 2,814 definitions (`testFooBar` to `test_foo_bar`,
   digits as words: `test_round_to_10_seconds`); the same tests
   run, file by file; 142 of them, too long for a line once snake
   case, shortened by hand 2026-10-07 (the same 4,062 tests).
   `testoutputOptionGroup` and
   `testselectionOptionGroup` stay for step 3: `config/options.py`
   finds them by the suffix `OptionGroup`. `cls` done 2026-10-06:
   106 class methods (`@classmethod`, `classmethod()` in
   `owner.py`, `__new__`, the `Singleton` metaclass), each one's
   first parameter only. Test locals done 2026-10-06: 571 names
   in 426 functions; left for step 2: parameters reassigned in
   their function; skipped: functions reading `locals()` or
   `vars()`, and a name whose snake_case is already a module
   (`Attachment`). Code locals done 2026-10-06: 801 names in 384
   functions, 84 files; left for step 2: 13 parameters reassigned
   in their function, `Attribute` (the module `attribute` is
   imported) and `eventType` in `TaskFile.__init__` (an
   `event_type` loop follows).
2. Parameters, with keyword callers and dict keys. Parameters no
   caller sees done 2026-10-06: 324 names in 235 functions, 95
   files; none is a keyword in a call (the repository's or an
   imported library's) or in a string other than a docstring.
   `BaseCommand.getItems()`, called nowhere, removed. Keyword
   parameters done the same day: 26 names renamed with every
   keyword use (176 places, 28 files), each in no string, no
   `dict()` key, no library's parameters and outside
   `thirdparty/` and `patches/`. Left: 60 names, each with what
   holds it: a string or `dict()` key naming it (task file and
   settings fields, kept for step 3 with their builders), a wx
   parameter of that name (`agwStyle`, `newValue`, `subMenu`),
   `thirdparty/` or `patches/` (`dateTime`,
   `includeMinutes`), and 11 locals (N806).
3. Methods and attributes, package by package, each string family
   with its builder; To Do 2 and D1 within.
4. Class, exception and module names.
5. Docs citing old names (P230, P112); pep8-naming in CI with the
   keep-list, so no new camelCase.

Risks: a name reached only through a string or a library fails only
when its line runs; `check_renames.py`, a search of every old name in
string literals, the suite and the app checks cover it. Two test
methods with the same snake_case name would hide one: checked per
class.

