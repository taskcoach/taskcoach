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

from taskcoachlib import patterns
from pubsub import pub


class Sorter(patterns.ListDecorator):
    """This class decorates a list and sorts its contents."""

    def __init__(self, *args, **kwargs):
        self._sortKeys = kwargs.pop("sortBy", ["subject"])
        self._sortCaseSensitive = kwargs.pop("sortCaseSensitive", True)
        super().__init__(*args, **kwargs)
        for sort_key in self._sortKeys:
            self._registerObserverForAttribute(sort_key.lstrip("-"))
        self.reset()

    def thaw(self):
        super().thaw()
        if not self.isFrozen():
            self.reset()

    def detach(self):
        super().detach()
        for sort_key in self._sortKeys:
            self._removeObserverForAttribute(sort_key.lstrip("-"))

    @classmethod
    def sort_event_type(cls):
        return "pubsub.%s.sorted" % cls.__name__

    @patterns.eventSource
    def extendSelf(self, items, event=None):
        super().extendSelf(items, event)
        self.reset()

    def is_ascending(self):
        if self._sortKeys:
            return not self._sortKeys[0].startswith("-")
        return True

    def sort_keys(self):
        return self._sortKeys

    # We don't implement removeItemsFromSelf() because there is no need
    # to resort when items are removed since after removing items the
    # remaining items are still in the right order.

    def sort_by(self, sort_key):
        if self._sortKeys and self._sortKeys[0] == sort_key:
            if sort_key == "ordering":
                return
            self._sortKeys[0] = "-" + sort_key
        elif self._sortKeys and self._sortKeys[0] == "-" + sort_key:
            self._sortKeys[0] = sort_key
        elif self._sortKeys and sort_key in self._sortKeys:
            self._sortKeys.remove(sort_key)
            self._sortKeys.insert(0, sort_key)
        elif self._sortKeys and ("-" + sort_key) in self._sortKeys:
            self._sortKeys.remove("-" + sort_key)
            self._sortKeys.insert(0, sort_key)
        else:
            self._sortKeys.insert(0, sort_key)
            self._registerObserverForAttribute(sort_key)

        self.reset()

    def sort_case_sensitive(self, sort_case_sensitive):
        self._sortCaseSensitive = sort_case_sensitive
        self.reset()

    def sort_ascending(self, ascending=True):
        if self._sortKeys:
            if (ascending and self._sortKeys[0].startswith("-")) or (
                not ascending and not self._sortKeys[0].startswith("-")
            ):
                self.sort_by(self._sortKeys[0].lstrip("-"))

    def reset(self, force_event=False):
        """reset does the actual sorting. If the order of the list changes,
        observers are notified by means of the list-sorted event."""
        if self.isFrozen():
            return

        old_self = self[:]
        # XXXTODO: create only one function with all keys ? Reversing may
        # be problematic.
        # UUID tiebreaker first (least significant) - guarantees
        # deterministic ordering for items with equal sort keys.
        self.sort(key=lambda item: item.id())
        for sort_key in reversed(self._sortKeys):
            self.sort(
                key=self.create_sort_key_function(sort_key.lstrip("-")),
                reverse=sort_key.startswith("-"),
            )
        if force_event or self != old_self:
            pub.sendMessage(self.sort_event_type(), sender=self)

    def create_sort_key_function(self, sort_key):
        """create_sort_key_function returns a function that is passed to the
        builtin list.sort method to extract the sort key from each element
        in the list. We expect the domain object class to provide a
        <sortKey>SortFunction(sortCaseSensitive) method that returns the
        sortKeyFunction for the sortKey."""
        return self._getSortKeyFunction(sort_key)(
            sortCaseSensitive=self._sortCaseSensitive
        )

    def _getSortKeyFunction(self, sort_key):
        try:
            return getattr(self.DomainObjectClass,
                           "%sSortFunction" % sort_key)
        except AttributeError:
            from taskcoachlib.meta.debug import log_step
            log_step('%sSortFunction not found on %s - falling back '
                     'to subject'
                     % (sort_key, self.DomainObjectClass.__name__),
                     prefix='SORTER')
            return self._getSortKeyFunction("subject")

    def _registerObserverForAttribute(self, attribute):
        for event_type in self._getSortEventTypes(attribute):
            if event_type.startswith("pubsub"):
                pub.subscribe(self.onAttributeChanged, event_type)
            else:
                patterns.Publisher().registerObserver(
                    self.onAttributeChanged_Deprecated,
                    eventType=event_type,
                )

    def _removeObserverForAttribute(self, attribute):
        for event_type in self._getSortEventTypes(attribute):
            if event_type.startswith("pubsub"):
                pub.unsubscribe(self.onAttributeChanged, event_type)
            else:
                patterns.Publisher().removeObserver(
                    self.onAttributeChanged_Deprecated,
                    eventType=event_type,
                )

    def onAttributeChanged(self, newValue, sender):  # pylint: disable=W0613
        self.reset()

    def onAttributeChanged_Deprecated(self, event):  # pylint: disable=W0613
        self.reset()

    def _getSortEventTypes(self, attribute):
        try:
            return getattr(
                self.DomainObjectClass, "%sSortEventTypes" % attribute
            )()
        except AttributeError:
            return []


class TreeSorter(Sorter):
    def __init__(self, *args, **kwargs):
        self.__rootItems = None  # Cached root items
        super().__init__(*args, **kwargs)

    def tree_mode(self):
        return True

    def create_sort_key_function(self, key):
        """create_sort_key_function returns a function that is passed to the
        builtin list.sort method to extract the sort key from each element
        in the list. We expect the domain object class to provide a
        <sortKey>SortFunction(sortCaseSensitive, tree_mode) method that
        returns the sortKeyFunction for the sortKey."""
        return self._getSortKeyFunction(key)(
            sortCaseSensitive=self._sortCaseSensitive, tree_mode=self.tree_mode()
        )

    def reset(self, *args, **kwargs):  # pylint: disable=W0221
        self.__invalidateRootItemCache()
        return super().reset(*args, **kwargs)

    @patterns.eventSource
    def extendSelf(self, items, event=None):
        self.__invalidateRootItemCache()
        return super().extendSelf(items, event=event)

    @patterns.eventSource
    def removeItemsFromSelf(self, items_to_remove, event=None):
        self.__invalidateRootItemCache()
        # FIXME: Why is it necessary to remove all children explicitly?
        items_to_remove = set(items_to_remove)
        if self.tree_mode():
            for item in items_to_remove.copy():
                items_to_remove.update(item.children(recursive=True))
        items_to_remove = [item for item in items_to_remove if item in self]
        return super().removeItemsFromSelf(items_to_remove, event=event)

    def rootItems(self):
        """Return the root items, i.e. items without a parent."""
        if self.__rootItems is None:
            self.__rootItems = [item for item in self if item.parent() is None]
        return self.__rootItems

    def __invalidateRootItemCache(self):
        self.__rootItems = None
