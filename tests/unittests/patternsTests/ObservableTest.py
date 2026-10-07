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

import gc
import weakref

import test
import wx
from taskcoachlib import patterns


class EventTest(test.TestCase):
    def setUp(self):
        self.event = patterns.Event("eventtype", self, "some value")

    def test_equal_when_all_values_are_equal(self):
        self.assertEqual(
            self.event, patterns.Event("eventtype", self, "some value")
        )

    def test_unequal_when_values_are_different(self):
        self.assertNotEqual(
            self.event, patterns.Event("eventtype", self, "other value")
        )

    def test_unequal_when_types_are_different(self):
        self.assertNotEqual(
            self.event, patterns.Event("other type", self, "some value")
        )

    def test_unequal_when_sources_are_different(self):
        self.assertNotEqual(
            self.event, patterns.Event("eventtype", None, "some value")
        )

    def test_event_without_type(self):
        event = patterns.Event()
        self.assertEqual(set(), event.types())

    def test_event_without_sources(self):
        event = patterns.Event("eventtype")
        self.assertEqual(set(), event.sources())

    def test_event_sources(self):
        self.assertEqual(set([self]), self.event.sources())

    def test_event_value(self):
        self.assertEqual("some value", self.event.value())

    def test_event_values(self):
        self.assertEqual(("some value",), tuple(self.event.values()))

    def test_event_value_for_specific_source(self):
        self.assertEqual("some value", self.event.value(self))

    def test_event_values_for_specific_source(self):
        self.assertEqual(("some value",), self.event.values(self))

    def test_add_source(self):
        self.event.addSource("source")
        self.assertEqual(set([self, "source"]), self.event.sources())

    def test_add_existing_source(self):
        self.event.addSource(self)
        self.assertEqual(set([self]), self.event.sources())

    def test_add_source_and_value(self):
        self.event.addSource("source", "value")
        self.assertEqual("value", self.event.value("source"))

    def test_add_source_and_values(self):
        self.event.addSource("source", "value1", "value2")
        self.assertEqual(
            set(["value1", "value2"]), set(self.event.values("source"))
        )

    def test_existing_source_and_value(self):
        self.event.addSource(self, "new value")
        self.assertEqual(
            set(["some value", "new value"]), set(self.event.values())
        )

    def test_event_types(self):
        self.assertEqual(set(["eventtype"]), self.event.types())

    def test_add_source_for_specific_type(self):
        self.event.addSource(self, type="another eventtype")
        self.assertEqual(
            set(["eventtype", "another eventtype"]), self.event.types()
        )

    def test_get_sources_for_specific_type(self):
        self.assertEqual(set([self]), self.event.sources("eventtype"))

    def test_get_sources_for_specific_types(self):
        self.event.addSource("source", type="another eventtype")
        self.assertEqual(
            set([self, "source"]), self.event.sources(*self.event.types())
        )

    def test_get_sources_for_non_existing_event_type(self):
        self.assertEqual(set(), self.event.sources("unused eventType"))

    def test_get_all_sources_after_adding_source_for_specific_type(self):
        self.event.addSource("source", type="another eventtype")
        self.assertEqual(set([self, "source"]), self.event.sources())

    def test_add_source_and_value_for_specific_type(self):
        self.event.addSource("source", "value", type="another eventtype")
        # value() picks an arbitrary type when there are several
        self.assertEqual(
            "value", self.event.value("source", type="another eventtype")
        )

    def test_add_source_and_values_for_specific_type(self):
        self.event.addSource(
            "source", "value1", "value2", type="another eventtype"
        )
        self.assertEqual(
            set(["value1", "value2"]),
            set(self.event.values("source", type="another eventtype")),
        )

    def test_add_existing_source_to_another_type(self):
        self.event.addSource(self, type="another eventtype")
        self.assertEqual(set([self]), self.event.sources())

    def test_add_existing_source_to_type_keeps_value_for_earlier_type(
        self,
    ):
        self.event.addSource(
            self, "value for another eventtype", type="another eventtype"
        )
        self.assertEqual(
            "some value", self.event.value(self, type="eventtype")
        )

    def test_add_existing_source_with_value_to_type(self):
        self.event.addSource(
            self, "value for another eventtype", type="another eventtype"
        )
        self.assertEqual(
            "value for another eventtype",
            self.event.value(self, type="another eventtype"),
        )

    def test_sub_event_for_one_type_when_event_has_one_type(self):
        self.assertEqual(
            self.event, self.event.subEvent((self.event.type(), self))
        )

    def test_sub_event_for_one_type_when_event_has_two_types(self):
        self.event.addSource("source", type="another eventtype")
        expected_event = patterns.Event("eventtype", self, "some value")
        self.assertEqual(
            expected_event, self.event.subEvent(("eventtype", self))
        )

    def test_sub_event_for_two_types_when_event_has_two_types(self):
        self.event.addSource("source", type="another eventtype")
        args = [("eventtype", self), ("another eventtype", "source")]
        self.assertEqual(
            self.event, self.event.subEvent(*args)
        )  # pylint: disable=W0142

    def test_sub_event_for_type_that_is_not_present(self):
        self.assertEqual(
            patterns.Event(), self.event.subEvent(("missing eventtype", self))
        )

    def test_sub_event_for_one_source_when_event_has_one_source(self):
        self.assertEqual(self.event, self.event.subEvent(("eventtype", self)))

    def test_sub_event_for_unspecified_source(self):
        self.assertEqual(self.event, self.event.subEvent(("eventtype", None)))

    def test_sub_event_for_unspecified_source_and_specified_sources(self):
        self.assertEqual(
            self.event,
            self.event.subEvent(("eventtype", self), ["eventtype", None]),
        )

    def test_sub_event_for_source_that_is_not_present(self):
        self.assertEqual(
            patterns.Event(),
            self.event.subEvent(("eventtype", "missing source")),
        )

    def test_sub_event_for_source_that_is_not_present_for_specified_type(self):
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
    def test_collection_equals_itself(self):
        self.assertTrue(self.collection == self.collection)

    def test_collection_does_not_equal_other_collections(self):
        self.assertFalse(self.collection == self.createObservableCollection())

    def test_append(self):
        self.collection.append(1)
        self.assertTrue(1 in self.collection)

    def test_append_notification(self):
        self.collection.append(1)
        self.assertEqual(1, self.receivedAddEvents[0].value())

    def test_extend(self):
        self.collection.extend([1, 2])
        self.assertTrue(1 in self.collection and 2 in self.collection)

    def test_extend_notification(self):
        self.collection.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def test_extend_no_notification_when_no_items(self):
        self.collection.extend([])
        self.assertFalse(self.receivedAddEvents)

    def test_remove(self):
        self.collection.append(1)
        self.collection.remove(1)
        self.assertFalse(self.collection)

    def test_remove_notification(self):
        self.collection.append(1)
        self.collection.remove(1)
        self.assertEqual(1, self.receivedRemoveEvents[0].value())

    def test_removing_an_item_not_in_collection_causes_exception(self):
        try:
            self.collection.remove(1)
            self.fail("Expected ValueError or KeyError")  # pragma: no cover
        except (ValueError, KeyError):
            pass

    def test_removing_an_item_not_in_collection_causes_no_notification(self):
        try:
            self.collection.remove(1)
        except (ValueError, KeyError):
            pass
        self.assertFalse(self.receivedRemoveEvents)

    def test_remove_items(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([1, 2])
        self.assertFalse(1 in self.collection or 2 in self.collection)

    def test_remove_items_notification(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([1, 2])
        self.assertEqual((1, 2), tuple(self.receivedRemoveEvents[0].values()))

    def test_remove_items_no_notification_when_no_items(self):
        self.collection.extend([1, 2, 3])
        self.collection.removeItems([])
        self.assertFalse(self.receivedRemoveEvents)

    def test_clear(self):
        self.collection.extend([1, 2, 3])
        self.collection.clear()
        self.assertFalse(self.collection)

    def test_clear_notification(self):
        self.collection.extend([1, 2, 3])
        self.collection.clear()
        self.assertEqual(
            (1, 2, 3), tuple(self.receivedRemoveEvents[0].values())
        )

    def test_clear_no_notification_when_no_items(self):
        self.collection.clear()
        self.assertFalse(self.receivedRemoveEvents)

    def test_modification_event_types(self):
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

    def test_append_same_item_twice(self):
        self.collection.append(1)
        self.collection.append(1)
        self.assertEqual(2, len(self.collection))


class ObservableSetTest(
    ObservableCollectionFixture, ObservableCollectionTestsMixin
):
    def createObservableCollection(self):
        return patterns.ObservableSet()

    def test_append_same_item_twice(self):
        self.collection.append(1)
        self.collection.append(1)
        self.assertEqual(1, len(self.collection))


class ListDecoratorTest_Constructor(test.TestCase):
    def test_original_not_empty(self):
        observable = patterns.ObservableList([1, 2, 3])
        observer = patterns.ListDecorator(observable)
        self.assertEqual([1, 2, 3], observer)


class SetDecoratorTest_Constructor(test.TestCase):
    def test_original_not_empty(self):
        observable = patterns.ObservableSet([1, 2, 3])
        observer = patterns.SetDecorator(observable)
        self.assertEqual([1, 2, 3], observer)


class ListDecoratorTest_AddItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.ListDecorator(self.observable)

    def test_append_to_observable(self):
        self.observable.append(1)
        self.assertEqual([1], self.observer)

    def test_append_to_observer(self):
        self.observer.append(1)
        self.assertEqual([1], self.observable)

    def test_extend_observable(self):
        self.observable.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observer)

    def test_extend_observer(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observable)


class SetDecoratorTest_AddItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.SetDecorator(self.observable)

    def test_append_to_observable(self):
        self.observable.append(1)
        self.assertEqual([1], self.observer)

    def test_append_to_observer(self):
        self.observer.append(1)
        self.assertEqual([1], self.observable)

    def test_extend_observable(self):
        self.observable.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observer)

    def test_extend_observer(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual([1, 2, 3], self.observable)


class ListDecoratorTest_RemoveItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.ListDecorator(self.observable)
        self.observable.extend([1, 2, 3])

    def test_remove_from_original(self):
        self.observable.remove(1)
        self.assertEqual([2, 3], self.observer)

    def test_remove_from_observer(self):
        self.observer.remove(1)
        self.assertEqual([2, 3], self.observable)

    def test_remove_items_from_original(self):
        self.observable.removeItems([1, 2])
        self.assertEqual([3], self.observer)

    def test_remove_items_from_observer(self):
        self.observer.removeItems([1, 2])
        self.assertEqual([3], self.observable)


class SetDecoratorTest_RemoveItems(test.TestCase):
    def setUp(self):
        self.observable = patterns.ObservableList()
        self.observer = patterns.SetDecorator(self.observable)
        self.observable.extend([1, 2, 3])

    def test_remove_from_original(self):
        self.observable.remove(1)
        self.assertEqual([2, 3], self.observer)

    def test_remove_from_observer(self):
        self.observer.remove(1)
        self.assertEqual([2, 3], self.observable)

    def test_remove_items_from_original(self):
        self.observable.removeItems([1, 2])
        self.assertEqual([3], self.observer)

    def test_remove_items_from_observer(self):
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

    def test_extend_original(self):
        self.list.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def test_extend_observer(self):
        self.observer.extend([1, 2, 3])
        self.assertEqual((1, 2, 3), tuple(self.receivedAddEvents[0].values()))

    def test_remove_items_from_original(self):
        self.list.extend([1, 2, 3])
        self.list.removeItems([1, 3])
        self.assertEqual((1, 3), tuple(self.receivedRemoveEvents[0].values()))


class DeletedWidgetUser(object):
    def use(self):
        raise RuntimeError(
            "wrapped C/C++ object of type Panel has been deleted"
        )


class ObservingPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []

    def on_event(self, event):
        self.events.append(event)


class PublisherWindowTest(test.TestCase):
    """A window's subscriptions end when it is destroyed."""

    def setUp(self):
        super().setUp()
        self.frame = wx.Frame(None)
        self.addCleanup(self.frame.Destroy)
        self.panel = ObservingPanel(self.frame)
        patterns.Publisher().registerObserver(
            self.panel.on_event, eventType="eventType"
        )

    def test_destroyed_window_is_unsubscribed(self):
        self.panel.Destroy()
        self.assertEqual([], patterns.Publisher().observers())

    def test_destroying_a_child_keeps_the_window_subscribed(self):
        wx.Panel(self.panel).Destroy()
        patterns.Event("eventType", "source").send()
        self.assertEqual(1, len(self.panel.events))

    def test_remove_observers_of_keeps_the_others(self):
        other = ObservingPanel(self.frame)
        patterns.Publisher().registerObserver(
            other.on_event, eventType="eventType"
        )
        patterns.Publisher().remove_observers_of(self.panel)
        self.assertEqual([other.on_event], patterns.Publisher().observers())


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

    def test_remove_observer_for_an_empty_collection_keeps_the_others(self):
        # An empty collection is false, but a source, not "any source"
        first, second = patterns.ObservableList(), patterns.ObservableList()
        for source in first, second:
            self.publisher.registerObserver(
                self.onEvent, eventType="eventType", eventSource=source
            )
        self.publisher.removeObserver(
            self.onEvent, eventType="eventType", eventSource=first
        )
        patterns.Event("eventType", second).send()
        self.assertEqual(1, len(self.events))

    def test_publisher_is_singleton(self):
        another_publisher = patterns.Publisher()
        self.assertTrue(self.publisher is another_publisher)

    def test_register_observer(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def test_register_observer_twice(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def test_register_observer_for_two_different_types(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def test_register_observer_list_method(self):
        """A previous implementation of Publisher used sets. This caused a
        "TypeError: list objects are unhashable" whenever one tried to use
        an instance method of a list (sub)class as callback."""

        class List(list):
            def onEvent(self, *args):
                pass  # pragma: no cover

        self.publisher.registerObserver(List().onEvent, eventType="eventType")

    def test_get_observers_without_observers(self):
        self.assertEqual([], self.publisher.observers())

    def test_get_observers_for_specific_event_type_without_observers(self):
        self.assertEqual([], self.publisher.observers(eventType="eventType"))

    def test_get_observers_for_specific_event_type_with_observer(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.assertEqual(
            [self.onEvent], self.publisher.observers(eventType="eventType")
        )

    def test_get_observers_for_event_type_with_different_types_registered(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        self.assertEqual(
            [self.onEvent], self.publisher.observers(eventType="eventType1")
        )

    def test_notify_observers_without_observers(self):
        patterns.Event("eventType", self).send()
        self.assertFalse(self.events)

    def test_notify_observers_with_observer_for_different_event_type(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        patterns.Event("eventType2", self).send()
        self.assertFalse(self.events)

    def test_notify_observers_with_observer_for_right_event_type(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType", self).send()
        self.assertEqual([patterns.Event("eventType", self)], self.events)

    def test_notify_observers_of_same_and_different_event_types(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent, eventType="eventType2")
        patterns.Event("eventType1", self).send()
        self.assertEqual([patterns.Event("eventType1", self)], self.events)

    def test_notify_observers_for_different_event_types_with_one_event(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType1")
        self.publisher.registerObserver(self.onEvent2, eventType="eventType2")
        event = patterns.Event("eventType1", self)
        event.addSource(self, type="eventType2")
        event.send()
        self.assertEqual([patterns.Event("eventType1", self)], self.events)
        self.assertEqual([patterns.Event("eventType2", self)], self.events2)

    def test_notify_observers_with_event_without_types(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event().send()
        self.assertFalse(self.events)

    def test_notify_observers_with_event_without_sources(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType").send()
        self.assertFalse(self.events)

    def test_remove_observer_for_any_event_type_not_registered_before(self):
        self.publisher.removeObserver(self.onEvent)
        self.assertEqual([], self.publisher.observers())

    def test_remove_observer_for_any_event_type_registered_before(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent)
        self.assertEqual([], self.publisher.observers())

    def test_remove_observer_for_specific_type_registered_for_same_type(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent, eventType="eventType")
        self.assertEqual([], self.publisher.observers())

    def test_remove_observer_for_specific_type_registered_for_different_type(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.removeObserver(self.onEvent, eventType="otherType")
        self.assertEqual([self.onEvent], self.publisher.observers())

    def test_remove_observer_for_type_registered_for_other_observed_type(
        self,
    ):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.registerObserver(self.onEvent2, eventType="otherType")
        self.publisher.removeObserver(self.onEvent, eventType="otherType")
        self.assertEqual([self.onEvent], self.publisher.observers("eventType"))

    def test_clear(self):
        self.publisher.registerObserver(self.onEvent, eventType="eventType")
        self.publisher.clear()
        self.assertEqual([], self.publisher.observers())

    def test_register_observer_for_specific_source(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        patterns.Event("eventType", "observable2").send()
        self.assertFalse(self.events)

    def test_notify_observer_for_specific_source(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        event = patterns.Event("eventType", "observable1")
        event.send()
        self.assertEqual([event], self.events)

    def test_remove_observer_registered_for_specific_source(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.removeObserver(self.onEvent)
        event = patterns.Event("eventType", "observable1")
        event.send()
        self.assertFalse(self.events)

    def test_remove_observer_for_event_type_registered_for_a_source(
        self,
    ):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.removeObserver(self.onEvent, eventType="eventType")
        patterns.Event("eventType", "observable1").send()
        self.assertFalse(self.events)

    def test_remove_observer_for_specific_event_source(self):
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable1"
        )
        self.publisher.registerObserver(
            self.onEvent, eventType="eventType", eventSource="observable2"
        )
        self.publisher.removeObserver(self.onEvent, eventSource="observable1")
        patterns.Event("eventType", "observable2").send()
        self.assertTrue(self.events)

    def test_remove_observer_for_specific_event_type_and_source(self):
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

    def test_remove_observer_for_event_type_and_source_keeps_other_sources(
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


class Source:
    """An event source that compares equal to another with its key, as
    domain objects compare by their id."""

    def __init__(self, key="source"):
        self.key = key

    def __eq__(self, other):
        return isinstance(other, Source) and self.key == other.key

    def __hash__(self):
        return hash(self.key)


class SubscribedToItself:
    def __init__(self):
        patterns.Publisher().registerObserver(
            self.on_event, eventType="eventType", eventSource=self
        )

    def on_event(self, event):
        pass


class Listener:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)


class PublisherCleanupTest(test.TestCase):
    """The Publisher cleans up after itself: it keeps no source or
    subscriber alive, and drops a subscription once either is freed
    (To Do 71)."""

    def setUp(self):
        super().setUp()
        self.publisher = patterns.Publisher()
        self.listener = Listener()

    def subscribe(self, source, listener=None):
        self.publisher.registerObserver(
            (listener or self.listener).on_event,
            eventType="eventType",
            eventSource=source,
        )

    def test_a_source_is_not_kept(self):
        source = Source()
        self.subscribe(source)
        source = weakref.ref(source)
        gc.collect()
        self.assertIsNone(source())

    def test_an_object_subscribed_to_its_own_events_is_freed(self):
        # As the settings were (P151)
        subscribed = weakref.ref(SubscribedToItself())
        gc.collect()
        self.assertIsNone(subscribed())

    def test_a_freed_sources_subscriptions_go(self):
        source = Source()
        self.subscribe(source)
        del source
        gc.collect()
        self.assertEqual([], self.publisher.observers())

    def test_a_freed_subscriber_goes_without_an_event(self):
        source = Source()
        self.subscribe(source)
        self.listener = None
        gc.collect()
        self.publisher.observers()  # Any call
        # pylint: disable=W0212
        self.assertEqual({}, self.publisher._Publisher__observers)

    def test_a_kept_source_still_reaches_its_subscriber(self):
        source = Source()
        self.subscribe(source)
        gc.collect()
        patterns.Event("eventType", source).send()
        self.assertEqual(1, len(self.listener.events))

    def test_an_equal_source_keeps_the_subscriptions_of_the_first(self):
        # Equal sources always shared their subscriptions
        first, second = Source(), Source()
        other = Listener()
        self.subscribe(first)
        self.subscribe(second, other)
        del first
        gc.collect()
        patterns.Event("eventType", second).send()
        self.assertEqual(
            (1, 1), (len(self.listener.events), len(other.events))
        )

    def test_a_value_source_stays(self):
        # A str cannot be held weakly and is never freed
        self.subscribe("source")
        gc.collect()
        patterns.Event("eventType", "source").send()
        self.assertEqual(1, len(self.listener.events))
