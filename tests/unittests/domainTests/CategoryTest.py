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

import test, wx
from taskcoachlib import patterns
from taskcoachlib.domain import category, categorizable, note, date


class CategoryTest(test.TestCase):
    def setUp(self):
        self.category = category.Category(subject="category")
        self.subCategory = category.Category(subject="subcategory")
        self.categorizable = categorizable.CategorizableCompositeObject(
            subject="parent"
        )
        self.child = categorizable.CategorizableCompositeObject(
            subject="child"
        )

    # State:

    def testGetState_Subject(self):
        self.assertEqual("category", self.category.__getstate__()["subject"])

    def testGetState_Description(self):
        self.assertEqual("", self.category.__getstate__()["description"])

    def testGetState_ForegroundColor(self):
        self.assertEqual(None, self.category.__getstate__()["fgColor"])

    def testGetState_BackgroundColor(self):
        self.assertEqual(None, self.category.__getstate__()["bgColor"])

    def testGetState_ExclusiveSubcategories(self):
        self.assertEqual(
            False, self.category.__getstate__()["exclusiveSubcategories"]
        )

    def testSetState_ExclusiveSubcategories(self):
        state = self.category.__getstate__()
        self.category.makeSubcategoriesExclusive()
        self.category.__setstate__(state)
        self.assertFalse(self.category.hasExclusiveSubcategories())

    def testSetState_OneNotification(self):
        newState = dict(
            subject="New subject",
            description="New description",
            fgColor=wx.WHITE,
            bgColor=wx.RED,
            font=wx.SWISS_FONT,
            status=self.category.STATUS_DELETED,
            parent=None,
            children=[self.subCategory],
            id=self.category.id(),
            categorizables=[self.categorizable],
            notes=[],
            attachments=[],
            filtered=True,
            exclusiveSubcategories=True,
            icon="icon",
            selectedIcon="selected",
            creationDateTime=date.Now(),
            modificationDateTime=date.Now(),
            ordering=42,
        )
        for eventType in self.category.modificationEventTypes():
            self.registerObserver(eventType)
        self.category.__setstate__(newState)
        self.assertEqual(1, len(self.events))

    # Subject:

    def testCreateWithSubject(self):
        self.assertEqual("category", self.category.subject())

    def testSetSubject(self):
        self.category.setSubject("New")
        self.assertEqual("New", self.category.subject())

    def testSetSubjectNotification(self):
        eventType = category.Category.subjectChangedEventType()
        self.registerObserver(eventType)
        self.category.setSubject("New")
        self.assertEqual(
            [patterns.Event(eventType, self.category, "New")], self.events
        )

    def testSetSubjectCausesNoNotificationWhenNewSubjectEqualsOldSubject(self):
        eventType = category.Category.subjectChangedEventType()
        self.registerObserver(eventType)
        self.category.setSubject(self.category.subject())
        self.assertFalse(self.events)

    # Description:

    def testCreateWithDescription(self):
        aCategory = category.Category("subject", description="Description")
        self.assertEqual("Description", aCategory.description())

    # Categorizables:

    def testNoCategorizablesAfterCreation(self):
        self.assertEqual(set(), self.category.categorizables())

    def testAddCategorizable(self):
        self.category.addCategorizable(self.categorizable)
        self.assertEqual(
            set([self.categorizable]), self.category.categorizables()
        )

    def testAddCategorizableDoesNotAddCategoryToCategorizable(self):
        self.category.addCategorizable(self.categorizable)
        self.assertEqual(set([]), self.categorizable.categories())

    def testAddCategorizableTwice(self):
        self.category.addCategorizable(self.categorizable)
        self.category.addCategorizable(self.categorizable)
        self.assertEqual(
            set([self.categorizable]), self.category.categorizables()
        )

    def testRemoveCategorizable(self):
        self.category.addCategorizable(self.categorizable)
        self.category.removeCategorizable(self.categorizable)
        self.assertFalse(self.category.categorizables())
        self.assertFalse(self.categorizable.categories())

    def testRemovecategorizableThatsNotInThisCategory(self):
        self.category.removeCategorizable(self.categorizable)
        self.assertFalse(self.category.categorizables())
        self.assertFalse(self.categorizable.categories())

    def testCreateWithCategorizable(self):
        cat = category.Category("category", [self.categorizable])
        self.assertEqual(set([self.categorizable]), cat.categorizables())

    def testCreateWithCategorizableDoesNotSetCategorizableCategories(self):
        category.Category("category", [self.categorizable])
        self.assertEqual(set([]), self.categorizable.categories())

    def testAddCategorizableToSubCategory(self):
        self.category.addChild(self.subCategory)
        self.subCategory.addCategorizable(self.categorizable)
        self.assertEqual(
            set([self.categorizable]),
            self.category.categorizables(recursive=True),
        )

    # Subcategories:

    def testAddSubCategory(self):
        self.category.addChild(self.subCategory)
        self.assertEqual([self.subCategory], self.category.children())

    def testCreateWithSubCategories(self):
        cat = category.Category("category", children=[self.subCategory])
        self.assertEqual([self.subCategory], cat.children())

    def testParentOfSubCategory(self):
        self.category.addChild(self.subCategory)
        self.assertEqual(self.category, self.subCategory.parent())

    def testParentOfRootCategory(self):
        self.assertEqual(None, self.category.parent())

    # Equality:

    def testEquality_SameSubjectAndNoParents(self):
        self.assertNotEqual(
            category.Category(self.category.subject()), self.category
        )
        self.assertNotEqual(
            self.category, category.Category(self.category.subject())
        )

    def testEquality_SameSubjectDifferentParents(self):
        self.category.addChild(self.subCategory)
        self.assertNotEqual(
            category.Category(self.subCategory.subject()), self.subCategory
        )

    # Filter:

    def testNotFilteredByDefault(self):
        self.assertFalse(self.category.isFiltered())

    def testSetFilteredOn(self):
        self.category.setFiltered()
        self.assertTrue(self.category.isFiltered())

    def testSetFilteredOff(self):
        self.category.setFiltered(False)
        self.assertFalse(self.category.isFiltered())

    def testSetFilteredViaConstructor(self):
        filteredCategory = category.Category("test", filtered=True)
        self.assertTrue(filteredCategory.isFiltered())

    # Copy:

    def testCopy_SubjectIsCopied(self):
        self.category.setSubject("New subject")
        copy = self.category.copy()
        self.assertEqual(copy.subject(), self.category.subject())

    def testCopy_IdIsDifferent(self):
        copy = self.category.copy()
        self.assertNotEqual(copy.id(), self.category.id())

    def testCopy_StatusIsNew(self):
        self.category.markDeleted()
        copy = self.category.copy()
        self.assertEqual(copy.getStatus(), copy.STATUS_NEW)

    # pylint: disable=E1101

    def testCopy_SubjectIsDifferentFromOriginalSubject(self):
        self.subCategory.setSubject("New subject")
        self.category.addChild(self.subCategory)
        copy = self.category.copy()
        self.subCategory.setSubject("Other subject")
        self.assertEqual("New subject", copy.children()[0].subject())

    def testCopy_FilteredStatusIsCopied(self):
        self.category.setFiltered()
        copy = self.category.copy()
        self.assertEqual(copy.isFiltered(), self.category.isFiltered())

    def testCopy_CategorizablesAreCopied(self):
        self.category.addCategorizable(self.categorizable)
        copy = self.category.copy()
        self.assertEqual(copy.categorizables(), self.category.categorizables())

    def testCopy_CategorizablesAreCopiedIntoADifferentList(self):
        copy = self.category.copy()
        self.category.addCategorizable(self.categorizable)
        self.assertFalse(self.categorizable in copy.categorizables())

    def testCopy_ChildrenAreCopied(self):
        self.category.addChild(self.subCategory)
        copy = self.category.copy()
        self.assertEqual(
            self.subCategory.subject(), copy.children()[0].subject()
        )

    # Notifications:

    def testAddTaskNotification(self):
        eventType = category.Category.categorizableAddedEventType()
        self.registerObserver(eventType)
        self.category.addCategorizable(self.categorizable)
        self.assertEqual(1, len(self.events))

    def testRemoveTaskNotification(self):
        eventType = category.Category.categorizableRemovedEventType()
        self.registerObserver(eventType)
        self.category.addCategorizable(self.categorizable)
        self.category.removeCategorizable(self.categorizable)
        self.assertEqual(1, len(self.events))

    # Color:

    def testGetDefaultForegroundColor(self):
        self.assertEqual(None, self.category.foregroundColor())

    def testGetDefaultBackgroundColor(self):
        self.assertEqual(None, self.category.backgroundColor())

    def testSetForegroundColor(self):
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, self.category.foregroundColor())

    def testSetBackgroundColor(self):
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.category.backgroundColor())

    def testCopy_ForegroundColorIsCopied(self):
        self.category.setForegroundColor(wx.RED)
        copy = self.category.copy()
        self.assertEqual(wx.RED, copy.foregroundColor())

    def testCopy_BackgroundColorIsCopied(self):
        self.category.setBackgroundColor(wx.RED)
        copy = self.category.copy()
        self.assertEqual(wx.RED, copy.backgroundColor())

    def testForegroundColorChangeNotification(self):
        eventType = category.Category.appearanceChangedEventType()
        self.registerObserver(eventType)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testBackgroundColorChangeNotification(self):
        eventType = category.Category.appearanceChangedEventType()
        self.registerObserver(eventType)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testSubCategoryWithoutForegroundColorHasParentForegroundColor(self):
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.subCategory.foregroundColor(recursive=True)
        )

    def testSubCategoryWithoutBackgroundColorHasParentBackgroundColor(self):
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.subCategory.backgroundColor(recursive=True)
        )

    def testSubCategoryWithoutForegroundColorHasNoOwnForegroundColor(self):
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(None, self.subCategory.foregroundColor())

    def testSubCategoryWithoutBackgroundColorHasNoOwnBackgroundColor(self):
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(None, self.subCategory.backgroundColor())

    def testParentForegroundColorChangeNotification(self):
        eventType = category.Category.appearanceChangedEventType()
        self.registerObserver(eventType)
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testParentBackgroundColorChangeNotification(self):
        eventType = category.Category.appearanceChangedEventType()
        self.registerObserver(eventType)
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    # Icon:

    def testIconChangedNotification(self):
        eventType = (
            categorizable.CategorizableCompositeObject.appearanceChangedEventType()
        )
        self.registerObserver(eventType)
        self.category.addCategorizable(self.categorizable)
        self.category.set_icon_id("icon")
        self.assertEqual(
            [patterns.Event(eventType, self.categorizable)], self.events
        )

    def testSelectedIconChangedNotification(self):
        eventType = (
            categorizable.CategorizableCompositeObject.appearanceChangedEventType()
        )
        self.registerObserver(eventType)
        self.category.addCategorizable(self.categorizable)
        self.category.set_selected_icon_id("icon")
        self.assertEqual(
            [patterns.Event(eventType, self.categorizable)], self.events
        )

    # Notes:

    def testAddNote(self):
        aNote = note.Note(subject="Note")
        self.category.addNote(aNote)
        self.assertEqual([aNote], self.category.notes())

    # Exclusive subcategories:

    def testSubcategoriesAreNotExclusiveByDefault(self):
        self.assertFalse(self.category.hasExclusiveSubcategories())

    def testMakeSubcategoriesExclusive(self):
        self.category.makeSubcategoriesExclusive()
        self.assertTrue(self.category.hasExclusiveSubcategories())

    def testMakeSubcategoriesNotExclusive(self):
        self.category.makeSubcategoriesExclusive()
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.category.hasExclusiveSubcategories())

    def testCreateWithExclusiveSubcategories(self):
        aCategory = category.Category("subject", exclusiveSubcategories=True)
        self.assertTrue(aCategory.hasExclusiveSubcategories())

    def testExclusiveSubcategoriesNotification(self):
        eventType = category.Category.exclusiveSubcategoriesChangedEventType()
        self.registerObserver(eventType)
        self.category.makeSubcategoriesExclusive()
        self.assertEqual(
            [patterns.Event(eventType, self.category, True)], self.events
        )

    def testNoExclusiveSubcategoriesNotificationWhenNotChanged(self):
        eventType = category.Category.exclusiveSubcategoriesChangedEventType()
        self.registerObserver(eventType)
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.events)

    def testMakeSubcategoriesExclusiveUnchecksAllSubcategories(self):
        self.subCategory.setFiltered(True)
        self.category.addChild(self.subCategory)
        self.category.makeSubcategoriesExclusive(True)
        self.assertFalse(self.subCategory.isFiltered())

    def testMakeSubcategoriesNonExclusiveUnchecksAllSubcategories(self):
        self.category.makeSubcategoriesExclusive(True)
        self.subCategory.setFiltered(True)
        self.category.addChild(self.subCategory)
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.subCategory.isFiltered())

    # Event types:

    def testModificationEventTypes(self):  # pylint: disable=E1003
        self.assertEqual(
            super(category.Category, self.category).modificationEventTypes()
            + [
                self.category.filterChangedEventType(),
                self.category.categorizableAddedEventType(),
                self.category.categorizableRemovedEventType(),
                self.category.exclusiveSubcategoriesChangedEventType(),
                self.category.stylePriorityChangedEventType(),
            ],
            self.category.modificationEventTypes(),
        )
