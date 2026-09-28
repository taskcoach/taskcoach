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

    def set_modification_datetime(self, date_time, event=None):
        self.modification_datetime = date_time


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
    def setUp(self):
        self.object = base.Object()
        self.subclassObject = ObjectSubclass()
        self.eventsReceived = []
        for eventType in (
            self.object.subjectChangedEventType(),
            self.object.descriptionChangedEventType(),
            self.object.appearanceChangedEventType(),
        ):
            patterns.Publisher().registerObserver(self.onEvent, eventType)

    def onEvent(self, event):
        self.eventsReceived.append(event)

    # Basic tests:

    def testCyclicReference(self):
        domainObject = base.Object()
        weak = weakref.ref(domainObject)
        del domainObject  # Assuming CPython
        self.assertTrue(weak() is None)

    # Custom attributes tests:

    def testCustomAttributes(self):
        self.object.setDescription(
            "\n[mailto:cc=foo@bar.com]\n[mailto:cc=baz@spam.com]\n"
        )
        self.assertEqual(
            self.object.customAttributes("mailto"),
            set(["cc=foo@bar.com", "cc=baz@spam.com"]),
        )

    # Id tests:

    def testSetIdOnCreation(self):
        domainObject = base.Object(id="123")
        self.assertEqual("123", domainObject.id())

    def testIdIsAString(self):
        self.assertEqual(type(""), type(self.object.id()))

    def test_a_new_id_is_a_random_uuid(self):
        self.assertEqual(4, uuid.UUID(self.object.id()).version)

    def testDifferentObjectsHaveDifferentIds(self):
        self.assertNotEqual(base.Object().id(), self.object.id())

    def testCopyHasDifferentId(self):
        objectId = self.object.id()  # Force generation of id
        copy = self.object.copy()
        self.assertNotEqual(copy.id(), objectId)

    # Creation date/time tests:

    def testSetCreationDateTimeOnCreation(self):
        creation_datetime = date.DateTime(2012, 12, 12, 10, 0, 0)
        domain_object = base.Object(creationDateTime=creation_datetime)
        self.assertEqual(creation_datetime, domain_object.creationDateTime())

    def testCreationDateTimeIsSetWhenNotPassed(self):
        now = date.Now()
        creation_datetime = self.object.creationDateTime()
        minute = date.TimeDelta(seconds=60)
        self.assertTrue(now - minute < creation_datetime < now + minute)
        self.assertIsInstance(creation_datetime, date.Timestamp)

    # Modification date/time tests:

    def testSetModificationDateTimeOnCreation(self):
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

    def testSubjectIsEmptyByDefault(self):
        self.assertEqual("", self.object.subject())

    def testSetSubjectOnCreation(self):
        domainObject = base.Object(subject="Hi")
        self.assertEqual("Hi", domainObject.subject())

    def testSetSubject(self):
        self.object.setSubject("New subject")
        self.assertEqual("New subject", self.object.subject())

    def testSetSubjectCausesNotification(self):
        self.object.setSubject("New subject")
        self.assertEqual(
            patterns.Event(
                self.object.subjectChangedEventType(),
                self.object,
                "New subject",
            ),
            self.eventsReceived[0],
        )

    def testSetSubjectUnchangedDoesNotCauseNotification(self):
        self.object.setSubject("")
        self.assertFalse(self.eventsReceived)

    def testSubjectChangedNotificationIsDifferentForSubclass(self):
        self.subclassObject.setSubject("New")
        self.assertFalse(self.eventsReceived)

    # Description tests:

    def testDescriptionIsEmptyByDefault(self):
        self.assertFalse(self.object.description())

    def testSetDescriptionOnCreation(self):
        domainObject = base.Object(description="Hi")
        self.assertEqual("Hi", domainObject.description())

    def testSetDescription(self):
        self.object.setDescription("New description")
        self.assertEqual("New description", self.object.description())

    def testSetDescriptionCausesNotification(self):
        self.object.setDescription("New description")
        self.assertEqual(
            patterns.Event(
                self.object.descriptionChangedEventType(),
                self.object,
                "New description",
            ),
            self.eventsReceived[0],
        )

    def testSetDescriptionUnchangedDoesNotCauseNotification(self):
        self.object.setDescription("")
        self.assertFalse(self.eventsReceived)

    def testDescriptionChangedNotificationIsDifferentForSubclass(self):
        self.subclassObject.setDescription("New")
        self.assertFalse(self.eventsReceived)

    # State tests:

    def testGetState(self):
        self.assertEqual(
            dict(
                subject="",
                description="",
                id=self.object.id(),
                fgColor=None,
                bgColor=None,
                font=None,
                icon="",
                creationDateTime=self.object.creationDateTime(),
                modificationDateTime=self.object.modificationDateTime(),
                ordering=self.object.ordering(),
            ),
            self.object.__getstate__(),
        )

    def testSetState(self):
        newState = dict(
            subject="New",
            description="New",
            id=None,
            fgColor=wx.GREEN,
            bgColor=wx.RED,
            font=wx.SWISS_FONT,
            icon="icon",
            creationDateTime=date.DateTime(2012, 12, 12, 12, 0, 0),
            modificationDateTime=date.DateTime(2012, 12, 12, 12, 1, 0),
            ordering=42,
        )
        self.object.__setstate__(newState)
        self.assertEqual(newState, self.object.__getstate__())

    def testSetState_SendsOneNotification(self):
        newState = dict(
            subject="New",
            description="New",
            id=None,
            fgColor=wx.GREEN,
            bgColor=wx.RED,
            font=wx.SWISS_FONT,
            icon="icon",
            creationDateTime=date.DateTime(2013, 1, 1, 0, 0, 0),
            modificationDateTime=date.DateTime(2013, 1, 1, 1, 0, 0),
            ordering=42,
        )
        self.object.__setstate__(newState)
        self.assertEqual(1, len(self.eventsReceived))

    # Copy tests:

    def testCopy_IdIsNotCopied(self):
        copy = self.object.copy()
        self.assertNotEqual(copy.id(), self.object.id())

    def testCopy_CreationDateTimeIsNotCopied(self):
        copy = self.object.copy()
        # Use >= to prevent failures on fast computers with low time granularity
        self.assertTrue(
            copy.creationDateTime() >= self.object.creationDateTime()
        )

    def testCopy_ModificationDateTimeIsNotCopied(self):
        self.object.set_modification_datetime(
            date.DateTime(2013, 1, 1, 1, 0, 0)
        )
        copy = self.object.copy()
        self.assertEqual(copy.creationDateTime(), copy.modificationDateTime())

    def testCopy_SubjectIsCopied(self):
        self.object.setSubject("New subject")
        copy = self.object.copy()
        self.assertEqual(copy.subject(), self.object.subject())

    def testCopy_DescriptionIsCopied(self):
        self.object.setDescription("New description")
        copy = self.object.copy()
        self.assertEqual(copy.description(), self.object.description())

    def testCopy_ForegroundColorIsCopied(self):
        self.object.setForegroundColor(wx.RED)
        copy = self.object.copy()
        self.assertEqual(copy.foregroundColor(), self.object.foregroundColor())

    def testCopy_BackgroundColorIsCopied(self):
        self.object.setBackgroundColor(wx.RED)
        copy = self.object.copy()
        self.assertEqual(copy.backgroundColor(), self.object.backgroundColor())

    def testCopy_FontIsCopied(self):
        self.object.setFont(wx.SWISS_FONT)
        copy = self.object.copy()
        self.assertEqual(copy.font(), self.object.font())

    def testCopy_IconIsCopied(self):
        self.object.set_icon_id("icon")
        copy = self.object.copy()
        self.assertEqual(copy.icon_id(), self.object.icon_id())

    def testCopy_ShouldUseSubclassForCopy(self):
        copy = self.subclassObject.copy()
        self.assertEqual(copy.__class__, self.subclassObject.__class__)

    # Color tests

    def testDefaultForegroundColor(self):
        self.assertEqual(None, self.object.foregroundColor())

    def testSetForegroundColor(self):
        self.object.setForegroundColor(wx.GREEN)
        self.assertEqual(wx.GREEN, self.object.foregroundColor())

    def testSetForegroundColorWithTupleColor(self):
        self.object.setForegroundColor((255, 0, 0, 255))
        self.assertEqual(wx.RED, self.object.foregroundColor())

    def testSetForegroundColorOnCreation(self):
        domainObject = base.Object(fgColor=wx.GREEN)
        self.assertEqual(wx.GREEN, domainObject.foregroundColor())

    def testForegroundColorChangedNotification(self):
        self.object.setForegroundColor(wx.BLACK)
        self.assertEqual(1, len(self.eventsReceived))

    def testDefaultBackgroundColor(self):
        self.assertEqual(None, self.object.backgroundColor())

    def testSetBackgroundColor(self):
        self.object.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.object.backgroundColor())

    def testSetBackgroundColorWithTupleColor(self):
        self.object.setBackgroundColor((255, 0, 0, 255))
        self.assertEqual(wx.RED, self.object.backgroundColor())

    def testSetBackgroundColorOnCreation(self):
        domainObject = base.Object(bgColor=wx.GREEN)
        self.assertEqual(wx.GREEN, domainObject.backgroundColor())

    def testBackgroundColorChangedNotification(self):
        self.object.setBackgroundColor(wx.BLACK)
        self.assertEqual(1, len(self.eventsReceived))

    # Font tests:

    def testDefaultFont(self):
        self.assertEqual(None, self.object.font())

    def testSetFont(self):
        self.object.setFont(wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, self.object.font())

    def testSetFontOnCreation(self):
        domainObject = base.Object(font=wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, domainObject.font())

    def testFontChangedNotification(self):
        self.object.setFont(wx.SWISS_FONT)
        self.assertEqual(1, len(self.eventsReceived))

    # Icon tests:

    def testDefaultIcon(self):
        self.assertEqual("", self.object.icon_id())

    def testSetIcon(self):
        self.object.set_icon_id("icon")
        self.assertEqual("icon", self.object.icon_id())

    def testSetIconOnCreation(self):
        domainObject = base.Object(icon="icon")
        self.assertEqual("icon", domainObject.icon_id())

    def testIconChangedNotification(self):
        self.object.set_icon_id("icon")
        self.assertEqual(1, len(self.eventsReceived))

    # Event types:

    def testModificationEventTypes(self):
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
        self.child.setParent(self.compositeObject)

    def removeChild(self):
        self.compositeObject.removeChild(self.child)

    def testIsExpanded(self):
        self.assertFalse(self.compositeObject.isExpanded())

    def testExpand(self):
        self.compositeObject.expand()
        self.assertTrue(self.compositeObject.isExpanded())

    def testCollapse(self):
        self.compositeObject.expand()
        self.compositeObject.expand(False)
        self.assertFalse(self.compositeObject.isExpanded())

    def testSetExpansionStateViaConstructor(self):
        compositeObject = base.CompositeObject(expandedContexts=["None"])
        self.assertTrue(compositeObject.isExpanded())

    def testSetExpansionStatesViaConstructor(self):
        compositeObject = base.CompositeObject(
            expandedContexts=["context1", "context2"]
        )
        self.assertEqual(
            ["context1", "context2"],
            sorted(compositeObject.expandedContexts()),
        )

    def testExpandInContext_DoesNotChangeExpansionStateInDefaultContext(self):
        self.compositeObject.expand(context="some_viewer")
        self.assertFalse(self.compositeObject.isExpanded())

    def testExpandInContext_DoesChangeExpansionStateInGivenContext(self):
        self.compositeObject.expand(context="some_viewer")
        self.assertTrue(self.compositeObject.isExpanded(context="some_viewer"))

    def testIsExpandedInUnknownContext_ReturnsFalse(self):
        self.assertFalse(self.compositeObject.isExpanded(context="whatever"))

    def testGetContextsWhereExpanded(self):
        self.assertEqual([], self.compositeObject.expandedContexts())

    def testRecursiveSubject(self):
        self.compositeObject.setSubject("parent")
        self.addChild(subject="child")
        self.assertEqual("parent -> child", self.child.subject(recursive=True))

    def testSubjectNotification(self):
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

    def test_composite_with_children_shows_plural_icon(self):
        self.compositeObject.set_icon_id("nuvola_actions_ledblue")
        self.assertEqual(
            "nuvola_actions_ledblue", self.compositeObject.shown_icon_id()
        )
        self.addChild()
        self.assertEqual(
            "nuvola_mimetypes_inode-directory",
            self.compositeObject.shown_icon_id(),
        )
        self.assertEqual(
            "nuvola_actions_ledblue", self.compositeObject.icon_id()
        )

    def test_own_icon_of_composite_without_children_is_not_singularized(self):
        self.compositeObject.set_icon_id("nuvola_mimetypes_inode-directory")
        self.assertEqual(
            "nuvola_mimetypes_inode-directory",
            self.compositeObject.shown_icon_id(),
        )

    def test_parent_shows_singular_icon_after_child_removed(self):
        self.compositeObject.set_icon_id("nuvola_actions_ledblue")
        self.addChild()
        self.assertEqual(
            "nuvola_mimetypes_inode-directory",
            self.compositeObject.shown_icon_id(),
        )
        self.removeChild()
        self.assertEqual(
            "nuvola_actions_ledblue", self.compositeObject.shown_icon_id()
        )

    def testCopy(self):
        self.compositeObject.expand(context="some_viewer")
        copy = self.compositeObject.copy()
        # pylint: disable=E1101
        self.assertEqual(
            copy.expandedContexts(), self.compositeObject.expandedContexts()
        )
        self.compositeObject.expand(context="another_viewer")
        self.assertFalse("another_viewer" in copy.expandedContexts())

    def testModificationEventTypes(self):
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

    def testLookupByIdWhenCollectionIsEmptyRaisesIndexError(self):
        self.assertRaises(IndexError, self.collection.getObjectById, "id")

    def testLookupIdWhenObjectIsInCollection(self):
        domainObject = base.CompositeObject()
        self.collection.append(domainObject)
        self.assertEqual(
            domainObject, self.collection.getObjectById(domainObject.id())
        )
