# Categories

What an item's categories are, what subtasks inherit, and how
exclusive subcategories work with both.

## Table of Contents

1. [Own and Inherited Categories](#own-and-inherited-categories)
2. [Exclusive Subcategories](#exclusive-subcategories)
3. [Exclusive Subcategories and Subtasks](#exclusive-subcategories-and-subtasks)
4. [Code](#code)

---

## Own and Inherited Categories

An item's own categories are the ones it is given (Toggle category,
the editor's Categories tab, New task with selected categories,
imports); the file stores them. A subtask or subnote also counts in
its parent's categories, recursively (0.66.0, 2007):

- **Category filter:** an item shows when it, or an item it is under,
  is in a ticked category or one of its subcategories. Effort views
  follow their tasks ([EFFORTS.md](EFFORTS.md#filters)).
- **Categories column, list mode:** its own, then the inherited ones
  in parentheses (1.2.30, 2011); sorting by categories the same.
- **iCalendar export:** own and inherited.
- Own only: the editor's Categories tab, the Toggle category menu's
  ticks, and appearance (own categories, then the
  parent task: [TASK_STATUS.md](TASK_STATUS.md#appearance-inheritance)).

In tree mode a collapsed parent's Categories column adds its
subtasks' categories in parentheses; sorting by categories the same.

A subtask inherits its parent's categories even when its own holds
another subcategory of the same exclusive category: exclusivity holds
among an item's own categories (ruled 2026-10-05,
[below](#exclusive-subcategories-and-subtasks)).

## Exclusive Subcategories

"Mutually exclusive subcategories" (category editor, 0.77.0, 2009)
shows a category's subcategories as radio buttons. The help: "items
can only belong to one of the subcategories. When filtering, you can
only filter by one of the subcategories at a time." The release named
the uses: "create your own statuses or to keep track of which task was
assigned to whom".

- Giving an item one removes its other choice: the other
  subcategories with theirs, or the exclusive category itself; giving
  the exclusive category removes its subcategories. Only the item's
  own categories are checked
  (`ToggleCategoryCommand.unlink_previous_categories()`).
- Toggle category enables a subcategory of a choice only for items
  that have the choice (`ToggleCategory.enabled()`).
- Switching it unticks the subcategories in the filter; making them
  exclusive leaves items already in two of them as they are.
- The editor's Check all gives every category, both radio choices
  included (P238 in
  [REFINEMENT_REFACTOR.md](REFINEMENT_REFACTOR.md#found-2026-10-05)).

In the filter:

- Categories pane: ticking a choice unticks the other choices with
  their subcategories, and the parent category unless the parent is
  itself a choice; ticking a category unticks its choices
  (`CheckTreeCtrl.on_item_checked()`). Subcategories of a choice are
  greyed until the choice is ticked, so a nested choice needs its
  parent ticked too, which then shows the parent's other choices'
  items (P239).
- View > Filter > Categories ticks one category at a time with none of
  these rules (`ToggleCategoryFilter`): any choice, two of a group.

## Exclusive Subcategories and Subtasks

GitHub #126 (P201): A with exclusive A.1 and A.2, task T in A.1, its
subtask T.2 given A.2. T.2 shows when A.1 is ticked; the reporter
expected it in A.2 only.

Reproduced 2026-10-05, the same on master. Scratch file: A exclusive
with A.1 and A.2; T in A.1 with subtasks T.1 (no category) and T.2
(A.2); U (no category).

1. Tree mode, Categories column: T "A -> A.1", T.1 empty, T.2
   "A -> A.2".
2. List mode: T.1 "(A -> A.1)", T.2 "A -> A.2 (A -> A.1)".
3. Tick A.1 in the Categories pane: T, T.1 and T.2 show.
4. Tick A.2: T (as T.2's parent) and T.2.
5. Right-click T.1 > Toggle category > A: A.1 and A.2 both offered;
   A.2 gives it A.2 under T in A.1.
6. T.1's editor, Categories tab: A.2 ticked, A.1 free; nothing shows
   the parent's A.1.

Pinned today: `CategoryFilterTest` (a subtask counts in its parent's
ticked category), `CategorizableTest` (upward categories),
`ToggleMutualExclusiveCategories` (own categories only),
`UICommandTest` (the menu's check). None combines exclusive
subcategories with subtasks.

### Reports

Searched 2026-10-05. All reports of this case are from 2010:

- [SourceForge bug 640](https://sourceforge.net/p/taskcoach/bugs/640/),
  February 2010: the same case, with "Assigned to" Frank, Jérôme and
  Jose. Frank Niessink kept it: the parent assigned to whoever answers
  for the whole, each subtask to whoever does it, which the change
  asked for "would become impossible"; the subtask "itself still
  belongs to only one of the mutual exclusive subcategories". The
  reporter then asked only that the subtask's own be shown.
- [SourceForge bug 773](https://sourceforge.net/p/taskcoach/bugs/773/),
  September 2010: the case above. Frank Niessink: "I guess it is a
  bug that Task Coach allows you to assign a subtask to a category
  that is mutual exclusive with a category assigned to the parent
  task." A second user confirmed it on 1.1.3; "We could reproduce the
  bug"; not fixed. 2012, Aaron Wolf: "still a bug ... I don't know how
  it should be addressed".
- [GitHub #126](https://github.com/taskcoach/taskcoach/issues/126):
  bug 773 moved there 2026-01-04 ("nobody figured out what the
  resolution should be"); no comments since.

Nothing else on it in: GitHub issues, open and closed (searched
"exclusive", "mutually", "subcategor", subtask, parent and inherited
categories, the category filter); GitHub discussions (all 25 read);
SourceForge bugs, support requests, patches and forum ("exclusive",
"mutual"); Launchpad Answers ("exclusive", "subcategory") and
Ubuntu's taskcoach bugs; the Yahoo mailing list archive (narkive),
Google Groups, Reddit and the web. SourceForge's mailing list search
fails ("Error running search"): those archives were not searched.

Related, not this case:

- [SourceForge bug 1414](https://sourceforge.net/p/taskcoach/bugs/1414/),
  2013: nested exclusive subcategories (A.B and A.C exclusive, A.B.X,
  A.B.Y and A.B.Z exclusive under A.B). A.B.Y can be ticked only after
  A.B, and A.B then also shows A.B.X's tasks. Closed 2026-01-12
  without moving to GitHub; P239.
- [SourceForge bug 1256](https://sourceforge.net/p/taskcoach/bugs/1256/),
  2012: a new subtask is given none of its parent's categories. Aaron
  Wolf: by design, it counts in them (filter, appearance) without
  holding them, so moving it to another parent leaves none behind.
- [SourceForge bug 1009](https://sourceforge.net/p/taskcoach/bugs/1009/),
  2011: a subtask should take its parent's categories, to sort by them
  in list mode; 1.2.30 shows the inherited ones there (the
  parentheses).
- [SourceForge bug 1609](https://sourceforge.net/p/taskcoach/bugs/1609/),
  2015, a file shared by two people: one task listed under the filter
  "Matthias" with its own categories "Implementation, Mirko, RBI";
  another showing categories its editor did not tick. Not exclusive
  categories; the cause was never found.
- GitHub #181 (fixed in 2.0.1.27), #242 and #260: the category filter
  with subtasks and other filters, not exclusivity.

In use: GitHub discussion
[#251](https://github.com/taskcoach/taskcoach/discussions/251) (Aaron
Wolf) plans a category for assignment with a subcategory per person
in a shared household file, and wants to filter out the other's
items.

### Options

- **A. Keep as released.** A subtask counts in its parent's
  categories whatever its own. No code. T.2 stays listed under both;
  the help's "only one" holds for its own categories (bug 640).
- **B. Forbid** (the bug 773 reply): a subtask cannot get a subcategory
  excluding an ancestor's. Touches the menu, the editor's radio
  buttons, Check all, giving a parent a choice its subtasks
  contradict, drag and drop, paste, imports, merge, and files that
  already hold it (converting on load drops memberships). Ends the
  released uses: a project "In progress" with a subtask "Done", or
  assigned to one person with a subtask assigned to another.
- **C. The subtask's own choice wins.** A subtask that chose another
  subcategory of an exclusive category does not inherit its
  ancestors' there; its own subtasks inherit its choice. Changes,
  for such subtasks only: the filter, the list-mode column and sort,
  iCalendar export, effort views. Stored data is untouched.

### Prototype of C

In a scratch copy, not committed. `Category.excludes(other)`: under
different subcategories of an exclusive category. Inherited
categories (`Categorizable.categories(recursive=True, upwards=True)`)
and the filter's subtasks drop the ones the item's own exclude. The
filter also re-runs when a category excluding a ticked one is given
or taken, and when "mutually exclusive" is switched; the switch tells
the members' subitems that their inherited categories changed, as
giving a parent a category does.

- Lines: code +67 / -10 (category.py, categorizable.py, filter.py),
  tests +152 (CategoryTest, CategorizableTest, CategoryFilterTest in
  list and tree mode).
- Tests: the 13 new ones fail before and pass after; removing either
  re-run trigger fails its tests; the full suite passes (138 files).
- App check: in list mode T.2 shows "A -> A.2"; with A.1 ticked, T
  and T.1 show. Giving T.1 A.2 while A.1 is ticked removes it at
  once; ticking A.2 then shows T, T.1 and T.2. Unticking "mutually
  exclusive" brings back T.2's "(A -> A.1)" at once; ticking it
  removes it.
- Filter time, 4,500 tasks (300 projects in A.1, 900 subtasks in
  A.2): A.1 22 ms (3.8 ms before), A.2 5.5 to 6.8 ms (2.4 ms).
- Undo: revert the code; no file changes.

**Recommended: A** (revised 2026-10-05 on finding bug 640). The
author designed it so in 2010: a subtask's own categories hold one
choice, its parent's still count for it; reported only in 2010, the
team never changed it, and users filtering on an assignee or status
see a whole project today. C changes that for them. If wanted, C is
ready as an opt-in beside the released behaviour, as for the sort
([TASK_STATUS_SORT.md](TASK_STATUS_SORT.md#tree-mode)).

**Ruled by designer 2026-10-05: kept as released** ("A").

## Code

- `taskcoachlib/domain/categorizable/categorizable.py`:
  `categories(recursive, upwards)`, `categoriesSortFunction()`
- `taskcoachlib/domain/category/category.py`:
  `hasExclusiveSubcategories()`, `isMutualExclusive()`
- `taskcoachlib/domain/category/filter.py`: `CategoryFilter`
- `taskcoachlib/command/categorizableCommands.py`:
  `ToggleCategoryCommand`, `LinkCategoriesCommand`
- `taskcoachlib/gui/uicommand/uicommand.py`: `ToggleCategory`
- `taskcoachlib/gui/dialog/editor.py`: `LocalCategoryViewer`
