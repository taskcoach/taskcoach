# -*- coding: utf-8 -*-

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

import wx
import test
import uuid
import weakref
from taskcoachlib import patterns
from taskcoachlib.domain import base, date


class AttributeOwner:
    def __init__(self):
        self.changes = 0
        self.modification_datetime = date.DateTime.min
        self.attribute = base.Attribute("old", self, self.on_change)
        self.computed_attribute = base.Attribute(
            "old", self, self.on_change, volatile=True
        )

    def on_change(self, event):
        self.changes += 1

    def modified_now(self, event=None):
        self.modification_datetime = date.Now()


class AttributeTest(test.TestCase):
    """An unchanged value creates no event: the master loop sets
    thousands of them."""

    def setUp(self):
        self.owner = AttributeOwner()
        self.events_created = 0
        self.original_event_class = patterns.observer.Event
        test_case = self

        class CountingEvent(self.original_event_class):
            def __init__(self, *args, **kwargs):
                test_case.events_created += 1
                super().__init__(*args, **kwargs)

        patterns.observer.Event = CountingEvent

    def tearDown(self):
        patterns.observer.Event = self.original_event_class
        super().tearDown()

    def test_unchanged_value_creates_no_event(self):
        self.assertFalse(self.owner.attribute.set("old"))
        self.assertEqual((0, 0), (self.events_created, self.owner.changes))

    def test_changed_value_calls_back_with_one_event(self):
        self.assertTrue(self.owner.attribute.set("new"))
        self.assertEqual("new", self.owner.attribute.get())
        self.assertEqual((1, 1), (self.events_created, self.owner.changes))

    def test_changed_value_sets_the_modification_date(self):
        before = date.Now()
        self.owner.attribute.set("new")
        self.assertTrue(before <= self.owner.modification_datetime)

    def test_unchanged_value_keeps_the_modification_date(self):
        self.owner.attribute.set("old")
        self.assertEqual(date.DateTime.min, self.owner.modification_datetime)

    def test_computed_value_keeps_the_modification_date(self):
        self.owner.computed_attribute.set("new")
        self.assertEqual(date.DateTime.min, self.owner.modification_datetime)


class ObjectSubclass(base.Object):
    pass


class ObjectTest(test.TestCase):

    def test_a_subject_is_one_line_of_text(self):
        # docs/ATTRIBUTE_PATTERN.md, Text
        item = base.Object(subject="a\tb\r\nc\x00d")
        self.assertEqual("a b cd", item.subject())
        item.setSubject("e\nf\x0c")
        self.assertEqual("e f", item.subject())

    def test_a_description_keeps_tabs_and_line_breaks(self):
        item = base.Object(description="a\tb\r\nc\x00d\x85\ud800")
        self.assertEqual("a\tb\r\ncd", item.description())
        item.setDescription("e\x0cf\ufffe")
        self.assertEqual("ef", item.description())

    def test_preview_hidden_by_default(self):
        self.assertFalse(self.object.is_preview_shown())

    def test_show_preview(self):
        self.object.show_preview()
        self.assertTrue(self.object.is_preview_shown())

    def test_hide_preview(self):
        self.object.show_preview()
        self.object.show_preview(False)
        self.assertFalse(self.object.is_preview_shown())

    def test_set_preview_state_via_constructor(self):
        self.assertTrue(base.Object(previewShown=True).is_preview_shown())

    def test_show_preview_sets_no_modification_date(self):
        before = self.object.modificationDateTime()
        self.object.show_preview()
        self.assertEqual(before, self.object.modificationDateTime())

    def test_show_preview_sends_event(self):
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=base.Object.preview_shown_changed_event_type(),
        )
        self.object.show_preview()
        self.assertEqual(1, len(self.eventsReceived))

    def setUp(self):
        self.object = base.Object()
        self.subclassObject = ObjectSubclass()
        self.eventsReceived = []
        for event_type in (
            self.object.subjectChangedEventType(),
            self.object.descriptionChangedEventType(),
            self.object.appearanceChangedEventType(),
        ):
            patterns.Publisher().registerObserver(self.onEvent, event_type)

    def onEvent(self, event):
        self.eventsReceived.append(event)

    # Basic tests:

    def test_cyclic_reference(self):
        domain_object = base.Object()
        weak = weakref.ref(domain_object)
        del domain_object  # Assuming CPython
        self.assertTrue(weak() is None)

    # Custom attributes tests:

    def test_custom_attributes(self):
        self.object.setDescription(
            "\n[mailto:cc=foo@bar.com]\n[mailto:cc=baz@spam.com]\n"
        )
        self.assertEqual(
            self.object.customAttributes("mailto"),
            set(["cc=foo@bar.com", "cc=baz@spam.com"]),
        )

    # Id tests:

    def test_set_id_on_creation(self):
        domain_object = base.Object(id="123")
        self.assertEqual("123", domain_object.id())

    def test_id_is_a_string(self):
        self.assertEqual(type(""), type(self.object.id()))

    def test_a_new_id_is_a_random_uuid(self):
        self.assertEqual(4, uuid.UUID(self.object.id()).version)

    def test_different_objects_have_different_ids(self):
        self.assertNotEqual(base.Object().id(), self.object.id())

    def test_copy_has_different_id(self):
        object_id = self.object.id()  # Force generation of id
        copy = self.object.copy()
        self.assertNotEqual(copy.id(), object_id)

    # Creation date/time tests:

    def test_set_creation_date_time_on_creation(self):
        creation_datetime = date.DateTime(2012, 12, 12, 10, 0, 0)
        domain_object = base.Object(creationDateTime=creation_datetime)
        self.assertEqual(creation_datetime, domain_object.creationDateTime())

    def test_creation_date_time_is_set_when_not_passed(self):
        now = date.Now()
        creation_datetime = self.object.creationDateTime()
        minute = date.TimeDelta(seconds=60)
        self.assertTrue(now - minute < creation_datetime < now + minute)
        self.assertIsInstance(creation_datetime, date.Timestamp)

    # Modification date/time tests:

    def test_set_modification_date_time_on_creation(self):
        modification_datetime = date.DateTime(2012, 12, 12, 10, 0, 0)
        domain_object = base.Object(modificationDateTime=modification_datetime)
        self.assertEqual(
            modification_datetime, domain_object.modificationDateTime()
        )

    def test_modification_date_starts_at_creation(self):
        self.assertEqual(
            self.object.creationDateTime(), self.object.modificationDateTime()
        )

    def test_stored_field_change_sets_the_modification_date(self):
        event_type = self.object.modification_datetime_changed_event_type()
        patterns.Publisher().registerObserver(
            self.onEvent, event_type, eventSource=self.object
        )
        before = date.Now()
        self.object.setSubject("New subject")
        modification_datetime = self.object.modificationDateTime()
        self.assertIsInstance(modification_datetime, date.Timestamp)
        self.assertTrue(before <= modification_datetime)
        self.assertEqual(
            [modification_datetime],
            [
                event.value(self.object, event_type)
                for event in self.eventsReceived
                if event_type in event.types()
            ],
        )

    def test_computed_style_keeps_the_modification_date(self):
        self.object.setDerivedFgColor(wx.RED, "category")
        self.object.setEffectiveFgColor(wx.RED, wx.BLACK, "category")
        self.assertEqual(wx.RED, self.object.effectiveFgColor())
        self.assertEqual(
            self.object.creationDateTime(), self.object.modificationDateTime()
        )

    # Subject tests:

    def test_subject_is_empty_by_default(self):
        self.assertEqual("", self.object.subject())

    def test_set_subject_on_creation(self):
        domain_object = base.Object(subject="Hi")
        self.assertEqual("Hi", domain_object.subject())

    def test_set_subject(self):
        self.object.setSubject("New subject")
        self.assertEqual("New subject", self.object.subject())

    def test_set_subject_causes_notification(self):
        self.object.setSubject("New subject")
        self.assertEqual(
            patterns.Event(
                self.object.subjectChangedEventType(),
                self.object,
                "New subject",
            ),
            self.eventsReceived[0],
        )

    def test_set_subject_unchanged_does_not_cause_notification(self):
        self.object.setSubject("")
        self.assertFalse(self.eventsReceived)

    def test_subject_changed_notification_is_different_for_subclass(self):
        self.subclassObject.setSubject("New")
        self.assertFalse(self.eventsReceived)

    # Description tests:

    def test_description_is_empty_by_default(self):
        self.assertFalse(self.object.description())

    def test_set_description_on_creation(self):
        domain_object = base.Object(description="Hi")
        self.assertEqual("Hi", domain_object.description())

    def test_set_description(self):
        self.object.setDescription("New description")
        self.assertEqual("New description", self.object.description())

    def test_set_description_causes_notification(self):
        self.object.setDescription("New description")
        self.assertEqual(
            patterns.Event(
                self.object.descriptionChangedEventType(),
                self.object,
                "New description",
            ),
            self.eventsReceived[0],
        )

    def test_set_description_unchanged_does_not_cause_notification(self):
        self.object.setDescription("")
        self.assertFalse(self.eventsReceived)

    def test_description_changed_notification_is_different_for_subclass(self):
        self.subclassObject.setDescription("New")
        self.assertFalse(self.eventsReceived)

    # Copy tests:

    def test_copy_id_is_not_copied(self):
        copy = self.object.copy()
        self.assertNotEqual(copy.id(), self.object.id())

    def test_copy_creation_date_time_is_not_copied(self):
        copy = self.object.copy()
        # Use >= to prevent failures on fast computers with low time granularity
        self.assertTrue(
            copy.creationDateTime() >= self.object.creationDateTime()
        )

    def test_copy_modification_date_time_is_not_copied(self):
        self.object.set_modification_datetime(
            date.DateTime(2013, 1, 1, 1, 0, 0)
        )
        copy = self.object.copy()
        self.assertEqual(copy.creationDateTime(), copy.modificationDateTime())

    def test_copy_subject_is_copied(self):
        self.object.setSubject("New subject")
        copy = self.object.copy()
        self.assertEqual(copy.subject(), self.object.subject())

    def test_copy_description_is_copied(self):
        self.object.setDescription("New description")
        copy = self.object.copy()
        self.assertEqual(copy.description(), self.object.description())

    def test_copy_foreground_color_is_copied(self):
        self.object.setForegroundColor(wx.RED)
        copy = self.object.copy()
        self.assertEqual(copy.foregroundColor(), self.object.foregroundColor())

    def test_copy_background_color_is_copied(self):
        self.object.setBackgroundColor(wx.RED)
        copy = self.object.copy()
        self.assertEqual(copy.backgroundColor(), self.object.backgroundColor())

    def test_copy_font_is_copied(self):
        self.object.setFont(wx.SWISS_FONT)
        copy = self.object.copy()
        self.assertEqual(copy.font(), self.object.font())

    def test_copy_icon_is_copied(self):
        self.object.set_icon_id("icon")
        copy = self.object.copy()
        self.assertEqual(copy.icon_id(), self.object.icon_id())

    def test_copy_should_use_subclass_for_copy(self):
        copy = self.subclassObject.copy()
        self.assertEqual(copy.__class__, self.subclassObject.__class__)

    # Color tests

    def test_default_foreground_color(self):
        self.assertEqual(None, self.object.foregroundColor())

    def test_set_foreground_color(self):
        self.object.setForegroundColor(wx.GREEN)
        self.assertEqual(wx.GREEN, self.object.foregroundColor())

    def test_set_foreground_color_with_tuple_color(self):
        self.object.setForegroundColor((255, 0, 0, 255))
        self.assertEqual(wx.RED, self.object.foregroundColor())

    def test_set_foreground_color_on_creation(self):
        domain_object = base.Object(fgColor=wx.GREEN)
        self.assertEqual(wx.GREEN, domain_object.foregroundColor())

    def test_foreground_color_changed_notification(self):
        self.object.setForegroundColor(wx.BLACK)
        self.assertEqual(1, len(self.eventsReceived))

    def test_default_background_color(self):
        self.assertEqual(None, self.object.backgroundColor())

    def test_set_background_color(self):
        self.object.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.object.backgroundColor())

    def test_set_background_color_with_tuple_color(self):
        self.object.setBackgroundColor((255, 0, 0, 255))
        self.assertEqual(wx.RED, self.object.backgroundColor())

    def test_set_background_color_on_creation(self):
        domain_object = base.Object(bgColor=wx.GREEN)
        self.assertEqual(wx.GREEN, domain_object.backgroundColor())

    def test_background_color_changed_notification(self):
        self.object.setBackgroundColor(wx.BLACK)
        self.assertEqual(1, len(self.eventsReceived))

    # Font tests:

    def test_default_font(self):
        self.assertEqual(None, self.object.font())

    def test_set_font(self):
        self.object.setFont(wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, self.object.font())

    def test_set_font_on_creation(self):
        domain_object = base.Object(font=wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, domain_object.font())

    def test_font_changed_notification(self):
        self.object.setFont(wx.SWISS_FONT)
        self.assertEqual(1, len(self.eventsReceived))

    # Icon tests:

    def test_default_icon(self):
        self.assertEqual("", self.object.icon_id())

    def test_set_icon(self):
        self.object.set_icon_id("icon")
        self.assertEqual("icon", self.object.icon_id())

    def test_set_icon_on_creation(self):
        domain_object = base.Object(icon="icon")
        self.assertEqual("icon", domain_object.icon_id())

    def test_icon_changed_notification(self):
        self.object.set_icon_id("icon")
        self.assertEqual(1, len(self.eventsReceived))

    # Event types:

    def test_modification_event_types(self):
        self.assertEqual(
            [
                self.object.subjectChangedEventType(),
                self.object.descriptionChangedEventType(),
                self.object.appearanceChangedEventType(),
                self.object.orderingChangedEventType(),
            ],
            self.object.modificationEventTypes(),
        )


class CompositeObjectTest(test.TestCase):
    def setUp(self):
        self.compositeObject = base.CompositeObject()
        self.child = None
        self.eventsReceived = []

    def onEvent(self, event):
        self.eventsReceived.append(event)

    def addChild(self, **kwargs):
        self.child = base.CompositeObject(**kwargs)
        self.compositeObject.addChild(self.child)
        self.child.set_parent(self.compositeObject)

    def removeChild(self):
        self.compositeObject.removeChild(self.child)

    def test_is_expanded(self):
        self.assertFalse(self.compositeObject.isExpanded())

    def test_expand(self):
        self.compositeObject.expand()
        self.assertTrue(self.compositeObject.isExpanded())

    def test_collapse(self):
        self.compositeObject.expand()
        self.compositeObject.expand(False)
        self.assertFalse(self.compositeObject.isExpanded())

    def test_set_expansion_state_via_constructor(self):
        composite_object = base.CompositeObject(expandedContexts=["None"])
        self.assertTrue(composite_object.isExpanded())

    def test_set_expansion_states_via_constructor(self):
        composite_object = base.CompositeObject(
            expandedContexts=["context1", "context2"]
        )
        self.assertEqual(
            ["context1", "context2"],
            sorted(composite_object.expandedContexts()),
        )

    def test_expand_in_context_keeps_expansion_in_default_context(
        self,
    ):
        self.compositeObject.expand(context="some_viewer")
        self.assertFalse(self.compositeObject.isExpanded())

    def test_expand_in_context_does_change_expansion_state_in_given_context(
        self,
    ):
        self.compositeObject.expand(context="some_viewer")
        self.assertTrue(self.compositeObject.isExpanded(context="some_viewer"))

    def test_is_expanded_in_unknown_context_returns_false(self):
        self.assertFalse(self.compositeObject.isExpanded(context="whatever"))

    def test_get_contexts_where_expanded(self):
        self.assertEqual([], self.compositeObject.expandedContexts())

    def test_recursive_subject(self):
        self.compositeObject.setSubject("parent")
        self.addChild(subject="child")
        self.assertEqual("parent -> child", self.child.subject(recursive=True))

    def test_subject_notification(self):
        self.addChild(subject="child")
        patterns.Publisher().registerObserver(
            self.onEvent,
            eventType=self.compositeObject.subjectChangedEventType(),
            eventSource=self.child,
        )
        self.compositeObject.setSubject("parent")
        self.assertEqual(
            [
                patterns.Event(
                    self.compositeObject.subjectChangedEventType(),
                    self.child,
                    "child",
                )
            ],
            self.eventsReceived,
        )

    def test_icon_is_shown_as_is_with_or_without_children(self):
        # Plural icons are deprecated: a group shows its own icon
        self.compositeObject.set_icon_id("nuvola_actions_ledblue")
        shown = [self.compositeObject.shown_icon_id()]
        self.addChild()
        shown.append(self.compositeObject.shown_icon_id())
        self.removeChild()
        shown.append(self.compositeObject.shown_icon_id())
        self.assertEqual(["nuvola_actions_ledblue"] * 3, shown)

    def test_a_folder_icon_stays_a_folder(self):
        self.compositeObject.set_icon_id("nuvola_mimetypes_inode-directory")
        self.assertEqual(
            "nuvola_mimetypes_inode-directory",
            self.compositeObject.shown_icon_id(),
        )

    def test_copy(self):
        self.compositeObject.expand(context="some_viewer")
        copy = self.compositeObject.copy()
        # pylint: disable=E1101
        self.assertEqual(
            copy.expandedContexts(), self.compositeObject.expandedContexts()
        )
        self.compositeObject.expand(context="another_viewer")
        self.assertFalse("another_viewer" in copy.expandedContexts())

    def test_modification_event_types(self):
        self.assertEqual(
            [
                self.compositeObject.addChildEventType(),
                self.compositeObject.removeChildEventType(),
                self.compositeObject.subjectChangedEventType(),
                self.compositeObject.descriptionChangedEventType(),
                self.compositeObject.appearanceChangedEventType(),
                self.compositeObject.orderingChangedEventType(),
                self.compositeObject.expansionChangedEventType(),
            ],
            self.compositeObject.modificationEventTypes(),
        )


class BaseCollectionTest(test.TestCase):
    def setUp(self):
        self.collection = base.Collection()

    def test_lookup_by_id_when_collection_is_empty_raises_index_error(self):
        self.assertRaises(IndexError, self.collection.getObjectById, "id")

    def test_lookup_id_when_object_is_in_collection(self):
        domain_object = base.CompositeObject()
        self.collection.append(domain_object)
        self.assertEqual(
            domain_object, self.collection.getObjectById(domain_object.id())
        )
