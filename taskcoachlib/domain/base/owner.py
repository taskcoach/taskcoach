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
from taskcoachlib.domain.date import Timestamp
from taskcoachlib.patterns.field import ListField
from .object import fresh_state


def DomainObjectOwnerMetaclass(name, bases, ns):
    """This metaclass makes a class an owner for some domain
    objects. The __ownedType__ attribute of the class must be a
    string. For each type, the following methods will be added to the
    class (here assuming a type of 'Foo'):

      - __init__, __getstate__, __setstate__, __getcopystate__, __setcopystate__
      - addFoo, removeFoo, addFoos, removeFoos
      - setFoos, foos
      - foosChangedEventType
      - fooAddedEventType
      - fooRemovedEventType
      - modificationEventTypes
      - __notifyObservers"""

    # This  metaclass is  a function  instead  of a  subclass of  type
    # because as we're replacing __init__, we don't want the metaclass
    # to be inherited by children.

    klass = type(name, bases, ns)
    field_name = "_%s__%ss" % (name, klass.__ownedType__.lower())
    restored_name = "_%ss_restored" % klass.__ownedType__.lower()

    def constructor(instance, *args, **kwargs):
        # A stored field (docs/UNDO_REDO.md, Architecture)
        setattr(
            instance,
            field_name,
            ListField(
                kwargs.pop(klass.__ownedType__.lower() + "s", []),
                instance,
                getattr(instance, restored_name),
            ),
        )
        super(klass, instance).__init__(*args, **kwargs)

    def owned_list(instance):
        return getattr(instance, field_name).get()

    klass.__init__ = constructor

    def owner_changed(owned_objects, event):
        # Each owned object's own link, as a subtask's parent: changing
        # it sets the object's date (docs/ATTRIBUTE_PATTERN.md,
        # Modification Date)
        now = Timestamp.now()
        for owned_object in owned_objects:
            owned_object.set_modification_datetime(now, event=event)

    def changed_event_type(class_):
        return "%s.%ss" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%ssChangedEventType" % klass.__ownedType__.lower(),
        classmethod(changed_event_type),
    )

    def added_event_type(class_):
        return "%s.%s.added" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%sAddedEventType" % klass.__ownedType__.lower(),
        classmethod(added_event_type),
    )

    def removed_event_type(class_):
        return "%s.%s.removed" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%sRemovedEventType" % klass.__ownedType__.lower(),
        classmethod(removed_event_type),
    )

    def modification_event_types(class_):
        try:
            event_types = super(klass, class_).modificationEventTypes()
        except AttributeError:
            event_types = []
        return event_types + [changed_event_type(class_)]

    klass.modificationEventTypes = classmethod(modification_event_types)

    def objects(instance, recursive=False):
        result = list(owned_list(instance))
        if recursive:
            for owned_object in result[:]:
                result.extend(owned_object.children(recursive=True))
        return result

    setattr(klass, "%ss" % klass.__ownedType__.lower(), objects)

    @patterns.eventSource
    def set_objects(instance, new_objects, event=None):
        old_objects = objects(instance)
        if new_objects == old_objects:
            return
        owned_list(instance)[:] = new_objects
        old_ids = {id(each) for each in old_objects}
        new_ids = {id(each) for each in new_objects}
        owner_changed(
            [each for each in new_objects if id(each) not in old_ids]
            + [each for each in old_objects if id(each) not in new_ids],
            event,
        )
        changed_event(instance, event, *new_objects)  # pylint: disable=W0142

    setattr(klass, "set%ss" % klass.__ownedType__, set_objects)

    def changed_event(instance, event, *objects):
        event.addSource(
            instance,
            *objects,
            **dict(type=changed_event_type(instance.__class__))
        )

    setattr(
        klass, "%ssChangedEvent" % klass.__ownedType__.lower(), changed_event
    )

    def added_event(instance, event, *objects):
        event.addSource(
            instance,
            *objects,
            **dict(type=added_event_type(instance.__class__))
        )

    setattr(klass, "%sAddedEvent" % klass.__ownedType__.lower(), added_event)

    def removed_event(instance, event, *objects):
        event.addSource(
            instance,
            *objects,
            **dict(type=removed_event_type(instance.__class__))
        )

    setattr(
        klass, "%sRemovedEvent" % klass.__ownedType__.lower(), removed_event
    )

    @patterns.eventSource
    def restored(instance, added, removed, event=None):
        changed_event(instance, event, *objects(instance))
        if added:
            added_event(instance, event, *added)
        if removed:
            removed_event(instance, event, *removed)

    setattr(klass, restored_name, restored)

    @patterns.eventSource
    def add_object(instance, owned_object, event=None):
        owned_list(instance).append(owned_object)
        owner_changed([owned_object], event)
        changed_event(instance, event, owned_object)
        added_event(instance, event, owned_object)

    setattr(klass, "add%s" % klass.__ownedType__, add_object)

    @patterns.eventSource
    def add_objects(instance, *owned_objects, **kwargs):
        if not owned_objects:
            return
        owned_list(instance).extend(owned_objects)
        event = kwargs.pop("event", None)
        owner_changed(owned_objects, event)
        changed_event(instance, event, *owned_objects)
        added_event(instance, event, *owned_objects)

    setattr(klass, "add%ss" % klass.__ownedType__, add_objects)

    @patterns.eventSource
    def remove_object(instance, owned_object, event=None):
        owned_list(instance).remove(owned_object)
        owner_changed([owned_object], event)
        changed_event(instance, event, owned_object)
        removed_event(instance, event, owned_object)

    setattr(klass, "remove%s" % klass.__ownedType__, remove_object)

    @patterns.eventSource
    def remove_objects(instance, *owned_objects, **kwargs):
        if not owned_objects:
            return
        removed = []
        for owned_object in owned_objects:
            try:
                owned_list(instance).remove(owned_object)
            except ValueError:
                pass
            else:
                removed.append(owned_object)
        event = kwargs.pop("event", None)
        owner_changed(removed, event)
        changed_event(instance, event, *owned_objects)
        removed_event(instance, event, *owned_objects)

    setattr(klass, "remove%ss" % klass.__ownedType__, remove_objects)

    def getstate(instance):
        state = fresh_state(super(klass, instance), instance)
        state[klass.__ownedType__.lower() + "s"] = owned_list(instance)[:]
        return state

    klass.__getstate__ = getstate

    @patterns.eventSource
    def setstate(instance, state, event=None):
        try:
            super(klass, instance).__setstate__(state, event=event)
        except AttributeError:
            pass
        set_objects(
            instance, state[klass.__ownedType__.lower() + "s"], event=event
        )

    klass.__setstate__ = setstate

    def getcopystate(instance):
        try:
            state = super(klass, instance).__getcopystate__()
        except AttributeError:
            state = dict()
        state["%ss" % klass.__ownedType__.lower()] = [
            owned_object.copy() for owned_object in objects(instance)
        ]
        return state

    klass.__getcopystate__ = getcopystate

    return klass
