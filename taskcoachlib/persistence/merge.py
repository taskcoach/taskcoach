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
from taskcoachlib.domain.task import Task


def merge_into(task_file, other):
    """Merge the items of the task file other into task_file. An item
    in both keeps its newest copy; its subitems from both files end up
    together under it. The items taken from other leave it."""
    their_file_is_newer = _newest_date(other) > _newest_date(task_file)
    mine_owned, theirs_owned = _owned(task_file), _owned(other)
    # Before any change: removing a replaced copy from the file also
    # removes it from the links pointing to it
    links = _links(task_file)
    links.update(_links(other))
    # Each item keeps the date and data of its winning copy: rebuilding
    # links is not an edit, so the parent rules do not run
    with ModificationDateRecorder() as recorder, Task.rebuilding_links():
        for mine, theirs in (
            (task_file.categories(), other.categories()),
            (task_file.tasks(), other.tasks()),
            (task_file.notes(), other.notes()),
        ):
            _merge_collection(mine, theirs, their_file_is_newer)
        _merge_owned(task_file, mine_owned, theirs_owned, their_file_is_newer)
        items = {item.id(): item for item in _walk(_roots(task_file))}
        _link_categories(task_file.categories(), items, links)
        _link_prerequisites(task_file.tasks(), items, links)
    for item, date_time in recorder.dates_before.values():
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
    parents = {item_id: _parent_id(item) for item_id, item in final.items()}
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
    mine.extend([item for item in final.values() if not _contains(mine, item)])


_OWNED_KINDS = ("notes", "attachments", "efforts")


def _owned(task_file):
    """The items other items own (notes and their subnotes,
    attachments, efforts), by id: (item, owner id, parent id, kind)."""
    records = {}

    def visit(owner):
        for kind in _OWNED_KINDS:
            for root in getattr(owner, kind, list)():
                family = [root] + list(
                    getattr(root, "children", lambda **kwargs: [])(
                        recursive=True
                    )
                )
                for item in family:
                    parent_id = _parent_id(item) if item is not root else None
                    records[item.id()] = (item, owner.id(), parent_id, kind)
                    visit(item)

    for collection in (
        task_file.categories(),
        task_file.tasks(),
        task_file.notes(),
    ):
        for item in collection:
            visit(item)
    return records


def _merge_owned(task_file, mine, theirs, their_file_is_newer):
    """Owned items item by item: each goes to the owner (and parent)
    its winning copy names."""
    winners = dict(mine)
    for item_id, record in theirs.items():
        own = mine.get(item_id)
        if own is None or _theirs_wins(own[0], record[0], their_file_is_newer):
            winners[item_id] = record
    owners = {item.id(): item for item in _walk(_roots(task_file))}
    owners.update((item_id, record[0]) for item_id, record in winners.items())
    wanted = {}
    for item, owner_id, parent_id, kind in winners.values():
        key = (parent_id, "children") if parent_id else (owner_id, kind)
        wanted.setdefault(key, []).append(item)
    for (owner_id, kind), items in wanted.items():
        if kind != "children" and owner_id in owners:
            _set_owned(owners[owner_id], kind, items)
    for owner_id, owner in owners.items():
        for kind in _OWNED_KINDS:
            if hasattr(owner, kind) and (owner_id, kind) not in wanted:
                _set_owned(owner, kind, [])
    for item_id, record in winners.items():
        if record[3] == "notes":
            _set_children(record[0], wanted.get((item_id, "children"), []))


def _identities(items):
    return [id(each) for each in items]


def _set_owned(owner, kind, items):
    current = getattr(owner, kind)()
    if _identities(current) == _identities(items):
        return
    if kind == "efforts":
        for effort in current:
            if not any(effort is each for each in items):
                owner.removeEffort(effort)
        for effort in items:
            if effort.task() is not owner:
                effort.setTask(owner)
            elif not any(effort is each for each in owner.efforts()):
                owner.addEffort(effort)
        return
    # Emptied first: a list holding equal copies (same ids) is unchanged
    setter = getattr(owner, "set" + kind.capitalize())
    setter([])
    setter(items)


def _set_children(item, children):
    if _identities(item.children()) == _identities(children):
        return
    for child in list(item.children()):
        item.removeChild(child)
    for child in children:
        item.addChild(child)


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


def _links(task_file):
    """The ids of each item's categories and prerequisites, by
    identity."""
    links = {}
    for item in _walk(_roots(task_file)):
        categories = getattr(item, "categories", None)
        prerequisites = getattr(item, "prerequisites", None)
        links[id(item)] = (
            {each.id() for each in categories()} if categories else set(),
            (
                {each.id() for each in prerequisites()}
                if prerequisites
                else set()
            ),
        )
    return links


def _link_categories(categories, items, links):
    """Category membership as each winning task or note copy has it:
    they own their categories, and a category's members are the
    reverse (docs/ATTRIBUTE_PATTERN.md, Modification Date)."""
    categories_of = {}
    for item in items.values():
        if hasattr(item, "setCategories"):
            category_ids = links.get(id(item), (set(), set()))[0]
            categories_of[id(item)] = (
                item,
                {items[each] for each in category_ids if each in items},
            )
    members = {id(each): set() for each in categories}
    for item, its_categories in categories_of.values():
        for each in its_categories:
            members.setdefault(id(each), set()).add(item)
    # Only where a link changed or points to a replaced copy; emptied
    # first, as a set holding an equal copy (same id) is unchanged
    for item, its_categories in categories_of.values():
        if not _same_objects(item.categories(), its_categories):
            item.setCategories(set())
            item.setCategories(its_categories)
    for each in categories:
        wanted = members.get(id(each), set())
        if not _same_objects(each.categorizables(), wanted):
            each.setCategorizables(set())
            each.setCategorizables(wanted)


def _link_prerequisites(tasks, items, links):
    """Prerequisites as each winning task copy has them, to the winning
    copies; dependencies are their reverse."""
    prerequisites = {}
    for each_task in tasks:
        prerequisite_ids = links.get(id(each_task), (set(), set()))[1]
        prerequisites[each_task] = {
            items[each] for each in prerequisite_ids if each in items
        }
    dependencies = {}
    for each_task, its_prerequisites in prerequisites.items():
        for prerequisite in its_prerequisites:
            dependencies.setdefault(id(prerequisite), set()).add(each_task)
    for each_task, its_prerequisites in prerequisites.items():
        # As categories
        if not _same_objects(each_task.prerequisites(), its_prerequisites):
            each_task.set_prerequisites(set())
            each_task.set_prerequisites(its_prerequisites)
        its_dependencies = dependencies.get(id(each_task), set())
        if not _same_objects(each_task.dependencies(), its_dependencies):
            each_task.set_dependencies(set())
            each_task.set_dependencies(its_dependencies)
