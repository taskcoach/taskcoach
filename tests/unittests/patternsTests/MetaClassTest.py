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


class Numbered(object, metaclass=patterns.NumberedInstances):
    def __init__(self, instanceNumber=-1):
        self.instanceNumber = instanceNumber


class SubclassOfNumbered(Numbered):
    pass


class NumberedInstancesTestsMixin(object):
    """The tests below should work for a class with NumberedInstances as
    metaclass as well as for a subclass of a class with NumberedInstances
    as metaclass."""

    def testCounterIncreasesAfterEachInstantation(self):
        instances = []
        for count in range(3):
            instance = self.classUnderTest()
            self.assertEqual(count, instance.instanceNumber)
            instances.append(instance)

    def testInstanceNumbersAreReusedWhenFreed(self):
        instance1 = self.classUnderTest()
        del instance1
        instance2 = self.classUnderTest()
        self.assertEqual(0, instance2.instanceNumber)

    def testInstanceNumbersAreTheLowestFreeNumber(self):
        instance1 = self.classUnderTest()
        instance2 = self.classUnderTest()
        instance2Number = instance2.instanceNumber
        del instance2
        instance3 = self.classUnderTest()
        self.assertEqual(instance3.instanceNumber, instance2Number)

    def testInstanceNumbersFillTheGap(self):
        instances = []
        for count in range(10):
            instances.append(self.classUnderTest())
        del instances[4:6]
        instance4 = self.classUnderTest()
        self.assertEqual(4, instance4.instanceNumber)
        instance5 = self.classUnderTest()
        self.assertEqual(5, instance5.instanceNumber)
        instance10 = self.classUnderTest()
        self.assertEqual(10, instance10.instanceNumber)

    def test_duplicate_explicit_number_is_not_handed_out_again(self):
        # Resetting the window layout recreates viewer 0 while the old
        # viewer 0 is still registered.
        old = self.classUnderTest(instanceNumber=0)
        new = self.classUnderTest(instanceNumber=0)
        first = self.classUnderTest()
        second = self.classUnderTest()
        self.assertEqual(
            [0, 0, 1, 2],
            [
                instance.instanceNumber
                for instance in (old, new, first, second)
            ],
        )


class NumberedInstancesTest(NumberedInstancesTestsMixin, test.TestCase):
    classUnderTest = Numbered


class SubclassOfNumberedInstancesTest(
    NumberedInstancesTestsMixin, test.TestCase
):
    classUnderTest = SubclassOfNumbered

    def testSubclassInstancesHaveTheirOwnNumbers(self):
        numberedInstance = Numbered()
        subclassOfNumberedInstance = SubclassOfNumbered()
        self.assertEqual(0, numberedInstance.instanceNumber)
        self.assertEqual(0, subclassOfNumberedInstance.instanceNumber)
