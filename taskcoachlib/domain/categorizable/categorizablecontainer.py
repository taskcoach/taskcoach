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
"""

from taskcoachlib.domain import base
from .categorizable import CategorizableCompositeObject


class CategorizableContainer(base.Collection):
    """Items with categories. Adding or removing one changes no
    membership: the item's categories are its own, and each category's
    index follows them (Category.member_joined)."""


def owner_chains(*collections):
    """Each note and attachment owned in a file's tasks, notes and
    categories -> its owners, from the top. They own them at any depth
    (a task's attachment's note), and an owned item does not know its
    owner."""
    chains = {}

    def walk(owner, chain):
        chain = chain + [owner]
        notes = owner.notes(recursive=True) if hasattr(owner, "notes") else []
        attachments = (
            owner.attachments() if hasattr(owner, "attachments") else []
        )
        for each in list(notes) + list(attachments):
            chains[each] = chain
            walk(each, chain)

    for collection in collections:
        for item in collection:
            walk(item, [])
    return chains


def categorizables_in(*collections):
    """Every item in a file's tasks, notes and categories that can have
    categories, owned ones included. A category's members may include
    items outside the file (a copy, a deleted item kept for undo); this
    says which are in."""
    items = [item for collection in collections for item in collection]
    return {
        each
        for each in items + list(owner_chains(*collections))
        if isinstance(each, CategorizableCompositeObject)
    }
