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

import test
from taskcoachlib import patterns


class EventTest(test.TestCase):
    def setUp(self):
        self.event = patterns.Event("eventtype", self, "some value")

    def testEqualWhenAllValuesAreEqual(self):
        self.assertEqual(
            self.event, patterns.Event("eventtype", self, "some value")
        )

    def testUnequalWhenValuesAreDifferent(self):
        self.assertNotEqual(
            self.event, patterns.Event("eventtype", self, "other value")
        )

    def testUnequalWhenTypesAreDifferent(self):
        self.assertNotEqual(
            self.event, patterns.Event("other type", self, "some value")
        )

    def testUnequalWhenSourcesAreDifferent(self):
        self.assertNotEqual(
            self.event, patterns.Event("eventtype", None, "some value")
        )

    def testEventWithoutType(self):
        event = patterns.Event()
        self.assertEqual(set(), event.types())

    def testEventWithoutSources(self):
        event = patterns.Event("eventtype")
        self.assertEqual(set(), event.sources())

    def testEventSources(self):
        self.assertEqual(set([self]), self.event.sources())

    def testEventValue(self):
        self.assertEqual("some value", self.event.value())

    def testEventValues(self):
        self.assertEqual(("some value",), tuple(self.event.values()))

    def testEventValueForSpecificSource(self):
        self.assertEqual("some value", self.event.value(self))

    def testEventValuesForSpecificSource(self):
        self.assertEqual(("some value",), self.event.values(self))

    def testAddSource(self):
        self.event.addSource("source")
        self.assertEqual(set([self, "source"]), self.event.sources())

    def testAddExistingSource(self):
        self.event.addSource(self)
        self.assertEqual(set([self]), self.event.sources())

    def testAddSourceAndValue(self):
        self.event.addSource("source", "value")
        self.assertEqual("value", self.event.value("source"))

    def testAddSourceAndValues(self):
        self.event.addSource("source", "value1", "value2")
        self.assertEqual(
            set(["value1", "value2"]), set(self.event.values("source"))
        )

    def testExistingSourceAndValue(self):
        self.event.addSource(self, "new value")
        self.assertEqual(
            set(["some value", "new value"]), set(self.event.values())
        )

    def testEventTypes(self):
        self.assertEqual(set(["eventtype"]), self.event.types())

    def testAddSourceForSpecificType(self):
        self.event.addSource(self, type="another eventtype")
        self.assertEqual(
            set(["eventtype", "another eventtype"]), self.event.types()
        )

    def testGetSourcesForSpecificType(self):
        self.assertEqual(set([self]), self.event.sources("eventtype"))

    def testGetSourcesForSpecificTypes(self):
        self.event.addSource("source", type="another eventtype")
        self.assertEqual(
            set([self, "source"]), self.event.sources(*self.event.types())
        )

    def testGetSourcesForNonExistingEventType(self):
        self.assertEqual(set(), self.event.sources("unused eventType"))

    def testGetAllSourcesAfterAddingSourceForSpecificType(self):
        self.event.addSource("source", type="another eventtype")
        self.assertEqual(set([self, "source"]), self.event.sources())

    def testAddSourceAndValueForSpecificType(self):
        self.event.addSource("source", "value", type="another eventtype")
        # value() picks an arbitrary type when there are several
        self.assertEqual(
            "value", self.event.value("source", type="another eventtype")
        )

    def testAddSourceAndValuesForSpecificType(self):
        self.event.addSource(
            "source", "value1", "value2", type="another eventtype"
        )
        self.assertEqual(
            set(["value1", "value2"]),
            set(self.event.values("source", type="another eventtype")),
        )

    def testAddExistingSourceToAnotherType(self):
        self.event.addSource(self, type="another eventtype")
        self.assertEqual(set([self]), self.event.sources())

    def testAddExistingSourceWithValueToTypeDoesNotRemoveValueForEarlierType(
        self,
    ):
        self.event.addSource(
            self, "value for another eventtype", type="another eventtype"
        )
        self.assertEqual(
            "some value", self.event.value(self, type="eventtype")
        )

    def testAddExistingSourceWithValueToType(self):
        self.event.addSource(
            self, "value for another eventtype", type="another eventtype"
        )
        self.assertEqual(
            "value for another eventtype",
            self.event.value(self, type="another eventtype"),
        )

    def testSubEventForOneTypeWhenEventHasOneType(self):
        self.assertEqual(
            self.event, self.event.subEvent((self.event.type(), self))
        )

    def testSubEventForOneTypeWhenEventHasTwoTypes(self):
        self.event.addSource("source", type="another eventtype")
        expectedEvent = patterns.Event("eventtype", self, "some value")
        self.assertEqual(
            expectedEvent, self.event.subEvent(("eventtype", self))
        )

    def testSubEventForTwoTypesWhenEventHasTwoTypes(self):
        self.event.addSource("source", type="another eventtype")
        args = [("eventtype", self), ("another eventtype", "source")]
        self.assertEqual(
            self.event, self.event.subEvent(*args)
        )  # pylint: disable=W0142

    def testSubEventForTypeThatIsNotPresent(self):
        self.assertEqual(
            patterns.Event(), self.event.subEvent(("missing eventtype", self))
        )

    def testSubEventForOneSourceWhenEventHasOneSource(self):
        self.assertEqual(self.event, self.event.subEvent(("eventtype", self)))

    def testSubEventForUnspecifiedSource(self):
        self.assertEqual(self.event, self.event.subEvent(("eventtype", None)))

    def testSubEventForUnspecifiedSourceAndSpecifiedSources(self):
        self.assertEqual(
            self.event,
            self.event.subEvent(("eventtype", self), ["eventtype", None]),
        )

    def testSubEventForSourceThatIsNotPresent(self):
        self.assertEqual(
            patterns.Event(),
            self.event.subEvent(("eventtype", "missing source")),
        )

    def testSubEventForSourceThatIsNotPresentForSpecifiedType(self):
        self.event.addSource("source", type="another eventtype")
        self.assertEqual(
            patterns.Event(), self.event.subEvent(("eventtype", "source"))
        )


class ObservableCollectionFixture(test.TestCase):
    def setUp(self):
        self.collection = self.createObservableCollection()
        patterns.Publisher().registerObserver(
            self.onAdd,
            eventType=self.collection.addItemEventType(),
            eventSource=self.collection,
        )
        patterns.Publisher().registerObserver(
            self.onRemove,
            eventType=self.collection.removeItemEventType(),
            eventSource=self.collection,
        )
        self.receivedAddEvents = []
        self.receivedRemoveEvents = []

    def createObservableCollection(self):
        raise NotImplementedError  # pragma: no cover

    def onAdd(self, event):
        self.receivedAddEvents.append(event)

    def onRemove(self, event):
        self.receivedRemoveEvents.append(event)


class ObservableCollectionTestsMixin(object):
    def testCollectionEqualsItself(self):
        self.assertTrue(self.collection == self.collection)

    def testCollectionDoesNotEqualOtherCollections(self):
        self.assertFalse(self.collection == self.createObservableCollection())

    def testAppend(self):
        self.collection.append(1)
        self.assertTrue(1 in self.collection)

    def testAppend_Notification(self):
        self.collection.append(1)
        self.assertEqual(1, self.receivedAddEvents[0].value())

    def testExtend(self):
        self.collection.extend([1, 2])
        self.assertTrue(1 in self.collection and 2 in self.collection)

    def testExtend_Notification(self):
        self.collection.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def testExtend_NoNotificationWhenNoItems(self):
        self.collection.extend([])
        self.assertFalse(self.receivedAddEvents)

    def testRemove(self):
        self.collection.append(1)
        self.collection.remove(1)
        self.assertFalse(self.collection)

    def testRemove_Notification(self):
        self.collection.append(1)
        self.collection.remove(1)
        self.assertEqual(1, self.receivedRemoveEvents[0].value())

    def testRemovingAnItemNotInCollection_CausesException(self):
        try:
            self.collection.remove(1)
            self.fail("Expected ValueError or KeyError")  # pragma: no cover
        except (ValueError, KeyError):
            pass

    def testRemovingAnItemNotInCollection_CausesNoNotification(self):
        try:
            self.collection.remove(1)
        except (ValueError, KeyError):
            pass
        self.assertFalse(self.receivedRemoveEvents)

    def testRemoveItems(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([1, 2])
        self.assertFalse(1 in self.collection or 2 in self.collection)

    def testRemoveItems_Notification(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([1, 2])
        self.assertEqual((1, 2), tuple(self.receivedRemoveEvents[0].values()))

    def testRemoveItems_NoNotificationWhenNoItems(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([])
        self.assertFalse(self.receivedRemoveEvents)

    def testClear(self):
        self.collection.extend([1, 2, 3])
        self.collection.clear()
        self.assertFalse(self.collection)

    def testClear_Notification(self):
        self.collection.extend([1, 2, 3])
        self.collection.clear()
        self.assertEqual(
            (1, 2, 3), tuple(self.receivedRemoveEvents[0].values())
        )

    def testClear_NoNotificationWhenNoItems(self):
        self.collection.clear()
        self.assertFalse(self.receivedRemoveEvents)

    def testModificationEventTypes(self):
        self.assertEqual(
            [
                self.collection.addItemEventType(),
                self.collection.removeItemEventType(),
            ],
            self.collection.modificationEventTypes(),
        )


class ObservableListTest(
    ObservableCollectionFixture, ObservableCollectionTestsMixin
):
    def createObservableCollection(self):
        return patterns.ObservableList()

    def testAppendSameItemTwice(self):
        self.collection.append(1)
        self.collection.append(1)
        self.assertEqual(2, len(self.collection))


class ObservableSetTest(
    ObservableCollectionFixture, ObservableCollectionTestsMixin
):
    def createObservableCollection(self):
        return patterns.ObservableSet()

    def testAppendSameItemTwice(self):
        self.collection.append(1)
        self.collection.append(1)
        self.assertEqual(1, len(self.collection))


class ListDecoratorTest_Constructor(test.TestCase):
    def testOriginalNotEmpty(self):
        observable = patterns.ObservableList([1, 2, 3])
        observer = patterns.ListDecorator(observable)
        self.assertEqual([1, 2, 3], observer)


class SetDecoratorTest_Constructor(test.TestCase):
    def testOriginalNotEmpty(self):
        observable = patterns.ObservableSet([1, 2, 3])
        observer = patterns.SetDecorator(observable)
        self.assertEqual([1, 2, 3], observer)


class ListDecoratorTest_AddItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.ListDecorator(self.observable)

    def testAppendToObservable(self):
        self.observable.append(1)
        self.assertEqual([1], self.observer)

    def testAppendToObserver(self):
        self.observer.append(1)
        self.assertEqual([1], self.observable)

    def testExtendObservable(self):
        self.observable.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observer)

    def testExtendObserver(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observable)


class SetDecoratorTest_AddItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.SetDecorator(self.observable)

    def testAppendToObservable(self):
        self.observable.append(1)
        self.assertEqual([1], self.observer)

    def testAppendToObserver(self):
        self.observer.append(1)
        self.assertEqual([1], self.observable)

    def testExtendObservable(self):
        self.observable.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observer)

    def testExtendObserver(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observable)


class ListDecoratorTest_RemoveItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.ListDecorator(self.observable)
        self.observable.extend([1, 2, 3])

    def testRemoveFromOriginal(self):
        self.observable.remove(1)
        self.assertEqual([2, 3], self.observer)

    def testRemoveFromObserver(self):
        self.observer.remove(1)
        self.assertEqual([2, 3], self.observable)

    def testRemoveItemsFromOriginal(self):
        self.observable.removeItems([1, 2])
        self.assertEqual([3], self.observer)

    def testRemoveItemsFromObserver(self):
        self.observer.removeItems([1, 2])
        self.assertEqual([3], self.observable)


class SetDecoratorTest_RemoveItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.SetDecorator(self.observable)
        self.observable.extend([1, 2, 3])

    def testRemoveFromOriginal(self):
        self.observable.remove(1)
        self.assertEqual([2, 3], self.observer)

    def testRemoveFromObserver(self):
        self.observer.remove(1)
        self.assertEqual([2, 3], self.observable)

    def testRemoveItemsFromOriginal(self):
        self.observable.removeItems([1, 2])
        self.assertEqual([3], self.observer)

    def testRemoveItemsFromObserver(self):
        self.observer.removeItems([1, 2])
        self.assertEqual([3], self.observable)


class ListDecoratorTest_ObserveTheObserver(test.TestCase):
    def setUp(self):
        self.list = patterns.ObservableList()
        self.observer = patterns.ListDecorator(self.list)
        patterns.Publisher().registerObserver(
            self.onAdd,
            eventType=self.observer.addItemEventType(),
            eventSource=self.observer,
        )
        patterns.Publisher().registerObserver(
            self.onRemove,
            eventType=self.observer.removeItemEventType(),
            eventSource=self.observer,
        )
        self.receivedAddEvents = []
        self.receivedRemoveEvents = []

    def onAdd(self, event):
        self.receivedAddEvents.append(event)

    def onRemove(self, event):
        self.receivedRemoveEvents.append(event)

    def testExtendOriginal(self):
        self.list.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def testExtendObserver(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def testRemoveItemsFromOriginal(self):
        self.list.extend([1, 2, 3])
        self.list.removeItems([1, 3])
        self.assertEqual((1, 3), tuple(self.receivedRemoveEvents[0].values()))


class DeletedWidgetUser(object):
    def use(self):
        raise RuntimeError(
            "wrapped C/C++ object of type Panel has been deleted"
        )


class PublisherTest(test.TestCase):
    def setUp(self):
        self.publisher = patterns.Publisher()
        self.events = []
        self.events2 = []

    def onEvent(self, event):
        self.events.append(event)

    def onEvent2(self, event):
        self.events2.append(event)

    def on_event_raising(self, event):
        self.events.append(event)
        raise ValueError("observer bug")

    def on_event_of_deleted_widget(self, event):
        self.events.append(event)
        raise RuntimeError(
            "wrapped C/C++ object of type Panel has been deleted"
        )

    def test_observer_that_raises_is_kept(self):
        self.publisher.registerObserver(
            self.on_event_raising, eventType="eventType"
        )
        patterns.Event("eventType", "observable").send()
        patterns.Event("eventType", "observable").send()
        self.assertEqual(2, len(self.events))

    def on_event_calling_deleted_widget_user(self, event):
        self.events.append(event)
        DeletedWidgetUser().use()

    def test_observer_whose_callee_hits_deleted_widget_is_kept(self):
        self.publisher.registerObserver(
            self.on_event_calling_deleted_widget_user, eventType="eventType"
        )
        patterns.Event("eventType", "observable").send()
        patterns.Event("eventType", "observable").send()
        self.assertEqual(2, len(self.events))

    def test_observer_of_deleted_widget_is_removed(self):
        self.publisher.registerObserver(
            self.on_event_of_deleted_widget, eventType="eventType"
        )
        patterns.Event("eventType", "observable").send()
        patterns.Event("eventType", "observable").send()
        self.assertEqual(1, len(self.events))

    def testPublisherIsSingleton(self):
        anotherPublisher = patterns.Publisher()
        self.assertTrue(self.publisher is anotherPublisher)

    def testRegisterObserver(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def testRegisterObserver_Twice(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def testRegisterObserver_ForTwoDifferentTypes(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def testRegisterObserver_ListMethod(self):
        """A previous implementation of Publisher used sets. This caused a
        "TypeError: list objects are unhashable" whenever one tried to use
        an instance method of a list (sub)class as callback."""

        class List(list):
            def onEvent(self, *args):
                pass  # pragma: no cover

        self.publisher.registerObserver(List().onEvent, eventType="eventType")

    def testGetObservers_WithoutObservers(self):
        self.assertEqual([], self.publisher.observers())

    def testGetObserversForSpecificEventType_WithoutObservers(self):
        self.assertEqual([], self.publisher.observers(eventType="eventType"))

    def testGetObserversForSpecificEventType_WithObserver(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual(
            [self.onEvent], self.publisher.observers(eventType="eventType")
        )

    def testGetObserversForSpecificEventType_WhenDifferentTypesRegistered(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        self.assertEqual(
            [self.onEvent], self.publisher.observers(eventType="eventType1")
        )

    def testNotifyObservers_WithoutObservers(self):
        patterns.Event("eventType", self).send()
        self.assertFalse(self.events)

    def testNotifyObservers_WithObserverForDifferentEventType(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        patterns.Event("eventType2", self).send()
        self.assertFalse(self.events)

    def testNotifyObservers_WithObserverForRightEventType(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType", self).send()
        self.assertEqual([patterns.Event("eventType", self)], self.events)

    def testNotifyObservers_WithObserversForSameAndDifferentEventTypes(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        patterns.Event("eventType1", self).send()
        self.assertEqual([patterns.Event("eventType1", self)], self.events)

    def testNotifyObservers_ForDifferentEventTypesWithOneEvent(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent2, eventType="eventType2")
        event = patterns.Event("eventType1", self)
        event.addSource(self, type="eventType2")
        event.send()
        self.assertEqual([patterns.Event("eventType1", self)], self.events)
        self.assertEqual([patterns.Event("eventType2", self)], self.events2)

    def testNotifyObserversWithEventWithoutTypes(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event().send()
        self.assertFalse(self.events)

    def testNotifyObserversWithEventWithoutSources(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType").send()
        self.assertFalse(self.events)

    def testRemoveObserverForAnyEventType_NotRegisteredBefore(self):
        self.publisher.removeObserver(self.onEvent)
        self.assertEqual([], self.publisher.observers())

    def testRemoveObserverForAnyEventType_RegisteredBefore(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent)
        self.assertEqual([], self.publisher.observers())

    def testRemoveObserverForSpecificType_RegisteredForSameType(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent, eventType="eventType")
        self.assertEqual([], self.publisher.observers())

    def testRemoveObserverForSpecificType_RegisteredForDifferentType(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent, eventType="otherType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def testRemoveObserverForSpecificType_RegisteredForDifferentTypeThatHasObservers(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.registerObserver(self.onEvent2, eventType="otherType")
        self.publisher.removeObserver(self.onEvent, eventType="otherType")
        self.assertEqual([self.onEvent], self.publisher.observers("eventType"))

    def testClear(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.clear()
        self.assertEqual([], self.publisher.observers())

    def testRegisterObserver_ForSpecificSource(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        patterns.Event("eventType", "observable2").send()
        self.assertFalse(self.events)

    def testNotifyObserver_ForSpecificSource(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        event = patterns.Event("eventType", "observable1")
        event.send()
        self.assertEqual([event], self.events)

    def testRemoveObserver_RegisteredForSpecificSource(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.removeObserver(self.onEvent)
        event = patterns.Event("eventType", "observable1")
        event.send()
        self.assertFalse(self.events)

    def testRemoveObserverForSpecificEventType_RegisteredForSpecificSource(
        self,
    ):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.removeObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType", "observable1").send()
        self.assertFalse(self.events)

    def testRemoveObserverForSpecificEventSource(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable2"
        )
        self.publisher.removeObserver(self.onEvent, eventSource="observable1")
        patterns.Event("eventType", "observable2").send()
        self.assertTrue(self.events)

    def testRemoveObserverForSpecificEventTypeAndSource(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType1", eventSource="observable1"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType1", eventSource="observable2"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType2", eventSource="observable1"
        )
        self.publisher.removeObserver(
            self.onEvent, eventType="eventType1", eventSource="observable1"
        )
        patterns.Event("eventType1", "observable1").send()
        self.assertFalse(self.events)
        patterns.Event("eventType2", "observable1").send()
        self.assertTrue(self.events)

    def testRemoveObserverForSpecificEventTypeAndSourceDoesNotRemoveOtherSources(
        self,
    ):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType1", eventSource="observable1"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType1", eventSource="observable2"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType2", eventSource="observable1"
        )
        self.publisher.removeObserver(
            self.onEvent, eventType="eventType1", eventSource="observable1"
        )
        patterns.Event("eventType1", "observable2").send()
        self.assertTrue(self.events)
