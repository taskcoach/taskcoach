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
from taskcoachlib.domain import category, categorizable


class CategorizableCompositeObjectTest(test.TestCase):
    def setUp(self):
        self.categorizable = categorizable.CategorizableCompositeObject(
            subject="categorizable"
        )
        self.category = category.Category("category")

    categoryAddedEventType = (
        categorizable.CategorizableCompositeObject.categoryAddedEventType()
    )
    categoryRemovedEventType = (
        categorizable.CategorizableCompositeObject.categoryRemovedEventType()
    )
    categorySubjectChangedEventType = (
        categorizable.CategorizableCompositeObject.categorySubjectChangedEventType()
    )
    appearanceChangedEventType = (
        categorizable.CategorizableCompositeObject.appearanceChangedEventType()
    )

    def assertEvent(self, *expectedEventArgs):
        expectedEvent = patterns.Event(*expectedEventArgs)
        self.assertEqual([expectedEvent], self.events)

    def testCategorizableDoesNotBelongToAnyCategoryByDefault(self):
        for recursive in False, True:
            for upwards in False, True:
                self.assertFalse(
                    self.categorizable.categories(
                        recursive=recursive, upwards=upwards
                    )
                )

    def testCategorizableHasNoForegroundColorByDefault(self):
        self.assertEqual(None, self.categorizable.foregroundColor())

    def testCategorizableHasNoBackgroundColorByDefault(self):
        self.assertEqual(None, self.categorizable.backgroundColor())

    def testCategorizableHasNoFontByDefault(self):
        self.assertEqual(None, self.categorizable.font())

    def testAddCategory(self):
        self.categorizable.addCategory(self.category)
        self.assertEqual(set([self.category]), self.categorizable.categories())

    def testAddCategoryNotification(self):
        self.registerObserver(self.categoryAddedEventType)
        self.categorizable.addCategory(self.category)
        self.assertEvent(
            self.categoryAddedEventType, self.categorizable, self.category
        )

    def testAddSecondCategory(self):
        self.categorizable.addCategory(self.category)
        cat2 = category.Category("category 2")
        self.categorizable.addCategory(cat2)
        self.assertEqual(
            set([self.category, cat2]), self.categorizable.categories()
        )

    def testAddSameCategoryTwice(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(self.category)
        self.assertEqual(set([self.category]), self.categorizable.categories())

    def testAddSameCategoryTwiceCausesNoNotification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryAddedEventType)
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.events)

    def testAddCategoryViaConstructor(self):
        categorizableObject = categorizable.CategorizableCompositeObject(
            categories=[self.category]
        )
        self.assertEqual(
            set([self.category]), categorizableObject.categories()
        )

    def testAddCategoriesViaConstructor(self):
        anotherCategory = category.Category("Another category")
        categories = [self.category, anotherCategory]
        categorizableObject = categorizable.CategorizableCompositeObject(
            categories=categories
        )
        self.assertEqual(set(categories), categorizableObject.categories())

    def testAddCategoryDoesNotAddCategorizableToCategory(self):
        self.categorizable.addCategory(self.category)
        self.assertEqual(set([]), self.category.categorizables())

    def testAddParentToCategory(self):
        child = categorizable.CategorizableCompositeObject(subject="child")
        self.registerObserver(self.categoryAddedEventType, eventSource=child)
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        cat = category.Category(subject="Parent category")
        self.categorizable.addCategory(cat)
        self.assertEvent(self.categoryAddedEventType, child, cat)

    def testRemoveCategory(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(set(), self.categorizable.categories())

    def testRemoveCategoryNotification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryRemovedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEvent(
            self.categoryRemovedEventType, self.categorizable, self.category
        )

    def testRemoveCategoryTwice(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(set(), self.categorizable.categories())

    def testRemoveCategoryTwiceNotification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryRemovedEventType)
        self.categorizable.removeCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def testCategorySubjectChanged(self):
        self.registerObserver(self.categorySubjectChangedEventType)
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.setSubject("New subject")
        self.assertEvent(
            self.categorySubjectChangedEventType,
            self.categorizable,
            "New subject",
        )

    def testCategorySubjectChanged_NotifySubItemsToo(self):
        childCategorizable = categorizable.CategorizableCompositeObject(
            subject="Child categorizable"
        )
        self.registerObserver(
            self.categorySubjectChangedEventType,
            eventSource=childCategorizable,
        )
        self.categorizable.addChild(childCategorizable)
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.setSubject("New subject")
        self.assertEvent(
            self.categorySubjectChangedEventType,
            childCategorizable,
            "New subject",
        )

    def testForegroundColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.foregroundColor(recursive=True)
        )

    def testBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.backgroundColor(recursive=True)
        )

    def testFont(self):
        self.categorizable.addCategory(self.category)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, self.categorizable.font(recursive=True)
        )

    def testCategorizableOwnForegroundColorOverridesCategoryForegroundColor(
        self,
    ):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor(wx.RED)
        self.categorizable.setForegroundColor(wx.GREEN)
        self.assertEqual(
            wx.GREEN, self.categorizable.foregroundColor(recursive=True)
        )

    def testCategorizableOwnBackgroundColorOverridesCategoryBackgroundColor(
        self,
    ):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor(wx.RED)
        self.categorizable.setBackgroundColor(wx.GREEN)
        self.assertEqual(
            wx.GREEN, self.categorizable.backgroundColor(recursive=True)
        )

    def testCategorizableOwnFontOverridesCategoryFont(self):
        self.categorizable.addCategory(self.category)
        self.category.setFont(wx.SWISS_FONT)
        self.categorizable.setFont(wx.NORMAL_FONT)
        self.assertEqual(wx.NORMAL_FONT, self.categorizable.font())

    def testForegroundColorWithTupleColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor((255, 0, 0, 255))
        self.assertEqual(
            wx.RED, self.categorizable.foregroundColor(recursive=True)
        )

    def testBackgroundColorWithTupleColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor((255, 0, 0, 255))
        self.assertEqual(
            wx.RED, self.categorizable.backgroundColor(recursive=True)
        )

    def testSubItemUsesParentForegroundColor(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, child.foregroundColor(recursive=True))

    def testSubItemUsesParentBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, child.backgroundColor(recursive=True))

    def testSubItemUsesParentFont(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, child.font(recursive=True))

    def testSubItemDoesNotUseParentForegroundColorWhenItHasItsOwnForegroundColor(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setForegroundColor(wx.RED)
        self.category.setForegroundColor(wx.BLUE)
        self.assertEqual(wx.BLUE, child.foregroundColor(recursive=True))

    def testSubItemDoesNotUseParentBackgroundColorWhenItHasItsOwnBackgroundColor(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setBackgroundColor(wx.RED)
        self.category.setBackgroundColor(wx.BLUE)
        self.assertEqual(wx.BLUE, child.backgroundColor(recursive=True))

    def testSubItemDoesNotUseParentFontWhenItHasItsOwnFont(self):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        child.setParent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setFont(
            wx.Font(
                10,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        categoryFont = wx.Font(
            11, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.category.setFont(categoryFont)
        self.assertEqual(categoryFont, child.font(recursive=True))

    def testForegroundColorChanged(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.registerObserver(self.appearanceChangedEventType)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testBackgroundColorChanged(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.registerObserver(self.appearanceChangedEventType)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testFontChanged(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.registerObserver(self.appearanceChangedEventType)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(1, len(self.events))

    def testIconChanged(self):
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.registerObserver(self.appearanceChangedEventType)
        self.category.set_icon_id("icon")
        self.assertEqual(1, len(self.events))

    def testForegroundColorChanged_NotifySubItemsToo(self):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(
            self.appearanceChangedEventType, eventSource=child
        )
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testBackgroundColorChanged_NotifySubItemsToo(self):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(
            self.appearanceChangedEventType, eventSource=child
        )
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testFontChanged_NotifySubItemsToo(self):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(
            self.appearanceChangedEventType, eventSource=child
        )
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(1, len(self.events))

    def testIconChanged_NotifySubItemsToo(self):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(
            self.appearanceChangedEventType, eventSource=child
        )
        self.categorizable.addCategory(self.category)
        self.category.addCategorizable(self.categorizable)
        self.category.set_icon_id("icon")
        self.assertEqual(1, len(self.events))

    def testCategorizableDoesNotNotifyWhenItHasItsOwnForegroundColor(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.setForegroundColor(wx.RED)
        self.registerObserver(self.categorizable.appearanceChangedEventType())
        self.category.setForegroundColor(wx.GREEN)
        self.assertFalse(self.events)

    def testCategorizableDoesNotNotifyWhenItHasItsOwnBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.setBackgroundColor(wx.RED)
        self.registerObserver(self.categorizable.appearanceChangedEventType())
        self.category.setBackgroundColor(wx.GREEN)
        self.assertFalse(self.events)

    def testCategorizableDoesNotNotifyWhenItHasItsOwnFont(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.setFont(wx.SWISS_FONT)
        self.registerObserver(self.categorizable.appearanceChangedEventType())
        self.category.setFont(wx.NORMAL_FONT)
        self.assertFalse(self.events)

    def testCategorizableDoesNotNotifyWhenItHasItsOwnIcon(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.set_icon_id("icon")
        self.registerObserver(self.categorizable.appearanceChangedEventType())
        self.category.set_icon_id("another icon")
        self.assertFalse(self.events)

    def testParentForegroundColorChanged(self):
        self.registerObserver(self.appearanceChangedEventType)
        subCategory = category.Category("Subcategory")
        self.category.addChild(subCategory)
        subCategory.setParent(self.category)
        self.categorizable.addCategory(subCategory)
        subCategory.addCategorizable(self.categorizable)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testParentBackgroundColorChanged(self):
        self.registerObserver(self.appearanceChangedEventType)
        subCategory = category.Category("Subcategory")
        self.category.addChild(subCategory)
        subCategory.setParent(self.category)
        self.categorizable.addCategory(subCategory)
        subCategory.addCategorizable(self.categorizable)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def testParentFontChanged(self):
        self.registerObserver(self.appearanceChangedEventType)
        subCategory = category.Category("Subcategory")
        self.category.addChild(subCategory)
        subCategory.setParent(self.category)
        self.categorizable.addCategory(subCategory)
        subCategory.addCategorizable(self.categorizable)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(1, len(self.events))

    def testParentIconChanged(self):
        self.registerObserver(self.appearanceChangedEventType)
        subCategory = category.Category("Subcategory")
        self.category.addChild(subCategory)
        subCategory.setParent(self.category)
        self.categorizable.addCategory(subCategory)
        subCategory.addCategorizable(self.categorizable)
        self.category.set_icon_id("icon")
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithForegroundColor(self):
        self.registerObserver(self.appearanceChangedEventType)
        newCategory = category.Category("New category")
        newCategory.setForegroundColor(wx.RED)
        self.categorizable.addCategory(newCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithBackgroundColor(self):
        self.registerObserver(self.appearanceChangedEventType)
        newCategory = category.Category("New category")
        newCategory.setBackgroundColor(wx.RED)
        self.categorizable.addCategory(newCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithFont(self):
        self.registerObserver(self.appearanceChangedEventType)
        newCategory = category.Category("New category")
        newCategory.setFont(wx.SWISS_FONT)
        self.categorizable.addCategory(newCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithIcon(self):
        self.registerObserver(self.appearanceChangedEventType)
        newCategory = category.Category("New category")
        newCategory.set_icon_id("icon")
        self.categorizable.addCategory(newCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithParentWithForegroundColor(self):
        self.registerObserver(self.appearanceChangedEventType)
        parentCategory = category.Category("Parent")
        parentCategory.setForegroundColor(wx.RED)
        childCategory = category.Category("Child")
        parentCategory.addChild(childCategory)
        childCategory.setParent(parentCategory)
        self.categorizable.addCategory(childCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithParentWithBackgroundColor(self):
        self.registerObserver(self.appearanceChangedEventType)
        parentCategory = category.Category("Parent")
        parentCategory.setBackgroundColor(wx.RED)
        childCategory = category.Category("Child")
        parentCategory.addChild(childCategory)
        childCategory.setParent(parentCategory)
        self.categorizable.addCategory(childCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithParentWithFont(self):
        self.registerObserver(self.appearanceChangedEventType)
        parentCategory = category.Category("Parent")
        parentCategory.setFont(wx.SWISS_FONT)
        childCategory = category.Category("Child")
        parentCategory.addChild(childCategory)
        childCategory.setParent(parentCategory)
        self.categorizable.addCategory(childCategory)
        self.assertEqual(1, len(self.events))

    def testAddCategoryWithParentWithIcon(self):
        self.registerObserver(self.appearanceChangedEventType)
        parentCategory = category.Category("Parent")
        parentCategory.set_icon_id("icon")
        childCategory = category.Category("Child")
        parentCategory.addChild(childCategory)
        childCategory.setParent(parentCategory)
        self.categorizable.addCategory(childCategory)
        self.assertEqual(1, len(self.events))

    def testRemoveCategoryWithForegroundColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor(wx.RED)
        self.registerObserver(self.appearanceChangedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def testRemoveCategoryWithBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor(wx.RED)
        self.registerObserver(self.appearanceChangedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def testRemoveCategoryWithFont(self):
        self.categorizable.addCategory(self.category)
        self.category.setFont(wx.SWISS_FONT)
        self.registerObserver(self.appearanceChangedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def testRemoveCategoryWithIcon(self):
        self.categorizable.addCategory(self.category)
        self.category.set_icon_id("icon")
        self.registerObserver(self.appearanceChangedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def testForegroundColorWhenOneOutOfTwoCategoriesHasForegroundColor(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.foregroundColor(recursive=True)
        )

    def testBackgroundColorWhenOneOutOfTwoCategoriesHasBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.backgroundColor(recursive=True)
        )

    def testFontWhenOneOutOfTwoCategoriesHasFont(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, self.categorizable.font(recursive=True)
        )

    def testIconWhenOneOutOfTwoCategoriesHasIcon(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.set_icon_id("icon")
        self.assertEqual("icon", self.categorizable.icon_id(recursive=True))

    def testForegroundColorWhenBothCategoriesHaveSameForegroundColor(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        for cat in [self.category, anotherCategory]:
            cat.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.foregroundColor(recursive=True)
        )

    def testBackgroundColorWhenBothCategoriesHaveSameBackgroundColor(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        for cat in [self.category, anotherCategory]:
            cat.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, self.categorizable.backgroundColor(recursive=True)
        )

    def testFontWhenBothCategoriesHaveSameFont(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        for cat in [self.category, anotherCategory]:
            cat.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, self.categorizable.font(recursive=True)
        )

    def testIconWhenBothCategoriesHaveSameIcon(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        for cat in [self.category, anotherCategory]:
            cat.set_icon_id("icon")
        self.assertEqual("icon", self.categorizable.icon_id(recursive=True))

    def testForegroundColorWhenBothCategoriesHaveDifferentForegroundColors(
        self,
    ):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        self.category.setForegroundColor(wx.RED)
        anotherCategory.setForegroundColor(wx.BLUE)
        expectedColor = wx.Colour(127, 0, 127, 255)
        self.assertEqual(
            expectedColor, self.categorizable.foregroundColor(recursive=True)
        )

    def testBackgroundColorWhenBothCategoriesHaveDifferentBackgroundColors(
        self,
    ):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        self.category.setBackgroundColor(wx.RED)
        anotherCategory.setBackgroundColor(wx.BLUE)
        expectedColor = wx.Colour(127, 0, 127, 255)
        self.assertEqual(
            expectedColor, self.categorizable.backgroundColor(recursive=True)
        )

    def testFontWhenBothCategoriesHaveDifferentFontSizes(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        font = wx.SWISS_FONT
        self.category.setFont(font)
        biggerFont = wx.Font(
            font.GetPointSize() + 2,
            font.GetFamily(),
            font.GetStyle(),
            font.GetWeight(),
        )
        anotherCategory.setFont(biggerFont)
        expectedFontSize = (
            biggerFont.GetPointSize() + font.GetPointSize()
        ) / 2
        self.assertEqual(
            expectedFontSize,
            self.categorizable.font(recursive=True).GetPointSize(),
        )

    def testIconWhenBothCategoriesHaveDifferentIcons(self):
        self.categorizable.addCategory(self.category)
        anotherCategory = category.Category("Another category")
        self.categorizable.addCategory(anotherCategory)
        self.category.set_icon_id("icon")
        anotherCategory.set_icon_id("another_icon")
        self.assertTrue(
            self.categorizable.icon_id(recursive=True)
            in ["icon", "another_icon"]
        )

    def testUseCategoryIcon(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertEqual(
            "categoryIcon", self.categorizable.icon_id(recursive=True)
        )

    def testDontUseCategoryIconWhenCategorizableHasItsOwnIcon(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.set_icon_id("icon")
        self.categorizable.addCategory(self.category)
        self.assertEqual("icon", self.categorizable.icon_id(recursive=True))

    def testDontUseCategoryIconWhenNotRecursive(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.categorizable.icon_id(recursive=False))

    def testUseCategoryIconEvenWhenCategorizableHasARecursiveIcon(self):
        child = categorizable.CategorizableCompositeObject(subject="child")
        self.categorizable.addChild(child)
        self.categorizable.set_icon_id("icon")
        self.category.set_icon_id("categoryIcon")
        child.addCategory(self.category)
        self.assertEqual("categoryIcon", child.icon_id(recursive=True))

    def testUseCategorySelectedIcon(self):
        self.category.set_selected_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertEqual(
            "categoryIcon", self.categorizable.selected_icon_id(recursive=True)
        )

    def testDontUseCategorySelectedIconWhenCategorizableHasItsOwnSelectedIcon(
        self,
    ):
        self.category.set_selected_icon_id("categoryIcon")
        self.categorizable.set_selected_icon_id("icon")
        self.categorizable.addCategory(self.category)
        self.assertEqual(
            "icon", self.categorizable.selected_icon_id(recursive=True)
        )

    def testDontUseCategorySelectedIconWhenNotRecursive(self):
        self.category.set_selected_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.categorizable.selected_icon_id(recursive=False))

    def testUseCategorySelectedIconEvenWhenCategorizableHasARecursiveSelectedIcon(
        self,
    ):
        child = categorizable.CategorizableCompositeObject(subject="child")
        self.categorizable.addChild(child)
        self.categorizable.set_selected_icon_id("icon")
        self.category.set_selected_icon_id("categoryIcon")
        child.addCategory(self.category)
        self.assertEqual(
            "categoryIcon", child.selected_icon_id(recursive=True)
        )

    def testParentCategoryIncludedInChildUpwardRecursiveCategories(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.assertEqual(
            set([self.category]),
            child.categories(recursive=True, upwards=True),
        )

    def testChildCategoryIncludedInParentDownwardRecursiveCategories(self):
        child = categorizable.CategorizableCompositeObject()
        child.addCategory(self.category)
        self.categorizable.addChild(child)
        self.assertEqual(
            set([self.category]),
            self.categorizable.categories(recursive=True, upwards=False),
        )

    def testParentCategoriesNotIncludedInNonRecursiveCategories(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.assertEqual(set(), child.categories(recursive=False))

    def testChildCategoriesNotIncludedInNonRecursiveCategories(self):
        child = categorizable.CategorizableCompositeObject()
        child.addCategory(self.category)
        self.categorizable.addChild(child)
        self.assertEqual(set(), self.categorizable.categories(recursive=False))

    def testGrandParentCategoryIncludedInGrandChildUpwardRecursiveCategories(
        self,
    ):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        self.assertEqual(
            set([self.category]),
            grandchild.categories(recursive=True, upwards=True),
        )

    def testGrandChildCategoryIncludedInGrandParentDownwardRecursiveCategories(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        grandchild.addCategory(self.category)
        self.assertEqual(
            set([self.category]), self.categorizable.categories(recursive=True)
        )

    def testGrandParentAndParentCategoriesIncludedInGrandChildUpwardRecursiveCategories(
        self,
    ):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        childCategory = category.Category("Child category")
        child.addCategory(childCategory)
        self.assertEqual(
            set([self.category, childCategory]),
            grandchild.categories(recursive=True, upwards=True),
        )

    def testGrandChildAndChildCategoriesIncludedInGrandParentDownwardRecursiveCategories(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        childCategory = category.Category("Child category")
        child.addCategory(childCategory)
        grandchild.addCategory(self.category)
        self.assertEqual(
            set([self.category, childCategory]),
            self.categorizable.categories(recursive=True),
        )

    def testRemoveCategoryCausesChildNotification(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(self.categoryRemovedEventType, eventSource=child)
        self.categorizable.removeCategory(self.category)
        self.assertEvent(self.categoryRemovedEventType, child, self.category)

    def testCopy(self):
        self.categorizable.addCategory(self.category)
        copy = self.categorizable.copy()
        self.assertEqual(
            copy.categories(), self.categorizable.categories()
        )  # pylint: disable=E1101

    def testModificationEventTypes(self):  # pylint: disable=E1003
        self.assertEqual(
            super(
                categorizable.CategorizableCompositeObject, self.categorizable
            ).modificationEventTypes()
            + [self.categoryAddedEventType, self.categoryRemovedEventType],
            self.categorizable.modificationEventTypes(),
        )
