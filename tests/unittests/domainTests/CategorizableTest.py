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
from taskcoachlib.domain import category, categorizable, date, note


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

    def assertEvent(self, *expected_event_args):
        expected_event = patterns.Event(*expected_event_args)
        self.assertEqual([expected_event], self.events)

    def test_categorizable_does_not_belong_to_any_category_by_default(self):
        for recursive in False, True:
            for upwards in False, True:
                self.assertFalse(
                    self.categorizable.categories(
                        recursive=recursive, upwards=upwards
                    )
                )

    def test_categorizable_has_no_foreground_color_by_default(self):
        self.assertEqual(None, self.categorizable.foregroundColor())

    def test_categorizable_has_no_background_color_by_default(self):
        self.assertEqual(None, self.categorizable.backgroundColor())

    def test_categorizable_has_no_font_by_default(self):
        self.assertEqual(None, self.categorizable.font())

    def test_add_category(self):
        self.categorizable.addCategory(self.category)
        self.assertEqual(set([self.category]), self.categorizable.categories())

    def test_category_change_sets_the_modification_date(self):
        before = date.Now()
        self.categorizable.addCategory(self.category)
        self.assertTrue(before <= self.categorizable.modificationDateTime())
        self.categorizable.set_modification_datetime(date.DateTime.min)
        self.categorizable.removeCategory(self.category)
        self.assertTrue(before <= self.categorizable.modificationDateTime())

    def test_add_category_notification(self):
        self.registerObserver(self.categoryAddedEventType)
        self.categorizable.addCategory(self.category)
        self.assertEvent(
            self.categoryAddedEventType, self.categorizable, self.category
        )

    def test_add_second_category(self):
        self.categorizable.addCategory(self.category)
        cat2 = category.Category("category 2")
        self.categorizable.addCategory(cat2)
        self.assertEqual(
            set([self.category, cat2]), self.categorizable.categories()
        )

    def test_add_same_category_twice(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(self.category)
        self.assertEqual(set([self.category]), self.categorizable.categories())

    def test_add_same_category_twice_causes_no_notification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryAddedEventType)
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.events)

    def test_add_category_via_constructor(self):
        categorizable_object = categorizable.CategorizableCompositeObject(
            categories=[self.category]
        )
        self.assertEqual(
            set([self.category]), categorizable_object.categories()
        )

    def test_add_categories_via_constructor(self):
        another_category = category.Category("Another category")
        categories = [self.category, another_category]
        categorizable_object = categorizable.CategorizableCompositeObject(
            categories=categories
        )
        self.assertEqual(set(categories), categorizable_object.categories())

    def test_adding_a_category_makes_the_item_a_member(self):
        # The category's members are the index of its items' categories
        self.categorizable.addCategory(self.category)
        self.assertEqual({self.categorizable}, self.category.members())

    def test_add_parent_to_category(self):
        child = categorizable.CategorizableCompositeObject(subject="child")
        self.registerObserver(self.categoryAddedEventType, eventSource=child)
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        cat = category.Category(subject="Parent category")
        self.categorizable.addCategory(cat)
        self.assertEvent(self.categoryAddedEventType, child, cat)

    def test_remove_category(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(set(), self.categorizable.categories())

    def test_remove_category_notification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryRemovedEventType)
        self.categorizable.removeCategory(self.category)
        self.assertEvent(
            self.categoryRemovedEventType, self.categorizable, self.category
        )

    def test_remove_category_twice(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(set(), self.categorizable.categories())

    def test_remove_category_twice_notification(self):
        self.categorizable.addCategory(self.category)
        self.registerObserver(self.categoryRemovedEventType)
        self.categorizable.removeCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    def test_category_subject_changed(self):
        self.registerObserver(self.categorySubjectChangedEventType)
        self.categorizable.addCategory(self.category)
        self.category.setSubject("New subject")
        self.assertEvent(
            self.categorySubjectChangedEventType,
            self.categorizable,
            "New subject",
        )

    def test_category_subject_changed_notify_sub_items_too(self):
        child_categorizable = categorizable.CategorizableCompositeObject(
            subject="Child categorizable"
        )
        self.registerObserver(
            self.categorySubjectChangedEventType,
            eventSource=child_categorizable,
        )
        self.categorizable.addChild(child_categorizable)
        self.categorizable.addCategory(self.category)
        self.category.setSubject("New subject")
        self.assertEvent(
            self.categorySubjectChangedEventType,
            child_categorizable,
            "New subject",
        )

    def test_categorizable_own_font_overrides_category_font(self):
        self.categorizable.addCategory(self.category)
        self.category.setFont(wx.SWISS_FONT)
        self.categorizable.setFont(wx.NORMAL_FONT)
        self.assertEqual(wx.NORMAL_FONT, self.categorizable.font())

    def test_own_icon_is_not_the_category_icon(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.categorizable.icon_id())

    def test_parent_category_included_in_child_upward_recursive_categories(
        self,
    ):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.assertEqual(
            set([self.category]),
            child.categories(recursive=True, upwards=True),
        )

    def test_child_category_included_in_parent_downward_recursive_categories(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        child.addCategory(self.category)
        self.categorizable.addChild(child)
        self.assertEqual(
            set([self.category]),
            self.categorizable.categories(recursive=True, upwards=False),
        )

    def test_parent_categories_not_included_in_non_recursive_categories(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.assertEqual(set(), child.categories(recursive=False))

    def test_child_categories_not_included_in_non_recursive_categories(self):
        child = categorizable.CategorizableCompositeObject()
        child.addCategory(self.category)
        self.categorizable.addChild(child)
        self.assertEqual(set(), self.categorizable.categories(recursive=False))

    def test_grandchild_upward_recursive_includes_grandparent(
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

    def test_grandparent_downward_recursive_includes_grandchild(
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

    def test_grandchild_upward_recursive_includes_both_ancestors(
        self,
    ):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        child_category = category.Category("Child category")
        child.addCategory(child_category)
        self.assertEqual(
            set([self.category, child_category]),
            grandchild.categories(recursive=True, upwards=True),
        )

    def test_grandparent_downward_recursive_includes_both_descendants(
        self,
    ):
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        grandchild = categorizable.CategorizableCompositeObject()
        child.addChild(grandchild)
        child_category = category.Category("Child category")
        child.addCategory(child_category)
        grandchild.addCategory(self.category)
        self.assertEqual(
            set([self.category, child_category]),
            self.categorizable.categories(recursive=True),
        )

    def test_remove_category_causes_child_notification(self):
        self.categorizable.addCategory(self.category)
        child = categorizable.CategorizableCompositeObject()
        self.categorizable.addChild(child)
        self.registerObserver(self.categoryRemovedEventType, eventSource=child)
        self.categorizable.removeCategory(self.category)
        self.assertEvent(self.categoryRemovedEventType, child, self.category)

    def test_copy(self):
        self.categorizable.addCategory(self.category)
        copy = self.categorizable.copy()
        self.assertEqual(
            copy.categories(), self.categorizable.categories()
        )  # pylint: disable=E1101

    def test_modification_event_types(self):  # pylint: disable=E1003
        self.assertEqual(
            super(
                categorizable.CategorizableCompositeObject, self.categorizable
            ).modificationEventTypes()
            + [self.categoryAddedEventType, self.categoryRemovedEventType],
            self.categorizable.modificationEventTypes(),
        )


class CategorizableStyleTest(test.TestCase):
    """The styles the master loop gives a categorizable from its
    categories (docs/APPEARANCE_STYLES.md); notes are categorizables it
    styles."""

    def setUp(self):
        self.categorizable = note.Note(subject="categorizable")
        self.category = category.Category("category")

    def test_category_foreground_color(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_fg_color()
        )

    def test_equal_priorities_take_the_first_category_by_name(self):
        later_by_name = category.Category("zzz")
        later_by_name.setForegroundColor(wx.BLUE)
        self.category.setForegroundColor(wx.RED)
        for each in (later_by_name, self.category):
            self.categorizable.addCategory(each)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_fg_color()
        )

    def test_category_background_color(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_bg_color()
        )

    def test_category_font(self):
        self.categorizable.addCategory(self.category)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, test.styled(self.categorizable).shown_font()
        )

    def test_own_foreground_color_overrides_category(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor(wx.RED)
        self.categorizable.setForegroundColor(wx.GREEN)
        self.assertEqual(
            wx.GREEN, test.styled(self.categorizable).shown_fg_color()
        )

    def test_own_background_color_overrides_category(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor(wx.RED)
        self.categorizable.setBackgroundColor(wx.GREEN)
        self.assertEqual(
            wx.GREEN, test.styled(self.categorizable).shown_bg_color()
        )

    def test_category_foreground_color_as_tuple(self):
        self.categorizable.addCategory(self.category)
        self.category.setForegroundColor((255, 0, 0, 255))
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_fg_color()
        )

    def test_category_background_color_as_tuple(self):
        self.categorizable.addCategory(self.category)
        self.category.setBackgroundColor((255, 0, 0, 255))
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_bg_color()
        )

    def test_child_takes_parent_category_foreground_color(self):
        self.categorizable.addCategory(self.category)
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, test.styled(child).shown_fg_color())

    def test_child_takes_parent_category_background_color(self):
        self.categorizable.addCategory(self.category)
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, test.styled(child).shown_bg_color())

    def test_child_takes_parent_category_font(self):
        self.categorizable.addCategory(self.category)
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(wx.SWISS_FONT, test.styled(child).shown_font())

    def test_child_category_foreground_color_wins_over_parent(self):
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setForegroundColor(wx.RED)
        self.category.setForegroundColor(wx.BLUE)
        self.assertEqual(wx.BLUE, test.styled(child).shown_fg_color())

    def test_child_category_background_color_wins_over_parent(self):
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setBackgroundColor(wx.RED)
        self.category.setBackgroundColor(wx.BLUE)
        self.assertEqual(wx.BLUE, test.styled(child).shown_bg_color())

    def test_child_category_font_wins_over_parent(self):
        child = note.Note()
        self.categorizable.addChild(child)
        child.set_parent(self.categorizable)
        child.addCategory(self.category)
        self.categorizable.setFont(
            wx.Font(
                10,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL,
            )
        )
        category_font = wx.Font(
            11, wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL
        )
        self.category.setFont(category_font)
        self.assertEqual(category_font, test.styled(child).shown_font())

    def test_foreground_color_of_one_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_fg_color()
        )

    def test_background_color_of_one_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_bg_color()
        )

    def test_font_of_one_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, test.styled(self.categorizable).shown_font()
        )

    def test_icon_of_one_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(category.Category("Another category"))
        self.category.set_icon_id("icon")
        self.assertEqual(
            "icon", test.styled(self.categorizable).shown_icon_id()
        )

    def test_same_foreground_color_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        for cat in [self.category, another_category]:
            cat.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_fg_color()
        )

    def test_same_background_color_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        for cat in [self.category, another_category]:
            cat.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.categorizable).shown_bg_color()
        )

    def test_same_font_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        for cat in [self.category, another_category]:
            cat.setFont(wx.SWISS_FONT)
        self.assertEqual(
            wx.SWISS_FONT, test.styled(self.categorizable).shown_font()
        )

    def test_same_icon_of_two_categories(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        for cat in [self.category, another_category]:
            cat.set_icon_id("icon")
        self.assertEqual(
            "icon", test.styled(self.categorizable).shown_icon_id()
        )

    def test_category_icon(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.addCategory(self.category)
        self.assertEqual(
            "categoryIcon", test.styled(self.categorizable).shown_icon_id()
        )

    def test_own_icon_overrides_category(self):
        self.category.set_icon_id("categoryIcon")
        self.categorizable.set_icon_id("icon")
        self.categorizable.addCategory(self.category)
        self.assertEqual(
            "icon", test.styled(self.categorizable).shown_icon_id()
        )

    def test_category_icon_wins_over_parent_icon(self):
        child = note.Note(subject="child")
        self.categorizable.addChild(child)
        self.categorizable.set_icon_id("icon")
        self.category.set_icon_id("categoryIcon")
        child.addCategory(self.category)
        self.assertEqual("categoryIcon", test.styled(child).shown_icon_id())

    def test_higher_style_priority_category_gives_the_foreground_color(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        self.category.setForegroundColor(wx.RED)
        another_category.setForegroundColor(wx.BLUE)
        another_category.setStylePriority(1)
        self.assertEqual(
            wx.BLUE, test.styled(self.categorizable).shown_fg_color()
        )

    def test_higher_style_priority_category_gives_the_background_color(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        self.category.setBackgroundColor(wx.RED)
        another_category.setBackgroundColor(wx.BLUE)
        another_category.setStylePriority(1)
        self.assertEqual(
            wx.BLUE, test.styled(self.categorizable).shown_bg_color()
        )

    def test_higher_style_priority_category_gives_the_font(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        self.category.setFont(wx.SWISS_FONT)
        another_category.setFont(wx.ITALIC_FONT)
        another_category.setStylePriority(1)
        self.assertEqual(
            wx.ITALIC_FONT, test.styled(self.categorizable).shown_font()
        )

    def test_higher_style_priority_category_gives_the_icon(self):
        self.categorizable.addCategory(self.category)
        another_category = category.Category("Another category")
        self.categorizable.addCategory(another_category)
        self.category.set_icon_id("icon")
        another_category.set_icon_id("another_icon")
        another_category.setStylePriority(1)
        self.assertEqual(
            "another_icon", test.styled(self.categorizable).shown_icon_id()
        )
