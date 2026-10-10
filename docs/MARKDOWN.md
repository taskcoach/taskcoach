# Markdown

A preview is built on the branch `markdown-preview`, as release
2.0.3.5 (10 October 2026): not merged yet. This records what is
decided, what is built, what is left out and what is left to do.

1. [The Request](#the-request)
2. [Decided](#decided)
3. [Built So Far](#built-so-far)
4. [Known Gaps](#known-gaps)
5. [To Do](#to-do)
6. [Own Converter or a Package](#own-converter-or-a-package)
7. [Options](#options)
8. [A Minimal Set](#a-minimal-set)
9. [What It Would Take](#what-it-would-take)
10. [Prototype Findings](#prototype-findings)
11. [Review Scenarios](#review-scenarios)

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
- **No WebView**: a browser engine needs far more packages
  ([Options](#options)).

By the designer, 2026-10-10:

- **Our own converter, no package**
  ([Own Converter or a Package](#own-converter-or-a-package)): "I
  don't need extensive syntax support, but the most common to be well
  supported, and render properly."

## Built So Far

On `markdown-preview`, 2026-10-09 and 10:

- **The converter**, our own (`tools/markdown.py`, no packages),
  reworked 2026-10-10 from line-by-line patterns into a small parser:
  a quote or a list item holds blocks of its own (paragraphs, code,
  tables, lists), read the same way once its marker and indent are
  taken off; inline text is read in one pass, emphasis marks paired by
  CommonMark's rules. It covers [the common syntax](#a-minimal-set);
  what stays out is in [Known Gaps](#known-gaps).
- **Checked against a reference parser** while reworking it
  (markdown-it-py 3.0.0 as found on the development machine; never a
  dependency, not in the tests):
  - 41 documents as pasted from AI chats and GitHub and as typed in
    notes: the same structure in 32 (20 before the rework). Of the
    other 9, six differ on purpose ([A Minimal Set](#a-minimal-set)),
    two hold an image inside a link, shown as its description, and one
    a space written in an address.
  - Bold and italic on 18,000 random strings: identical.
  - 50,000 random documents and oversized ones (thousands of nested
    markers): no error, tags balanced, a 43 KB text in 0.03 s.
- **The preview** in `widgets.MultiLineTextCtrl`: a read-only
  `wx.html` window in place of the box, drawn as window text
  ([Prototype Findings](#prototype-findings)); web and mail links open
  in the browser, any other link is ignored.
- **Remembered per item** in the task file, as saved view state like
  a task's expanded state
  ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)): it marks the file
  unsaved so autosave keeps it, sets no modification date and has no
  undo. A field older releases ignore (`previewShown`, format 40).
- **The button says what a click does**: a square Markdown icon
  (the M over its down arrow, `taskcoach_actions_markdown_icon`:
  [ICON_LIBRARY.md](ICON_LIBRARY.md#taskcoach-custom-icons)) with
  "Preview" while editing; pressed, with the pencil and "Edit", while
  the preview shows. A tooltip says the same in words.
- **Placement, in space already empty**: in editors with labels (task,
  note, category, attachment), right under the "Description" label; in
  the effort editor, which has none, bottom left in the Close button's
  row, starting where the description box starts.
- **In French, Portuguese and Spanish**: the two tooltips translated;
  "Preview" and "Edit" already were.
- **A sample** in `Welcome.tsk`: a task, a note, an effort and a
  category with Markdown.
- **Tests**: `MarkdownTest` (the converter), `TextCtrlTest` (toggle,
  links), `EditorTest` and `EffortEditorTest` (buttons, placement,
  remembered state), `BaseTest` and the persistence tests (the field).
  Checked in the app on a virtual display, light theme: the buttons in
  the task and effort editors, the preview of the Welcome sample and
  of three pasted documents (numbered steps holding code, a table with
  a quote holding a list and code, task lists with emphasis).
- **Found on the way**, in
  [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-10-09):
  a key pressed in a list with no row logged an error, fixed (P252);
  the custom icons' generated catalog out of step with its source,
  recorded (P253); with a hierarchical calendar view a focus change
  logged an error, fixed (P254).

## Known Gaps

Left out and shown as typed (the common syntax well supported, no
extensive set: [Decided](#decided)):

| Input | The preview shows |
|---|---|
| Reference links (`[text][1]`, with `[1]: address` further down), footnotes | the text as typed; the address is still a link |
| A heading by underlining (`===` or `---` under a line) | the line, then `===` as text, `---` as a rule |
| Code by indenting four spaces | a paragraph |
| HTML tags other than `<br>` | the tag as typed |
| An image | its description, as a link to the image: `wx.html` loads no web image |

The display, `wx.html`: no syntax colours in code; inline code is not
shaded; items written with blank lines between them are not spaced
apart.

The window:

- Switching to the preview starts at the top: the scroll position of
  the box is not kept.
- No keyboard shortcut for the toggle.
- In a dark theme links are hard to read: they stay `wx.html`'s
  default blue (`#0000ff`) on the dark background, while the text,
  the code's shade and the quotes follow the theme (checked 2026-10-10
  on Adwaita dark). **Ruled by designer 2026-10-10**: left as the
  default, no preference covering it. Preferences > Theme sets the
  mode, the calendar's colours, the spell check underline and the
  hover outline, and Statuses the task colours; none sets a link's
  colour, and the edit box underlines links in one blue in every
  theme. The system's own link colour (`wx.SYS_COLOUR_HOTLIGHT`) is
  `#3584e4` on Adwaita dark and `#1b6acb` on the light theme, should
  it be wanted later.
- Not run on Windows or macOS: their builds come with the pull
  request.

## To Do

1. Keep the scroll position across the toggle; a shortcut for it.
2. The pull request, and a look at the preview in its Windows and
   macOS builds.

## Own Converter or a Package

Settled by the designer, 2026-10-10: our own converter, made to
support the common syntax well ([Decided](#decided)).

How it got there: the objective is no dependency packages, but a
preview that formats Markdown wrongly is not much better than none.
The designer asked the reporter on #436 (2026-10-08) whether a minimal
preview would be acceptable. The first converter, patterns applied
line by line, got pasted text wrong (a code block inside a list item
cut the list in two, bold over two lines stayed unformatted), and a
package was proposed as an optional parser, ours otherwise. The
reporter is on Windows: that build carries its own Python with pip, so
he could have added it (`python\python.exe -m pip install
markdown-it-py` in the Task Coach folder; read from
`build-windows.yml`, not run), or the build could have bundled it. The
designer chose to rework our own instead.

## Options

| | Own converter | markdown-it (package) | WebView |
|---|---|---|---|
| Packages | none | markdown-it-py, mdurl; for bare links linkify-it-py, uc-micro-py | wx.html2: on Linux a separate package (Debian `python3-wxgtk-webview4.0`) with WebKitGTK; on Windows Edge's WebView2 runtime; and a converter too |
| Size | 770 lines and 400 of tests | 100 KB download, 125 KB with bare links; 450 KB installed on Debian 13 | WebKitGTK alone is large |
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

The Markdown Guide's basic syntax and the extensions pasted text uses
most (GitHub, AI chats):

- Headings: `#` to `######` at the start of a line
- Bold and italic: `**`, `__`, `*`, `_` (underscores not inside
  words), one inside the other, over several lines
- Lists: `-`, `*`, `+` and numbered, nested by indent; an item holds
  what is indented under it: more paragraphs, code, a quote, a table
- Task lists: `- [ ]` and `- [x]` shown as boxes
- Code: inline `` `code` ``, fenced blocks (```` ``` ```` and `~~~`,
  a language after the fence ignored)
- Links: `[text](url)`, `<url>`, bare `https://` and `www.`, mail
  addresses; an image (`![text](url)`) as its description, linked
- Block quotes: `>`, holding any of the above, one inside another
- Horizontal rule: `---`, `***` or `___` on a line of their own
- Tables: GitHub's pipe tables, with column alignment
- Strikethrough: `~~`
- Backslash escapes, named characters (`&copy;`), and `<br>` for a
  line break (the only way to break a line inside a table cell)

Unlike GitHub, on purpose, so plain notes look as typed:

- Each line break stays one (GitHub does this in comments, not in
  files).
- A line right after a list item or a quote is not part of it: it
  takes a deeper indent, or a `>`, to belong.
- A list may start right under a line of text, at any number.
- A pipe inside inline code stays in its table cell; GitHub wants it
  escaped (`\|`), which works here too.

Left out, because they change plain text unexpectedly or need more
than `wx.html`: headings by underlining (a line followed by `---` or
`===`), indented code blocks (four spaces), raw HTML (shown as typed),
web images, reference links, footnotes, definition lists.

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
  `border` attribute), code, quotes and links; fenced code shaded
  through a borderless one-cell table and quotes greyed through
  `<font>`, both re-rendered on a theme change; no quote bar, no web
  images.
- Its background must be the window's own colour
  (`wx.GetTopLevelParent(...).GetBackgroundColour()`): on GTK a panel
  reports the stock grey (241, 240, 238) while the window's (246, 245,
  244) shows through.
- markdown-it with `breaks` keeps each line break; a line right after
  a list item joins that item unless a blank line separates them.
- What `wx.html` cannot do, and how the converter goes around it
  (2026-10-10): `<strike>` and `<del>` draw an underline, which reads
  as a link, so struck text takes the combining long stroke on each
  character; `<ol start>` and `<li value>` are ignored, so a numbered
  list not starting at 1, and a task list (no bullet wanted), are laid
  out as a table with their own markers; a clicked link that is not
  `http`, `https`, `mailto` or `www.` is ignored, since the window
  would load it in place of the text. The text colour follows the
  window's foreground (dark theme) and the sizes the system font
  (headings 2, 1.5 and 1.25 times, as on GitHub).
- More of what `wx.html` does, found reworking the converter
  (2026-10-10):
  - A `<pre>` takes a blank line above it: a code block is a shaded
    one-cell table instead, a row of `<tt>` for each line, its spaces
    as `&nbsp;`. Copied out of the preview they are plain spaces, the
    indent kept (a test holds this).
  - `<blockquote>` indents both sides and draws no bar: a quote is a
    table whose first cell, 4 pixels wide and coloured, is the bar.
  - Only `<p>` and headings put space above themselves: code, quotes
    and tables are wrapped in `<p>` to stand a line apart (two code
    blocks in a row drew as one box). The first block in a list item
    or a quote takes none, or it drops a line below its marker.
  - An `<hr>` after a heading sits two lines under it; inside the
    heading (`<h2>Title<hr></h2>`) it sits right under the title.
  - `<li>` holds paragraphs, code and tables, indented under the
    item's text; `<p>` around an item's only text changes nothing, so
    blank lines between items cannot space them apart.
  - `<h4>` and `<h6>` come out in italics: the three lowest heading
    levels are bold text instead, the last two smaller.
  - The code's shade goes by the window's real background, as the
    text colour does, not by the Mode setting: with Mode Dark chosen
    on a light GTK desktop the window stays light, and a dark shade
    under its dark text could not be read.
- Fonts in the edit box, dropped as not asked: Scintilla gives every
  line the height of the tallest font, so larger headings spread every
  line apart, and its own Markdown lexer bolds only a heading's `#`.

## Review Scenarios

Gone through 2026-10-10 on a virtual display, in the light theme, on
a dark desktop theme (Adwaita dark), with Mode Dark on a light
desktop, and the buttons in French: as designed, after two fixes they
brought (heading levels 4 to 6, the code's shade) and but for the
link colour in a dark theme, left as it is
([Known Gaps](#known-gaps)). 14 is the edit box's, unchanged.

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
