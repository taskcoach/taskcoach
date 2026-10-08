# Refinement Refactor

What the master scheduler refactor leaves open, carried forward for a
refinement and cleanup pass after the release, **asked by designer
2026-10-04**: "carry forward the open issues to a new ... refactor task
that's refinement cleanup rather than a major cleanup". Details stay
where each item was recorded; this list only orders them.

The project review of 2026-10-04, **asked by designer 2026-10-04**
("review the whole current project ... Also do a review for security
... for other things that you think should be done"), is kept here in
full, **asked by designer 2026-10-04** ("Keep all your detailed notes
in the refinement refactor document").

1. [To Do](#to-do)
2. [Pre-existing Issues](#pre-existing-issues)
3. [Open GitHub Issues](#open-github-issues)
4. [Low Priority, Deferred](#low-priority-deferred)

## To Do

The one list for this refactor, numbered in the order found; an item
is crossed out and cut to a stub when done or decided, and new items
go at the end.

Open, in the order to take them (2026-10-06, **asked by designer**:
"document the others as future to-dos so we don't forget"):

- Now: 28, the release of 2.0.3.1 (with 27's Windows and macOS builds,
  checked by the pull request's CI).
- After the release, **ruled by designer 2026-10-07** ("defer the rest
  of the PEP8 renames. You can keep all this in refinement refactors.
  We'll continue working this at another time"): 26 (the PEP 8
  migration's steps 3 to 5), then 6 (pre-existing issues still to
  rule).
- On the designer's desktop: 9 (black tray icon backgrounds on LXDE).
- Postponed or parked by the designer: 1, 13, 14, 20, 24; P238 and
  P239.

1. Task statistics view: draw it in Task Coach's own code instead of
   `wx.lib.agw.piectrl`, whose paint loop keeps a core busy
   ([TASK_STATISTICS.md](TASK_STATISTICS.md#to-do) 1).
2. Renames too wide for the PEP 8 pass of 2026-10-04, each its own
   comprehensive change ([PEP8_MIGRATION.md](PEP8_MIGRATION.md)):
   `selectionOnly` and the other export writer parameters (60 uses),
   `foregroundColor`/`backgroundColor` (45), `modificationEventTypes`
   (48), the sort interface (`sortBy`, `sortKey()`,
   `isSortCaseSensitive()`, `sortCaseSensitive`, and the
   `<key>SortFunction`/`<key>SortEventTypes` names the sorter builds
   from the column name), `onSelect` (36), and the editor tests' hooks
   `getItems`/`createTasks` (39); with D1's below.
3. ~~Plain dialogs placed by wxGTK's deferred first show~~: done
   2026-10-06, **ruled by designer** ("You can proceed"): every dialog
   but the editors sends its position, and a fitted one its size, again
   at the first show, as the editors do; the Tip of the day and the
   new-version notice are destroyed on close, not hidden. Reproduced
   on the branch and on master: after any window closed, or at start,
   a dialog opened at the screen's top-left, a fitted one a title bar
   short (the Tip of the day without its check box)
   ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#first-show-on-wxgtk)).
4. Prototyped 2026-10-04, ruled low value then (rarely used); P170
   and P57 deferred 2026-10-06 (D17, D18 below):
   - ~~To Do 82, the Windows and macOS builds' Python 3.11.9 has Expat~~
     Done 2026-10-06, **ruled by designer** ("proceed with them as you
     suggest"): those builds on Python 3.13 (To Do 27), and the reader
     refuses a DOCTYPE
     ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#expat-by-package)).
     Was: the Windows and macOS builds' Python 3.11.9 has Expat
     2.6.0: build both on Python 3.13 (3.13.16 has Expat 2.8.5;
     wxPython 4.3.1, pywin32 312 and py2app 0.28.10 support it), and
     a build check that Expat is 2.7.2 or later. The same Python
     carries its OpenSSL and standard library of April 2024.
     Researched again 2026-10-06, **asked by designer**: every Expat
     fix since 2.6.0, the crash reproduced, and the ways out
     ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#expat-by-package));
     a ruling first.
5. ~~`dbus-python` to Gio~~: done 2026-10-06, **ruled by designer**
   ("that is perfect for both of those"): the idle notice's GNOME
   reading and the start-up tray check use Gio; the ScreenSaver reading
   removed; dbus-python out of every package. Researched first: Gio
   suits every supported system; a restarted idle service no longer
   turns the notice off, a hung one holds the window at most 1 s
   ([DEPENDENCIES.md](DEPENDENCIES.md#dbus-python-to-do-92)).
6. The open pre-existing issues of
   [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#pre-existing-issues),
   each still to rule: P65 (code only tests use), P69 (Python 2 style),
   P70 (stale comments), P71 (pylint leftovers), P76 (unused image
   folders), P77 (three AppStream files), P84 (build inputs adrift),
   P85 (no CI job runs the tests), P86 (old CI actions and images),
   P92 (done 2026-10-06), P93 (done 2026-10-06),
   P94 (done 2026-10-07: TODO.md 3 dropped, 6 removed, 10 deferred
   as D24), P96 (will
   not do, D23), P97 (done 2026-10-06), P98 (date and time
   refactors), P100
   (a selection outline, AUI repaint questions; its delete part done
   in To Do 18), P101 (link colour), P103 (toolbar sentinels),
   P104 (long-term migration items), P106 (geometry checks on LXDE),
   P109 (editor shortcuts against translations, relative date
   presets), P110 (done 2026-10-06), P112 (stale doc text), P125
   (Windows display scale factors), P138 (Windows tree scrollbars),
   P159 (AppImage tray), P162 (done 2026-10-06), P176 (macOS
   spelling), P244 (done 2026-10-06).
7. Test suite, fixed as found without a ruling (ruled by designer,
   [DEVELOPMENT.md](DEVELOPMENT.md#working-plan) 5; never listed as
   next or open work): P90 (a test file now
   and then fails to start). P63 (the translation coverage tests read
   a stale template) deferred 2026-10-06 (D20 below). Analysed
   2026-10-06, **asked by designer**:
   - P90: the two failures kept (2026-10-04, 2026-10-05) show no
     refusal from the X server (it would print "Authorization
     required" or "Maximum number of clients reached"): no display
     answered at all. One was not `test.py` but a script of mine
     importing wx, so P90's "the trigger is in `test.py`'s own start"
     does not hold. `xvfb-run` keeps the display's key under `/tmp`,
     shared with the designer's other workers. Not seen in the 7 full
     runs of 2026-10-06; that afternoon one file run alone under
     `xvfb-run -a` printed no result and passed when run again (its
     output not kept). Proposed: when a file fails to start, the
     runner records whether the display's server, socket and key are
     there and what a plain connection answers, so the next failure
     names its cause; then fix that cause, with no retry (a retry hid
     it before). Done 2026-10-06 (`display_report()` in `test.py`,
     [TESTING.md](TESTING.md#running)); the cause waits for the next
     failure.
   - P90 again 2026-10-06, the runner itself at its start (a full run
     under `xvfb-run -a`, the machine busy): wx's own display check
     passed, then GTK's connection right after it failed
     ("wxEntryStart failed"), so the display was up and then lost or
     refused within milliseconds. The report did not print: it covered
     the files, not the runner's own `wx.App`. Now it prints for both,
     and for wx's check failing too. Suspected: the X server resets
     when its last client leaves (wx's check is the first), and drops
     a client still connecting; not reproduced (190 starts on fresh
     displays and on one resetting display, 0 failures), so no
     `-noreset` on a guess. Then done the standard way, as
     pytest-xvfb and PyVirtualDisplay do: each run starts its own
     Xvfb, its number picked by the server (`-displayfd`, no race
     with other runs), with `-noreset`; the tests never use the
     desktop's display ([TESTING.md](TESTING.md#running)).
8. ~~The texts still in English in French, Spanish and Portuguese~~:
   deferred 2026-10-06, **ruled by designer** (D20 below).
9. Black tray icon backgrounds on LXDE: find the trigger on the
   designer's desktop; the fix belongs to lxpanel
   ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#black-icon-backgrounds-on-lxde),
   TODO 2).
10. ~~Right and centre aligned columns (the dates) cut on both sides
    when too narrow~~: closed 2026-10-06, **ruled by designer** ("when
    we resize smaller, it gets left align and it just simply gets cut
    off to the right"), as it is: not reproduced as described (Task
    Coach never sets `TR_ELLIPSIZE_LONG_ITEMS`, so `ChopText()` never
    runs; the same on master). A right-aligned value wider than its
    column (dates, amounts, the reminder) is drawn from the column's
    left edge and cut on the right, without "..." (D15). Researched the
    same day: Windows' list view, Qt's item views, wx's own list
    (Task Coach's effort and attachment views) and CSS all start-align
    text that does not fit; all but GTK's lists, which cut the start,
    add "..." at the end. No "..." in the task and category lists,
    the dense views, and the effort and attachment lists keep wx's,
    **ruled by designer** the same day
    ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#text-too-wide-for-its-column)).
11. ~~Window geometry leftovers~~: closed 2026-10-06, **ruled by
    designer**: the normal rect while shown and the Xvfb tab not
    reproduced; Windows checks left to users' reports; wxWidgets' own
    geometry saving closed for good (D22 below); the wxGTK first-show
    bug documented in this project instead of reported upstream ("As
    long as you document it in this project, other people can find
    it": [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#wxgtk-bug-position-lost-on-a-deferred-first-show)).
    Floating panes are P92, done 2026-10-06 (editors: P91, done).
12. ~~Flatpak: drop `--filesystem=home` and the Flathub steps~~:
    deferred 2026-10-06, **ruled by designer** (D21 below).
13. Base and effective fields, postponed 2026-09-29 by designer
    ([TASK_FIELDS.md](TASK_FIELDS.md#postponed-base-and-effective-fields)).
14. Mail attachments, later: open the mail program's search on the
    stored fields; the mail's own attachments
    ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions) 1).
15. ~~The AppImage's Python 3.11 and its Expat~~: not an issue,
    2026-10-06: the AppImage takes python-appimage's latest 3.11
    (3.11.17), with its own Expat 2.8.5
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#expat-by-package)).
16. ~~Mail stays local~~: done 2026-10-04, **ruled by designer**
    ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#decisions) 8): the
    IMAP reader, its password dialog and `keyring` removed, and the
    Thunderbird profile reader too, which attached empty or wrong
    mails (its URI numbers are index keys); a Thunderbird drag that
    gives only addresses shows why and how to attach the mail. The
    mail code PEP 8 migrated with the drag-and-drop module.
17. ~~Thunderbird on Linux X11: one dragged mail read~~: done
    2026-10-06. Thunderbird offers the message's URI as text before its
    `.eml` file, and wx takes the text; the drop now asks the drag's
    source for its `text/uri-list` (`x11_drag_files()` in
    `widgets/draganddrop.py`, GTK's clipboard on the `XdndSelection`)
    and reads the mail, local or IMAP; without a file the message says
    why, as before. Checked in the app with `tools/fake_mail_drag.py`
    (its "Thunderbird, X11" drag): the mail attached with its fields;
    4 new tests in `MailDropTest` fail before
    ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#the-drop)). Seen while
    checking, recorded already: opening a Welcome.tsk task's editor the
    first time writes its planned duration (P133, ruled).
18. ~~Next three issues~~, **asked by designer 2026-10-05** ("Ok,
    next three issues now"): done 2026-10-05, each ruled; analysed and
    prototyped on the branch, each reproduced on master (40bfd42c7) and
    on the branch.
    - ~~**P100, the effort and attachment views lose the selected
      item.**~~ Done 2026-10-05, **ruled by designer** ("we should be
      doing the modern best practices, which means that the row stays
      on its current index ... I think that's already ruled. I think
      you can proceed"): every view keeps the selection on the same
      line after a delete
      ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#which-row-gets-selected)),
      the trees included, which took the row above since 2026-08-24;
      a deleted only child now passes the selection to the next row,
      where the code before 2026-08-24 took the parent. Steps: Effort view, select the third effort, then
      Ctrl+T on another task: the new effort's row comes on top and
      the highlight moves to the effort above the selected one.
      Delete a selected effort: the row below is selected, where the
      task views select the row above
      ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#select-next-after-deletion)).
      A sort moves it too. Cause: the native list keeps row numbers
      selected, and the presentation has changed before the list
      refills, so the objects behind the old numbers are unknown
      (`ListViewer.select_next_items_after_removal()` was a no-op).
      Fix: `VirtualListCtrl` keeps the objects of its rows at each
      refill (a list and a dict), reselects the same objects after it
      and moves the keyboard's current row with them, without
      scrolling; `selection_neighbours()` as in the tree; the one rule
      for every view lives in `Viewer`, the tree keeping its fallback
      for widgets without rows. Painting still reads the
      presentation (reading the kept rows painted a removed effort
      once, a traceback). Tests: `EffortViewerSelectionTest` (5 of 7
      fail before), four in `ViewerTest` on rows where the same line
      and the row above differ (all fail before); `ListCtrlTest`'s
      stub now paints (16 tracebacks before, on master too). App:
      highlight kept at Ctrl+T; after Delete, the row that moved into
      the line, in the Effort view and the task tree, the last child
      of a group passing it to the next row.
19. ~~Columns moved by drag and drop~~: done 2026-10-05
    ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#moving-columns)), **asked
    by designer 2026-10-05**:
    "make it possible for users to slide the columns left and right
    when one column is clicked and it's dragged, there should be an
    indicator, an indicating vertical line that shows where the column
    will be dropped and it should be able to be dropped ... to the far
    right and any of the lines in between columns all the way to the
    furthest left column". In every list and tree view.
20. Postponed by designer 2026-10-05: P203 (recurrence from
    completion) and P204 (a task's family as its prerequisites); the
    analyses are in their entries below.
21. ~~Tasks drawn plain at start, coloured a second or two later~~:
    done 2026-10-05 by the start-up design, **ruled by designer**
    ("show the screen as soon as possible. While the tasks are
    loading, you're showing a spinner. And then after that, you show
    the tasks once you have them";
    [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#opening-the-file)).
    Asked the same morning ("if it's very simple to fix, that would be
    nice"). Structural: statuses and styles are not in the file; the
    master loop computed them at the next tick, after the views drew
    the rows. The full loop within the read was tried first, then
    reverted ("I'd rather give a response to the user
    sooner than later"): then the window was still blank during the
    read (P234). With the window painted first, it is the design: the
    list drawn once, complete.

      Which row after a delete, researched 2026-10-05, **asked by
      designer** ("what is modern best practices for a selected row
      that is deleted?"): the row that moves up into the deleted
      one's place, so the highlight stays on the same line; the new
      last row when the last one went. So do GTK 3's tree view
      (`gtk_tree_view_row_deleted()`: "If the cursor row got deleted,
      move the cursor to the next row", the previous one only when
      there is none), Qt's item views, the W3C listbox example
      ("focus lands on the first of the subsequent options that is
      still present"), Outlook ("the cursor is moved down to select
      the next item"), Thunderbird (the next message), Gmail (the
      older conversation, below in its newest-first list) and Apple
      Mail (the next one, or the direction one was reading). Outlook,
      Gmail and Apple Mail offer the other way as a setting. Task
      Coach's trees did the same until 2026-08-24 (f776d544d), when
      they took the row above "so that repeated deletes keep walking
      up the list", with no ruling recorded; the effort and attachment
      lists keep the same line now, by accident.
    - ~~**P189, Mail task cuts the subject.**~~ Done 2026-10-05,
      **ruled by designer** ("you can proceed as you suggest ... you
      can also replace characters that are problematic with
      placeholder characters"). Steps: a task "R&D review #12
      révisé", Ctrl+M: the mail program got subject "R"; all after
      "#", body included, was a link fragment and dropped (recorded
      with an `xdg-open` stand-in first in `PATH`). Cause: the
      subject was escaped in 2008 (e64184a2b), every escape was
      dropped for macOS in February 2012 (c87946483, bug 3489341;
      the same `open URL` call as now), and in April the body's came
      back off macOS (3fac7df02), not the subject's. Fix: the subject
      escaped as the body; letters beyond ASCII stay as they are, as
      before, because Outlook reads their UTF-8 escapes in its own
      code page
      ([Mozilla 227268](https://bugzilla.mozilla.org/show_bug.cgi?id=227268)).
      macOS, untested here: the link stays unescaped as released, `&`
      and `#` in the subject and body become `_` (addresses are left
      as they are: changed, they would reach someone else). Tests:
      `SendMailLinkTest` (5, all fail before). App: subject "R&D
      review #12 révisé".
    - ~~**P91, editors first open at 400x300.**~~ Done 2026-10-05,
      **ruled by designer** ("we will go with 80% ... Go the
      conservative path"):
      [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#decisions) 10. Steps: with no saved
      size, open any editor: 400x300, Description's priority and
      dates cut off, the effort editor too. Cause, two parts: the
      tracker takes the 400x300 minimum when nothing is saved, not
      the fitted size (`load()`); and the tabbed editors fit to
      226x293, since their pages lost their best size in the Python 3
      migration ([PYTHON3_MIGRATION_1.md](PYTHON3_MIGRATION_1.md),
      layer 4: it locked the editor to the effort list's 3021 px).
      Measured page needs (task): Description 369x297, Dates
      851x570, Appearance 294x557, Progress 692x88, Budget 214x269;
      tab strip 1251 px (category 585). Releases up to 1.4 opened at
      the fitted size of the largest page and could not shrink below
      it; the fork's 400x300 is "production" for
      [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#decisions) 9, so this
      changes a result. Prototype: the notebook reports its largest
      page (scrolled pages rounded to whole 20 px scroll steps, else
      their scroll bars show; the AUI pane border) for the first fit
      only, then may shrink; the tracker takes the fitted size, at
      least 400x300, when nothing is saved. First opens: task
      888x706, effort 590x517, category 432x690, note 400x690. Tests:
      `EditorFirstSizeTest`, the tracker's fitted-size test (fail
      before). Left: a first show that wxGTK defers (after a closed
      dialog, [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#first-show-on-wxgtk))
      keeps the outer size, so the editor is a title bar (27 px)
      short; the tab strip still scrolls, as in the releases.

      Larger than the screen, **asked by designer 2026-10-05** ("Maybe
      the data on the page is larger than the window ... the control
      buttons might not be accessible, nor the top bar"): the first
      prototype did not prevent it; centering kept the top left on
      the monitor, the rest ran off it. Rules now: an editor never
      starts larger than the work area (the monitor less its panels)
      of the main window's monitor: the fitted size is cut to it
      before the show, so the rules that leave the size to the system
      keep it too, and a saved size without position is cut the same
      way; centered, then moved inside that work area. The pages that
      then lack room scroll (Dates, Appearance); the others need at
      most 369x297 (Description). Checked on a 1024x600 screen with a
      40 px panel (work area 1024x560): task editor 888x560 at the
      top, title bar and Close on screen, Dates scrolling; category
      430x560, also after a deferred first show. Tests: 3 more in
      `EditorPlacementTest`.

      Reviewed again, **asked by designer 2026-10-05** ("Are you 100%
      sure that the window size you will be getting is correct? ...
      75% ... or 85 or 80% ... make sure that we're using the proper
      screen ... better to be safe and let the user resize"). The work
      area wx reports (`wx.Display.GetClientArea()`, wxWidgets 3.2.8
      `src/gtk/display.cpp`) comes from GDK
      (`gdk_x11_monitor_get_workarea()`, GTK 3.24.38): exact per
      monitor where the window manager publishes `_GTK_WORKAREAS`
      (GNOME), and on Windows and macOS; elsewhere on X11 the EWMH
      work area applies to the primary monitor only, the others count
      their panels in; on Wayland it is the whole monitor ("will
      return the monitor geometry if a workarea is not available").
      The monitor was the one holding the main window's centre, which
      on Wayland, where positions read (0, 0), can be the wrong one.
      Now: the first size is at most 80% of the work area each way
      (`wxhelper.SIZE_SHARE`), room for unreported panels; the monitor
      is the system's answer for the main window
      (`wx.Display.GetFromWindow()`: GDK's monitor of the window, the
      one it overlaps most, Wayland included). A saved size is kept as
      before; the user resizes and it is remembered. Checked on the
      1024x600 screen: 819x448, centred, margins all round. Not
      checkable here: two monitors (Xvfb gives one; no Xephyr or
      Wayland compositor), covered by `EditorPlacementTest` with a
      fake two-monitor display.
22. ~~P234, the window blank while the file is read~~: done
    2026-10-05, **asked by designer** ("work on P234 and provide me
    your suggestions ... what's best for users, especially ... the
    advanced users"). The file is read once the main window has
    painted, else at the first tick
    ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#opening-the-file)).
    The busy pointer during a read (open, merge): done 2026-10-05,
    **ruled by designer** ("Ok for busy pointer"). The other
    suggestions, **approved by designer** ("The rest is ok"): the
    status bar's "Opening <file>..." during the read, where it showed
    "Closed" (done 2026-10-05; in French, Spanish and Portuguese the
    same day, with "Merging <file>..."); the list shown complete (To Do 21, done); the first
    pass's 16,560 style events (done, To Do 25); what comes back when
    a file is reopened, checked 2026-10-05: the expanded rows, the
    sort, mode, columns, search, filters, panes and window are kept;
    the selection and the scroll position are not, as in the release,
    and stay so, **ruled by designer** ("No!";
    [LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#between-sessions)). The
    views not open imported at start: dropped, **ruled by designer**
    ("for the faster cold start, no ... Optimization on the startups
    will make a mess").
23. ~~The Linux tray menu rebuilt whole at each change (P235)~~: done
    2026-10-05, **asked by designer**: each icon prepared once and
    named where GTK draws the menu, the menu updated in place
    ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#menu-updates)).
24. Parked 2026-10-05, **ruled by designer** ("Postpone the ...
    in-house tray"): a tray icon of our own on Linux; the analysis to
    do is TODO 3 in [SYSTEM_TRAY.md](SYSTEM_TRAY.md#todo).
25. Start-up flow against the ruling, **asked by designer 2026-10-05**
    ("redo a full analysis and tell me where the gaps and problems you
    still have. Things like icons missing in the tray and event storm
    are symptoms of incorrect implementation"). Every step traced from
    the process start to idle (2,000 tasks and the Welcome copy, Xvfb):
    1. ~~The tray made before the window, its menu built twice
       empty~~: done, made once the list is built.
    2. ~~The first open closed an untouched start ("Closed", both
       lists rebuilt empty)~~: done, nothing closed then.
    3. ~~16,598 events in the batch, the views frozen: the computed
       values sent theirs~~: done, set quietly (39 left: list
       additions, stored changes).
    4. ~~"Calculate, then show" held by chance~~: the observers of
       one event run in no fixed order, and a list was sometimes
       built before the colours (seen in the trace); done, two notices
       (`taskfile.settle`, then `taskfile.justRead`).
    5. The window's placement and the list are decoupled, **ruled by
       designer 2026-10-05** ("resizing and list display should be
       decoupled completely, they both run each when ready"; "Yes B
       please!": the batch does not wait for the placement). Neither
       waits for the other; but they share the one UI thread, so
       whichever runs holds the other: with 2,000 tasks a window saved
       maximized was ready to maximize at +1.31 s after its creation,
       and did at +2.20 s, after the batch (+0.37 to +1.57 s) and the
       tray's build (to +2.19 s) (Known Issues in
       [WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#known-issues)).
    6. P236, the categories pane blank: on the code before these
       changes too; not seen since.
    ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#opening-the-file))
26. Finish the PEP 8 migration, **asked by designer 2026-10-05**
    ("can you finalize the whole pep8 migration?"); steps 1 and 2 done,
    3 to 5 after the release of 2.0.3.1 (ruled 2026-10-07, above):
    every name not
    tied to wx or another library, To Do 2 and D1 included; inventory
    and steps in
    [PEP8_MIGRATION.md](PEP8_MIGRATION.md#finishing-the-migration).
27. The bundled builds to Python 3.13, **asked by designer
    2026-10-06** ("see if we can move to 3.13 for most of them
    without breaking any support for systems that still absolutely
    require 3.11"). On 3.11 now: Windows (3.11.9), macOS (3.11.9) and
    the AppImage (3.11.17), each with its own Python, and the CI's
    static checks; the Linux packages use their system's (Ubuntu
    22.04 3.10, Debian 12 3.11, Ubuntu 24.04 3.12, Debian 13 and the
    Flatpak 3.13, Fedora 43 and Arch 3.14), so no supported system
    depends on the bundled ones. All three can move: wxPython 4.3.1
    and pywin32 312 have 3.13 wheels, and the wxPython extras now
    have 4.2.5 for 3.13 on Ubuntu 22.04 (the AppImage's reason for
    3.11, [APPIMAGE.md](APPIMAGE.md#why-python-313));
    python-appimage has 3.13.16 for manylinux_2_28; Windows 8.1, macOS
    11 and glibc 2.28 stay the minimums. The code still parses as 3.10
    (`setup.py`: `python_requires >= 3.10`); the static checks would
    run on 3.10 to keep it so. With To Do 82
    ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#expat-by-package)).
    **Go-ahead by designer 2026-10-06** ("If we control them
    completely, then yes"). Done: the AppImage on python-appimage's
    3.13 (3.13.16, Expat 2.8.5) and wxPython 4.2.5 for 3.13; Windows on
    3.13.16 (`python313._pth`); macOS on setup-python "3.13"; each
    build stops on an Expat older than 2.7.2; the static checks on 3.10
    (both pass on Python 3.10.22); the local `scripts/build-appimage.sh`
    fixed (AppRun was written through python-appimage's link, the
    packing needed FUSE, the version came from an installed Task Coach,
    an unused `patchelf` was required). Checked here: the AppImage
    built locally (with Ubuntu 22.04's `libjpeg.so.8` and `libtiff.so.5`,
    which the CI copies from its system); the full suite in its Python
    passes (138 files, 302,092 tests, as on the certified platform); in
    the app from it, a file opened, sorted, filtered, a task added,
    tracked, completed and saved. Windows and macOS are checked by the
    pull request's CI only (py2app's setuptools pin there is the
    unknown). Supported systems below 3.13 and their end dates:
    [PACKAGING.md](PACKAGING.md#systems-below-python-313).
    The pull request's first Windows build failed (2026-10-07):
    squaremap, a source package, could not be built, as `get-pip.py`
    installs setuptools only before Python 3.12 and the embedded
    Python hides pip's build environment; fixed in the workflow
    ([WINDOWS.md](WINDOWS.md#5-packages-built-from-source)).
28. Release steps, last, **asked by designer 2026-10-06**: open the
    pull request (its CI builds every package; the Windows and macOS
    builds on Python 3.13 are checked there only); the designer's
    desktop test of the release build (a local AppImage is built with
    `scripts/build-appimage.sh`); squash when the designer says the
    pull request is ready.
29. ~~Todo.txt: keep or remove~~: removed 2026-10-06, **ruled by
    designer** ("remove the to do for now ... document what you
    found"): Export as Todo.txt, Import Todo.txt, the automatic import
    and export, and the replace-file cleanup that served it; the
    settings are dropped from an old settings file. Why, the format's
    apps in 2026 and how to bring it back:
    [TODO_TXT.md](TODO_TXT.md); synchronization as a future project,
    CalDAV included: [SYNC.md](SYNC.md). App: started with an old
    settings file with both options on and a `.txt` beside the task
    file: the options gone from the file and from Preferences > Files,
    Export lists HTML, CSV and iCalendar, Import lists CSV, a save
    leaves the `.txt` untouched.
30. ~~Every window at most 80% of the screen~~: done 2026-10-06,
    **ruled by designer** ("Yes, you can set one rule to 80% ... You
    can make the icon picker taller"): every dialog as the main
    window, editors and floating views (P92), one constant
    ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#decisions) 10). App, a
    1024x600 screen: Preferences 819x480 (its pages scroll), About
    726x480, the Backup Manager 800x480, the icon picker 700x480, each
    centred; master filled the screen with Preferences and About.
31. ~~The README for users, development docs apart~~: done
    2026-10-06, **asked by designer** ("I want to make it clear to
    users when they land on the first page exactly how to install the
    simplest way possible for their platform and that everything else
    be put away under dev docs"): the README holds the downloads, a
    short install per platform, support, licence and one developer
    link; each platform has its detailed page
    (`README_INSTALL_LINUX.md` added, for uninstalling, the Flatpak
    and the tray); running from source, the architecture and every
    document's purpose are in [README.md](README.md). P213 with it.
32. ~~The sash throttle that never runs (P245)~~: removed 2026-10-06,
    **ruled by designer** ("Ok, as you suggest for point 1"): it never
    ran and, made to run, changed nothing
    ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#divider-drags)).
33. ~~Release review~~: done 2026-10-07, **asked by designer** ("Do a
    carefull review of all the work done in this branch, also make sure
    the PEP8 migration is properly followed for all the sections worked
    on"). Every commit since master read again, by area, against the
    code at the branch's head; each finding checked before a fix, each
    fix with a test that fails before.
    - Bugs of the branch, fixed: Ctrl+PgDn or a click on a docked view
      left the keys in the old one (P162's check asked AUI's report for
      a manager it never names, [AUI.md](AUI.md#floating-views-and-the-keys));
      a paste dropped a prerequisite the view hid, and a cut task lost
      its link to one ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids));
      with several tracked efforts (an older file), a view showing one
      stopped the others ([EFFORTS.md](EFFORTS.md#tracking)); a
      settings file given as `--ini=name.ini` was never written; the
      undo of a move between two collapsed or empty parents left the
      tree stale; after a delete the effort and attachment lists
      scrolled with auto scroll off; the Prerequisites tab in list mode
      kept the expanders' room; the attachment view widened the first
      column, not the type column, after a column move; a backup cut
      short counted as made; under `nohup` closing the terminal ended
      Task Coach; ended in its first second, Task Coach forgot the file
      to open; a Thunderbird message that could not be read held the
      mail program until the message was answered (Windows).
    - Found on master too, fixed: Mail of several tasks put stray
      line-break characters after each description. Recorded: P250.
    - Unverified here: the tray's menu with a real tray host (KDE,
      GNOME's AppIndicator extension; [SYSTEM_TRAY.md](SYSTEM_TRAY.md));
      the Windows and macOS builds, checked by the pull request's CI.
    - PEP 8 on the lines the branch changed: 142 test names longer than
      a line shortened (the same 4,062 tests, none twice in a class),
      the long lines and the `== None`, `== True`, `not in` and
      lambda forms fixed, the camelCase attributes of new test classes
      renamed, `createBackup`, `restoreFile` and the backup tests'
      helpers renamed; no new camelCase name left in the code. The old
      camelCase names on lines a parameter rename touched wait for the
      migration's step 3 (To Do 26). Docs no longer cite commits a
      squash drops.

## Pre-existing Issues

Found in the review of 2026-10-04 by reading the code (lines as of
that day); none reproduced in the app yet. Each is reproduced on the
branch and master before it is proposed
([DEVELOPMENT.md](DEVELOPMENT.md#working-plan)). Numbered after the
scheduler refactor's P179, so a P number names one issue; sizes S, M,
L.

### Security

- P180. Dropping a Thunderbird IMAP mail sends the password
  unprotected. Thunderbird hands over only the message's address in
  most drags ([EMAIL_ATTACHMENTS.md](EMAIL_ATTACHMENTS.md#by-program-and-system)):
  a local folder's carries the mail's offset in the profile's mbox,
  read directly; an IMAP account's only server, folder and UID, so the
  reader of 2007 (e75d97c6e) logs in to the server as the user.
  Reachable again since P41 and P177.
  - `mailer/thunderbird.py:341`: only socketType 3 uses TLS; 1 and 2
    (STARTTLS) log in over plain `imaplib.IMAP4` (`:368-370`); nothing
    calls `starttls()`.
  - `:368`: `IMAP4_SSL` without `ssl_context` uses
    `ssl._create_stdlib_context`, the unverified context (checked on
    Python 3.13.5): no certificate or host name check.
  - `widgets/password.py:33,130`: the dialog names neither server nor
    user, and the server comes from the dragged text: an
    `imap-message://me@evil.example/INBOX#1` dragged from a web page
    asks for "your password" and sends it in clear to port 143.

  Ended by To Do 16 (no network for mail), 2026-10-04.
- P181. Attachments from a task file open without a check. Location
  and type are read as stored (`persistence/xml/reader.py:806`) and
  handed to `os.startfile`, `open` or `xdg-open`
  (`tools/openfile.py:43-50`) by `FileAttachment.open`,
  `URIAttachment.open` and `MailAttachment.open`
  (`domain/attachment/attachment.py:192-195, 217-218, 253-255`); Open
  all attachments (Shift+Ctrl+O) opens every one of the selected
  tasks. A shared task file whose "Agenda.pdf" points to a `.bat`,
  `.lnk`, `.hta`, `\\host\share\x.exe`, a `search-ms:` link or a macOS
  `.command` runs it. Bidi controls (U+202A to U+202E, U+2066 to
  U+2069) are kept (`tools/text.py:25`), so the Location column can
  show another name. Fix (M): allow-list link schemes; ask, showing
  the real location, before opening programs, scripts, shortcuts and
  remote paths; strip bidi controls.
- P182. Windows: showing attachments contacts the SMB hosts a file
  names: `exists()` per row for the icon
  (`gui/viewer/attachment.py:380`), `isdir()` per `file://` link
  (`:60-70`, `gui/dialog/editor.py:455-467`), `exists()` in the editor
  (`:541`). An attachment `\\attacker.example\s\a.pdf` sends the
  user's NetNTLMv2 hash when the task's editor opens. Fix (S): no file
  check for UNC or `//host` paths; show them as unknown.
- P183. The AppImage loads libraries from the folder it starts in:
  `LD_LIBRARY_PATH="...:$LD_LIBRARY_PATH"`
  (`.github/workflows/build-appimage.yml:248`,
  `scripts/build-appimage.sh:199`) ends in an empty entry when the
  variable is unset, which glibc reads as the current folder; the local
  script's `PYTHONPATH` the same (`:196`). A `libXss.so.1` (loaded by
  `powermgt/idle.py:321`) downloaded to ~/Downloads runs when the
  AppImage is started from there. Fix (S):
  `${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}`.
- P184. ~~Todo.txt auto import and export follow links~~: gone with
  Todo.txt, removed 2026-10-06 (To Do 29).
- P185. The templates list is a pickle
  (`persistence/templatelist.py:80-91`), read when the New from
  template menu is built, at start; its names are joined unchecked, so
  an absolute path is read as a template. Whoever can write the data
  folder (a portable `--ini` on a share; on Windows a `templates.lnk`,
  `config/settings.py:640-648`) runs code in Task Coach.
  [SECURITY.md](SECURITY.md) does not list it. Fix (S): JSON or text;
  an old pickle read by an Unpickler that allows only lists and
  strings.
- P186. Help > Anonymize keeps mail senders: `tools/anonymize.py:39-62`
  blanks subject, description, data and location, not `fromName`,
  `fromAddress` and `sentDateTime` (written since 2.0.3.0,
  `persistence/xml/writer.py:325-327`), and the menu suggests attaching
  the result to a public issue. Fix (S): blank them.
- P187. Backups and the data folder are readable by other users: the
  data and backup folders are made 0777 less the umask
  (`config/settings.py:32, 622, 658`; only the configuration folder is
  0700, `:601`), backups 0644 (`persistence/autobackup.py:38-39, 201`),
  and the save's temporary file 0666 less the umask until the task
  file's mode is copied (`persistence/taskfile.py:177, 146`). A task
  file kept at 0600 has readable copies where homes are open. Fix (S):
  0700 folders, backups with the task file's mode, the temporary file
  0600 first.
- P188. Opening a task file moves and deletes every 1.x backup in its
  folder: the pattern takes any `*.YYYYMMDD-HHMMSS.tsk.bak`, whatever
  its prefix (`persistence/autobackup.py:182-206`), follows links and
  removes the source. In a synced folder that deletes other files' and
  other users' old backups; a FIFO of that name hangs the open. Fix
  (S): remove the 1.x migration, or limit it to this file's own
  backups, copied.
- P189. Mail task: the subject goes into the `mailto:` link unquoted
  (`mailer/__init__.py:188-192`; body, To and Cc are quoted only off
  macOS, `:183-186`). "R&D review" arrives as "R";
  "Budget&bcc=someone@example.org" adds a recipient. A
  `[mailto:to=...]` or `[mailto:cc=...]` line in the description adds
  one by design (ee4dda7d4, 2014). Fixed 2026-10-05: To Do 18.
- P190. CSV export writes cells as they are
  (`persistence/csv/writer.py:53-54`): a subject starting with `=`,
  `+`, `-` or `@` runs as a formula in Excel or LibreOffice. Fix (S):
  a leading `'`, or a ruling not to.
- P191. Build supply chain: `softprops/action-gh-release@v1` (7
  workflows, `contents: write`) and `flatpak-builder@v6` are pinned by
  tag, not commit; downloaded without a checksum: the Python AppImage
  (`build-appimage.yml:77-87`), `appimagetool` continuous (`:304`), the
  python.org embeddable zip and `get-pip.py`
  (`build-windows.yml:78-81`). P86 has the old versions. Fix (S): pin
  by commit, check the downloads' checksums.
- P192. Templates older than `tskversion` 32 evaluate their date
  expressions (`persistence/xml/reader.py:118-182, 957-960`):
  `"x"*8000000000` or deep nesting exhausts memory or raises
  `RecursionError` at each menu build. No code runs. Fix (S): cap sizes
  and catch the error, or drop the pre-32 form.
- P193. The iCalendar export does not escape TEXT values (RFC 5545,
  `persistence/icalendar/ical.py`); a bare CR kept in a description
  (`tools/text.py`) can add a property for readers that split lines on
  CR. Fix (S).

Checked and found safe (not to redo): task files are read with Expat,
external entities and DTDs refused
([PERSISTENCE_XML.md](PERSISTENCE_XML.md)); no `eval` or `exec`, only
`ast.literal_eval` on tuples; dispatch as [SECURITY.md](SECURITY.md);
the HTML export escapes every cell; `wx.html` runs no scripts, and
description links match http(s) and www only; no listening network
service; the version check uses verified HTTPS and reads its tag
through `int()`; subprocesses take argument lists, never a shell;
temporary files by `mkstemp` or `O_EXCL`; lock files refuse links; a
swapped task file is caught before each save; passwords never reach
the INI, the task file or the logs; dropped mail is parsed header by
header; the bundled code parses no outside data; no dependency has a
known flaw in the way it is used; the Windows installer quotes the
`.tsk` association.

### Data Safety

- P194. ~~Saves are not forced to disk~~: fixed 2026-10-04, **asked by
  designer**: the new file is on disk before it replaces the old one,
  then the folder's entry, also when written in place in a cloud
  folder ([PERSISTENCE_XML.md](PERSISTENCE_XML.md#saving)). Left:
  temporary files named `tmp-N` (`persistence/taskfile.py`) stay
  after a crash during a save; names that say whose they are, removed
  at open. TODO.md 4 asks for atomic writes.
- P195. ~~The settings file is written only at quit, by removing it
  and then renaming the new one~~: fixed 2026-10-04 with P196: written
  while running, replaced in one step once on disk
  ([SESSION_END.md](SESSION_END.md)).
- P196. ~~A session's end loses unsaved changes and the session's
  settings~~: fixed 2026-10-04, **asked by designer** ("document and do
  per modern best practices"): the settings written 2 s after a change
  and every 30 s with the window's state; SIGTERM and SIGHUP save
  without asking; each quit step logged on its own. The research, the
  rules and the checks: [SESSION_END.md](SESSION_END.md); asking
  through the portal on GNOME and KDE is left for later there.
- P197. Every save, autosave included, writes a full bz2 backup on the
  UI thread, in place, not through a temporary file
  (`persistence/autobackup.py:37-43, 208-220, 272-279`); pruning
  removes at most 3 per save. With TODO.md 4 (P94).
- P198. A failing `taskfile.aboutToSave` is swallowed without a log
  (`persistence/taskfile.py:556-558`). Low risk: the Publisher logs
  each observer's failure. S.

### Core Bugs Reported on GitHub

Recorded nowhere else; each is reproduced on 2.0.3.0 first.

- P199. ~~#40: several efforts track at once; Stop and Resume ignore
  the selected effort~~: fixed 2026-10-04, **ruled by designer** ("For
  now, simplify to only track one task at a time, but document other
  app examples that track multiple"): Start tracking and New effort
  take one task, any effort that starts being tracked ends the other,
  a copy is not tracked; Stop and Resume then concern one task. The
  analysis (Release 0.23's one set of active tasks, 0.24's efforts per
  task, Start replacing the set), the checks and other applications'
  ways: [EFFORTS.md](EFFORTS.md#tracking).
- P200. ~~#157: a new effort vanishes in the task editor under the
  category filter~~: fixed 2026-10-04, **ruled by designer**: the
  editor's Effort tab has no category filter, as its Notes and
  Attachments tabs (Frank Niessink's rule of 2008); the main window's
  Effort and Effort for selected task(s) keep it, as designed in 1.2.10
  ([EFFORTS.md](EFFORTS.md#filters), with the history).
- P201. ~~#126: a subtask can get a category exclusive with its
  parent's~~: by design. A with exclusive subcategories A.1 and A.2,
  task T in A.1, its subtask T.2 given A.2: T.2 shows under both (a
  subtask counts in its parent's categories). The reporter expected the
  exclusivity to hold for inherited categories too. The menu's check
  (`ToggleCategory.enabled()`) covers a category's own parent
  categories, not a task's parent task. Read 2026-10-05; a ruling first:
  forbid it, or let the subtask's own choice win.

  Full analysis 2026-10-05
  ([CATEGORIES.md](CATEGORIES.md#exclusive-subcategories-and-subtasks)).
  Reproduced in the app, the same on master: the menu and the editor
  allow it, and list mode shows T.2 "A -> A.2 (A -> A.1)"; the help's
  "items can only belong to one of the subcategories" holds for its own
  categories. Options: keep; forbid (the bug 773 reply: ends per-subtask
  statuses and assignees, touches stored data); or the subtask's own
  choice wins (prototyped: code +67 / -10, 13 tests failing before,
  filter 22 ms on 4,500 tasks against 3.8 ms). Reported twice, both in
  2010 (SourceForge 640, which Frank Niessink kept as designed, and
  773); none since. **Ruled by designer 2026-10-05: kept as released**
  ("A"): by design; the subtask's own choice winning stays recorded for
  an opt-in, if wanted.
- P202. ~~#48: hidden items still affect the sort~~: by design. In the tree, a
  parent's priority and date sort values are taken over all its
  subtasks (`Task.prioritySortFunction(tree_mode=True)`, `recursive`
  in `task.py`), hidden ones included: parents with only inactive
  high-priority subtasks sort above, with those subtasks hidden. Read
  2026-10-05; with P206, one rule to rule on.

  Full analysis 2026-10-05, **asked by designer** ("this is very
  complicated and very critical, we don't change anything unless we
  are 100% sure of no regressions";
  [TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#tree-mode)). Reproduced in
  the app, the same on master: Parent_1 (priority 1, its subtask 9
  hidden by "hide inactive") above Parent_2 (5), its Priority column
  showing "(9)" and its planned start the hidden subtask's. Released,
  consistent (the order follows what a collapsed parent shows) and
  ruled as relied on ([TASK_FIELDS.md](TASK_FIELDS.md#core-fields)).
  Counting only shown subtasks would change, in tree mode, the sort
  and the parenthesised value of the 14 core columns, the exports
  showing them and the square map; make the subtree value depend on
  each view's filters (a value per view, not per task); and need a
  re-sort when a filter hides a subtask (removals do not re-sort
  today). The designer's path for such changes: new fields and sort
  keys beside the core ones, so saved views keep theirs (To Do 13,
  postponed). **Ruled by designer 2026-10-05: kept as released**
  ("Option A please"): by design; the opt-in way, if wanted, is To Do
  13.
- P203. #49: recurrence from completion moves the due date, not the
  planned start. **Postponed by designer 2026-10-05** ("for the other
  issues, I will um, postpone. You can document your analysis"; To Do
  20). Analysed 2026-10-05: with "Schedule each next
  recurrence based on: last completion date", a task with a planned
  start and a due date takes due = completion + interval, start at the
  same distance before (`Task.recur()`); one with a planned start only
  already restarts from the completion. So start yesterday, due
  tomorrow, completed today: the dates do not move (master too, a
  scratch file in the app); start tomorrow, due the day after,
  completed today: the next one starts today. Four tests of 2010 pin
  that. Other applications: the interval moves the due date in
  Outlook ("Regenerate new task"), Todoist ("every!") and OmniFocus
  "Due Again"; the start in OmniFocus "Defer Another" and Things
  ("after completion"). Prototype: with a planned start, the next one
  starts the interval after the completion (the planned start's time
  kept) and the due date keeps its distance; without one, as before.
  In the app: start today, due tomorrow, completed: start and due one
  day later; start yesterday, due tomorrow: start tomorrow, due in
  three days. Tests: the four updated and the report's case, which
  fail before. The prototype, not kept: in `Task.recur()`, when
  `recurBasedOnCompletion` and a planned start is set, the next
  planned start is `recur(completion)` at the planned start's time and
  the due date the old due date's distance after it; the due-date and
  planned-start blocks below skip that case.
- P204. #58: a subtask can have its parent as prerequisite.
  **Postponed by designer 2026-10-05** (To Do 20). Analysed 2026-10-05, reproduced on master and the branch (a scratch
  file): "Book flights", due yesterday, its parent its prerequisite,
  shows inactive, never overdue, beside its overdue sibling. A task
  waits for its prerequisites and its ancestors' (`_update_status()`,
  `prerequisites(recursive=True, upwards=True)`), and a parent is done
  only with its subtasks: an ancestor as prerequisite waits for the
  task's own completion; a descendant as prerequisite is inherited by
  that descendant, which then waits for itself. Two prerequisites
  waiting for each other trap the same way. Ways in: the editor's
  Prerequisites tab (only the task itself is not checkable,
  `LocalPrerequisiteViewer.getIsItemCheckable()`), a drop on the
  Prerequisites or Dependencies column (`DragAndDropTaskCommand`, no
  check), moving a task under one of its prerequisites or dependents
  (drag, paste as subtask), older files. Proposed rule, to rule on
  before the code: no prerequisite a task would wait for itself
  through (its ancestors, its descendants, a task waiting for it);
  not checkable in the editor, drops and moves refused, older files
  corrected on load with a message as for duplicate IDs. Size M.
- P205. #169: copied tasks' dependencies point to the originals (To Do
  30 of the scheduler refactor handled cut and paste only). Analysed
  2026-10-05. Done 2026-10-05, **ruled by designer** ("proceed with
  your point one, which is P205, as you suggested";
  [PERSISTENCE_XML.md](PERSISTENCE_XML.md#ids)). Was: a copy has no
  prerequisites at all, since 2010
  (`Task.__getcopystate__()` leaves them out; templates copy through
  it too), so copying "Phase 3: Development" of the sample file gives
  subtasks with no links among them (master too; read from the saved
  file). Cut and paste keeps them (the same tasks). Other
  applications: Microsoft Project keeps the links among the copied
  tasks, not those to tasks outside (its forum); the report asks the
  outside ones kept. Prototype (`command/clipboard.py`): a copied task
  keeps its original's prerequisites, those copied with it as their
  copies, the others as they are; at the paste those the file no
  longer holds are dropped and the reverse links added; no task that
  was not copied changes, templates unchanged. In the app the copy's
  links come out as the original's, "Get client approval" kept; undo
  restores the file. Tests: `CopyAndPasteWithPrerequisitesTest`, 3 of
  6 fail before (the other 3 guard the originals, a deleted
  prerequisite and cut and paste).
- P206. ~~#321: the status-first sort ignores subtasks in the tree: an
  inactive parent with a late child sorts last~~: by design. Its status key is the
  parent's own (`sorter.py:114`), while its other sort values take the
  subtasks (P202). The reporter asked a parent to sort in the section
  of its most urgent subtask. Read 2026-10-05.

  Full analysis 2026-10-05 (with P202): reproduced in the app, the
  same on master ("A inactive parent", its subtask due in 2 hours,
  below "B active task"). A status is the task's own by design
  ([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#tree-mode)). Sorting a
  parent by its most urgent subtask would move, in every tree view
  with "Sort by status first" (the default), each parent with a more
  urgent subtask; leave its colour, icon and Status column at its own
  status (a grey parent among overdue tasks) unless those change too;
  need a re-sort when a subtask is removed, moved or completed; and
  decide for a completed parent with open subtasks and for the
  descending sort. **Ruled by designer 2026-10-05: kept as released**
  ("Option A please"), as P202.

### Performance

- P207. Each row scans the whole list: the effort view's period cells
  call `presentation().index(effort)`
  (`gui/viewer/effort.py:769-778`); a selection-only export asks
  `isselected()` per item (`gui/viewer/base.py:528-532`;
  `persistence/csv/generator.py:148`,
  `persistence/html/generator.py:221`), each rebuilding
  `curselection()` over the whole tree (`widgets/treectrl.py:477-489`);
  `listctrl.select()` (`widgets/listctrl.py:329-332`); `on_new_item`'s
  `item in self.presentation()` (`gui/viewer/base.py:395-400`); the
  Timeline and Square map (`gui/viewer/task.py:553-559, 742-753`). Fix
  (M): direct lookups.
- P208. Undo snapshots every item before and after each action
  (`patterns/snapshot.py:92-110`; 27 ms for 2,000 tasks,
  [UNDO_REDO.md](UNDO_REDO.md)), efforts included; not measured with
  many efforts.
- P209. The scale files hold no efforts:
  `tools/generate_task_file.py` and
  `tests/integrationtests/PerformanceTest.py:42` (100 tasks), while
  long-used files are mostly efforts. Fix (S): add efforts (20,000),
  then measure P207 and P208.

### Release, Packaging and CI

- P210. A release goes public before its packages exist: the 8
  workflows publish with `draft: false` (`release-notes.yml:27-32`,
  `build-deb.yml:304-309` and the others), so the first build done
  makes the public "latest" release, which the version check offers
  while the others run; a failed build leaves it without that package.
  `prerelease: contains(ref, 'beta')` is never true (numeric tags
  only). Fix (S/M): a draft, published by a last job once all pass.
- P211. No checksums (`SHA256SUMS`) are published. S.
- P212. RPM: the spec uses `%py3_build` and `%py3_install`
  (`build.in/fedora/taskcoach.spec:81, 84`), deprecated in Fedora 43
  and expected to stop working in 45; only Fedora 43 is built (end of
  life 2026-12-09, `build-rpm.yml:40-44`), not 44; the spec's
  `%changelog` still says pyparsing is bundled (`:135, 152`). The deb
  build has no `pybuild-plugin-pyproject` and takes the `setup.py`
  path. Fix (S): `%pyproject_*` macros, Fedora 44.
- P213. ~~README lists packages that are not built~~: done
  2026-10-06 with To Do 31: no Debian Sid (off in `build-deb.yml`),
  Fedora 43 only (42 ended 2026-05-27), the "installaion" heading
  gone with the section.
- P214. `debian/patches/series:5` points to
  `docs/CRITICAL_WXPYTHON_PATCH.md`, which does not exist. S (with
  P84).
- P215. The macOS Intel build's runner, `macos-15-intel`
  (`build-macos.yml:38`), is GitHub's last x86_64 image, retired in
  August 2027: drop Intel or build a universal app. S.
- P216. The `.desktop` file's `Keywords` lacks its closing `;` (#172):
  `build.in/linux_common/taskcoach.desktop:10`; the Flatpak copy is
  right. S.
- P217. `setup.py`'s `install_requires` leaves out wxPython,
  PyGObject, dbus-python and pywayland (`:74-80`), against its own
  comment (`:69`); `author_email` is a URL (`meta/data.py:95`). Low
  value: nobody installs from pip. S.
- P218. Nothing proposes updates of the workflow actions (Dependabot).
  S.

### Tests

- P219. Before a CI test job (P85): `tests/test.py:65-72` pins the
  exact Python, wxPython, wxWidgets and GTK versions with no override,
  so the job would stop after a Debian point update; `debian/rules`
  overrides `dh_auto_test` with nothing.
- P220. Thin tests in core: the effort editor 5 (the task editor 45;
  #476 was an effort editor crash), reminders 13 (controller 7, dialog
  6), the category viewer 7, integration 10, the backup manager dialog
  none; one test commented out (`TaskViewerTest.py:213`); no coverage
  measured. M.
- P221. No black or wider flake8 in CI (`.github/workflows/checks.yml:33-39`),
  and black is not pinned (`pyproject.toml` has no
  `required-version`). S.

### Code Health

- P222. black: 7 files drifted: `sounds/generate_sounds.py` (137
  lines), `sounds/__init__.py` (66; a hand-aligned table, for
  `# fmt: off`), `gui/toplevelcontroller.py` (28),
  `AmountEntryTest.py` (20), `persistence/xml/templates.py` (18),
  `icons/image_list_cache.py` (7),
  `gui/uicommand/mixin_uicommand.py` (6), `widgets/dirchooser.py` (3);
  6 more differ only by black's version-dependent blank lines; 5 are
  the generated icon tables. S.
- P223. Lint in own code: loop variables shadow the `effort` and
  `task` modules (F402, 16: `domain/effort/effortlist.py`,
  `reducer.py`, `command/effortCommands.py:39`,
  `command/noteCommands.py:116`, `domain/task/tasklist.py:53`,
  `gui/menu.py:877`); `== True` and `== None` on a three-state value
  (`domain/task/task.py:528-530`); a type compared with `==`
  (`widgets/treectrl.py:190`); F811 (3), F841 (`i18n/__init__.py:105`),
  F541 (1); 3 unused imports that are not re-exports
  (`gui/viewer/factory.py:43, 68`,
  `icons/synthetic_icon_generator.py:135`); `_MSURL` unused
  (`help/__init__.py:26`). S.
- P224. The largest functions: Preferences' two `__init__`
  (`gui/dialog/preferences.py:728, 1408`; 470 and 467 lines),
  `_createColumns` (`gui/viewer/task.py:1253`, 415), and the editor's
  (`gui/dialog/editor.py:3837, 1484, 4152`; 254, 219, 205): the
  hardest places to change safely. L to split.
- P225. 114 broad `except Exception`, 36 silent; the core ones are
  P196 and P198.
- P226. `sounds/generate_sounds.py` (429 lines), a developer tool,
  ships in the package; the icon generators are in `tools/`. S.

### Scope Rulings

- P227. The views outside the core: Timeline, Square map, Hierarchical
  calendar, Calendar and Task statistics, about 6,600 lines (viewers
  781, widgets 1,485, the bundled wxScheduler 3,893 and timeline 434),
  with squaremap (last release 2019-12-06, D13) and piectrl; 0 to 2
  tests each. Keep and test, or retire (as P82, the Dependency Graph).
- P228. Help > FAQ opens the old project's Launchpad FAQ
  (`meta/data.py:101`, `gui/uicommand/uicommand.py:3306-3308`). S.
- P229. The old `[syncml]` and `[iphone]` sections are kept and written
  back ([SETTINGS.md](SETTINGS.md)), though
  `_remove_obsolete_settings()` exists
  (`config/settings.py:329-363`). S.

### Docs

- P230. Code names in docs spelled as before their renames (the two
  from this refactor's branch fixed 2026-10-04): ICON_DISPLAY
  (`viewerIconIds`, `isSequentialNode`, `_clockRunning`, `iconName`,
  `_refreshImage`, `iconWidth`), FLATPAK (`exportAsHTML`,
  `exportAsCSV`, `exportAsICalendar`, `__askUserForFile`),
  LIST_MANAGEMENT (`onEndIO`), WAYLAND_ISSUES (`closeViewer`,
  `dockedPanes`), DATETIME_CONTROLS (`SetDateTime`,
  `_rebuildDemoDateCtrl`), DATETIME_PRESETS (`suggestedDateTime`),
  TASK_STATUS (`dueSoonHours`). SETTINGS.md cites
  `_fixValuesFromOldIniFiles`, which is gone; LIST_MANAGEMENT.md
  describes the UpdateUI polling, off since
  `application/application.py:483-485`, and `NeedsSelectionMixin`,
  gone. A rule in `tools/check_renames.py` (a name in a doc whose
  snake_case twin is defined) keeps them right. With P112. S.
- P231. SYSTEM_TRAY.md, "Why No Left-Click/Right-Click
  Differentiation?", says SNI cannot tell the clicks apart; the SNI
  specification has `Activate`, `SecondaryActivate` and `ContextMenu`,
  so the limit is AppIndicator's (#442 shows direct SNI working). S.

### Found 2026-10-05

- P232. ~~Effort for selected task(s): select an effort there, then a
  task without efforts in the task view: 5 tracebacks in the log~~
  Fixed 2026-10-05 ("If it's all completed, please commit and push"):
  (`None is not in list`, `'NoneType' object has no attribute
  'task'`), nothing visible; on master too. Cause:
  `EffortViewer._refresh()` sets the new presentation, then clears
  the selection; the deselect event asks the old row's text from the
  new, shorter presentation (stack recorded with a probe). Not about
  categories or filters: only the order of two steps when the view
  changes tasks. Prototyped 2026-10-05: the selection cleared before
  the presentation changes (`EffortViewer._refresh()`, which the
  aggregation switch uses too); test
  `test_no_row_is_asked_of_the_new_presentation` fails before (and
  logs the same tracebacks); in the app 0 tracebacks, the view the
  same. Nothing changes for the user: the log only.
- P233. ~~Mail task: when opening the `mailto:` link fails, it is
  opened again addressed to `recipient@domain.com`~~ Removed
  2026-10-05, **ruled by designer** ("This is dangerous. We should not
  have such code in this app"). The retry came in 2009 (c600189f8,
  "Hopefully this satisfies Groupwise": GroupWise refused a message
  without recipient); domain.com is a real domain, so a message sent
  unchecked left the task's text with a stranger. Reproduced on
  master with an `xdg-open` stand-in refusing links without
  recipient: the second link, `mailto:recipient%40domain.com?...`,
  opened, no error shown. First made one link with the error shown;
  then, researched below, a mail without recipient is opened again to
  the reserved placeholder (`recipient@example.com`), and any other
  failure is shown.

  Placeholder addresses, researched 2026-10-05, **asked by designer**
  ("What are the modern best practices for putting a placeholder
  email?"): first, none at all: a `mailto:` link's recipient is
  optional (RFC 6068, `mailtoURI = "mailto:" [ to ] [ hfields ]`), the
  link Task Coach opens; when a placeholder cannot be avoided, a name
  nobody can own: `.invalid` (RFC 2606, "sure to be invalid and ...
  obvious at a glance"; RFC 6761: lookups fail at once), or
  `example.com`, `.net`, `.org` (RFC 2606; IANA: for documentation,
  never registered), example.com publishing a null MX, `0 .` (RFC
  7505: it accepts no mail). Mail programs do not refuse `.invalid`
  themselves (Mozilla bug 29497, open since 2000); it cannot be
  delivered. domain.com is an ordinary company domain whose mail goes
  to Microsoft's servers (MX `domain-com.mail.protection.outlook.com`,
  checked 2026-10-05): the old placeholder was deliverable.

  **Ruled by designer 2026-10-05**: "use the most common one. It looks
  like example.com ... As a second attempt, if the first one is
  blocked ... something like recipient at example.com". Done: when the
  mail program refuses a message without recipient, it opens again
  addressed to `recipient@example.com`, the copies kept; a message
  that names recipients is not opened again (the old retry replaced
  them with its placeholder and dropped the copies); any other failure
  is shown. Tests: `test_no_recipient_refused_opens_again_to_the_placeholder`
  (fails before), `test_a_message_with_recipients_is_not_opened_again`.
  App: a stand-in refusing links without recipient got
  `mailto:recipient%40example.com?...`, no error; a stand-in failing
  every link got both, then the error.
- P251. Tab into a Subject or Description box keeps its caret where it
  was; native text fields select all their text (Windows' dialog
  manager, GTK's `gtk-entry-select-on-focus`, macOS): found
  2026-10-08 researching the focus rule, the same on master. Not the
  concern then (designer); recorded in
  [FOCUS_MANAGEMENT.md](FOCUS_MANAGEMENT.md#not-changed).
- P250. A session end while "Save changes?" is open loses the
  changes: found in the release review of 2026-10-07, read from the
  code, the same on master. With autosave off, close the window (or
  press Ctrl+C in a terminal) so Task Coach asks; then SIGTERM (a
  shutdown) reaches `quit_application(force=True)`, which returns at
  once while quitting, and the question waits until SIGKILL.
- P249. ~~Preferences > Theme: unchecking System for "Other Months
  Days Background" keeps showing the system's colour~~: fixed
  2026-10-07, found checking P247 in the app, the same on master (the
  same handler): the picker showed (241, 240, 238) while the saved
  (211, 211, 211) was then used. It now shows the colour used. Test:
  `test_unchecking_system_shows_the_other_months_colour_used`.
- P248. ~~Preferences failed to open once in a test run~~: fixed
  2026-10-07: `SettingsPage.fit()` read `GetPos()` from the grid's
  items, and wxPython handed one back as a plain `SizerItem` (1 of 33
  dialogs; not reproduced since). It now asks the grid
  (`GetItemPosition()`), whatever the item's type
  ([PREFERENCES.md](PREFERENCES.md#layout)).
- P247. ~~Preferences' Cancel keeps some changes~~: fixed 2026-10-07,
  **ruled by designer** ("proceed with holding all changes and having
  the apply/cancel options, and having them grey/disabled/enabled as
  relevant, following modern best practices"), with D24: every page
  saves on OK or Apply, Cancel drops the rest, Apply is greyed until a
  change ([PREFERENCES.md](PREFERENCES.md#ok-apply-and-cancel)).
  Found 2026-10-07 analysing P94's item 10, the same on master:
  Preferences > Durations, Delete "2 days", Cancel, open Preferences
  again: "2 days" was gone, from TaskCoach.ini too; Add and the Theme
  page's colours, System checkboxes and Reset buttons the same. Tests
  in `PreferencesTest` (11 fail before). App: Delete then Cancel keeps
  "2 days" and the file; Apply saves and greys Apply; a Theme change
  then Cancel leaves the file as it was.
- P246. ~~With "Let the computer say the reminder" on and no `espeak`,
  the reminder never shows~~: fixed 2026-10-06, found analysing P94's
  speech item, the same on master. Preferences > Reminders, turn it
  on, on a system without `espeak` (Debian and Ubuntu install none;
  their espeak-ng names its command `espeak-ng`): at the reminder's
  time nothing shows; the log has `FileNotFoundError: 'espeak'` from
  the reminder window's making. Now the failure is logged and the
  reminder shows; `espeak-ng` runs where `espeak` is missing.
  Tests: `SpeakerTest` (fail before). App: the reminder shows,
  "cannot say the reminder" in the log. Then the option was removed
  2026-10-07, **ruled by designer**, and the fix with it
  ([SPOKEN_REMINDERS.md](SPOKEN_REMINDERS.md)).
- P245. ~~The sash throttle never runs~~: removed 2026-10-06, **ruled
  by designer** ("Ok, as you suggest for point 1"). `frame.py`'s
  `_install_sash_resize_optimization()` replaces the AUI manager's
  `OnMotion` attribute after AUI has bound its own handler
  (`self.Bind(wx.EVT_MOTION, self.OnMotion)` in AGW's framemanager),
  so a sash drag calls AUI's handler directly, unthrottled. Found
  2026-10-06 analysing P96; To Do 32. Its test is also wrong: it
  throttles action 3 (`actionClickCaption`), a sash drag is 1
  (`actionResize`). Measured 2026-10-06 (2,050 tasks, a 120 px drag
  at 60 moves a second): as released, 19 drag steps laid out, 1,417
  ms of layout, the last 0.43 s after the release; with the throttle
  bound and testing action 1, 16 steps (5 of 20 moves dropped), 1,199
  ms, 0.13 s; runs vary more than that. Each layout takes 60 to 75
  ms, so GTK already merges the moves that come meanwhile.
- P244. ~~The Backup Manager has no title~~: fixed 2026-10-06. File >
  Manage backups opened a window whose title bar and task bar entry
  were blank, since 2014 (`BackupManagerDialog` passed none). Its
  title is now its menu item's text, already translated, without the
  dots. Test: `BackupManagerTest` (fails before). App: titled "Manage
  backups".
- P243. ~~The lists' frames have rounded corners~~: done 2026-10-06,
  **found and ruled by designer** ("commit the borderless. It seems
  fine"), the same on master. Seen at the header's top corners (task,
  category, note, effort lists): each list kept wx's default themed
  border, and wxGTK 3 draws that border in a text entry's style
  (`draw_border()` in wx's `src/gtk/window.cpp`), which the theme
  rounds, inside the pane's own square border. Done: the lists have
  no border of their own (`wx.BORDER_NONE` in `TreeListCtrl` and
  `VirtualListCtrl`); the pane's border is the only frame, square; in
  an editor's tab the list reaches the page's edges. Checked by the
  designer on the desktop.
- P242. ~~In list mode the subjects start a button's width right of
  the header's text~~: done 2026-10-06, **found by designer** ("the
  space is for the arrows in tree mode ... tree mode and list mode
  are understood to be different views"), the same on master. The
  task list's widget always had expand buttons, so list mode kept
  their room (about 16 px) though no row has any. Done: list mode
  turns them off (`TreeListCtrl.show_expand_buttons()`), tree mode
  keeps them, as GTK's own lists and trees do. Tests: the buttons in
  tree mode only, and after a switch (2 failing before). App: list
  mode's icons under the header's "Subject", tree mode unchanged, a
  double click opens the row's task.
- P241. ~~Importing a Todo.txt export adds a copy of each category
  whose name has a space~~: done 2026-10-06, ruled by the decider
  ("reloading a to-do has to reload it exactly like it exported it").
  Steps (the same on master), on the Welcome file: File > Export >
  Export as Todo.txt; File > Import > Import Todo.txt of that file:
  the categories pane shows a new top-level "@Contexts_(GTD-Style)"
  beside "@Contexts (GTD-Style)". The export writes spaces as
  underscores on purpose (one word per context or project, 2011,
  270036860); the import looked categories up by the name as written,
  and did so for every line and the `-meta` file before skipping the
  unchanged ones, so a category deleted in Task Coach also came back.
  An edited line also lost the times of its dates, a priority outside
  A to Z, and a subtask's subject got a leading space. Done: a
  category is the one the export writes with that name, the task's
  own first, looked up only for edited lines; a value the export
  writes as the task's own keeps the task's own. Tests:
  `TodoTxtRoundTripTest`, 8 of 9 failing before. App: automatic
  import and export, an edited subject and a due date added on a
  subtask: 18 categories as before, times kept, no leading space.
  Then Todo.txt was removed (To Do 29); the fix is described in
  [TODO_TXT.md](TODO_TXT.md), to redo with the feature.
- P240. ~~File dialogs start in folders that do not follow the open
  task file~~: done 2026-10-06, **ruled by designer** ("proceed ... as
  you propose"), the same on master before: each file dialog opens in
  the folder last chosen in one of its kind this session, before that
  in the open task file's, with no saved file in Documents;
  attachments keep their folder across sessions, Save As opens next to
  the current file ([FILE_DIALOGS.md](FILE_DIALOGS.md)). Import CSV,
  Import template and Add attachment opened in the folder Task Coach
  started from, on Windows its program folder. Checked in the app
  (Import CSV in the task file's folder, started elsewhere); 7 new
  tests fail before.
- P239. Parked by designer 2026-10-05. Nested exclusive subcategories
  filter too much (SourceForge bug 1414, 2013; closed 2026-01-12 without
  moving to GitHub). Found 2026-10-05 searching the reports of P201;
  reproduced the same day, the same on master. Categories: A's
  subcategories A.B and A.C exclusive, A.B's A.B.X, A.B.Y and A.B.Z
  exclusive; a task in each of A.B.X, A.B.Y and A.C:
  1. Categories pane: A.B.X, A.B.Y and A.B.Z greyed; clicking A.B.Y
     does nothing.
  2. Tick A.B: the three enabled; the tasks in A.B.X and A.B.Y show.
  3. Tick A.B.Y: A.B stays ticked ("2 filtered"); the task in A.B.X
     still shows.
  4. Reset the filter (pane toolbar): nothing filtered, but A.B.X and
     A.B.Z drawn enabled and A.B.Y greyed; A.B.X can then be ticked
     alone: only its task shows, and it is drawn greyed while ticked.
  5. View > Filter > Categories > A (subcategories) > A.B
     (subcategories) > A.B.Y while A.B.X is ticked: both stay ticked,
     two radio buttons on; both tasks show.
  6. With View > Filter > "Filter on all checked categories", steps
     2 and 3 show only the task in A.B.Y (the 2013 reply's way).

  Causes: ticking a choice unticks its parent category, except when
  the parent is itself a choice (`CheckTreeCtrl.on_item_checked()`),
  and a ticked category shows all its subcategories' items
  (`CategoryFilter`); a row is greyed while the nearest choice above it
  is unticked, set only for the rows refreshed
  (`CheckTreeCtrl._refresh_check_state()`; the widget's
  `EnableChildren()` when one is ticked); the menu ticks one category
  with no exclusivity (`ToggleCategoryFilter.do_command()`). Pinned:
  `TreeCtrlTest` (a choice unticks a check box parent; ticking a
  parent unticks its choices); nothing for nested choices, the grey
  rows or the menu
  ([CATEGORIES.md](CATEGORIES.md#exclusive-subcategories)).
- P238. Parked by designer 2026-10-05. The task editor's Check all gives
  every category, both radio choices of an exclusive category included.
  Steps (the same on master): A with exclusive A.1 and A.2; a task's
  editor, Categories tab, Check all: A, A.1 and A.2 all ticked, both
  radio buttons on; its Categories column "A, A -> A.1, A -> A.2". The
  help: "items can only belong to one of the subcategories". A single
  tick follows the rules (`ToggleCategoryCommand`: a choice removes the
  other choice and the exclusive category; the exclusive category
  removes its choices); Check all links every category to every edited
  task (`LocalCategoryViewer.check_all_categories()`,
  `LinkCategoriesCommand`). Since Check all came (097b46718, #148,
  2.0.1.2, 2026-01-09); P28 (2026-09-29) made it one undoable command,
  the same links. Uncheck all is right: none ticked is allowed. Pinned:
  `LinkCategories` and `CategoryViewerTest` (both sides linked, undo),
  none with exclusive categories. The Categories pane's copies
  (`CategoryViewer.check_all_categories()`, `uncheck_all_categories()`)
  are unreachable: only the editor's toolbar has the buttons. Found
  2026-10-05 with P201
  ([CATEGORIES.md](CATEGORIES.md#exclusive-subcategories)).
- P237. The Spanish, Portuguese and Brazilian Portuguese catalogs repeat
  messages (`msgfmt --check`: 1, 5 and 7 duplicate definitions, such
  as `es.po:7946` and `:4362`); the loader keeps one of each, which
  one not checked. Found 2026-10-05 while adding To Do 22's messages.
- P236. The categories pane can stay blank after start-up, its toolbar
  and rows unpainted until something redraws them: 7 of about 80
  starts on the virtual display on 2026-10-05 (2,000 tasks and the
  Welcome copy), on the committed code and with To Do 21's change
  alike, and partly twice (rows only; on master its toolbar). The
  list's paint handler ran with its rows; the screen stayed blank.
  Not seen in the last 10 starts, nor under a trace (the geometry
  trace, an event filter): timing; not traced.
- P235. ~~The Linux tray menu (AppIndicator) is rebuilt whole after each
  task added, removed, renamed or completed and each tracking start
  or stop~~: fixed 2026-10-05 (To Do 23): its "Start tracking" submenu lists every task, and the
  tray host shows the menu itself, so it is built ahead
  ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#menu-contents)). Once per action
  (a burst is one), not per task; a rename commits once, on leaving
  the field. With 2,000 tasks each Mark completed froze the window
  1.6, 2.6, 2.6 s (three in a row): 0.5 s building the items,
  then 1.1, 2.0, 2.1 s handing the menu to AppIndicator, which
  replaces the old one. After a load 0.25 s. On master too (1.6,
  2.5 s). Found 2026-10-05, **asked by designer** ("Why rebuilt for
  every task???").

  Traced 2026-10-05 (five completions each): the hand-over levels
  off at about 1.8 s, memory at 223 MB: no leak; destroying the old
  menu changes nothing (1.7 to 1.9 s). Without the items' icons it is
  0.25 s, the whole rebuild 0.38 s against 2.3 s: libdbusmenu-gtk
  turns each item's icon into image data for the tray host, 2,000 per
  rebuild. The first menu after a load is cheap only because the
  tasks have no icons before the first pass (so it shows none).
  A quiet-period debounce (`patterns.later.debounced`, 2 s), **asked
  by designer** ("Why don't you have some kind of debounce?"): two
  completions in a row gave one rebuild, of 3.3 s, the next 2.5 s,
  and the first build, now after the first pass, 1.5 s at start
  instead of 0.25 s: it moves the freezes, not removes them. Changing
  only the affected items: removing a completed task's items from the
  live menu took 0.1 ms each, 1 ms per completion (prototype).

  Icons prepared once, **asked by designer** ("This would be a
  one-time pass where the icons are prepared ... a change that is
  totally technical and not functional"): done 2026-10-05. Not NumPy's
  doing: the tray read each item's icon file again (`Gtk.Image`
  from the file) and the tray library turned each picture into image
  data. Each icon is now read once; where GTK draws the menu (no tray
  host, as on the designer's LXDE) items name it, and the library
  passes the name: a rebuild with 2,000 tasks 0.30 to 0.46 s instead
  of 1.7 to 2.4 s. With a tray host (KDE, GNOME) items share the
  picture, still converted per item: in-place edits remain for
  that ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#menu-icons)).

  In place, **ruled by designer** ("do all the other work of the
  icons ... a technical fix. Has no functional impact"): done
  2026-10-05. The menu is handed over once and brought to its lines
  in place, only the changed items touched, whatever draws it: 11 to
  17 ms an update with 2,000 tasks
  ([SYSTEM_TRAY.md](SYSTEM_TRAY.md#menu-updates)). The same updates at
  the same moments.

  Icons, **asked by designer** ("Please give me all the details";
  "if there's missing icons, it should be fixed"; "If they get changed
  after, they get changed after"): the menu followed a task's icon
  only at its next add, remove, rename, completion or tracking change,
  so the first menu after a load had no task icons (built before the
  first pass) and a status the clock changed kept its old icon (a task
  turned overdue still due soon in the tray: virtual display, lxpanel,
  on the committed code). Done 2026-10-05: the first menu comes after
  the read's full loop (To Do 21), and an icon change updates the menu
  once after the pass.
- P234. ~~At start the file can be read before the main window first
  paints~~: fixed 2026-10-05 (To Do 22). The window stayed unpainted
  (black on the virtual display) until the read, and often the first
  tick's full pass, were done: with 2,000 tasks 2.1 to 2.6 s, on
  master too. The 1.8 s not traced earlier was that pass. Cause: the
  read was a `wx.CallAfter` queued before the first show, which wxGTK
  defers until the window manager reports the frame extents.

---

## Open GitHub Issues

The 89 open issues of 2026-10-04 (no open pull requests), read through
GitHub's public API. Closing them is the designer's.

**Core bugs**: P199 to P206 above.

**Likely fixed or decided**, to close after a check on 2.0.3.0: #47
(the `.delta` file is gone), #61 (mail drop, P31), #88 and #187 (the
version check), #123 (no log file, by design: TODO.md 1), #268
(TODO.md 7, no action), #286 and #318 (status refresh,
[TASK_STATUS.md](TASK_STATUS.md)), #303 (status reworked), #381 (idle
CPU, the scheduler refactor), #385 (P118), #473 (P132). Perhaps also
#25 ([FILE_LOCKING.md](FILE_LOCKING.md)), #407
([WINDOWS.md](WINDOWS.md)), #459 (P133), #469 (FILE_LOCKING.md).

**Core feature requests**, recorded nowhere else: move by keyboard in
manual order (#89, #479 the same), show only a subtree (#92), new tasks
start active (#95), shortcuts for the status filters (#99), postpone
the start at once (#100, #150), the effort editor on Stop (#107), turn
off unused features (#108), confirm deletes (#115), change history
(#165, #224), recurrence on several weekdays (#228), a completion
toggle (#230), subtask counts by status (#245), a "not now" status
(#259), AND, OR and NOT category filters (#260), due soon per task
(#274), a tree and list shortcut (#284), typing dates without the
pop-ups (#328), a look for Today and Tomorrow (#335), working-day marks
in the time picker (#349), extra due reminders (#352), sort by several
columns (#358), shift dates in bulk (#400).

**Recorded under another item**: #29, #91 (TODO.md 4, P94); #46, #106
(P97); #121, #457 (HiDPI: P125, To Do 11); #161, #173, #252, #320
(Wayland: [WAYLAND_ISSUES.md](WAYLAND_ISSUES.md), D8); #172 (P216);
#242 ([TASK_FIELDS.md](TASK_FIELDS.md)); #310 (D11); #329 (D24, done); #340
(P98); #384 (P138); #390 ([SYSTEM_TRAY.md](SYSTEM_TRAY.md)); #435
(P77); #436 ([MARKDOWN.md](MARKDOWN.md), parked); #442 (P231).

**Others**: a Tkinter port (#17) and a Qt port discussion (#19);
CalDAV sync to mobile (#27); a sample file and better defaults at
first start (#32); copyright years (#38); the note editor closes with
its category editor (#51); 2.0.0.84 errors on Ubuntu 24.04, likely
stale (#74); reminders in one window (#93); row separator lines (#97);
a better toolbar customizer (#103); "tracker" or "timer" in the
description (#104); PyPI (#105); a relative task file path in the INI
(#151); printing: dark preview, PDF fails (#167); a column
configuration tool (#191); a hint when search hides filtered items
(#234); icon-only columns (#248); ~~columns reordered by dragging
(#311)~~ (done, To Do 19); macOS: where Preferences is (#403; `wx.ID_PREFERENCES` puts it
in the application menu); macOS: two horizontal scrollbars (#461).

---

## Low Priority, Deferred

The Deferred and Will Not Do items of the master scheduler refactor,
**asked by designer 2026-10-04**: out of that refactor's scope, open
here at low priority. Details under their numbers in
[MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#deferred-and-will-not-do).

- D1. The renames too wide for that refactor: domain and viewer
  methods (`addChild`, `removeChild`, `computedStatus`,
  `processReminder`, `onSelect`, `_createColumns`,
  `subjectImageIndices`, `registerObserver`, `removeObserver`) and
  keyword families (`taskList`, `effortList`, `cssFilename`,
  `selectionOnly`).
- D2. The GTK warning at every launch, from inside GTK.
- D3. Attachment styling.
- D4. One base class for the two tray icons (different by design).
- D5. The Plasma window management protocol on KDE Plasma Wayland,
  for users there to test.
- D6. The `wx.Display` replacement on Windows, for users there to
  test.
- D8. What cannot be tested here: Windows, macOS, Wayland, KDE and
  Flatpak items.
- D9. Retire the forms written for releases reading `tskversion` 37,
  between January and April 2027.
- D10. The Task statistics view's busy repaint loop (To Do 1 above).
- D11. Dark theme colours: only on the designer's request.
- D12. The reminder sound's player process left running unwatched.
- D13. `squaremap` kept as a dependency, not copied.
- D14. The Calendar view's `invalid bitmap size` log line.
- D15. Text cut without "..." in too-narrow list columns; for the
  task and category lists, ruled so 2026-10-06
  ([LIST_MANAGEMENT.md](LIST_MANAGEMENT.md#text-too-wide-for-its-column)).
- D16. Empty Papirus icon folders and monochrome icons.
- D17. P170, template dates read in part, **deferred by designer
  2026-10-06**: the templates dialog would accept a date only when all
  its text is read; prototype in
  [prototypes/P170.diff](prototypes/P170.diff).
- D18. P57, Norwegian systems get British or C dates, **deferred by
  designer 2026-10-06**: the workaround would run only on Windows,
  where the date picker it was for is native; prototype in
  [prototypes/P57.diff](prototypes/P57.diff).
- D19. Scrolling past the last column with automatic resizing off, to
  resize it, **ruled by designer 2026-10-06** ("dragging it beyond the
  window seems to work ... we don't need to make further changes"):
  a header border dragged past the window's edge keeps resizing; only
  the last column, scrolled to the far right, has its border at the
  window's edge (the scroll range is the columns' width plus 2 px,
  `AdjustMyScrollbars()` in the bundled tree, the same on master). If
  asked again: a margin of about 150 px added there in fixed-width
  mode, set by `TreeListCtrl`; the effort and attachment lists
  (`wx.ListCtrl`) have no way to add one.
- D20. Translations, **deferred by designer 2026-10-06** ("for
  translation, you can set in a section that is deferred, will not
  do in this refinement refactor"): To Do 8 and P63, analysed
  2026-10-06.
  - The texts still in English, of today's 1,441 screen texts: French
    212, Spanish 246, Portuguese 224, Brazilian Portuguese 245; 212
    of them absent from all four catalogues (not merged since
    January), the rest empty entries. Preferences 109, export dialogs
    19, sounds 18, attachments view 15, CSV import 15, tray 11, help
    4 to 30; and 23 on the core screens, new since To Do 100 of
    [MASTER_SCHEDULER_REFACTOR.md](MASTER_SCHEDULER_REFACTOR.md#to-do):
    the file-in-use messages, "On days:" in the recurrence editor, the
    ID column's menu items, the spell checker's menu, the autosave
    failure message.
  - P63, the coverage tests: their template, `i18n.in/messages.pot`,
    is untracked and from 2026-01-14 (1,309 texts); the source has
    10,153 (8,712 icon labels and hints, the icon picker's search
    words). They divide a language's translated entries, old ones
    included, by the template's size, so enabled languages score 100
    to 125% and pass. As the share of today's screen texts, every
    enabled language is under the 90% they require: French 85.3%,
    Portuguese 84.5%, Brazilian Portuguese 83.0%, Spanish 82.9%, the
    19 others 65 to 75%. Proposed then: read the texts from the source
    (the strings given to `_()` and `i18n._()` in the syntax trees,
    the same 10,153 as xgettext), measure the share translated, leave
    the icon texts out, require every screen text in French, Spanish,
    Portuguese and Brazilian Portuguese once translated, and no share
    of the other languages.
- D21. The Flatpak's `--filesystem=home` dropped for the file-chooser
  portal, and the Flathub steps
  ([FLATPAK.md](FLATPAK.md#required-before-submission)), **deferred by
  designer 2026-10-06** ("if it's for the flat hub or anything like
  that, then we don't need to do it because flat hub is not accepting
  any new submissions"): only Flathub's review asks for them. Found
  then: wxPython 4.3.1 already shows the portal picker (wxWidgets
  3.3.1 `filedlg.cpp`: native chooser without preview or extra
  controls). Without home access a picked file is a document portal
  path: saving through a temporary file works, but `name.lock`
  becomes a hidden `.xdp-` file the host does not see, and dropped
  files and attachments outside the sandbox are out of reach. If
  revisited, on a machine with flatpak: open and save a task file
  outside home (a portal path even with home access, to confirm),
  its lock, and a change made from outside.
- D22. wxWidgets' own geometry saving (`SaveGeometry()`/
  `RestoreToGeometry()`), **closed for good by designer 2026-10-06**
  ("We won't be doing it anytime soon"), analysed 2026-09-27 and
  2026-10-06 ([WINDOW_GEOMETRY.md](WINDOW_GEOMETRY.md#wxwidgets-facilities),
  option D in its Placement Strategy):
  - the Linux packages' wxPython, 4.0.7 to 4.2.5, cannot use it (its
    `GeometrySerializer` cannot be subclassed), for years;
  - Windows and macOS already place directly before the first show,
    with years of use and no reports;
  - only the Flatpak has wxPython 4.3: a second Linux path, against
    one design for every platform;
  - wx does not check where the window landed and checks one corner
    against the monitors: the quiet-period checks and
    `fit_to_monitors()` stay ours;
  - the dialogs, not restored through it, need the first-show fix
    (`keep_placement_at_first_show()`) anyway.
- D23. Narrow panes and small windows, **ruled by designer 2026-10-06**
  (P96): "I don't want to work on it. The user can remove buttons from
  the toolbar and can remove columns as they wish ... we're not going
  to address smaller windows. There are many ways for the user to deal
  with that." So a toolbar wider than its pane hides what does not fit
  (wxPython's AUI toolbar: Search below 646 px with the default tools,
  the gear with it), and the icons' blank frames while a sash is
  dragged, stay as they are.
- D24. ~~Preferences' OK and Apply greyed until a change~~ (TODO.md
  10, GitHub #329): deferred by designer 2026-10-07, then done the
  same day, **ruled by designer** with P247: Apply greyed until a
  change, OK and Cancel always enabled, as Windows' property sheets
  ([PREFERENCES.md](PREFERENCES.md#ok-apply-and-cancel)).
