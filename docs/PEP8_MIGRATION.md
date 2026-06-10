# PEP 8 Migration Guidance

Key guidance for the ongoing PEP 8 migration. Read this before "fixing" style
warnings, especially CamelCase names. This is intentionally short: guidance,
not a changelog.

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
dispatch: pubsub topics and handlers, `getattr`-based dispatch, and the
`humanReadable`/`renderXxx` coupling (see `ATTRIBUTE_PATTERN.md` and
`PUBLISHER_OBSERVER.md`).

Before renaming any non-wx CamelCase name:

1. Confirm it is internal (not a wx override or wx-interface method).
2. Find every reference: `registerObserver`, `pub.subscribe`, `Bind`,
   `getattr`, and cross-module callers.
3. Rename in lockstep and run the tests.

## flake8 codes: fix vs expected

- **Fix:** `E501` (except unbreakable URLs/strings), `E1xx`/`E3xx`,
  `F401`/`F402`, blank-line rules.
- **Expected / ignore:** `N802/N803/N812/N813` on wx names; `W503/W504`
  (black's preferred operator-wrapping style).
