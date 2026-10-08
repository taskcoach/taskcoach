# Markdown

A request, parked 2026-10-08 by the designer: nothing is implemented.
This records what is decided, the open question and what a build
would take.

1. [The Request](#the-request)
2. [Decided](#decided)
3. [The Open Question](#the-open-question)
4. [Options](#options)
5. [A Minimal Set](#a-minimal-set)
6. [What It Would Take](#what-it-would-take)
7. [Prototype Findings](#prototype-findings)
8. [Review Scenarios](#review-scenarios)

## The Request

[#436](https://github.com/taskcoach/taskcoach/issues/436), 2026-05-08,
from the reporter of #458, who keeps a work log in effort descriptions
and exports it to HTML: "a tab or button to show [the effort text]
formatted as MarkDown", the text still saved as plain text, only the
display converted; if possible, Markdown highlighted while typing.
Their sketch: `wx.stc.StyledTextCtrl > markdown > wx.html2.WebView`.

Inferred, not stated: Markdown pasted from GitHub or AI chats, read
formatted.

## Decided

By the designer, 2026-10-08:

- **A Preview button only**: the description formatted in place of the
  box, read only; a second click goes back to editing. The edit box
  stays as released: no Markdown fonts while typing, its spell check
  unchanged.
- **Every multi-line Description box** (tasks, notes, categories,
  attachments, efforts), through the shared box
  (`widgets.MultiLineTextCtrl`), so a later window with a long text
  box gets it too. One-line fields (Subject) do not.
- **The text stays as typed**: files unchanged; older releases show
  the raw text.
- **No new packages, ideally**
  ([The Open Question](#the-open-question)). **No WebView**: a browser
  engine needs far more packages ([Options](#options)).

Proposed, to confirm when built:

- **Remembered per item** in the task file, as saved view state like
  a task's expanded state
  ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)): it marks the file
  unsaved so autosave keeps it, sets no modification date and has no
  undo. A field older releases ignore; the format number goes up.
- **Placement, in space already empty**: in editors with labels (task,
  note, category, attachment), right under the "Description" label; in
  the effort editor, which has none, bottom left in the Close button's
  row, mirroring Close.

## The Open Question

A minimal Markdown preview in Task Coach's own code, or a converter
package? The objective is no dependency packages; but a preview that
formats Markdown wrongly is not much better than none. The designer
asked the reporter on #436 (2026-10-08) whether a minimal Markdown
preview would be acceptable; waiting for the answer.

## Options

| | Own converter | markdown-it (package) | WebView |
|---|---|---|---|
| Packages | none | markdown-it-py, mdurl; for bare links linkify-it-py, uc-micro-py | wx.html2: on Linux a separate package (Debian `python3-wxgtk-webview4.0`) with WebKitGTK; on Windows Edge's WebView2 runtime; and a converter too |
| Size | about 300 to 400 lines and their tests (estimate) | 100 KB download, 125 KB with bare links; 450 KB installed on Debian 13 | WebKitGTK alone is large |
| Markdown | [the minimal set](#a-minimal-set) | CommonMark, tables, strikethrough: pasted GitHub or AI text comes out right | the same converter, with CSS: GitHub's look, web images |
| Display | `wx.html` (in wxPython) | `wx.html` | a browser engine: scripts off, HTML cleaned |
| Platforms | all alike | Debian, Ubuntu 24.04, Fedora and Arch package it; Ubuntu 22.04 has 1.1.0 and no linkify; the Windows and macOS builds bundle it; without it, no Preview button | Linux only with the extra package |

The packages, checked 2026-10-08, all plain Python:

| Package | Depends on | Wheel | Installed (Debian 13) |
|---|---|---|---|
| markdown-it-py 3.0.0 | mdurl | 88 KB | 287 KB |
| mdurl 0.1.2 | nothing | 10 KB | 42 KB |
| linkify-it-py 2.0.3 (optional) | uc-micro-py | 20 KB | 79 KB |
| uc-micro-py 1.0.3 | nothing | 6 KB | 43 KB |

Debian's `python3-markdown-it` depends on all three others. For
comparison, pyenchant is 180 KB plus its C library and dictionaries
([DEPENDENCIES.md](DEPENDENCIES.md)).

Rejected: Python-Markdown joins single lines into one paragraph and
needs a blank line before a list, so plain descriptions lose their
line breaks.

## A Minimal Set

A proposal: the Markdown Guide's basic syntax and the extensions
pasted text uses most (GitHub, AI chats).

- Headings: `#` to `######` at the start of a line
- Bold and italic: `**`, `__`, `*`, `_` (underscores not inside words)
- Lists: `-`, `*`, `+` and numbered, nested by indent
- Code: inline `` `code` ``, fenced blocks (```` ``` ```` and `~~~`)
- Links: `[text](url)`, `<url>`, bare `https://` and `www.` (the box
  already finds these: `_StyledTextCtrl._url_pattern`)
- Block quotes: `>`
- Horizontal rule: `---` on a line between blank lines
- Tables: GitHub's pipe tables
- Strikethrough: `~~`
- Task lists: `- [ ]` and `- [x]` shown as boxes
- Backslash escapes

Each line break stays one, as in GitHub comments (not strict
CommonMark), so a plain description looks as typed.

Left out, because they change plain text unexpectedly or need more
than `wx.html`: headings by underlining (a line followed by `---` or
`===`), indented code blocks (four spaces), raw HTML (shown as typed),
images (`wx.html` loads no web images), footnotes, definition lists.

## What It Would Take

- **The box** (`widgets/textctrl.py`): `MultiLineTextCtrl` swaps a
  `wx.html.HtmlWindow` in for the box; the border drawn around the box
  only; the page rendered again when the program sets the text or the
  theme changes; links opened in the web browser.
- **The converter**: a module of our own, or the package, guarded so
  the Preview hides without it.
- **The remembered state**: a field on every item, in the XML writer,
  reader and defaults, the format number; the editors read it when
  they open.
- **The buttons** in the editors ([Decided](#decided)).
- **Tests**: the converter's rules, the toggle, the saved state, the
  placement; these docs; the translations of "Preview".
- **With a package**: an entry in each build, as for pyenchant
  (Recommends on deb and rpm, optdepends on Arch, bundled in the
  Windows, macOS and Flatpak builds), and a section in
  [DEPENDENCIES.md](DEPENDENCIES.md) with the designer's ruling.

## Prototype Findings

A prototype (removed) showed, 2026-10-08:

- `wx.html` (HTML 3.2, no CSS) renders headings, lists, tables (with a
  `border` attribute), code, quotes and links; no code background, no
  quote bar, no web images.
- Its background must be the window's own colour
  (`wx.GetTopLevelParent(...).GetBackgroundColour()`): on GTK a panel
  reports the stock grey (241, 240, 238) while the window's (246, 245,
  244) shows through.
- markdown-it with `breaks` keeps each line break; a line right after
  a list item joins that item unless a blank line separates them.
- Fonts in the edit box, dropped as not asked: Scintilla gives every
  line the height of the tallest font, so larger headings spread every
  line apart, and its own Markdown lexer bolds only a heading's `#`.

## Review Scenarios

The cases a build is reviewed with, one task each in a sample file:

1. Plain text with no Markdown: `3 * 4 = 12`, `file_name_here`
2. Headings 1 to 6, and `#5` (not a heading)
3. Bold, italic, both, inside a word, snake_case left alone
4. Lists: right after a line, nested, numbered, `*` and `+`
5. Task lists
6. Code: inline, fenced, `~~~`, indented
7. Links: bare, `www.`, `<url>`, `[text](url)`, a mail address
8. A table with column alignment
9. Quotes, a quote in a quote, a horizontal rule
10. A line followed by `---` or `===`
11. Strikethrough
12. HTML and `&`, `<`, `>` shown as typed
13. Line breaks and paragraphs
14. Spell check in prose, code and links
15. Accents, Greek, Japanese, emoji
16. Backslash escapes
17. Markers never closed
18. Meeting notes mixing everything
19. A note, a category and an effort with Markdown
