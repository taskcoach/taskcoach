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

from . import singleton
import functools
from pubsub import pub

# Ignore these pylint messages:
# - W0142: * or ** magic
# - W0622: Redefining builtin types
# pylint: disable=W0142,W0622


class List(list):
    def __eq__(self, other):
        """Subclasses of List are always considered to be unequal, even when
        their contents are the same. This is because List subclasses are
        used as Collections of domain objects. When compared to other types,
        the contents are compared."""
        if isinstance(other, List):
            return self is other
        else:
            return list(self) == other

    def removeItems(self, items):
        """List.removeItems is the opposite of list.extend. Useful for
        ObservableList to be able to generate just one notification
        when removing multiple items."""
        for item in items:
            # No super() to prevent overridden remove method from being invoked
            list.remove(self, item)


class Set(set):
    """The builtin set type does not like keyword arguments, so to keep
    it happy we don't pass these on."""

    def __new__(class_, iterable=None, *args, **kwargs):
        return set.__new__(class_, iterable)


class Event(object):
    """Event represents notification events. Events can notify about a single
    event type for a single source or for multiple event types and multiple
    sources at the same time. The Event methods try to make both uses easy.

    This creates an event for one type, one source and one value
    >>> event = Event('event type', 'event source', 'new value')

    To add more event sources with their own value:
    >>> event.addSource('another source', 'another value')

    To add a source with a different event type:
    >>> event.addSource('yet another source', 'its value', type='another type')
    """

    def __init__(self, type=None, source=None, *values):
        self.__sourcesAndValuesByType = (
            {}
            if type is None
            else {type: {} if source is None else {source: values}}
        )

    def __repr__(self):  # pragma: no cover
        return "Event(%s)" % (self.__sourcesAndValuesByType)

    def __eq__(self, other):
        """Events compare equal when all their data is equal."""
        return self.sourcesAndValuesByType() == other.sourcesAndValuesByType()

    def addSource(self, source, *values, **kwargs):
        """Add a source with optional values to the event. Optionally specify
        the type as keyword argument. If no type is specified, the source
        and values are added for a random type, i.e. only omit the type if
        the event has only one type."""
        eventType = kwargs.pop("type", self.type())
        currentValues = set(
            self.__sourcesAndValuesByType.setdefault(eventType, {}).setdefault(
                source, tuple()
            )
        )
        currentValues |= set(values)
        self.__sourcesAndValuesByType.setdefault(eventType, {})[source] = (
            tuple(currentValues)
        )

    def type(self):
        """Return the event type. If there are multiple event types, this
        method returns an arbitrary event type. This method is useful if
        the caller is sure this event instance has exactly one event
        type."""
        return list(self.types())[0] if self.types() else None

    def types(self):
        """Return the set of event types that this event is notifying."""
        return set(self.__sourcesAndValuesByType.keys())

    def sources(self, *types):
        """Return the set of all sources of this event instance, or the
        sources for specific event types."""
        types = types or self.types()
        sources = set()
        for type in types:
            sources |= set(
                self.__sourcesAndValuesByType.get(type, dict()).keys()
            )
        return sources

    def sourcesAndValuesByType(self):
        """Return all data {type: {source: values}}."""
        return self.__sourcesAndValuesByType

    def value(self, source=None, type=None):
        """Return the value that belongs to source. If there are multiple
        values, this method returns only the first one. So this method is
        useful if the caller is sure there is only one value associated
        with source. If source is None return the value of an arbitrary
        source. This latter option is useful if the caller is sure there
        is only one source."""
        return self.values(source, type)[0]

    def values(self, source=None, type=None):
        """Return the values that belong to source. If source is None return
        the values of an arbitrary source. This latter option is useful if
        the caller is sure there is only one source."""
        type = type or self.type()
        source = source or list(self.__sourcesAndValuesByType[type].keys())[0]
        return self.__sourcesAndValuesByType.get(type, {}).get(source, [])

    def subEvent(self, *typesAndSources):
        """Create a new event that contains a subset of the data of this
        event."""
        subEvent = self.__class__()
        for type, source in typesAndSources:
            sourcesToAdd = self.sources(type)
            if source is not None:
                # Make sure source is actually in self.sources(type):
                sourcesToAdd &= set([source])
            kwargs = dict(
                type=type
            )  # Python doesn't allow type=type after *values
            for eachSource in sourcesToAdd:
                subEvent.addSource(
                    eachSource, *self.values(eachSource, type), **kwargs
                )  # pylint: disable=W0142
        return subEvent

    def send(self):
        """Send this event to observers of the type(s) of this event."""
        Publisher().notifyObservers(self)


def eventSource(f):
    """Decorate methods that send events with code to optionally create the
    event and optionally send it. This allows for sending just one event
    for chains of multiple methods that each need to send an event."""

    @functools.wraps(f)
    def decorator(*args, **kwargs):
        event = kwargs.pop("event", None)
        notify = event is None  # We only notify if we're the event creator
        kwargs["event"] = event = event if event else Event()
        result = f(*args, **kwargs)
        if notify:
            event.send()
        return result

    return decorator


class MethodProxy(object):
    """Wrap methods in a class that allows for comparing methods. Comparison
    if instance methods was changed in python 2.5. In python 2.5, instance
    methods are equal when their instances compare equal, which is not
    the behaviour we need for callbacks. So we wrap callbacks in this class
    to get back the old (correct, imho) behaviour."""

    def __init__(self, method):
        self.method = method

    def __repr__(self):
        return "MethodProxy(%s)" % self.method  # pragma: no cover

    def __call__(self, *args, **kwargs):
        return self.method(*args, **kwargs)

    def __eq__(self, other):
        return (
            self.method.__self__.__class__ is other.method.__self__.__class__
            and self.method.__self__ is other.method.__self__
            and self.method.__func__ is other.method.__func__
        )

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        # Can't use self.method.__self__ for the hash, it might be mutable
        return hash(
            (
                self.method.__self__.__class__,
                id(self.method.__self__),
                self.method.__func__,
            )
        )

    def get_im_self(self):
        return self.method.__self__

    im_self = property(get_im_self)
    __self__ = im_self


def wrapObserver(decoratedMethod):
    """Wrap the observer argument (assumed to be the first after self) in
    a MethodProxy class."""

    def decorator(self, observer, *args, **kwargs):
        assert hasattr(observer, "__self__")
        observer = MethodProxy(observer)
        return decoratedMethod(self, observer, *args, **kwargs)

    return decorator


def unwrapObservers(decoratedMethod):
    """Unwrap the returned observers from their MethodProxy class."""

    def decorator(*args, **kwargs):
        observers = decoratedMethod(*args, **kwargs)
        return [proxy.method for proxy in observers]

    return decorator


class Publisher(object, metaclass=singleton.Singleton):
    """Publisher is used to register for event notifications. It supports
    the publisher/subscribe pattern, also known as the observer pattern.
    Objects (Observers) interested in change notifications register a
    callback method via Publisher.registerObserver. The callback should
    expect one argument; an instance of the Event class. Observers can
    register their interest in specific event types (topics), and
    optionally specific event sources, when registering.

    Implementation note:
    - Publisher is a Singleton class since all observables and all
    observers have to use exactly one registry to be sure that all
    observables can reach all observers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clear()

    def clear(self):
        """Clear the registry of observers. Mainly for testing purposes."""
        # observers = {(eventType, eventSource): set(callbacks)}
        self.__observers = {}  # pylint: disable=W0201

    @wrapObserver
    def registerObserver(self, observer, eventType, eventSource=None):
        """Register an observer for an event type. The observer is a callback
        method that should expect one argument, an instance of Event.
        The eventType can be anything hashable, typically a string. When
        passing a specific eventSource, the observer is only called when the
        event originates from the specified eventSource."""

        observers = self.__observers.setdefault(
            (eventType, eventSource), set()
        )
        observers.add(observer)

    @wrapObserver
    def removeObserver(self, observer, eventType=None, eventSource=None):
        """Remove an observer. If no event type is specified, the observer
        is removed for all event types. If an event type is specified
        the observer is removed for that event type only. If no event
        source is specified, the observer is removed for all event sources.
        If an event source is specified, the observer is removed for that
        event source only. If both an event type and an event source are
        specified, the observer is removed for the combination of that
        specific event type and event source only."""

        # pylint: disable=W0613

        # First, create a match function that will select the combination of
        # event source and event type we're looking for:

        if eventType and eventSource:

            def match(type, source):
                return type == eventType and source == eventSource

        elif eventType:

            def match(type, source):
                return type == eventType

        elif eventSource:

            def match(type, source):
                return source == eventSource

        else:

            def match(type, source):
                return True

        # Next, remove observers that are registered for the event source and
        # event type we're looking for, i.e. that match:
        matchingKeys = [key for key in self.__observers if match(*key)]
        for key in matchingKeys:
            self.__observers[key].discard(observer)
            if not self.__observers[key]:
                del self.__observers[key]

    def notifyObservers(self, event):
        """Notify observers of the event. The event type and sources are
        extracted from the event."""
        if not event.sources():
            return
        # Collect observers *and* the types and sources they are registered for
        observers = dict()  # {observer: set([(type, source), ...])}
        types = event.types()
        # Include observers not registered for a specific event source:
        sources = event.sources() | set([None])
        eventTypesAndSources = [
            (type, source) for source in sources for type in types
        ]
        for eventTypeAndSource in eventTypesAndSources:
            for observer in self.__observers.get(eventTypeAndSource, set()):
                observers.setdefault(observer, set()).add(eventTypeAndSource)
        import wx
        if wx.GetApp() and wx.GetApp().quitting:
            return
        for observer, eventTypesAndSources in observers.items():
            subEvent = event.subEvent(*eventTypesAndSources)
            if subEvent.types():
                try:
                    observer(subEvent)
                except RuntimeError:
                    from taskcoachlib.meta.debug import log_step
                    log_step("Observer RuntimeError: %s on %s" % (
                        observer, subEvent.types()), prefix="OBSERVER")

    @unwrapObservers
    def observers(self, eventType=None):
        """Get the currently registered observers. Optionally specify
        a specific event type to get observers for that event type only."""
        if eventType:
            return self.__observers.get((eventType, None), set())
        else:
            result = set()
            for observers in list(self.__observers.values()):
                result |= observers
            return result


class Observer(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__observers = set()

    def registerObserver(self, observer, *args, **kwargs):
        self.__observers.add(observer)
        Publisher().registerObserver(observer, *args, **kwargs)

    def removeObserver(self, observer, *args, **kwargs):
        self.__observers.discard(observer)
        Publisher().removeObserver(observer, *args, **kwargs)

    def removeInstance(self):
        for observer in self.__observers.copy():
            self.removeObserver(observer)
        pub.unsubAll(
            listenerFilter=lambda listener: hasattr(
                listener.getCallable(), "__self__"
            )
            and listener.getCallable().__self__ is self
        )


class Decorator(Observer):
    def __init__(self, observable, *args, **kwargs):
        self.__observable = observable
        super().__init__(*args, **kwargs)

    def observable(self, recursive=False):
        if recursive:
            try:
                return self.__observable.observable(recursive=True)
            except AttributeError:
                pass
        return self.__observable

    def __getattr__(self, attribute):
        return getattr(self.observable(), attribute)


class ObservableCollection(object):
    def __hash__(self):
        """Make ObservableCollections suitable as keys in dictionaries."""
        return hash(id(self))

    def detach(self):
        """Break cycles"""

    @classmethod
    def addItemEventType(class_):
        """The event type used to notify observers that one or more items
        have been added to the collection."""
        return "%s.add" % class_

    @classmethod
    def removeItemEventType(class_):
        """The event type used to notify observers that one or more items
        have been removed from the collection."""
        return "%s.remove" % class_

    @classmethod
    def modificationEventTypes(class_):
        try:
            eventTypes = super(
                ObservableCollection, class_
            ).modificationEventTypes()
        except AttributeError:
            eventTypes = []
        return eventTypes + [
            class_.addItemEventType(),
            class_.removeItemEventType(),
        ]


class ObservableSet(ObservableCollection, Set):
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            result = self is other
        else:
            result = set(self) == set(other)
        return result

    # FIXME: Only for satisfying registerObserver()
    def __hash__(self):
        return hash(id(self))

    @eventSource
    def append(self, item, event=None):
        self.add(item)
        event.addSource(self, item, type=self.addItemEventType())

    @eventSource
    def extend(self, items, event=None):
        if not items:
            return
        self.update(items)
        event.addSource(self, *items, **dict(type=self.addItemEventType()))

    @eventSource
    def remove(self, item, event=None):
        super().remove(item)
        event.addSource(self, item, type=self.removeItemEventType())

    @eventSource
    def removeItems(self, items, event=None):
        if not items:
            return
        self.difference_update(items)
        event.addSource(self, *items, **dict(type=self.removeItemEventType()))

    @eventSource
    def clear(self, event=None):
        if not self:
            return
        items = tuple(self)
        super().clear()
        event.addSource(self, *items, **dict(type=self.removeItemEventType()))


class ObservableList(ObservableCollection, List):
    """ObservableList is a list that notifies observers
    when items are added to or removed from the list."""

    @eventSource
    def append(self, item, event=None):
        super().append(item)
        event.addSource(self, item, type=self.addItemEventType())

    @eventSource
    def extend(self, items, event=None):
        if not items:
            return
        super().extend(items)
        event.addSource(self, *items, **dict(type=self.addItemEventType()))

    @eventSource
    def remove(self, item, event=None):
        super().remove(item)
        event.addSource(self, item, type=self.removeItemEventType())

    @eventSource
    def removeItems(self, items, event=None):  # pylint: disable=W0221
        if not items:
            return
        super().removeItems(items)
        event.addSource(self, *items, **dict(type=self.removeItemEventType()))

    @eventSource
    def clear(self, event=None):
        if not self:
            return
        items = tuple(self)
        del self[:]
        event.addSource(self, *items, **dict(type=self.removeItemEventType()))


class CollectionDecorator(Decorator, ObservableCollection):
    """CollectionDecorator observes an ObservableCollection and is an
    ObservableCollection itself too. Its purpose is to decorate another
    collection and add some behaviour, such as sorting or filtering.
    Users of this class shouldn't see a difference between using the
    original collection or a decorated version."""

    def __init__(self, observedCollection, *args, **kwargs):
        super().__init__(observedCollection, *args, **kwargs)
        self.__freezeCount = 0
        observable = self.observable()
        self.registerObserver(
            self.onAddItem,
            eventType=observable.addItemEventType(),
            eventSource=observable,
        )
        self.registerObserver(
            self.onRemoveItem,
            eventType=observable.removeItemEventType(),
            eventSource=observable,
        )
        self.extendSelf(observable)

    def __repr__(self):  # pragma: no cover
        return "%s(%s)" % (
            self.__class__,
            super().__repr__(),
        )

    def freeze(self):
        if isinstance(self.observable(), CollectionDecorator):
            self.observable().freeze()
        self.__freezeCount += 1

    def thaw(self):
        self.__freezeCount -= 1
        if isinstance(self.observable(), CollectionDecorator):
            self.observable().thaw()

    def isFrozen(self):
        return self.__freezeCount != 0

    def detach(self):
        self.removeObserver(self.onAddItem)
        self.removeObserver(self.onRemoveItem)
        self.observable().detach()
        super().detach()

    def onAddItem(self, event):
        """The default behaviour is to simply add the items that are
        added to the original collection to this collection too.
        Extend to add behaviour."""
        self.extendSelf(list(event.values()))

    def onRemoveItem(self, event):
        """The default behaviour is to simply remove the items that are
        removed from the original collection from this collection too.
        Extend to add behaviour."""
        self.removeItemsFromSelf(list(event.values()))

    def extendSelf(self, items, event=None):
        """Provide a method to extend this collection without delegating to
        the observed collection."""
        return super().extend(items, event=event)

    def removeItemsFromSelf(self, items, event=None):
        """Provide a method to remove items from this collection without
        delegating to the observed collection."""
        return super().removeItems(items, event=event)

    # Delegate changes to the observed collection

    def append(self, *args, **kwargs):
        return self.observable().append(*args, **kwargs)

    def extend(self, *args, **kwargs):
        return self.observable().extend(*args, **kwargs)

    def remove(self, *args, **kwargs):
        return self.observable().remove(*args, **kwargs)

    def removeItems(self, *args, **kwargs):
        return self.observable().removeItems(*args, **kwargs)


class ListDecorator(CollectionDecorator, ObservableList):
    pass


class SetDecorator(CollectionDecorator, ObservableSet):
    pass
