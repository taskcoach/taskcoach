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


class Singleton(object, metaclass=patterns.Singleton):
    pass


class SingletonTest(test.TestCase):
    def tearDown(self):
        super().tearDown()
        self.resetSingleton()

    def resetSingleton(self):
        Singleton.deleteInstance()  # pylint: disable=E1101

    def test_creation(self):
        singleton = Singleton()
        self.assertTrue(isinstance(singleton, Singleton))

    def test_create_twice(self):
        single1 = Singleton()
        single2 = Singleton()
        self.assertTrue(single1 is single2)

    def test_singletons_can_have_init(self):
        class SingletonWithInit(metaclass=patterns.Singleton):
            def __init__(self):
                self.a = 1

        single = SingletonWithInit()
        self.assertEqual(1, single.a)

    def test_singleton_init_can_have_args(self):
        class SingletonWithInit(metaclass=patterns.Singleton):
            def __init__(self, arg):
                self.a = arg

        single = SingletonWithInit("Yo")
        self.assertEqual("Yo", single.a)

    def test_singleton_init_is_only_called_once(self):
        class SingletonWithInit(metaclass=patterns.Singleton):
            _count = 0

            def __init__(self):
                SingletonWithInit._count += 1

        SingletonWithInit()
        SingletonWithInit()
        self.assertEqual(1, SingletonWithInit._count)  # pylint: disable=W0212

    def test_delete_instance(self):
        singleton1 = Singleton()
        self.resetSingleton()
        singleton2 = Singleton()
        self.assertFalse(singleton1 is singleton2)

    def test_singleton_has_no_instance_before_first_creation(self):
        self.assertFalse(Singleton.hasInstance())  # pylint: disable=E1101

    def test_singleton_has_instance_after_first_creation(self):
        Singleton()
        self.assertTrue(Singleton.hasInstance())  # pylint: disable=E1101

    def test_singleton_has_instance_after_second_creation(self):
        Singleton()
        Singleton()
        self.assertTrue(Singleton.hasInstance())  # pylint: disable=E1101

    def test_singleton_has_no_instance_after_deletion(self):
        Singleton()
        self.resetSingleton()
        self.assertFalse(Singleton.hasInstance())  # pylint: disable=E1101


class SingletonSubclassTest(test.TestCase):
    def test_subclasses_are_singletons_too(self):
        class Sub(Singleton):
            pass

        sub1 = Sub()
        sub2 = Sub()
        self.assertTrue(sub1 is sub2)

    def test_different_subclasses_are_not_the_same_singleton(self):
        class Sub1(Singleton):
            pass

        sub1 = Sub1()

        class Sub2(Singleton):
            pass

        sub2 = Sub2()
        self.assertFalse(sub1 is sub2)

    def test_subclasses_can_have_init(self):
        class Sub(Singleton):
            def __init__(self):
                super().__init__()
                self.a = 1

        sub = Sub()
        self.assertEqual(1, sub.a)

    def test_subclass_init_can_have_args(self):
        class Sub(Singleton):
            def __init__(self, arg):
                super().__init__()
                self.arg = arg

        self.assertEqual("Yo", Sub("Yo").arg)

    def test_subclass_init_is_only_called_once(self):
        class Sub(Singleton):
            _count = 0

            def __init__(self):
                super().__init__()
                Sub._count += 1

        Sub()
        Sub()
        self.assertEqual(1, Sub._count)  # pylint: disable=W0212
