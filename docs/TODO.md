# Task Coach TODO

General to-dos: work that concerns several features or the whole code
base.

## How To-dos Are Recorded

**Ruled by designer 2026-11-10:**

- A feature's to-dos are in its own doc, in its TODO section; this
  list holds only the general ones. A refactor keeps its own To Do
  list in its record ([DEVELOPMENT.md](DEVELOPMENT.md#documentation)).
- A doc that has a TODO section keeps it, near the top (after its
  index or table of contents), so the to-dos stay grouped by feature.
  When its last item goes, the section stays, with "Nothing to do." A
  doc without one gets one with its first to-do.
- A done item is crossed out and cut to a stub that links where its
  outcome is recorded. Once it has shipped in several releases, the
  stub goes: git keeps the history.

## Table of Contents

1. [Monkeypatches and Workarounds](#1-monkeypatches-and-workarounds)

---

## 1. Monkeypatches and Workarounds

**Status:** Review periodically to determine if still needed

The list of bundled, copied and runtime-patched third-party code is
[THIRD_PARTY_CODE.md](THIRD_PARTY_CODE.md); review it every 6 to 12
months and whenever a dependency's version changes.
