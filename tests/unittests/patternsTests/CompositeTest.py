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


class CompositeTest(test.TestCase):
    def setUp(self):
        self.composite = patterns.Composite()
        self.child = patterns.Composite()

    def test_no_parent_by_default(self):
        self.assertFalse(self.composite.parent())

    def test_no_children_by_default(self):
        self.assertFalse(self.composite.children())

    def test_no_recursive_children_by_default(self):
        self.assertFalse(self.composite.children(recursive=True))

    def test_no_ancestors_by_default(self):
        self.assertEqual([], self.composite.ancestors())

    def test_add_child(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.child], self.composite.children())

    def test_add_child_sets_parent_of_child(self):
        self.composite.addChild(self.child)
        self.assertEqual(self.composite, self.child.parent())

    def test_remove_child(self):
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual([], self.composite.children())

    def test_remove_child_does_not_reset_parent_of_child(self):
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual(self.composite, self.child.parent())

    def test_create_with_children(self):
        object_with_children = patterns.Composite(children=[self.child])
        self.assertEqual([self.child], object_with_children.children())

    def test_create_with_parent(self):
        object_with_parent = patterns.Composite(parent=self.composite)
        self.assertEqual(self.composite, object_with_parent.parent())

    def test_create_with_parent_does_not_add_object_to_parent(self):
        patterns.Composite(parent=self.composite)
        self.assertFalse(self.composite.children())

    def test_children_recursive_without_grand_children(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.child], self.composite.children(recursive=True))

    def test_children_recursive(self):
        self.composite.addChild(self.child)
        grand_child = patterns.Composite()
        self.child.addChild(grand_child)
        self.assertEqual(
            [self.child, grand_child], self.composite.children(recursive=True)
        )

    def test_ancestors_with_two_generations(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite], self.child.ancestors())

    def test_ancestors_with_three_generations(self):
        grand_child = patterns.Composite()
        self.composite.addChild(self.child)
        self.child.addChild(grand_child)
        self.assertEqual([self.composite, self.child], grand_child.ancestors())

    def test_composite_is_its_only_family_by_default(self):
        self.assertEqual([self.composite], self.composite.family())

    def test_parent_is_part_of_family(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite, self.child], self.child.family())

    def test_child_is_part_of_family(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite, self.child], self.composite.family())

    def test_siblings_without_parent_is_empty(self):
        self.assertFalse(self.composite.siblings())

    def test_siblings_without_siblings(self):
        self.composite.addChild(self.child)
        self.assertFalse(self.child.siblings())

    def test_siblings_with_one_sibling(self):
        self.composite.addChild(self.child)
        child2 = patterns.Composite()
        self.composite.addChild(child2)
        self.assertEqual([child2], self.child.siblings())

    def test_new_child_has_correct_parent(self):
        child = self.composite.newChild()
        self.assertEqual(self.composite, child.parent())

    def test_new_child_not_in_parents_children(self):
        child = self.composite.newChild()
        self.assertFalse(child in self.composite.children())

    def test_copy(self):
        copy = self.composite.copy()
        self.assertEqual(copy.children(), self.composite.children())

    def test_copy_add_children_after_copy(self):
        copy = self.composite.copy()
        self.composite.addChild(self.child)
        self.assertFalse(self.child in copy.children())

    def test_copy_with_children(self):
        self.composite.addChild(self.child)
        copy = self.composite.copy()
        self.assertEqual(1, len(copy.children()))

    def test_copy_with_children_parent_of_copied_children_is_new_composite(
        self,
    ):
        self.composite.addChild(self.child)
        copy = self.composite.copy()
        self.assertEqual(copy, copy.children()[0].parent())

    def test_copy_with_parent(self):
        self.composite.addChild(self.child)
        copy = self.child.copy()
        self.assertEqual(self.child.parent(), copy.parent())

    def test_copy_with_children_does_not_create_extra_children_for_original(
        self,
    ):
        self.composite.addChild(self.child)
        self.composite.copy()
        self.assertEqual(1, len(self.composite.children()))


class ObservableCompositeTest(test.TestCase):
    def setUp(self):
        self.composite = patterns.ObservableComposite()
        self.child = patterns.ObservableComposite()

    def test_add_child(self):
        event_type = self.composite.addChildEventType()
        self.registerObserver(event_type)
        self.composite.addChild(self.child)
        self.assertEqual(
            [patterns.Event(event_type, self.composite, self.child)],
            self.events,
        )

    def test_remove_child(self):
        event_type = self.composite.removeChildEventType()
        self.registerObserver(event_type)
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual(
            [patterns.Event(event_type, self.composite, self.child)],
            self.events,
        )

    def test_modification_event_types(self):
        self.assertEqual(
            [
                self.composite.addChildEventType(),
                self.composite.removeChildEventType(),
            ],
            self.composite.modificationEventTypes(),
        )


class CompositeCollectionTest(test.TestCase):
    def setUp(self):
        self.composite = patterns.ObservableComposite()
        self.composite2 = patterns.ObservableComposite()
        self.collection = patterns.CompositeList()

    def test_initial_size(self):
        self.assertEqual(0, len(self.collection))

    def test_create_with_initial_content(self):
        collection = patterns.CompositeList([self.composite])
        self.assertEqual([self.composite], collection)

    def test_root_items_no_items(self):
        self.assertEqual([], self.collection.rootItems())

    def test_root_items_one_root_item(self):
        self.collection.append(self.composite)
        self.assertEqual([self.composite], self.collection.rootItems())

    def test_root_items_multiple_root_items(self):
        self.collection.extend([self.composite, self.composite2])
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection.rootItems()
        )

    def test_root_items_root_and_child_items(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqual([self.composite], self.collection.rootItems())

    def test_add_child(self):
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.assertEqual([self.composite], self.collection.rootItems())

    def test_add_root_with_child_items(self):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection
        )

    def test_add_root_with_child_items_add_all_at_once(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection
        )

    def test_add_root_with_child_items_does_not_add_child_to_parent(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqual([self.composite2], self.composite.children())

    def test_add_composite_with_parent_adds_it_to_parent(self):
        self.collection.append(self.composite)
        self.composite2.set_parent(self.composite)
        self.collection.append(self.composite2)
        self.assertEqual([self.composite2], self.composite.children())

    def test_add_composite_with_parent_triggers_notification_by_parent(self):
        self.registerObserver(self.composite.addChildEventType())
        self.collection.append(self.composite)
        self.composite2.set_parent(self.composite)
        self.collection.append(self.composite2)
        expected_event = patterns.Event(
            self.composite.addChildEventType(), self.composite, self.composite2
        )
        self.assertEqual([expected_event], self.events)

    def test_remove_child_from_collection_removes_child_from_parent(self):
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.collection.remove(self.composite2)
        self.assertFalse(self.composite.children())

    def test_remove_child_from_collection_triggers_notification_by_parent(
        self,
    ):
        self.registerObserver(self.composite.removeChildEventType())
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.collection.remove(self.composite2)
        expected_event = patterns.Event(
            self.composite.removeChildEventType(),
            self.composite,
            self.composite2,
        )
        self.assertEqual([expected_event], self.events)

    def test_remove_composite_with_child_removes_child_too(self):
        self.composite.addChild(self.composite2)
        grand_child = patterns.ObservableComposite()
        self.composite2.addChild(grand_child)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.assertEqual([self.composite], self.collection)

    def test_remove_composite_and_child_removes_both(self):
        self.composite.addChild(self.composite2)
        grand_child = patterns.ObservableComposite()
        self.composite2.addChild(grand_child)
        self.collection.append(self.composite)
        self.collection.removeItems([self.composite2, grand_child])
        self.assertEqual([self.composite], self.collection)

    def test_remove_child_with_children_notifies_parent_and_child(
        self,
    ):
        self.registerObserver(self.collection.removeItemEventType())
        self.composite.addChild(self.composite2)
        grand_child = patterns.ObservableComposite()
        self.composite2.addChild(grand_child)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.assertEqualLists(
            [self.composite2, grand_child],
            self.events[0].values(type=self.collection.removeItemEventType()),
        )

    def test_remove_composite_with_children_keeps_parent_child_relation(
        self,
    ):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.collection.remove(self.composite)
        self.assertEqual([self.composite2], self.composite.children())

    def test_remove_child_and_then_adding_it_adds_it_to_previous_parent_too(
        self,
    ):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.collection.append(self.composite2)
        self.assertEqual([self.composite2], self.composite.children())

    def test_remove_composite_not_in_collection(self):
        self.collection.remove(self.composite)
