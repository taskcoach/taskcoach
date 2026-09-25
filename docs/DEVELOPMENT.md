# Development Standards

Standing standards for working on this codebase: how to write, verify,
and land changes. Deep-dive rationale for specific subsystems lives in
dedicated `docs/*.md` files (grep `docs/` before changing pins, flags,
or config defaults; non-obvious decisions are documented there).

## Code style

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
  python3 -m flake8 --select=E9,F63,F7,F821,F822,F823 taskcoachlib tests tools taskcoach.py setup.py
  python3 tools/check_renames.py
  ```

  A library name `check_renames.py` mistakes for a missed rename goes
  in its `ALLOWED` table, with the reason.
- **Naming:** `snake_case` by default. Keep CamelCase when the name
  comes from wx (method overrides, duck-typed wx interfaces) or is
  name-coupled (pubsub topics, `getattr` dispatch, the
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
- **Unit tests are a regression net**, not the verification. Run a file
  from `tests/`, under `xvfb-run` so no windows open on your desktop:

  ```
  xvfb-run -a ../.venv/bin/python test.py unittests/domainTests/TaskTest.py
  ```

  A test that no longer matches the app and needs a rewrite is marked
  `@test.stale("reason")`; `grep -rn "test.stale" tests` lists them.

## Documentation

- Update documentation when adding or changing features.
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
- Squash work-in-progress commits into one concise commit before
  pushing a branch.
