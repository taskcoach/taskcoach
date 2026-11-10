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
   - State only what was measured or read; mark the rest "inferred".
     "Probably" means the analysis is not done. A claim about a
     library or platform cites its source: file, line, version or
     commit, link. A site that refuses is no stopping point: an
     encyclopedia, an archive, the project's machine-readable data or
     a clone of its repository closes the gap.
   - A redesign starts with a scenario table in its topic doc, inside
     the decider's model of it: one row per user action or event, the
     signal it sends, its effect. It is reviewed before any code.
   - A replacement or a removal comes with what the old code does and
     where, the lines added and removed (code, tests, packaging), each
     behaviour difference and its risk, the evidence, and how to undo
     it.
2. **Propose fully analysed options.** Each item as the steps a user
   takes and what appears, checked on master and the branch; its
   cause; the fix and what it changes for the user; risks and how they
   will be checked; effort; a recommendation. Questions are numbered.
   Rulings already given are applied, not asked again: they are in
   `docs/`, cited by the proposal. In a list of what is outstanding,
   the work's objective comes first and finishing steps (desktop test,
   squash) last.
   - **One issue at a time** (ruled by the decider 2026-10-03): the
     simplest open one that matters to people using Task Coach (what
     they see or do, their data, security, the release) or to keeping
     it building; core use first (tasks, categories, efforts; English,
     French, Portuguese, Spanish). One recommended solution, prototyped
     with its tests and an app check, and a yes or no to rule on. An
     item with no clear solution goes to the end of the To Do list; an
     edge case with no effect on use goes to Deferred.
   - **Rulings cover their edge cases**: grep `docs/` for each
     question's topic before asking and apply what is ruled. "The rest
     is ok" approves every remaining item. Restoring released
     behaviour is not a question, nor is undoing one's own mistake or
     unrequested addition: fix it and say so.
   - Each question carries the background to answer it without the
     doc, inside its item of the one numbered list.
3. **Do the work with its tests.** New behaviour gets tests that fail
   on the code before (run in a scratch copy) and pass after; run the
   related test files, then the full suite ([TESTING.md](TESTING.md)).
   Check in the full app ([Verifying changes](#verifying-changes)) with
   the proposal's steps, on master too for comparison. Check in scratch
   copies only, never the decider's own files or settings. Lint, update
   the feature's doc and the work's record in the same commit, and push
   each finished piece.
   - **No rewrites** (ruled by designer 2026-11-10): code and documents
     change by incremental edits, never rewritten whole: a rewrite
     drops what mattered. Each edit is reviewed in place (the diff and
     the text around it) for anything dropped or broken, with the
     integrated analysis and the tests between edits.
4. **Report back** what was done as user steps and results, what was
   found on the way (a new issue numbered with its steps; a regression
   of the branch fixed), then the next proposals. A defect found, a
   feature not doing what it is for, comes with its fix, not a
   question (ruled by the decider 2026-10-06): fixed with its tests
   and an app check when the fix follows from the feature's design,
   prototyped and proposed when a design choice is open.
   - A finding gives its trigger exactly (what makes it happen and
     what does not), on master and the branch.
   - An issue that does not reproduce after a real attempt is closed,
     with where it was looked for. A warning traced to inside a
     library, no app code on its stack, stays in the logs.
   - A problem older than the work goes to the P list, verified on
     master; intended behaviour is not a defect.
   - Every fix and review comes first, then one test list for the
     decider. When the decider reviews by running the app, each
     change ends with the new version running on their desktop
     (`./taskcoach-run.sh`).
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
  a result: one general rule that every case follows. When something
  cannot be done cleanly, do the simple thing and document what it
  leaves out; never risk core behaviour for a fringe feature.
- **Keep released behaviour** (ruled by designer 2026-09-29): what
  users rely on stays, unless shown to be a bug in the app on master.
  A feature carries only what was asked for. A better field comes
  beside the old one, under a new key, and only when the work needs
  it. A changed default reaches new installs only
  ([SETTINGS.md](SETTINGS.md#persistence)).
- **Support only the interface** (ruled by designer 2026-09-29): no
  code for hand-edited task files or settings. Older files are
  converted when loaded, and code that only an unreachable case uses
  is removed.
- **Remove obsolete workarounds:** once its cause is shown to be gone
  (the history, the original bug, the library's source), a workaround
  is deleted with its docs, with no safety net in its place.
- **Own code before packages:** a missing package is first replaced
  by own code (the standard library, `ctypes` to a library already
  present) where that is safe and simple
  ([DEPENDENCIES.md](DEPENDENCIES.md)).
- **Draw through the system theme** (ruled by designer 2026-10-19):
  borders, focus marks and colours come from `wx.RendererNative` and
  `wx.SystemSettings`, never from values measured on one desktop.
  "The same look as X" is X's own theme drawing, with only what must
  not show taken away, never another element. Dark-theme colours
  change only on the designer's instruction (D11 in
  [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do)).
- **Speed through direct structures:** a slow path gets lookups built
  once and kept until the data changes (an item's position, a
  parent's children), not a faster scan per item. Anything still
  above a fraction of a second is traced.
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
  turns read-only greys out, as the date controls do and the Markdown
  preview does, its text in the normal colour
  ([MARKDOWN.md](MARKDOWN.md#decided), 2026-11-10).
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
- **Every changed line follows PEP 8**, whatever the code around it
  does: new names in snake_case, tests included; a camelCase method
  whose body is rewritten is renamed, with its siblings when the
  rename is contained ([PEP8_MIGRATION.md](PEP8_MIGRATION.md#changed-lines)).
- **ASCII only** in code, comments, log messages and commit messages:
  no em or en dash; consoles such as Windows' cp932 fail on them.
- **Review one step out** before a change is done: callers and
  callees, overrides, names coupled by string (`getattr`, keyword
  arguments, event names), behaviour that moves with a mechanism. A
  removed parameter is searched by position too, not only by name.
  Then the static checks, the full suite and the app check.
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
- **App checks run on a private display**, with their own settings
  and a scratch task file, never on the decider's desktop, settings or
  files: [TESTING.md](TESTING.md#app-checks).
- **Speed on a loaded computer:** compare counts (repaints, layouts,
  calls) and runs alternated in the same minutes, never times across
  runs: both wall and CPU time drift with the load
  ([RENDERING_SPEED.md](RENDERING_SPEED.md#how-it-was-measured)).

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
  version being made ([Versions](#versions)): its release notes
  ([PACKAGING.md](PACKAGING.md#release-notes)).
- Record non-obvious rationale (version pins, platform workarounds,
  design decisions) in a dedicated `docs/*.md` so the next reader does
  not have to rediscover it.
- **One doc per topic**, holding everything about it; other docs link
  to it rather than repeat it.
- **To-dos live in the doc of the feature they concern**, in its TODO
  section near the top, kept with "Nothing to do." once empty; only
  general ones go in [TODO.md](TODO.md#how-to-dos-are-recorded).
- **Rulings are recorded in the topic's doc**, marked "Ruled by
  designer <date>", with the designer's words where they matter. The
  docs are the record of what is ruled, not the code or the tests.
- **Before investigating**, grep `docs/` and `git log` for the
  subject: recorded work and measurements are cited, not redone. A
  topic that keeps coming back gets its own doc.
- **A refactor's record** (such as
  [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md)) keeps one numbered
  To Do list in the order items were found. A done or decided item
  stays in place, crossed out and cut to a stub linking its detail; an
  item parked for later moves to the end. Problems older than the work
  go in its Pre-existing Issues (P1, P2, ...), work ruled out of it in
  Deferred and Will Not Do (D1, D2, ...), never listed as outstanding
  again. It holds only that work and what the decider asked for: a
  standalone fix is recorded in its feature's doc and the changelog,
  and a feature's doc links every open issue about it, wherever
  recorded.
- **A bug in a third-party library** gets a section of its own in the
  topic's doc, its title naming the library and the symptom so a
  search finds it: the versions, the cause with source links, what
  triggers it, the workaround and where it lives. No reports upstream
  (ruled by designer 2026-10-06): "As long as you document it in this
  project, other people can find it through searching".

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
- **Release text and docs describe the fixes (ruled by designer
  2026-10-19):** release notes (`CHANGELOG.md`), commit messages and
  PR descriptions say what changes for the app's users: only what a
  user of the previous release notices, in their words; nothing that
  is not packaged (docs, tests, tools, build checks, code style), no
  implementation, never how a change was found or checked, and no fix
  of a step taken while making the change. Docs and
  comments describe the solution, technical detail and source
  references included, without process or what one machine showed.
  The designer's words, on a commit message that said how the fixes
  were checked: "that is not relevant for release information!?";
  "It's also very specific to a machine and is of no use to anyone
  else. Your fix and docs should only describe the solutions/fixes...";
  "Some of the very specifics docs, like under MacOS docs, you have
  have technical information like that with cross reference to the
  files, etc. But regardless, none of that is actually packaged nor
  released, so it's not relevant to a release or PR file." And on the
  release notes: "Your release note is STILL a mess!  users don't care
  that you fixed your mistakes because you had steps you did that did
  not belong in the release notes..., eg "A dropped folder gets a
  file:///C:/ link.""
- **No issue or pull request numbers (ruled by designer
  2026-10-25):** code, comments, docs, release notes, commit messages
  and PR descriptions never cite a GitHub issue or pull request number
  (`#123`): GitHub turns each mention into a cross-reference on that
  issue. Describe the problem instead; the designer adds the
  references by hand. The designer's words: "don't put the issue
  numbers in the code and docs, because they github creates a buch of
  crossreferences and noise.  I only put the references in after
  manually."

## Commits

- Keep commits atomic.
- Title: what the change does, imperative, short. No version numbers
  and no issue references ([Writing](#writing)).
- Body: short bullets of what changed for users, each with its why,
  said once; no paragraph that the bullets repeat (**ruled by designer
  2026-11-10**: "The two are duplicating ... very not human-like").
  The state before is described as it was, and every change of the
  branch is named, speed-ups included ([Writing](#writing)).
- No attribution lines: a commit or pull request carries its author
  only, no co-author or "generated with" line.
- A branch is named by its change (or, for a release collecting
  several, by what they share), never by an issue number.
- Commit and push each finished piece. During a long stretch of
  development, keep every commit: versions stay comparable commit by
  commit. Once the pull request is open and the work stabilizes,
  every push is the branch squashed into one concise commit (**ruled
  by designer 2026-10-07**: "once we have pushed a PR and we're
  stabilizing we always squash"). The unsquashed history stays in a
  local `<branch>-history` branch, not pushed. A pull request opened
  from several commits gets no description: squash first, so the one
  commit's text is the description.

## Versions

**Ruled by designer 2026-10-25**: the patch is incremented for each
release, as `taskcoachlib/meta/data.py` says, not for each change: the
version being made is one patch ahead of the current release (2.0.3.7
released: 2.0.3.8). The designer's words: "don't increment the version
for each change! ... we should only increment 1 patch ahead of the
current release."

Versions are Major.Minor.Milestone.Patch. A bump bigger than a patch
raises the Milestone and resets the patch (2.0.2.27 to 2.0.3.0), never
the Minor (**ruled by designer 2026-09-28**): a lower patch in the
same milestone would sort as a downgrade for package managers.

A version change sets `version`, `patch` and the release date in
`taskcoachlib/meta/data.py` and the package names in `README.md`, opens
its `## <version>` section in `CHANGELOG.md`, and is a line in the
commit body ("Version 2.0.3.10."), never in the title. The release
itself: [PACKAGING.md](PACKAGING.md#creating-a-release).
