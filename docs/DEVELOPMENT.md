# Development Standards

Standing standards for working on this codebase: how to write, verify,
and land changes. Deep-dive rationale for specific subsystems lives in
dedicated `docs/*.md` files (grep `docs/` before changing pins, flags,
or config defaults; non-obvious decisions are documented there).

## Working plan

Asked by the decider, 2026-10-02: the cycle every worker follows, a
person or an AI. The **decider** rules on proposals (the "designer" of
the records); the worker analyses, proposes and does the work.

1. **Analyse before proposing.** Read the docs and the code together:
   grep `docs/` and the git history for rulings, rationale and earlier
   attempts; follow the code one step out (callers, other views, other
   platforms, what else uses it). Reproduce in the full app with debug
   logging, on the branch and on master, with the exact user steps and
   what triggers it. Read the cause from logs ([Diagnosing](#diagnosing)):
   when a finding depends on where the pointer or the focus is, log
   that position and the target from the app itself. Research outside
   when it applies (upstream code, platform docs, other applications'
   conventions). When the size of a fix is unclear, prototype it in a
   scratch copy.
2. **Propose fully analysed options.** Each item as the steps a user
   takes and what appears, checked on master and the branch; its
   cause; the fix and what it changes for the user; risks and how they
   will be checked; effort; a recommendation. Questions are numbered.
   Rulings already given are applied, not asked again: they are in
   `docs/`, cited by the proposal. In a list of what is outstanding,
   the work's objective comes first and finishing steps (desktop test,
   squash) last.
3. **Do the work with its tests.** New behaviour gets tests that fail
   on the code before (run in a scratch copy) and pass after; run the
   related test files, then the full suite ([TESTING.md](TESTING.md)).
   Check in the full app ([Verifying changes](#verifying-changes)) with
   the proposal's steps, on master too for comparison. Check in scratch
   copies only, never the decider's own files or settings. Lint, update
   the feature's doc and the work's record in the same commit, and push
   each finished piece.
4. **Report back** what was done as user steps and results, what was
   found on the way (a new issue numbered with its steps; a regression
   of the branch fixed), then the next proposals. A defect found, a
   feature not doing what it is for, comes with its fix, not a
   question (ruled by the decider 2026-10-06): fixed with its tests
   and an app check when the fix follows from the feature's design,
   prototyped and proposed when a design choice is open.
5. **The tests are the worker's** (ruled by the decider 2026-10-04,
   and twice 2026-10-06). The tests and the scripts that run them are
   the worker's responsibility: "Do not ask me about correcting test
   suites. You must absolutely correct test suites when you find
   error ... This is your job. This is your scope. It has no
   functional impact." Anything that stops them working is fixed "in
   the direct scripts or higher up in the flow of the test scripts",
   with "the best business practices": "This is not a concern you ask
   me." The end result is ruled: "the tests must be working in a sense
   that you're testing the app completely and correctly for all the
   functionalities and the design intent of the tests." So a wrong,
   unsafe or flaky test or harness is fixed as found, to the standard
   practice (not a diagnosis left open), with before and after runs,
   and reported as done: never a question, an issue to rule on, or an
   item in a list of next or open work. Asked a third time,
   2026-10-06: "I already ruled that test script are fully your
   responsibility. I also already ruled on the end results of the
   tests."

## Design

Canon decision by designer, 2026-09-28.

- **One source of truth:** no duplicated logic or data; derive what
  can be derived.
- **Modular:** one implementation per operation, reused by every path
  (the UI, loading, merging, undo).
- **Not brittle:** no special cases or order-dependent steps to force
  a result. When something cannot be done cleanly, do the simple thing
  and document what it leaves out; never risk core behaviour for a
  fringe feature.
- **Explicit fields:** a value computed from other fields gets its own
  named field (column, editor line, sort) instead of being folded into
  another field's display or sort, so users choose what to see and can
  tell what each value means. The core fields that fold a subtree value
  in keep doing so; explicit fields beside them are postponed
  ([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).
- **Read-only looks read-only (ruled by designer 2026-09-30):** a
  value the user cannot change is drawn as the window's text, like the
  dates in the editors, never in an input box: a box that ignores
  typing misleads. `widgets.read_only_text()` draws it; a control that
  turns read-only greys out, as the date controls do.
- **Interaction rules are ruled (designer 2026-10-05):** how the
  selection, the focus and the scrolling answer an action (the row a
  delete selects, where the keys move from) follows the platforms'
  conventions, is the same in every view, and changes only with a
  ruling, after researching those conventions; never as a side effect
  of another fix. Tests tell each rule from its alternatives. The
  rules: [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md) (the lists),
  [FOCUS_MANAGEMENT.md](FOCUS_MANAGEMENT.md) (the controls).
- **Deferred calls through `patterns.later`:** a debounce, delay,
  repeat or "when idle" call names its owner and never uses
  `wx.CallLater`, `wx.CallAfter` or `wx.Timer` directly, so none can
  reach a deleted window. Lazy teardown: nothing is stopped when a
  window closes or the app quits; a call whose owner is gone is
  skipped when due ([DEFERRED_CALLS.md](DEFERRED_CALLS.md)).
- **Never keep a window wx creates:** a window wx makes inside another
  (a list's header or rows, a dialog's buttons) is looked up when
  needed, never stored in an attribute. wxPython does not learn when
  wx destroys it, so a kept wrapper outlives it and is handed out for
  whatever wx creates at its address next: a button comes back as a
  plain `wx.Window`, and calls through it crash
  ([CRASH_GUARD.md](CRASH_GUARD.md#stale-wrappers-of-wxs-own-windows)).

## Code style

- **The tools live in the repository's `.venv`**
  ([DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md#step-2-create-virtual-environment)),
  flake8 at the version CI runs, black at the one that formatted the
  code:

  ```
  .venv/bin/pip install flake8==7.3.0 pep8-naming==0.15.1 black==26.3.1
  ```

  Not `pip install --user`: Debian refuses it
  ([PEP 668](https://peps.python.org/pep-0668/)), and a copy forced
  in belongs to one Python version, so it stopped working when Debian
  12 became 13 (3.11 to 3.13). A new system Python needs the
  `.venv` made again (same command) and the line above.
- **Format the files you touch with black**, line-length 79 (configured
  in `pyproject.toml`, `[tool.black]`). black output is PEP 8 compliant;
  running it is the standard way to fix whitespace and wrapping. Wrap
  comments and docstrings by hand at 72.
- **Lint with flake8.** Some codes are expected and must NOT be "fixed",
  e.g. `N802/N803/N812/N813` on wxPython's mixed-case names.
- **Run the static checks before pushing**; CI runs them on each pull
  request (`.github/workflows/checks.yml`). They catch what fails only
  when its line runs: undefined names, and names a rename missed.

  ```
  .venv/bin/python -m flake8 --select=E9,F63,F7,F821,F822,F823 taskcoachlib tests tools taskcoach.py setup.py
  .venv/bin/python tools/check_renames.py
  ```

  A library name `check_renames.py` mistakes for a missed rename goes
  in its `ALLOWED` table, with the reason.
- **Time resolution:** dates, times and durations are whole seconds;
  only log timestamps carry fractions. `DateTime` and `TimeDelta`
  enforce it. Ruling and scope:
  [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#time-resolution).
- **Naming:** `snake_case` by default. Keep CamelCase when the name
  comes from wx (method overrides, duck-typed wx interfaces) or is
  name-coupled (event type strings, `getattr` dispatch, the
  `renderXxx`/`humanReadable` coupling).
- Full rules, the flake8 fix-vs-expected list, and rename traps:
  [PEP8_MIGRATION.md](PEP8_MIGRATION.md). The style rules were first
  written down there during the PEP 8 migration; this document is the
  standing home, the migration doc keeps the migration-specific
  guidance.

## Verifying changes

- **Test through the full app, not ad-hoc scripts.** Most behavior here
  depends on real widget state, settings, and wx event flow; isolated
  snippets and throwaway test harnesses give misleading results and rot
  quickly. Launch the real app (`taskcoach-run.sh`) and exercise the
  change by hand.
- **Use the built-in debug logging** to see what the app is doing while
  you test: see [LOGGING_GUIDE.md](LOGGING_GUIDE.md).
- **Search the terminal output of an app check for `Traceback`.** An
  error inside an event handler stops nothing and shows nothing: wx
  prints it and goes on, and nothing writes a log file. Go through the
  empty states too (a new file, a view with no row) and every kind of
  view: P252 and P254 were released unseen that way
  ([REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-10-09)).
- **Unit tests are a regression net**, not the verification,
  certified for one platform: [TESTING.md](TESTING.md).

## Diagnosing

- **Work from detailed logs, not guesses.** For a UI, timing or
  ordering problem, log the state at high frequency with millisecond
  timestamps (`log_step()`) through the full app, and read the cause
  from the sequence. The screen shows the result, not the cause; a fix
  that hides the symptom (a repaint, a delay) is not a fix.
- **Layout, placement and drawing:** the geometry trace
  (`taskcoachlib/meta/geometry_trace.py`) logs the windows' wx and GTK
  geometry every 10 ms for 2 s after each event of interest, then
  every second; on GTK 3 also each allocation and each draw, with its
  place in the toplevel and the Python call that forced it. Call it
  from the code under investigation, remove the call once the cause is
  found.
- **Third-party code** (bundled, copied or patched at runtime): start
  from [THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md#before-analysing-it).
  A copy's base comes from diffing it against upstream releases, never
  from its header; a copy may still import the installed library, which
  differs per build.

## Documentation

- Update documentation when adding or changing features.
- A change users notice gets a line in `CHANGELOG.md`, under the
  version being made: its release notes
  ([PACKAGING.md](PACKAGING.md#release-notes)).
- Record non-obvious rationale (version pins, platform workarounds,
  design decisions) in a dedicated `docs/*.md` so the next reader does
  not have to rediscover it.

## Writing

Applies to commit messages, PR descriptions, code comments,
docstrings, docs and log messages.

- Say it once, in the fewest words. Leave out what the reader can get
  from the diff, the code or a linked doc.
- Explain why, not what; the code shows what.
- No investigation narrative, test diary or restated context.
- Link to an existing doc section instead of repeating it.
- Existing text is not a style template: older commits and docs may be
  wordier than this standard.

## Commits

- Keep commits atomic.
- Title: what the change does, imperative, short. No version numbers
  and no issue references (issue links are added to the PR).
- Body: a sentence or two of why, then short bullets of what changed.
- During a long stretch of development, keep every commit and push
  it: versions stay comparable commit by commit. Once the pull
  request is open and the work stabilizes, every push is the branch
  squashed into one concise commit (**ruled by designer 2026-10-07**:
  "once we have pushed a PR and we're stabilizing we always squash").
