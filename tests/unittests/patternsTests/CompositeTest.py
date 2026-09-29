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

    def testNoParentByDefault(self):
        self.assertFalse(self.composite.parent())

    def testNoChildrenByDefault(self):
        self.assertFalse(self.composite.children())

    def testNoRecursiveChildrenByDefault(self):
        self.assertFalse(self.composite.children(recursive=True))

    def testNoAncestorsByDefault(self):
        self.assertEqual([], self.composite.ancestors())

    def testAddChild(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.child], self.composite.children())

    def testAddChild_SetsParentOfChild(self):
        self.composite.addChild(self.child)
        self.assertEqual(self.composite, self.child.parent())

    def testRemoveChild(self):
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual([], self.composite.children())

    def testRemoveChild_DoesNotResetParentOfChild(self):
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual(self.composite, self.child.parent())

    def testCreateWithChildren(self):
        objectWithChildren = patterns.Composite(children=[self.child])
        self.assertEqual([self.child], objectWithChildren.children())

    def testCreateWithParent(self):
        objectWithParent = patterns.Composite(parent=self.composite)
        self.assertEqual(self.composite, objectWithParent.parent())

    def testCreateWithParentDoesNotAddObjectToParent(self):
        patterns.Composite(parent=self.composite)
        self.assertFalse(self.composite.children())

    def testChildrenRecursive_WithoutGrandChildren(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.child], self.composite.children(recursive=True))

    def testChildrenRecursive(self):
        self.composite.addChild(self.child)
        grandChild = patterns.Composite()
        self.child.addChild(grandChild)
        self.assertEqual(
            [self.child, grandChild], self.composite.children(recursive=True)
        )

    def testAncestorsWithTwoGenerations(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite], self.child.ancestors())

    def testAncestorsWithThreeGenerations(self):
        grandChild = patterns.Composite()
        self.composite.addChild(self.child)
        self.child.addChild(grandChild)
        self.assertEqual([self.composite, self.child], grandChild.ancestors())

    def testCompositeIsItsOnlyFamilyByDefault(self):
        self.assertEqual([self.composite], self.composite.family())

    def testParentIsPartOfFamily(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite, self.child], self.child.family())

    def testChildIsPartOfFamily(self):
        self.composite.addChild(self.child)
        self.assertEqual([self.composite, self.child], self.composite.family())

    def testSiblingsWithoutParentIsEmpty(self):
        self.assertFalse(self.composite.siblings())

    def testSiblingsWithoutSiblings(self):
        self.composite.addChild(self.child)
        self.assertFalse(self.child.siblings())

    def testSiblingsWithOneSibling(self):
        self.composite.addChild(self.child)
        child2 = patterns.Composite()
        self.composite.addChild(child2)
        self.assertEqual([child2], self.child.siblings())

    def testNewChild_HasCorrectParent(self):
        child = self.composite.newChild()
        self.assertEqual(self.composite, child.parent())

    def testNewChild_NotInParentsChildren(self):
        child = self.composite.newChild()
        self.assertFalse(child in self.composite.children())

    def testGetState(self):
        self.assertEqual(
            dict(children=[], parent=None), self.composite.__getstate__()
        )

    def testGetState_WithChildren(self):
        self.composite.addChild(self.child)
        state = self.composite.__getstate__()
        self.assertEqual(
            dict(children=[state["children"][0]], parent=None), state
        )

    def testGetState_WithParent(self):
        self.composite.addChild(self.child)
        self.assertEqual(
            dict(children=[], parent=self.composite), self.child.__getstate__()
        )

    def testSetState_Parent(self):
        state = self.composite.__getstate__()
        self.composite.set_parent(self.child)
        self.composite.__setstate__(state)
        self.assertEqual(None, self.composite.parent())

    def testSetState_Children(self):
        state = self.composite.__getstate__()
        self.composite.addChild(self.child)
        self.composite.__setstate__(state)
        self.assertEqual([], self.composite.children())

    def testCopy(self):
        copy = self.composite.copy()
        self.assertEqual(copy.children(), self.composite.children())

    def testCopy_AddChildrenAfterCopy(self):
        copy = self.composite.copy()
        self.composite.addChild(self.child)
        self.assertFalse(self.child in copy.children())

    def testCopy_WithChildren(self):
        self.composite.addChild(self.child)
        copy = self.composite.copy()
        self.assertEqual(1, len(copy.children()))

    def testCopy_WithChildren_ParentOfCopiedChildrenIsNewComposite(self):
        self.composite.addChild(self.child)
        copy = self.composite.copy()
        self.assertEqual(copy, copy.children()[0].parent())

    def testCopy_WithParent(self):
        self.composite.addChild(self.child)
        copy = self.child.copy()
        self.assertEqual(self.child.parent(), copy.parent())

    def testCopy_WithChildren_DoesNotCreateExtraChildrenForOriginal(self):
        self.composite.addChild(self.child)
        self.composite.copy()
        self.assertEqual(1, len(self.composite.children()))


class ObservableCompositeTest(test.TestCase):
    def setUp(self):
        self.composite = patterns.ObservableComposite()
        self.child = patterns.ObservableComposite()

    def testAddChild(self):
        eventType = self.composite.addChildEventType()
        self.registerObserver(eventType)
        self.composite.addChild(self.child)
        self.assertEqual(
            [patterns.Event(eventType, self.composite, self.child)],
            self.events,
        )

    def testRemoveChild(self):
        eventType = self.composite.removeChildEventType()
        self.registerObserver(eventType)
        self.composite.addChild(self.child)
        self.composite.removeChild(self.child)
        self.assertEqual(
            [patterns.Event(eventType, self.composite, self.child)],
            self.events,
        )

    def testModificationEventTypes(self):
        self.assertEqual(
            [
                self.composite.addChildEventType(),
                self.composite.removeChildEventType(),
            ],
            self.composite.modificationEventTypes(),
        )

    def testSetState(self):
        self.composite.addChild(self.child)
        state = self.composite.__getstate__()
        self.registerObserver(self.composite.removeChildEventType())
        self.registerObserver(self.composite.addChildEventType())
        self.composite.__setstate__(state)
        self.assertEqual([], self.events)


class CompositeCollectionTest(test.TestCase):
    def setUp(self):
        self.composite = patterns.ObservableComposite()
        self.composite2 = patterns.ObservableComposite()
        self.collection = patterns.CompositeList()

    def testInitialSize(self):
        self.assertEqual(0, len(self.collection))

    def testCreateWithInitialContent(self):
        collection = patterns.CompositeList([self.composite])
        self.assertEqual([self.composite], collection)

    def testRootItems_NoItems(self):
        self.assertEqual([], self.collection.rootItems())

    def testRootItems_OneRootItem(self):
        self.collection.append(self.composite)
        self.assertEqual([self.composite], self.collection.rootItems())

    def testRootItems_MultipleRootItems(self):
        self.collection.extend([self.composite, self.composite2])
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection.rootItems()
        )

    def testRootItems_RootAndChildItems(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqual([self.composite], self.collection.rootItems())

    def testAddChild(self):
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.assertEqual([self.composite], self.collection.rootItems())

    def testAddRootWithChildItems(self):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection
        )

    def testAddRootWithChildItems_AddAllAtOnce(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqualLists(
            [self.composite, self.composite2], self.collection
        )

    def testAddRootWithChildItems_DoesNotAddChildToParent(self):
        self.composite.addChild(self.composite2)
        self.collection.extend([self.composite, self.composite2])
        self.assertEqual([self.composite2], self.composite.children())

    def testAddCompositeWithParentAddsItToParent(self):
        self.collection.append(self.composite)
        self.composite2.set_parent(self.composite)
        self.collection.append(self.composite2)
        self.assertEqual([self.composite2], self.composite.children())

    def testAddCompositeWithParentTriggersNotificationByParent(self):
        self.registerObserver(self.composite.addChildEventType())
        self.collection.append(self.composite)
        self.composite2.set_parent(self.composite)
        self.collection.append(self.composite2)
        expectedEvent = patterns.Event(
            self.composite.addChildEventType(), self.composite, self.composite2
        )
        self.assertEqual([expectedEvent], self.events)

    def testRemoveChildFromCollectionRemovesChildFromParent(self):
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.collection.remove(self.composite2)
        self.assertFalse(self.composite.children())

    def testRemoveChildFromCollectionTriggersNotificationByParent(self):
        self.registerObserver(self.composite.removeChildEventType())
        self.collection.extend([self.composite, self.composite2])
        self.composite.addChild(self.composite2)
        self.collection.remove(self.composite2)
        expectedEvent = patterns.Event(
            self.composite.removeChildEventType(),
            self.composite,
            self.composite2,
        )
        self.assertEqual([expectedEvent], self.events)

    def testRemoveCompositeWithChildRemovesChildToo(self):
        self.composite.addChild(self.composite2)
        grandChild = patterns.ObservableComposite()
        self.composite2.addChild(grandChild)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.assertEqual([self.composite], self.collection)

    def testRemoveCompositeAndChildRemovesBoth(self):
        self.composite.addChild(self.composite2)
        grandChild = patterns.ObservableComposite()
        self.composite2.addChild(grandChild)
        self.collection.append(self.composite)
        self.collection.removeItems([self.composite2, grandChild])
        self.assertEqual([self.composite], self.collection)

    def testRemoveChildWithChildren_CollectionNotificationContainsParentAndChild(
        self,
    ):
        self.registerObserver(self.collection.removeItemEventType())
        self.composite.addChild(self.composite2)
        grandChild = patterns.ObservableComposite()
        self.composite2.addChild(grandChild)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.assertEqualLists(
            [self.composite2, grandChild],
            self.events[0].values(type=self.collection.removeItemEventType()),
        )

    def testRemoveCompositeWithChildrenDoesNotBreakParentChildRelation(self):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.collection.remove(self.composite)
        self.assertEqual([self.composite2], self.composite.children())

    def testRemoveChildAndThenAddingItAddsItToPreviousParentToo(self):
        self.composite.addChild(self.composite2)
        self.collection.append(self.composite)
        self.collection.remove(self.composite2)
        self.collection.append(self.composite2)
        self.assertEqual([self.composite2], self.composite.children())

    def testRemoveCompositeNotInCollection(self):
        self.collection.remove(self.composite)
