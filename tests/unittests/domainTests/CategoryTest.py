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

    # Subject:

    def test_create_with_subject(self):
        self.assertEqual("category", self.category.subject())

    def test_set_subject(self):
        self.category.setSubject("New")
        self.assertEqual("New", self.category.subject())

    def test_set_subject_notification(self):
        event_type = category.Category.subjectChangedEventType()
        self.registerObserver(event_type)
        self.category.setSubject("New")
        self.assertEqual(
            [patterns.Event(event_type, self.category, "New")], self.events
        )

    def test_setting_same_subject_causes_no_notification(
        self,
    ):
        event_type = category.Category.subjectChangedEventType()
        self.registerObserver(event_type)
        self.category.setSubject(self.category.subject())
        self.assertFalse(self.events)

    # Description:

    def test_create_with_description(self):
        a_category = category.Category("subject", description="Description")
        self.assertEqual("Description", a_category.description())

    # Members: the items whose categories hold it

    def test_no_members_after_creation(self):
        self.assertEqual(set(), self.category.members())

    def test_an_item_claiming_it_is_a_member(self):
        self.categorizable.addCategory(self.category)
        self.assertEqual({self.categorizable}, self.category.members())

    def test_membership_change_keeps_the_categorys_date(self):
        # The task owns its categories; the members are the reverse
        before = self.category.modificationDateTime()
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(before, self.category.modificationDateTime())

    def test_claiming_it_twice_is_one_member(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.addCategory(self.category)
        self.assertEqual({self.categorizable}, self.category.members())

    def test_an_item_dropping_it_leaves(self):
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertFalse(self.category.members())

    def test_dropping_it_without_claiming_it(self):
        self.categorizable.removeCategory(self.category)
        self.assertFalse(self.category.members())

    def test_members_given_at_creation_join_when_it_enters_the_file(self):
        cat = category.Category("category", [self.categorizable])
        members = [cat.members()]
        category.CategoryList([cat])
        members.append(cat.members())
        self.assertEqual([set(), {self.categorizable}], members)

    def test_members_given_at_creation_do_not_claim_it_yet(self):
        category.Category("category", [self.categorizable])
        self.assertEqual(set(), self.categorizable.categories())

    def test_members_of_subcategories_count_recursively(self):
        self.category.addChild(self.subCategory)
        self.categorizable.addCategory(self.subCategory)
        self.assertEqual(
            set([self.categorizable]),
            self.category.members(recursive=True),
        )

    # Subcategories:

    def test_add_sub_category(self):
        self.category.addChild(self.subCategory)
        self.assertEqual([self.subCategory], self.category.children())

    def test_create_with_sub_categories(self):
        cat = category.Category("category", children=[self.subCategory])
        self.assertEqual([self.subCategory], cat.children())

    def test_parent_of_sub_category(self):
        self.category.addChild(self.subCategory)
        self.assertEqual(self.category, self.subCategory.parent())

    def test_parent_of_root_category(self):
        self.assertEqual(None, self.category.parent())

    # Equality:

    def test_equality_same_subject_and_no_parents(self):
        self.assertNotEqual(
            category.Category(self.category.subject()), self.category
        )
        self.assertNotEqual(
            self.category, category.Category(self.category.subject())
        )

    def test_equality_same_subject_different_parents(self):
        self.category.addChild(self.subCategory)
        self.assertNotEqual(
            category.Category(self.subCategory.subject()), self.subCategory
        )

    # Filter:

    def test_not_filtered_by_default(self):
        self.assertFalse(self.category.isFiltered())

    def test_set_filtered_on(self):
        self.category.setFiltered()
        self.assertTrue(self.category.isFiltered())

    def test_set_filtered_off(self):
        self.category.setFiltered(False)
        self.assertFalse(self.category.isFiltered())

    def test_set_filtered_via_constructor(self):
        filtered_category = category.Category("test", filtered=True)
        self.assertTrue(filtered_category.isFiltered())

    # Exclusive subcategories:

    def test_exclusive_subcategories_change_sets_the_modification_date(self):
        before = date.Now()
        self.category.makeSubcategoriesExclusive()
        self.assertTrue(before <= self.category.modificationDateTime())

    def test_unchanged_exclusivity_keeps_the_modification_date(self):
        self.category.makeSubcategoriesExclusive(False)
        self.assertEqual(
            self.category.creationDateTime(),
            self.category.modificationDateTime(),
        )

    # Style priority:

    def test_style_priority_is_zero_by_default(self):
        self.assertEqual(0, self.category.stylePriority())

    def test_style_priority_change_notifies_with_the_category(self):
        self.registerObserver(
            self.category.stylePriorityChangedEventType(),
            eventSource=self.category,
        )
        self.category.setStylePriority(3)
        self.assertEqual(3, self.category.stylePriority())
        self.assertEqual(
            [
                patterns.Event(
                    self.category.stylePriorityChangedEventType(),
                    self.category,
                    3,
                )
            ],
            self.events,
        )

    def test_style_priority_change_sets_the_modification_date(self):
        before = date.Now()
        self.category.setStylePriority(3)
        self.assertTrue(before <= self.category.modificationDateTime())

    def test_unchanged_style_priority_keeps_the_modification_date(self):
        self.category.setStylePriority(0)
        self.assertEqual(
            self.category.creationDateTime(),
            self.category.modificationDateTime(),
        )

    # Copy:

    def test_copy_subject_is_copied(self):
        self.category.setSubject("New subject")
        copy = self.category.copy()
        self.assertEqual(copy.subject(), self.category.subject())

    def test_copy_id_is_different(self):
        copy = self.category.copy()
        self.assertNotEqual(copy.id(), self.category.id())

    # pylint: disable=E1101

    def test_copy_subject_is_different_from_original_subject(self):
        self.subCategory.setSubject("New subject")
        self.category.addChild(self.subCategory)
        copy = self.category.copy()
        self.subCategory.setSubject("Other subject")
        self.assertEqual("New subject", copy.children()[0].subject())

    def test_copy_filtered_status_is_copied(self):
        self.category.setFiltered()
        copy = self.category.copy()
        self.assertEqual(copy.isFiltered(), self.category.isFiltered())

    def test_a_copys_members_join_it_when_it_is_pasted(self):
        self.categorizable.addCategory(self.category)
        copy = self.category.copy()
        category.CategoryList([copy])
        self.assertEqual(copy.members(), self.category.members())

    def test_a_copy_has_its_own_members(self):
        copy = self.category.copy()
        self.categorizable.addCategory(self.category)
        self.assertFalse(self.categorizable in copy.members())

    def test_copy_children_are_copied(self):
        self.category.addChild(self.subCategory)
        copy = self.category.copy()
        self.assertEqual(
            self.subCategory.subject(), copy.children()[0].subject()
        )

    # Notifications:

    def test_joining_notifies(self):
        self.registerObserver(category.Category.member_added_event_type())
        self.categorizable.addCategory(self.category)
        self.assertEqual(1, len(self.events))

    def test_leaving_notifies(self):
        self.registerObserver(category.Category.member_removed_event_type())
        self.categorizable.addCategory(self.category)
        self.categorizable.removeCategory(self.category)
        self.assertEqual(1, len(self.events))

    # Color:

    def test_get_default_foreground_color(self):
        self.assertEqual(None, self.category.foregroundColor())

    def test_get_default_background_color(self):
        self.assertEqual(None, self.category.backgroundColor())

    def test_set_foreground_color(self):
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(wx.RED, self.category.foregroundColor())

    def test_set_background_color(self):
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(wx.RED, self.category.backgroundColor())

    def test_copy_foreground_color_is_copied(self):
        self.category.setForegroundColor(wx.RED)
        copy = self.category.copy()
        self.assertEqual(wx.RED, copy.foregroundColor())

    def test_copy_background_color_is_copied(self):
        self.category.setBackgroundColor(wx.RED)
        copy = self.category.copy()
        self.assertEqual(wx.RED, copy.backgroundColor())

    def test_foreground_color_change_notification(self):
        event_type = category.Category.appearanceChangedEventType()
        self.registerObserver(event_type)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def test_background_color_change_notification(self):
        event_type = category.Category.appearanceChangedEventType()
        self.registerObserver(event_type)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def test_subcategory_takes_parent_foreground_color(self):
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.subCategory).shown_fg_color()
        )

    def test_subcategory_takes_parent_background_color(self):
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(
            wx.RED, test.styled(self.subCategory).shown_bg_color()
        )

    def test_sub_category_without_foreground_color_has_no_own_foreground_color(
        self,
    ):
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(None, self.subCategory.foregroundColor())

    def test_sub_category_without_background_color_has_no_own_background_color(
        self,
    ):
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(None, self.subCategory.backgroundColor())

    def test_parent_foreground_color_change_notification(self):
        event_type = category.Category.appearanceChangedEventType()
        self.registerObserver(event_type)
        self.category.addChild(self.subCategory)
        self.category.setForegroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    def test_parent_background_color_change_notification(self):
        event_type = category.Category.appearanceChangedEventType()
        self.registerObserver(event_type)
        self.category.addChild(self.subCategory)
        self.category.setBackgroundColor(wx.RED)
        self.assertEqual(1, len(self.events))

    # Icon:

    def test_subcategory_shows_its_parents_icon_as_is(self):
        self.category.addChild(self.subCategory)
        self.category.set_icon_id("nuvola_mimetypes_inode-directory")
        self.assertEqual(
            "nuvola_mimetypes_inode-directory",
            test.styled(self.subCategory).shown_icon_id(),
        )

    def test_icon_change_names_its_items(self):
        # Their Category icons column shows it
        self.categorizable.addCategory(self.category)
        events = test.ChangeRecorder(
            self.categorizable.effectiveIconChangedEventType()
        )
        self.category.set_icon_id("icon")
        self.assertIn(self.categorizable, events)

    # Notes:

    def test_add_note(self):
        a_note = note.Note(subject="Note")
        self.category.addNote(a_note)
        self.assertEqual([a_note], self.category.notes())

    # Exclusive subcategories:

    def test_subcategories_are_not_exclusive_by_default(self):
        self.assertFalse(self.category.hasExclusiveSubcategories())

    def test_make_subcategories_exclusive(self):
        self.category.makeSubcategoriesExclusive()
        self.assertTrue(self.category.hasExclusiveSubcategories())

    def test_make_subcategories_not_exclusive(self):
        self.category.makeSubcategoriesExclusive()
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.category.hasExclusiveSubcategories())

    def test_create_with_exclusive_subcategories(self):
        a_category = category.Category("subject", exclusiveSubcategories=True)
        self.assertTrue(a_category.hasExclusiveSubcategories())

    def test_exclusive_subcategories_notification(self):
        event_type = category.Category.exclusiveSubcategoriesChangedEventType()
        self.registerObserver(event_type)
        self.category.makeSubcategoriesExclusive()
        self.assertEqual(
            [patterns.Event(event_type, self.category, True)], self.events
        )

    def test_no_exclusive_subcategories_notification_when_not_changed(self):
        event_type = category.Category.exclusiveSubcategoriesChangedEventType()
        self.registerObserver(event_type)
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.events)

    def test_make_subcategories_exclusive_unchecks_all_subcategories(self):
        self.subCategory.setFiltered(True)
        self.category.addChild(self.subCategory)
        self.category.makeSubcategoriesExclusive(True)
        self.assertFalse(self.subCategory.isFiltered())

    def test_make_subcategories_non_exclusive_unchecks_all_subcategories(self):
        self.category.makeSubcategoriesExclusive(True)
        self.subCategory.setFiltered(True)
        self.category.addChild(self.subCategory)
        self.category.makeSubcategoriesExclusive(False)
        self.assertFalse(self.subCategory.isFiltered())

    # Event types:

    def test_modification_event_types(self):  # pylint: disable=E1003
        self.assertEqual(
            super(category.Category, self.category).modificationEventTypes()
            + [
                self.category.filterChangedEventType(),
                self.category.member_added_event_type(),
                self.category.member_removed_event_type(),
                self.category.exclusiveSubcategoriesChangedEventType(),
                self.category.stylePriorityChangedEventType(),
            ],
            self.category.modificationEventTypes(),
        )
