"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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
from taskcoachlib.changes import ChangeMonitor
from taskcoachlib.domain.base import Object, CompositeObject
from taskcoachlib.patterns import ObservableList


def setter_name(getter):
    """Setter of a getter: setFoo for foo, set_foo_id for foo_id."""
    if "_" in getter:
        return "set_" + getter
    return "set" + getter[:1].upper() + getter[1:]


class MonitorBaseTest(test.TestCase):
    klass = Object
    listClass = ObservableList

    def setUp(self):
        self.monitor = ChangeMonitor()
        self.monitor.monitorClass(self.klass)

        self.list = self.listClass()
        self.monitor.monitorCollection(self.list)
        self.obj = self.klass(subject="New object")
        self.list.append(self.obj)

    def tearDown(self):
        self.monitor.unmonitorClass(self.klass)
        self.monitor.unmonitorCollection(self.list)


class MonitorObjectTest(MonitorBaseTest):
    def doTestAttributeChanged(
        self, name, value, initialValue, methodName=None
    ):
        if methodName is None:
            methodName = name
        getattr(self.obj, setter_name(methodName))(initialValue)
        self.monitor.resetChanges(self.obj)
        getattr(self.obj, setter_name(methodName))(value)
        self.assertEqual(self.monitor.getChanges(self.obj), set([name]))

    def doTestAttributeDidNotChange(self, name, initialValue, methodName=None):
        if methodName is None:
            methodName = name
        getattr(self.obj, setter_name(methodName))(initialValue)
        self.monitor.resetChanges(self.obj)
        getattr(self.obj, setter_name(methodName))(
            getattr(self.obj, methodName)()
        )
        self.assertEqual(self.monitor.getChanges(self.obj), set())

    def testSubjectChanged(self):
        self.doTestAttributeChanged("subject", "New subject", "Old subject")

    def testSubjectDidNotChange(self):
        self.doTestAttributeDidNotChange("subject", "Subject")

    def testDescriptionChanged(self):
        self.doTestAttributeChanged(
            "description", "New description", "Old description"
        )

    def testDescriptionDidNotChange(self):
        self.doTestAttributeDidNotChange("description", "Description")

    def testForegroundColorChanged(self):
        self.doTestAttributeChanged(
            "appearance", (128, 128, 128), (64, 64, 64), "foregroundColor"
        )

    def testForegroundColorDidNotChange(self):
        self.doTestAttributeDidNotChange(
            "appearance", (128, 128, 128), "backgroundColor"
        )

    def testBackgroundColorChanged(self):
        self.doTestAttributeChanged(
            "appearance", (128, 128, 128), (64, 64, 64), "backgroundColor"
        )

    def testBackgroundColorDidNotChange(self):
        self.doTestAttributeDidNotChange(
            "appearance", (128, 128, 128), "backgroundColor"
        )

    def testFontChanged(self):
        self.doTestAttributeChanged("appearance", "dummy1", "dummy2", "font")

    def testFontDidNotChange(self):
        self.doTestAttributeDidNotChange("appearance", "dummy", "font")

    def testIconChanged(self):
        self.doTestAttributeChanged("appearance", "foo", "bar", "icon_id")

    def testIconDidNotChange(self):
        self.doTestAttributeDidNotChange("appearance", "foo", "icon_id")

    def testSelectedIconChanged(self):
        self.doTestAttributeChanged(
            "appearance", "foo", "bar", "selected_icon_id"
        )

    def testSelectedIconDidNotChange(self):
        self.doTestAttributeDidNotChange(
            "appearance", "foo", "selected_icon_id"
        )

    def testNewObject(self):
        obj = self.klass(subject="New")
        self.list.append(obj)
        self.assertEqual(self.monitor.getChanges(obj), None)

    def testDeletedObject(self):
        self.monitor.setChanges(self.obj.id(), set())
        self.list.remove(self.obj)
        self.assertTrue(self.monitor.isRemoved(self.obj))

    def testRemoveAdd(self):
        self.monitor.resetChanges(self.obj)
        self.obj.setSubject("Foo")
        self.list.remove(self.obj)
        self.assertEqual(
            self.monitor.getChanges(self.obj), set(["subject", "__del__"])
        )
        self.list.append(self.obj)
        self.assertEqual(self.monitor.getChanges(self.obj), set(["subject"]))
        self.assertFalse(self.monitor.isRemoved(self.obj))


class MonitorCompositeObjectTest(MonitorObjectTest):
    klass = CompositeObject

    def setUp(self):
        super().setUp()

        self.child = self.klass(subject="Child")
        self.obj.addChild(self.child)

    def testNewChild(self):
        child = self.obj.newChild(subject="Child")
        self.assertEqual(self.monitor.getChanges(child), None)

    def testChangeChildSubject1(self):
        self.monitor.resetChanges(self.obj)
        self.child.setSubject("Child subject")
        self.assertEqual(self.monitor.getChanges(self.obj), set())

    def testChangeChildSubject2(self):
        self.monitor.resetChanges(self.child)
        self.child.setSubject("Child subject")
        self.assertEqual(self.monitor.getChanges(self.child), set(["subject"]))

    def testExpansionChanged(self):
        self.monitor.resetChanges(self.obj)
        self.obj.expand()
        self.assertEqual(
            self.monitor.getChanges(self.obj), set(["expandedContexts"])
        )

    def testAddChild(self):
        child = self.klass(subject="Child")
        self.list.append(child)
        self.monitor.resetChanges(child)
        self.obj.addChild(child)
        self.assertEqual(self.monitor.getChanges(child), set(["__parent__"]))
