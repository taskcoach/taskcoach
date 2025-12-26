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
        for sortKey in self._sortKeys:
            self._registerObserverForAttribute(sortKey.lstrip("-"))
        self.reset()

    def thaw(self):
        super().thaw()
        if not self.isFrozen():
            self.reset()

    def detach(self):
        super().detach()
        for sortKey in self._sortKeys:
            self._removeObserverForAttribute(sortKey.lstrip("-"))

    @classmethod
    def sortEventType(cls):
        return "pubsub.%s.sorted" % cls.__name__

    @patterns.eventSource
    def extendSelf(self, items, event=None):
        super().extendSelf(items, event)
        self.reset()

    def isAscending(self):
        if self._sortKeys:
            return not self._sortKeys[0].startswith("-")
        return True

    def sortKeys(self):
        return self._sortKeys

    # We don't implement removeItemsFromSelf() because there is no need
    # to resort when items are removed since after removing items the
    # remaining items are still in the right order.

    def sortBy(self, sortKey):
        if self._sortKeys and self._sortKeys[0] == sortKey:
            if sortKey == "ordering":
                return
            self._sortKeys[0] = "-" + sortKey
        elif self._sortKeys and self._sortKeys[0] == "-" + sortKey:
            self._sortKeys[0] = sortKey
        elif self._sortKeys and sortKey in self._sortKeys:
            self._sortKeys.remove(sortKey)
            self._sortKeys.insert(0, sortKey)
        elif self._sortKeys and ("-" + sortKey) in self._sortKeys:
            self._sortKeys.remove("-" + sortKey)
            self._sortKeys.insert(0, sortKey)
        else:
            self._sortKeys.insert(0, sortKey)
            self._registerObserverForAttribute(sortKey)

        self.reset()

    def sortCaseSensitive(self, sortCaseSensitive):
        self._sortCaseSensitive = sortCaseSensitive
        self.reset()

    def sortAscending(self, ascending=True):
        if self._sortKeys:
            if (ascending and self._sortKeys[0].startswith("-")) or (
                not ascending and not self._sortKeys[0].startswith("-")
            ):
                self.sortBy(self._sortKeys[0].lstrip("-"))

    def reset(self, forceEvent=False):
        """reset does the actual sorting. If the order of the list changes,
        observers are notified by means of the list-sorted event."""
        if self.isFrozen():
            return

        oldSelf = self[:]
        # XXXTODO: create only one function with all keys ? Reversing may
        # be problematic.
        for sortKey in reversed(self._sortKeys):
            self.sort(
                key=self.createSortKeyFunction(sortKey.lstrip("-")),
                reverse=sortKey.startswith("-"),
            )
        if forceEvent or self != oldSelf:
            pub.sendMessage(self.sortEventType(), sender=self)

    def createSortKeyFunction(self, sortKey):
        """createSortKeyFunction returns a function that is passed to the
        builtin list.sort method to extract the sort key from each element
        in the list. We expect the domain object class to provide a
        <sortKey>SortFunction(sortCaseSensitive) method that returns the
        sortKeyFunction for the sortKey."""
        return self._getSortKeyFunction(sortKey)(
            sortCaseSensitive=self._sortCaseSensitive
        )

    def _getSortKeyFunction(self, sortKey):
        try:
            return getattr(self.DomainObjectClass, "%sSortFunction" % sortKey)
        except AttributeError:
            return self._getSortKeyFunction("subject")

    def _registerObserverForAttribute(self, attribute):
        for eventType in self._getSortEventTypes(attribute):
            if eventType.startswith("pubsub"):
                pub.subscribe(self.onAttributeChanged, eventType)
            else:
                patterns.Publisher().registerObserver(
                    self.onAttributeChanged_Deprecated, eventType=eventType
                )

    def _removeObserverForAttribute(self, attribute):
        for eventType in self._getSortEventTypes(attribute):
            if eventType.startswith("pubsub"):
                pub.unsubscribe(self.onAttributeChanged, eventType)
            else:
                patterns.Publisher().removeObserver(
                    self.onAttributeChanged_Deprecated, eventType=eventType
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

    def treeMode(self):
        return True

    def createSortKeyFunction(self, key):
        """createSortKeyFunction returns a function that is passed to the
        builtin list.sort method to extract the sort key from each element
        in the list. We expect the domain object class to provide a
        <sortKey>SortFunction(sortCaseSensitive, treeMode) method that
        returns the sortKeyFunction for the sortKey."""
        return self._getSortKeyFunction(key)(
            sortCaseSensitive=self._sortCaseSensitive, treeMode=self.treeMode()
        )

    def reset(self, *args, **kwargs):  # pylint: disable=W0221
        self.__invalidateRootItemCache()
        return super().reset(*args, **kwargs)

    @patterns.eventSource
    def extendSelf(self, items, event=None):
        self.__invalidateRootItemCache()
        return super().extendSelf(items, event=event)

    @patterns.eventSource
    def removeItemsFromSelf(self, itemsToRemove, event=None):
        self.__invalidateRootItemCache()
        # FIXME: Why is it necessary to remove all children explicitly?
        itemsToRemove = set(itemsToRemove)
        if self.treeMode():
            for item in itemsToRemove.copy():
                itemsToRemove.update(item.children(recursive=True))
        itemsToRemove = [item for item in itemsToRemove if item in self]
        return super().removeItemsFromSelf(itemsToRemove, event=event)

    def rootItems(self):
        """Return the root items, i.e. items without a parent."""
        if self.__rootItems is None:
            self.__rootItems = [item for item in self if item.parent() is None]
        return self.__rootItems

    def __invalidateRootItemCache(self):
        self.__rootItems = None
