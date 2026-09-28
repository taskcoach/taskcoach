"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

File > Merge: a union of two task files, item by item
(docs/PERSISTENCE_XML.md, Merging).
"""

from taskcoachlib.domain import date
from taskcoachlib.domain.base import ModificationDateRecorder


def merge_into(task_file, other):
    """Merge the items of the task file other into task_file. An item
    in both keeps its newest copy; its subitems from both files end up
    together under it. The items taken from other leave it."""
    their_file_is_newer = _newest_date(other) > _newest_date(task_file)
    # Each item keeps the date of its winning copy: rebuilding links is
    # not an edit
    with ModificationDateRecorder() as recorder:
        for mine, theirs in (
            (task_file.categories(), other.categories()),
            (task_file.tasks(), other.tasks()),
            (task_file.notes(), other.notes()),
        ):
            _merge_collection(mine, theirs, their_file_is_newer)
        items = {item.id(): item for item in _walk(_roots(task_file))}
        _link_categories(task_file.categories(), items)
        _link_prerequisites(task_file.tasks(), items)
    for item, date_time in recorder.dates_before.items():
        item.set_modification_datetime(date_time)


def _theirs_wins(mine, theirs, their_file_is_newer):
    """The newer modification date wins. When a copy has none (a file
    from before the dates were kept), the file with the newest date
    wins; on a tie the open file keeps its copy."""
    unknown = date.DateTime.min
    mine_date = mine.modificationDateTime()
    their_date = theirs.modificationDateTime()
    if mine_date > unknown and their_date > unknown:
        return their_date > mine_date
    return their_file_is_newer


def _merge_collection(mine, theirs, their_file_is_newer):
    mine_by_id = {item.id(): item for item in mine}
    final = dict(mine_by_id)
    incoming, replaced = [], []
    for item in list(theirs):
        own = mine_by_id.get(item.id())
        if own is None or _theirs_wins(own, item, their_file_is_newer):
            final[item.id()] = item
            incoming.append(item)
            if own is not None:
                replaced.append(own)
    # Parents as the winning copies name them, before any link changes
    parents = {
        item_id: _parent_id(item) for item_id, item in final.items()
    }
    # Items compare equal by id, so the copies they replace must leave
    # the collection and their parents first
    mine.removeItems(replaced)
    for item in replaced:
        parent = item.parent()
        if parent is not None and _has_child(parent, item):
            parent.removeChild(item)
    for item in incoming:
        for child in list(item.children()):
            item.removeChild(child)
    for item_id, item in final.items():
        parent = final.get(parents[item_id])
        current = item.parent()
        if current is not parent:
            if current is not None and _has_child(current, item):
                current.removeChild(item)
            item.setParent(parent)
    mine.extend(
        [item for item in final.values() if not _contains(mine, item)]
    )


def _parent_id(item):
    parent = item.parent()
    return None if parent is None else parent.id()


def _has_child(parent, child):
    return any(each is child for each in parent.children())


def _contains(collection, item):
    return any(each is item for each in collection)


def _same_objects(current, wanted):
    return {id(each) for each in current} == {id(each) for each in wanted}


def _roots(task_file):
    return (
        task_file.categories().rootItems()
        + task_file.tasks().rootItems()
        + task_file.notes().rootItems()
    )


def _walk(items):
    """The items, their subitems, and the notes, attachments and
    efforts they own, recursively."""
    for item in items:
        yield item
        yield from _walk(getattr(item, "children", list)())
        yield from _walk(getattr(item, "notes", list)())
        yield from _walk(getattr(item, "attachments", list)())
        yield from _walk(getattr(item, "efforts", list)())


def _newest_date(task_file):
    return max(
        (item.modificationDateTime() for item in _walk(_roots(task_file))),
        default=date.DateTime.min,
    )


def _link_categories(categories, items):
    """Category membership as each winning category copy has it, to the
    winning copies of its members."""
    members = {}
    for each_category in categories:
        members[each_category] = {
            items[member.id()]
            for member in each_category.categorizables()
            if member.id() in items
        }
    categories_of = {}
    for each_category, categorizables in members.items():
        for categorizable in categorizables:
            categories_of.setdefault(id(categorizable), set()).add(
                each_category
            )
    # Only where a link changed or points to a replaced copy; emptied
    # first, as a set holding an equal copy (same id) is unchanged
    for item in items.values():
        wanted = categories_of.get(id(item), set())
        if hasattr(item, "setCategories") and not _same_objects(
            item.categories(), wanted
        ):
            item.setCategories(set())
            item.setCategories(wanted)
    for each_category, categorizables in members.items():
        if not _same_objects(each_category.categorizables(), categorizables):
            each_category.setCategorizables(set())
            each_category.setCategorizables(categorizables)


def _link_prerequisites(tasks, items):
    """Prerequisites as each winning task copy has them, to the winning
    copies; dependencies are their reverse."""
    prerequisites = {}
    for each_task in tasks:
        prerequisites[each_task] = {
            items[prerequisite.id()]
            for prerequisite in each_task.prerequisites()
            if prerequisite.id() in items
        }
    dependencies = {}
    for each_task, its_prerequisites in prerequisites.items():
        for prerequisite in its_prerequisites:
            dependencies.setdefault(id(prerequisite), set()).add(each_task)
    for each_task, its_prerequisites in prerequisites.items():
        # As categories
        if not _same_objects(each_task.prerequisites(), its_prerequisites):
            each_task.setPrerequisites(set())
            each_task.setPrerequisites(its_prerequisites)
        its_dependencies = dependencies.get(id(each_task), set())
        if not _same_objects(each_task.dependencies(), its_dependencies):
            each_task.setDependencies(set())
            each_task.setDependencies(its_dependencies)
