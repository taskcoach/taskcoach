"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

from taskcoachlib.patterns import Observer, ObservableComposite
from taskcoachlib.domain.categorizable import CategorizableCompositeObject
from taskcoachlib.domain.note import NoteOwner
from taskcoachlib.domain.task import Task
from taskcoachlib.domain.effort import Effort
from taskcoachlib.domain.attachment import AttachmentOwner
import uuid
from pubsub import pub


class ChangeMonitor(Observer):
    """
    This class monitors change to object on a per-attribute basis.
    """

    def __init__(self, id_=None):
        super().__init__()

        self.__guid = id_ or str(uuid.uuid4())
        self.__frozen = False
        self.__collections = []

        self.reset()

    def freeze(self):
        self.__frozen = True

    def thaw(self):
        self.__frozen = False

    def guid(self):
        return self.__guid

    def reset(self):
        self._changes = dict()
        self._classes = set()

    def monitorClass(self, klass):
        if klass not in self._classes:
            for name in klass.monitoredAttributes():
                eventType = getattr(klass, "%sChangedEventType" % name)()
                if eventType.startswith("pubsub"):
                    pub.subscribe(self.onAttributeChanged, eventType)
                else:
                    self.registerObserver(
                        self.onAttributeChanged_Deprecated, eventType
                    )
                self._classes.add(klass)
            if issubclass(klass, ObservableComposite):
                self.registerObserver(
                    self.onChildAdded, klass.addChildEventType()
                )
                self.registerObserver(
                    self.onChildRemoved, klass.removeChildEventType()
                )
            if issubclass(klass, CategorizableCompositeObject):
                self.registerObserver(
                    self.onCategoryAdded, klass.categoryAddedEventType()
                )
                self.registerObserver(
                    self.onCategoryRemoved, klass.categoryRemovedEventType()
                )
            if issubclass(klass, Task):
                pub.subscribe(
                    self.onEffortAddedOrRemoved, Task.effortsChangedEventType()
                )
                pub.subscribe(
                    self.onPrerequisitesChanged,
                    Task.prerequisitesChangedEventType(),
                )
            if issubclass(klass, NoteOwner):
                self.registerObserver(
                    self.onOtherObjectAdded, klass.noteAddedEventType()
                )
                self.registerObserver(
                    self.onOtherObjectRemoved, klass.noteRemovedEventType()
                )
            if issubclass(klass, AttachmentOwner):
                self.registerObserver(
                    self.onOtherObjectAdded, klass.attachmentAddedEventType()
                )
                self.registerObserver(
                    self.onOtherObjectRemoved,
                    klass.attachmentRemovedEventType(),
                )
            if issubclass(klass, Effort):
                pub.subscribe(
                    self.onEffortTaskChanged, Effort.taskChangedEventType()
                )

    def unmonitorClass(self, klass):
        if klass in self._classes:
            for name in klass.monitoredAttributes():
                eventType = getattr(klass, "%sChangedEventType" % name)()
                if eventType.startswith("pubsub"):
                    pub.unsubscribe(self.onAttributeChanged, eventType)
                else:
                    self.removeObserver(
                        self.onAttributeChanged_Deprecated, eventType
                    )
            if issubclass(klass, ObservableComposite):
                self.removeObserver(
                    self.onChildAdded, klass.addChildEventType()
                )
                self.removeObserver(
                    self.onChildRemoved, klass.removeChildEventType()
                )
            if issubclass(klass, CategorizableCompositeObject):
                self.removeObserver(
                    self.onCategoryAdded, klass.categoryAddedEventType()
                )
                self.removeObserver(
                    self.onCategoryRemoved, klass.categoryRemovedEventType()
                )
            if issubclass(klass, Task):
                pub.unsubscribe(
                    self.onEffortAddedOrRemoved, Task.effortsChangedEventType()
                )
                pub.unsubscribe(
                    self.onPrerequisitesChanged,
                    Task.prerequisitesChangedEventType(),
                )
            if issubclass(klass, NoteOwner):
                self.removeObserver(
                    self.onOtherObjectAdded, klass.noteAddedEventType()
                )
                self.removeObserver(
                    self.onOtherObjectRemoved, klass.noteRemovedEventType()
                )
            if issubclass(klass, AttachmentOwner):
                self.removeObserver(
                    self.onOtherObjectAdded, klass.attachmentAddedEventType()
                )
                self.removeObserver(
                    self.onOtherObjectRemoved,
                    klass.attachmentRemovedEventType(),
                )
            if issubclass(klass, Effort):
                pub.unsubscribe(
                    self.onEffortTaskChanged, Effort.taskChangedEventType()
                )
            self._classes.remove(klass)

    def monitorCollection(self, collection):
        self.__collections.append(collection)
        self.registerObserver(
            self.onObjectAdded,
            collection.addItemEventType(),
            eventSource=collection,
        )
        self.registerObserver(
            self.onObjectRemoved,
            collection.removeItemEventType(),
            eventSource=collection,
        )

    def unmonitorCollection(self, collection):
        self.__collections.remove(collection)
        self.removeObserver(
            self.onObjectAdded,
            collection.addItemEventType(),
            eventSource=collection,
        )
        self.removeObserver(
            self.onObjectRemoved,
            collection.removeItemEventType(),
            eventSource=collection,
        )

    def onAttributeChanged(self, newValue, sender, topic=pub.AUTO_TOPIC):
        if self.__frozen:
            return

        for name in sender.monitoredAttributes():
            if name in topic.getNameTuple():
                if (
                    sender.id() in self._changes
                    and self._changes[sender.id()] is not None
                ):
                    self._changes[sender.id()].add(name)

    def onAttributeChanged_Deprecated(self, event):
        if self.__frozen:
            return

        for type_, valBySource in list(event.sourcesAndValuesByType().items()):
            for obj in list(valBySource.keys()):
                for name in obj.monitoredAttributes():
                    if type_ == getattr(obj, "%sChangedEventType" % name)():
                        if (
                            obj.id() in self._changes
                            and self._changes[obj.id()] is not None
                        ):
                            self._changes[obj.id()].add(name)

    def _objectAdded(self, obj):
        if obj.id() in self._changes:
            if (
                self._changes[obj.id()] is not None
                and "__del__" in self._changes[obj.id()]
            ):
                self._changes[obj.id()].remove("__del__")
        else:
            self._changes[obj.id()] = None

    def _objectsAdded(self, event):
        for obj in list(event.values()):
            self._objectAdded(obj)

    def _objectRemoved(self, obj):
        if obj.id() in self._changes:
            if self._changes[obj.id()] is None:
                del self._changes[obj.id()]
            else:
                self._changes[obj.id()].add("__del__")

    def _objectsRemoved(self, event):
        for obj in list(event.values()):
            self._objectRemoved(obj)

    def onChildAdded(self, event):
        if self.__frozen:
            return

        self._objectsAdded(event)
        for obj in list(event.values()):
            if self._changes[obj.id()] is not None:
                self._changes[obj.id()].add("__parent__")

    def onChildRemoved(self, event):
        if self.__frozen:
            return

        self._objectsRemoved(event)
        for obj in list(event.values()):
            if obj in self._changes and self._changes[obj.id()] is not None:
                self._changes[obj.id()].add("__parent__")

    def onObjectAdded(self, event):
        if self.__frozen:
            return

        self._objectsAdded(event)

    def onObjectRemoved(self, event):
        if self.__frozen:
            return

        self._objectsRemoved(event)

    def onOtherObjectAdded(self, event):
        if self.__frozen:
            return

        self._objectsAdded(event)

    def onOtherObjectRemoved(self, event):
        if self.__frozen:
            return

        self._objectsRemoved(event)

    def onEffortAddedOrRemoved(self, newValue, sender):
        efforts, oldValue = newValue
        effortsToAdd = [effort for effort in efforts if effort not in oldValue]
        effortsToRemove = [
            effort for effort in oldValue if effort not in efforts
        ]
        for effort in effortsToAdd:
            self._objectAdded(effort)
        for effort in effortsToRemove:
            self._objectRemoved(effort)

    def onEffortTaskChanged(self, newValue, sender):
        changes = self._changes.get(sender.id(), None)
        if changes is not None:
            changes.add("__task__")

    def onCategoryAdded(self, event):
        if self.__frozen:
            return

        for obj in event.sources():
            if (
                obj.id() in self._changes
                and self._changes[obj.id()] is not None
            ):
                for theCategory in event.values(source=obj):
                    name = "_category:%s" % theCategory.id()
                    if "__del" + name in self._changes[obj.id()]:
                        self._changes[obj.id()].remove("__del" + name)
                    else:
                        self._changes[obj.id()].add("__add" + name)

    def onCategoryRemoved(self, event):
        if self.__frozen:
            return

        for obj in event.sources():
            if (
                obj.id() in self._changes
                and self._changes[obj.id()] is not None
            ):
                for theCategory in event.values(source=obj):
                    name = "_category:%s" % theCategory.id()
                    if "__add" + name in self._changes[obj.id()]:
                        self._changes[obj.id()].remove("__add" + name)
                    else:
                        self._changes[obj.id()].add("__del" + name)

    def onPrerequisitesChanged(
        self, newValue, sender
    ):  # pylint: disable-msg=W0613
        # Need to check whether the sender is actually in one of the collections we monitor
        # Is this really the best way?
        for collection in self.__collections:
            if sender in collection:
                break
        else:
            return
        if (
            sender.id() in self._changes
            and self._changes[sender.id()] is not None
        ):
            self._changes[sender.id()].add("__prerequisites__")

    def allChanges(self):
        return self._changes

    def getChanges(self, obj):
        return self._changes.get(obj.id(), None)

    def setChanges(self, id_, changes):
        if changes is None:
            del self._changes[id_]
        else:
            self._changes[id_] = changes

    def isRemoved(self, obj):
        return (
            obj.id() in self._changes
            and self._changes[obj.id()] is not None
            and "__del__" in self._changes[obj.id()]
        )

    def resetChanges(self, obj):
        self._changes[obj.id()] = set()

    def addChange(self, obj, name):
        changes = self._changes.get(obj.id(), set())
        changes.add(name)
        self._changes[obj.id()] = changes

    def resetAllChanges(self):
        for id_, changes in list(self._changes.items()):
            if changes is not None and "__del__" in changes:
                del self._changes[id_]
            else:
                self._changes[id_] = set()

    def empty(self):
        self._changes = dict()

    def merge(self, monitor):
        for id_, changes in list(self._changes.items()):
            theirChanges = monitor._changes.get(id_, None)
            if theirChanges is not None:
                changes.update(theirChanges)
