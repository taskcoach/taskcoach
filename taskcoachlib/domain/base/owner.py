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

    def constructor(instance, *args, **kwargs):
        # NB: we use a simple list here. Maybe we should use a container type.
        setattr(
            instance,
            "_%s__%ss" % (name, klass.__ownedType__.lower()),
            kwargs.pop(klass.__ownedType__.lower() + "s", []),
        )
        super(klass, instance).__init__(*args, **kwargs)

    klass.__init__ = constructor

    def changedEventType(class_):
        return "%s.%ss" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%ssChangedEventType" % klass.__ownedType__.lower(),
        classmethod(changedEventType),
    )

    def addedEventType(class_):
        return "%s.%s.added" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%sAddedEventType" % klass.__ownedType__.lower(),
        classmethod(addedEventType),
    )

    def removedEventType(class_):
        return "%s.%s.removed" % (class_, klass.__ownedType__.lower())

    setattr(
        klass,
        "%sRemovedEventType" % klass.__ownedType__.lower(),
        classmethod(removedEventType),
    )

    def modificationEventTypes(class_):
        try:
            eventTypes = super(klass, class_).modificationEventTypes()
        except AttributeError:
            eventTypes = []
        return eventTypes + [changedEventType(class_)]

    klass.modificationEventTypes = classmethod(modificationEventTypes)

    def objects(instance, recursive=False):
        ownedObjects = getattr(
            instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
        )
        result = [
            ownedObject
            for ownedObject in ownedObjects
            if not ownedObject.isDeleted()
        ]
        if recursive:
            for ownedObject in result[:]:
                result.extend(ownedObject.children(recursive=True))
        return result

    setattr(klass, "%ss" % klass.__ownedType__.lower(), objects)

    @patterns.eventSource
    def setObjects(instance, newObjects, event=None):
        if newObjects == objects(instance):
            return
        setattr(
            instance,
            "_%s__%ss" % (name, klass.__ownedType__.lower()),
            newObjects,
        )
        changedEvent(instance, event, *newObjects)  # pylint: disable=W0142

    setattr(klass, "set%ss" % klass.__ownedType__, setObjects)

    def changedEvent(instance, event, *objects):
        event.addSource(
            instance,
            *objects,
            **dict(type=changedEventType(instance.__class__))
        )

    setattr(
        klass, "%ssChangedEvent" % klass.__ownedType__.lower(), changedEvent
    )

    def addedEvent(instance, event, *objects):
        event.addSource(
            instance, *objects, **dict(type=addedEventType(instance.__class__))
        )

    setattr(klass, "%sAddedEvent" % klass.__ownedType__.lower(), addedEvent)

    def removedEvent(instance, event, *objects):
        event.addSource(
            instance,
            *objects,
            **dict(type=removedEventType(instance.__class__))
        )

    setattr(
        klass, "%sRemovedEvent" % klass.__ownedType__.lower(), removedEvent
    )

    @patterns.eventSource
    def addObject(instance, ownedObject, event=None):
        getattr(
            instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
        ).append(ownedObject)
        changedEvent(instance, event, ownedObject)
        addedEvent(instance, event, ownedObject)

    setattr(klass, "add%s" % klass.__ownedType__, addObject)

    @patterns.eventSource
    def addObjects(instance, *ownedObjects, **kwargs):
        if not ownedObjects:
            return
        getattr(
            instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
        ).extend(ownedObjects)
        event = kwargs.pop("event", None)
        changedEvent(instance, event, *ownedObjects)
        addedEvent(instance, event, *ownedObjects)

    setattr(klass, "add%ss" % klass.__ownedType__, addObjects)

    @patterns.eventSource
    def removeObject(instance, ownedObject, event=None):
        getattr(
            instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
        ).remove(ownedObject)
        changedEvent(instance, event, ownedObject)
        removedEvent(instance, event, ownedObject)

    setattr(klass, "remove%s" % klass.__ownedType__, removeObject)

    @patterns.eventSource
    def removeObjects(instance, *ownedObjects, **kwargs):
        if not ownedObjects:
            return
        for ownedObject in ownedObjects:
            try:
                getattr(
                    instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
                ).remove(ownedObject)
            except ValueError:
                pass
        event = kwargs.pop("event", None)
        changedEvent(instance, event, *ownedObjects)
        removedEvent(instance, event, *ownedObjects)

    setattr(klass, "remove%ss" % klass.__ownedType__, removeObjects)

    def getstate(instance):
        state = fresh_state(super(klass, instance), instance)
        state[klass.__ownedType__.lower() + "s"] = getattr(
            instance, "_%s__%ss" % (name, klass.__ownedType__.lower())
        )[:]
        return state

    klass.__getstate__ = getstate

    @patterns.eventSource
    def setstate(instance, state, event=None):
        try:
            super(klass, instance).__setstate__(state, event=event)
        except AttributeError:
            pass
        setObjects(
            instance, state[klass.__ownedType__.lower() + "s"], event=event
        )

    klass.__setstate__ = setstate

    def getcopystate(instance):
        try:
            state = super(klass, instance).__getcopystate__()
        except AttributeError:
            state = dict()
        state["%ss" % klass.__ownedType__.lower()] = [
            ownedObject.copy() for ownedObject in objects(instance)
        ]
        return state

    klass.__getcopystate__ = getcopystate

    return klass
