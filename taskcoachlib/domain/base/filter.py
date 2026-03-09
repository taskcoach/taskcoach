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

import re
import sre_constants
from taskcoachlib import patterns
from taskcoachlib.domain.base import object as domainobject


class Filter(patterns.SetDecorator):
    """Base class for filters that can operate in tree or list mode.

    In tree mode, when an item matches the filter criteria, its ancestors are
    automatically included to maintain the tree hierarchy. These ancestor items
    are tracked as "filter_forced" - they were added to preserve structure, not
    because they matched the filter criteria themselves.

    This tracking is important for filter chains (e.g., CategoryFilter -> ViewFilter).
    When an outer filter removes items, it can use getAccumulatedFilterForced() to
    identify ancestors that may have become orphans (no visible children) and should
    also be removed. See ViewFilter.reset() for the cleanup implementation.
    """

    def __init__(self, *args, **kwargs):
        self.__tree_mode = kwargs.pop("tree_mode", False)
        # Track items added as ancestors to maintain tree hierarchy, not because
        # they matched filter criteria. Used by outer filters for orphan cleanup.
        self.__filterForced = set()
        super().__init__(*args, **kwargs)
        self.reset()

    def thaw(self):
        super().thaw()
        if not self.isFrozen():
            self.reset()

    def set_tree_mode(self, tree_mode):
        self.__tree_mode = tree_mode
        observable = self.observable()
        if isinstance(observable, Filter):
            observable.set_tree_mode(tree_mode)
        elif not isinstance(observable, patterns.ObservableCollection):
            from taskcoachlib.meta.debug import log_step
            log_step("set_tree_mode: unexpected observable type %s"
                     % type(observable).__name__, prefix="FILTER")
        self.reset()

    def tree_mode(self):
        return self.__tree_mode

    @classmethod
    def filter_change_event_type(cls):
        return "filter.change"

    @patterns.eventSource
    def reset(self, event=None):
        """Recompute the filtered set based on current filter criteria.

        In tree mode, ancestors of matching items are included to maintain
        hierarchy. These ancestors are tracked in __filterForced so that
        outer filters can identify and remove them if they become orphans
        (i.e., all their matching descendants are later filtered out).
        """
        if self.isFrozen():
            return

        # Get items that directly match this filter's criteria
        direct_matches = set(self.filter_items(self.observable()))
        filtered_items = direct_matches.copy()

        # Reset and rebuild filter_forced tracking
        self.__filterForced = set()
        if self.tree_mode():
            # In tree mode, include ancestors of matching items to maintain
            # tree structure. Track these as "filter_forced" since they don't
            # match criteria themselves - they're only included for hierarchy.
            for item in direct_matches:
                for ancestor in item.ancestors():
                    if ancestor not in direct_matches:
                        self.__filterForced.add(ancestor)
                        filtered_items.add(ancestor)

        self.removeItemsFromSelf(
            [item for item in self if item not in filtered_items], event=event
        )
        self.extendSelf(
            [item for item in filtered_items if item not in self], event=event
        )
        patterns.Event(self.filter_change_event_type(), self).send()

    def getFilterForced(self):
        """Return items that were added as ancestors, not directly matched.

        These items are in the filter only to maintain tree hierarchy, not
        because they passed the filter criteria.
        """
        return self.__filterForced.copy()

    def getAccumulatedFilterForced(self):
        """Return filter_forced items accumulated from the entire filter chain.

        Walks up the filter chain (via observable()) to collect all items that
        were added as ancestors by any filter in the chain. This is used by
        the outermost filter (typically ViewFilter) to identify items that may
        need cleanup if they've become orphans.

        Example: CategoryFilter adds a parent as ancestor of a categorized child.
        ViewFilter later hides the child (completed). ViewFilter uses this method
        to find that the parent was filter_forced, and removes it since it has
        no visible children.
        """
        accumulated = self.__filterForced.copy()
        try:
            inner = self.observable()
            if hasattr(inner, 'getAccumulatedFilterForced'):
                accumulated |= inner.getAccumulatedFilterForced()
        except AttributeError:
            from taskcoachlib.meta.debug import log_step
            log_step("getAccumulatedFilterForced: AttributeError on observable",
                     prefix="FILTER")
        return accumulated

    def filter_items(self, items):
        """filter returns the items that pass the filter."""
        raise NotImplementedError  # pragma: no cover

    def rootItems(self):
        return [item for item in self if item.parent() is None]

    def onAddItem(self, event):
        self.reset()

    def onRemoveItem(self, event):
        self.reset()


class SelectedItemsFilter(Filter):
    def __init__(self, *args, **kwargs):
        self.__selectedItems = set(kwargs.pop("selectedItems", []))
        self.__includeSubItems = kwargs.pop("includeSubItems", True)
        super().__init__(*args, **kwargs)

    @patterns.eventSource
    def removeItemsFromSelf(self, items, event=None):
        super().removeItemsFromSelf(items, event)
        self.__selectedItems.difference_update(set(items))
        if not self.__selectedItems:
            self.extendSelf(self.observable(), event)

    def filter_items(self, items):
        if self.__selectedItems:
            result = [
                item
                for item in items
                if self.itemOrAncestorInSelectedItems(item)
            ]
            if self.__includeSubItems:
                for item in result[:]:
                    result.extend(item.children(recursive=True))
            return result
        else:
            return [item for item in items if item not in self]

    def itemOrAncestorInSelectedItems(self, item):
        if item in self.__selectedItems:
            return True
        elif item.parent():
            return self.itemOrAncestorInSelectedItems(item.parent())
        else:
            return False


class SearchFilter(Filter):
    def __init__(self, *args, **kwargs):
        searchString = kwargs.pop("searchString", "")
        matchCase = kwargs.pop("matchCase", False)
        includeSubItems = kwargs.pop("includeSubItems", False)
        searchDescription = kwargs.pop("searchDescription", False)
        regularExpression = kwargs.pop("regularExpression", False)

        self.setSearchFilter(
            searchString,
            matchCase=matchCase,
            includeSubItems=includeSubItems,
            searchDescription=searchDescription,
            regularExpression=regularExpression,
            doReset=False,
        )

        super().__init__(*args, **kwargs)

    def setSearchFilter(
        self,
        searchString,
        matchCase=False,
        includeSubItems=False,
        searchDescription=False,
        regularExpression=False,
        doReset=True,
    ):
        # pylint: disable=W0201
        self.__includeSubItems = includeSubItems
        self.__searchDescription = searchDescription
        self.__regularExpression = regularExpression
        self.__searchPredicate = self.__compileSearchPredicate(
            searchString, matchCase, regularExpression
        )
        if doReset:
            self.reset()

    @staticmethod
    def __compileSearchPredicate(searchString, matchCase, regularExpression):
        if not searchString:
            return ""
        flag = 0 if matchCase else re.IGNORECASE | re.UNICODE
        if regularExpression:
            try:
                rx = re.compile(searchString, flag)
            except sre_constants.error:
                if matchCase:
                    return lambda x: x.find(searchString) != -1
                else:
                    return lambda x: x.lower().find(searchString.lower()) != -1
            else:
                return rx.search
        elif matchCase:
            return lambda x: x.find(searchString) != -1
        else:
            return lambda x: x.lower().find(searchString.lower()) != -1

    def filter_items(self, items):
        return (
            [
                item
                for item in items
                if self.__searchPredicate(self.__itemText(item))
            ]
            if self.__searchPredicate
            else items
        )

    def __itemText(self, item):
        text = self.__itemOwnText(item)
        if self.__includeSubItems:
            parent = item.parent()
            while parent:
                text += self.__itemOwnText(parent)
                parent = parent.parent()
        if self.tree_mode():
            text += " ".join(
                [
                    self.__itemOwnText(child)
                    for child in item.children(recursive=True)
                    if child in self.observable()
                ]
            )
        return text

    def __itemOwnText(self, item):
        text = item.subject()
        if self.__searchDescription:
            text += item.description()
        return text


class DeletedFilter(Filter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for eventType in [
            domainobject.Object.markDeletedEventType(),
            domainobject.Object.markNotDeletedEventType(),
        ]:
            patterns.Publisher().registerObserver(
                self.onObjectMarkedDeletedOrNot, eventType=eventType
            )

    def detach(self):
        patterns.Publisher().removeObserver(self.onObjectMarkedDeletedOrNot)
        super().detach()

    def onObjectMarkedDeletedOrNot(self, event):  # pylint: disable=W0613
        self.reset()

    def filter_items(self, items):
        return [item for item in items if not item.isDeleted()]
