import test, patterns, string, gui, config
import domain.task as task
import domain.date as date

class TestFilter(task.filter.Filter):
    def filter(self, item):
        return item > 'b' 


class FilterTest(test.TestCase):
    def setUp(self):
        self.list = patterns.ObservableList(['a', 'b', 'c', 'd'])
        self.filter = TestFilter(self.list)

    def testLength(self):
        self.assertEqual(2, len(self.filter))

    def testGetItem(self):
        self.assertEqual('c', self.filter[0])

    def testRemoveItem(self):
        self.filter.remove('c')
        self.assertEqual(1, len(self.filter))
        self.assertEqual('d', self.filter[0])
        self.assertEqual(['a', 'b', 'd'], self.list)

    def testNotification(self):
        self.list.append('e')
        self.assertEqual(3, len(self.filter))
        self.assertEqual('e', self.filter[-1])


class DummyFilter(task.filter.Filter):
    def filter(self, item):
        return 1

    def test(self):
        self.testcalled = 1

class StackedFilterTest(test.TestCase):
    def setUp(self):
        self.list = patterns.ObservableList(['a', 'b', 'c', 'd'])
        self.filter1 = DummyFilter(self.list)
        self.filter2 = TestFilter(self.filter1)

    def testDelegation(self):
        self.filter2.test()
        self.assertEqual(1, self.filter1.testcalled)


class ViewFilterTest(test.TestCase):
    def setUp(self):
        self.list = task.TaskList()
        self.settings = config.Settings(load=False)
        self.filter = task.filter.ViewFilter(self.list, settings=self.settings)
        self.task = task.Task()
        self.dueToday = task.Task(duedate=date.Today())
        self.dueTomorrow = task.Task(duedate=date.Tomorrow())
        self.dueYesterday = task.Task(duedate=date.Yesterday())
        self.child = task.Task()

    def testCreate(self):
        self.assertEqual(0, len(self.filter))

    def testAddTask(self):
        self.filter.append(self.task)
        self.assertEqual(1, len(self.filter))
        
    def testViewActiveTasks(self):
        self.filter.append(self.task)
        self.settings.set('view', 'activetasks', 'False')
        self.assertEqual(0, len(self.filter))

    def testFilterCompletedTask(self):
        self.task.setCompletionDate()
        self.filter.append(self.task)
        self.assertEqual(1, len(self.filter))
        self.settings.set('view', 'completedtasks', 'False')
        self.assertEqual(0, len(self.filter))
        
    def testFilterCompletedTask_RootTasks(self):
        self.task.setCompletionDate()
        self.filter.append(self.task)
        self.settings.set('view', 'completedtasks', 'False')
        self.assertEqual(0, len(self.filter.rootTasks()))

    def testFilterDueToday(self):
        self.filter.extend([self.task, self.dueToday])
        self.assertEqual(2, len(self.filter))
        self.settings.set('view', 'tasksdue', 'Today')
        self.assertEqual(1, len(self.filter))
    
    def testFilterDueToday_ShouldIncludeOverdueTasks(self):
        self.filter.append(self.dueYesterday)
        self.settings.set('view', 'tasksdue', 'Today')
        self.assertEqual(1, len(self.filter))

    def testFilterDueToday_ShouldIncludeCompletedTasks(self):
        self.filter.append(self.dueToday)
        self.dueToday.setCompletionDate()
        self.settings.set('view', 'tasksdue', 'Today')
        self.assertEqual(1, len(self.filter))

    def testFilterDueTomorrow(self):
        self.filter.extend([self.task, self.dueTomorrow, self.dueToday])
        self.assertEqual(3, len(self.filter))
        self.settings.set('view', 'tasksdue', 'Tomorrow')
        self.assertEqual(2, len(self.filter))
    
    def testFilterDueWeekend(self):
        dueNextWeek = task.Task(duedate=date.Today() + \
            date.TimeDelta(days=8))
        self.filter.extend([self.dueToday, dueNextWeek])
        self.settings.set('view', 'tasksdue', 'Workweek')
        self.assertEqual(1, len(self.filter))


class ViewFilterInTreeModeTest(test.TestCase):
    def setUp(self):
        self.list = task.TaskList()
        self.settings = config.Settings(load=False)
        self.filter = task.filter.ViewFilter(self.list, settings=self.settings, treeMode=True)
        self.task = task.Task()
        self.dueToday = task.Task(duedate=date.Today())
        self.dueTomorrow = task.Task(duedate=date.Tomorrow())
        self.dueYesterday = task.Task(duedate=date.Yesterday())
        self.child = task.Task()
        
    def testCreate(self):
        self.assertEqual(0, len(self.filter))
        
    def testAddTask(self):
        self.filter.append(self.task)
        self.assertEqual(1, len(self.filter))

    def testFilterDueToday(self):
        self.task.addChild(self.dueToday)
        self.list.append(self.task)
        self.settings.set('view', 'tasksdue', 'Today')
        self.assertEqual(2, len(self.filter))
        
    def testFilterOverDueTasks(self):
        self.task.addChild(self.dueYesterday)
        self.list.append(self.task)
        self.settings.set('view', 'overduetasks', 'False')
        self.assertEqual(1, len(self.filter))
        
        
class CompositeFilterTest(test.wxTestCase):
    def setUp(self):
        self.list = task.TaskList()
        self.settings = config.Settings(load=False)
        self.filter = task.filter.CompositeFilter(self.list, 
            settings=self.settings)
        self.task = task.Task()
        self.child = task.Task()
        self.task.addChild(self.child)
        self.filter.append(self.task)

    def testInitial(self):
        self.assertEqual(2, len(self.filter))
                
    def testTurnOn(self):
        self.settings.set('view', 'compositetasks', 'False')
        self.assertEqual([self.child], list(self.filter))
                
    def testTurnOnAndAddChild(self):
        self.settings.set('view', 'compositetasks', 'False')
        grandChild = task.Task()
        self.child.addChild(grandChild)
        self.list.append(grandChild)
        self.assertEqual([grandChild], list(self.filter))


class SearchFilterTest(test.TestCase):
    def setUp(self):
        self.parent = task.Task(subject='ABC')
        self.child = task.Task(subject='DEF')
        self.parent.addChild(self.child)
        self.list = task.TaskList([self.parent, self.child])
        self.settings = config.Settings(load=False)
        self.filter = task.filter.SearchFilter(self.list, settings=self.settings)

    def setSearchString(self, searchString):
        self.settings.set('view', 'tasksearchfilterstring', searchString)
        
    def testNoMatch(self):
        self.setSearchString('XYZ')
        self.assertEqual(0, len(self.filter))

    def testMatch(self):
        self.setSearchString('AB')
        self.assertEqual(1, len(self.filter))

    def testMatchIsCaseInSensitiveByDefault(self):
        self.setSearchString('abc')
        self.assertEqual(1, len(self.filter))

    def testMatchCaseInsensitive(self):
        self.settings.set('view', 'tasksearchfiltermatchcase', 'True')
        self.setSearchString('abc')
        self.assertEqual(0, len(self.filter))

    def testMatchWithRE(self):
        self.setSearchString('a.c')
        self.assertEqual(1, len(self.filter))

    def testMatchWithEmptyString(self):
        self.setSearchString('')
        self.assertEqual(2, len(self.filter))

    def testMatchChildDoesNotSelectParentWhenNotInTreeMode(self):
        self.setSearchString('DEF')
        self.assertEqual(1, len(self.filter))

    def testMatchChildAlsoSelectsParentWhenInTreeMode(self):
        self.filter.setTreeMode(True)
        self.setSearchString('DEF')
        self.assertEqual(2, len(self.filter))
        
    def testMatchChildDoesNotSelectParentWhenChildNotInList(self):
        self.list.remove(self.child) 
        self.parent.addChild(self.child) # simulate a child that has been filtered 
        self.setSearchString('DEF')
        self.assertEqual(0, len(self.filter))

        
class CategoryFilterTest(test.TestCase):
    def setUp(self):
        self.parent = task.Task()
        self.parent.addCategory('parent')
        self.child = task.Task()
        self.child.addCategory('child')
        self.parent.addChild(self.child)
        self.list = task.TaskList([self.parent, self.child])
        self.filter = task.filter.CategoryFilter(self.list)
        
    def testInitial(self):
        self.assertEqual(2, len(self.filter))

    def testFilterOnCategoryNotPresent(self):
        self.filter.addCategory('test')
        self.assertEqual(0, len(self.filter))
        
    def testFilterOnCategoryChild(self):
        self.filter.addCategory('child')
        self.assertEqual(1, len(self.filter))
        self.assertEqual(self.child, self.filter[0])
        
    def testFilterOnCategoryParent(self):
        self.filter.addCategory('parent')
        self.assertEqual(2, len(self.filter))
        
    def testRemoveCategory(self):
        self.filter.addCategory('parent')
        self.filter.removeCategory('parent')
        self.assertEqual(2, len(self.filter))
                             
    def testFilteredCategories(self):
        self.filter.addCategory('test')
        self.failUnless('test' in self.filter.filteredCategories())
        
    def testClearFilter(self):
        self.filter.addCategory('parent')
        self.filter.removeAllCategories()
        self.assertEqual(2, len(self.filter))
        
    def testRemoveCategoryThatIsNotUsed(self):
        self.filter.removeCategory('parent')
        self.assertEqual(2, len(self.filter))


class OriginalLengthTest(test.TestCase):
    def setUp(self):
        self.list = task.TaskList()
        self.filter = task.filter.CategoryFilter(self.list)
        
    def testEmptyList(self):
        self.assertEqual(0, self.filter.originalLength())
        
    def testNoFilter(self):
        self.list.append(task.Task())
        self.assertEqual(1, self.filter.originalLength())
        
    def testFilter(self):
        aTask = task.Task()
        aTask.addCategory('test')
        self.list.append(aTask)
        self.filter.addCategory('nottest')
        self.assertEqual(0, len(self.filter))
        self.assertEqual(1, self.filter.originalLength())

     
