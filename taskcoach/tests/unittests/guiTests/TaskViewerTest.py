'''
Task Coach - Your friendly task manager
Copyright (C) 2004-2011 Task Coach developers <developers@taskcoach.org>

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
'''

import wx, os, locale
import test
from taskcoachlib import gui, config, persistence, command, patterns, render
from taskcoachlib.i18n import _
from taskcoachlib.domain import task, date, effort, category, attachment


class TaskViewerUnderTest(gui.viewer.task.TaskViewer): # pylint: disable-msg=W0223
    def __init__(self, *args, **kwargs):
        super(TaskViewerUnderTest, self).__init__(*args, **kwargs)
        self.events = []
    
    def onAttributeChanged(self, event):
        super(TaskViewerUnderTest, self).onAttributeChanged(event)
        self.events.append(event)
        

class TaskViewerTestCase(test.wxTestCase):
    treeMode = 'Subclass responsibility'
    
    def setUp(self):
        super(TaskViewerTestCase, self).setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.task = task.Task(subject='task', startDateTime=date.Now())
        self.child = task.Task(subject='child', startDateTime=date.Now())
        self.child.setParent(self.task)
        self.taskFile = persistence.TaskFile()
        self.taskList = self.taskFile.tasks()
        self.viewer = TaskViewerUnderTest(self.frame, self.taskFile, 
                                          self.settings)
        self.viewer.sortBy('subject')
        self.viewer.setSortOrderAscending()
        self.viewer.setSortByTaskStatusFirst(True)
        self.viewer.showTree(self.treeMode)
        self.newColor = (100, 200, 100, 255)
        attachment.Attachment.attdir = os.getcwd()
        self.originalLocale = locale.getlocale(locale.LC_ALL)
        tmpLocale = os.environ['LC_ALL'] if 'LC_ALL' in os.environ else ('en_US' if '__WXMAC__' == wx.Platform else '')
        locale.setlocale(locale.LC_ALL, tmpLocale)

    def tearDown(self):
        super(TaskViewerTestCase, self).tearDown()
        locale.setlocale(locale.LC_ALL, self.originalLocale)
        attachment.Attachment.attdir = None

        for name in os.listdir('.'):
            if os.path.isdir(name) and name.endswith('_attachments'):
                os.rmdir(name) # pragma: no cover
        if os.path.isfile('test.mail'):
            os.remove('test.mail')

    def assertItems(self, *tasks):
        self.viewer.expandAll()
        self.assertEqual(self.viewer.size(), len(tasks))
        for index, eachTask in enumerate(tasks):
            self.assertItem(index, eachTask)
            
    def assertItem(self, index, aTask):
        if type(aTask) == type((), ):
            aTask, nrChildren = aTask
        else:
            nrChildren = 0
        subject = aTask.subject(recursive=not self.viewer.isTreeViewer())
        treeItem = self.viewer.widget.GetItemChildren(recursively=True)[index]
        self.assertEqual(subject, self.viewer.widget.GetItemText(treeItem))
        self.assertEqual(nrChildren, 
            self.viewer.widget.GetChildrenCount(treeItem, recursively=False))

    def firstItem(self):
        widget = self.viewer.widget
        return widget.GetFirstChild(widget.GetRootItem())[0]

    def getItemText(self, row, column):
        assert row==0
        return self.viewer.widget.GetItemText(self.firstItem(), column)
                                             
    def getFirstItemTextColor(self):
        return self.viewer.widget.GetItemTextColour(self.firstItem())
    
    def getFirstItemBackgroundColor(self):
        return self.viewer.widget.GetItemBackgroundColour(self.firstItem())

    def getFirstItemFont(self):
        return self.viewer.widget.GetItemFont(self.firstItem())
    
    def getFirstItemIcon(self, column=0):
        return self.viewer.widget.GetItemImage(self.firstItem(), column=column)

    def showColumn(self, columnName, show=True):
        self.viewer.showColumnByName(columnName, show)

    def setColor(self, setting):
        self.settings.set('fgcolor', setting, str(self.newColor))        
         
    def assertColor(self, expectedColor=None):
        expectedColor = expectedColor or wx.Colour(*self.newColor)
        self.assertEqual(expectedColor, self.getFirstItemTextColor())
        
    def assertBackgroundColor(self):
        self.assertEqual(wx.Colour(*self.newColor), 
                         self.getFirstItemBackgroundColor())
                         
    def assertIcon(self, icon, column=0):
        self.assertEqual(self.viewer.imageIndex[icon], 
                         self.getFirstItemIcon(column))
        

class CommonTestsMixin(object):
    def testCreate(self):
        self.assertItems()
        
    def testAddTask(self):
        self.taskList.append(self.task)
        self.assertItems(self.task)

    def testRemoveTask(self):
        self.taskList.append(self.task)
        self.taskList.remove(self.task)
        self.assertItems()

    def testUndoRemoveTaskWithSubtask(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.viewer.select([self.task])
        self.viewer.updateSelection()
        deleteItem = self.viewer.deleteItemCommand()
        deleteItem.do()
        deleteItem.undo()
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)

    def testCurrent(self):
        self.taskList.append(self.task)
        self.assertEqual([self.task], self.viewer.curselection())

    def testDeleteSelectedTask(self):
        self.taskList.append(self.task)
        self.viewer.widget.selectall()
        self.viewer.updateSelection()
        self.taskList.removeItems(self.viewer.curselection())
        self.assertItems()

    def testSelectedTaskStaysSelectedWhenStartingEffortTracking(self):
        self.taskList.append(self.task)
        self.assertEqual([self.task], self.viewer.curselection())
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual([self.task], self.viewer.curselection())
        
    def testChildOrder(self):
        child1 = task.Task(subject='1', startDateTime=date.Now())
        self.task.addChild(child1)
        child2 = task.Task(subject='2', startDateTime=date.Now())
        self.task.addChild(child2)
        self.taskList.append(self.task)
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 2), child1, child2)
        else:
            self.assertItems(child1, child2, self.task)

    def testChildSubjectRendering(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)
           
    def testSortOrder(self):
        self.task.addChild(self.child)
        task2 = task.Task(subject='zzz')
        self.taskList.extend([self.task, task2])
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), self.child, task2)
        else:
            self.assertItems(self.child, self.task, task2)

    def testMarkCompleted(self):
        task2 = task.Task(subject='task2')
        self.taskList.extend([self.task, task2])
        self.assertItems(self.task, task2)
        self.task.setCompletionDateTime()
        self.assertItems(task2, self.task)
        
    def testMakeInactive(self):
        task2 = task.Task(subject='task2', startDateTime=date.Now())
        self.taskList.extend([self.task, task2])
        self.assertItems(self.task, task2)
        self.task.setStartDateTime(date.Now() + date.oneDay)
        self.assertItems(task2, self.task)
                        
    def testViewDueTodayHidesTasksNotDueToday(self):
        self.viewer.setFilteredByDueDateTime('Today')
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.assertItems()
        
    def testViewDueTodayShowsTasksWhoseChildrenAreDueToday(self):
        self.viewer.setFilteredByDueDateTime('Today')
        child = task.Task(subject='child', dueDateTime=date.Now().replace(hour=12))
        self.task.addChild(child)
        self.taskList.append(self.task)
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), child)
        else:
            self.assertItems(child)
        
    def testFilterCompletedTasks(self):
        self.viewer.setFilteredByCompletionDateTime('Always')
        completedChild = task.Task(completionDateTime=date.Now() - date.oneHour)
        notCompletedChild = task.Task(startDateTime=date.Now())
        self.task.addChild(notCompletedChild)
        self.task.addChild(completedChild)
        self.taskList.append(self.task)
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), notCompletedChild)
        else:
            self.assertItems(notCompletedChild, self.task)
            
    def testUndoMarkCompletedWhenFilteringCompletedTasks(self):
        self.viewer.setFilteredByCompletionDateTime('Always')
        child1 = task.Task('child1')
        child2 = task.Task('child2')
        grandChild = task.Task('grandChild')
        self.task.addChild(child1)
        self.task.addChild(child2)
        child2.addChild(grandChild)
        self.taskList.append(self.task)
        self.viewer.expandAll()
        self.assertEqual(4, self.viewer.size())
        markCompletedCommand = command.MarkCompletedCommand(self.taskList, 
                                                            [grandChild])
        markCompletedCommand.do()
        self.assertEqual(2, self.viewer.size())
        patterns.CommandHistory().undo()
        self.assertEqual(4, self.viewer.size())
            
    def testDefaultVisibleColumns(self):
        self.assertEqual(_('Subject'), self.viewer.widget.GetColumn(0).GetText())    
        self.assertEqual(_('Start date'), self.viewer.widget.GetColumn(1).GetText())    
        self.assertEqual(_('Due date'), self.viewer.widget.GetColumn(2).GetText())
        self.assertEqual(3, self.viewer.widget.GetColumnCount())
    
    def testTurnOffStartDateColumn(self):
        self.showColumn('startDateTime', False)
        self.assertEqual(_('Due date'), self.viewer.widget.GetColumn(1).GetText())
        self.assertEqual(2, self.viewer.widget.GetColumnCount())
        
    def testShowSort_Subject(self):
        self.assertNotEqual(-1, self.viewer.widget.GetColumn(0).GetImage())
        self.assertEqual(-1, self.viewer.widget.GetColumn(1).GetImage())
    
    def testForegroundColorWhenTaskIsCompleted(self):
        self.taskList.append(self.task)
        self.task.setCompletionDateTime()
        newColor = self.task.statusFgColor()
        newColor = wx.Colour(newColor.Red(), newColor.Green(), newColor.Blue())
        self.assertColor(newColor)
        
    def testTurnColumnsOnAndOff(self):
        columns = dict(hourlyFee=(3, _('Hourly fee')), 
                       fixedFee=(3, _('Fixed fee')),
                       revenue=(3, _('Revenue')),
                       priority=(3, _('Priority')),
                       prerequisites=(1, _('Prerequisites')),
                       dependencies=(1, _('Dependencies')),
                       categories=(1, _('Categories')),
                       percentageComplete=(3, _('% complete')),
                       recurrence=(3, _('Recurrence')),
                       notes=(1, ''),
                       attachments=(1, ''))
        for column in columns:
            columnIndex, expectedHeader = columns[column] 
            self.showColumn(column)
            actualHeader = self.viewer.widget.GetColumn(columnIndex).GetText()
            self.assertEqual(expectedHeader, actualHeader)
            self.showColumn(column, False)
            self.assertEqual(3, self.viewer.widget.GetColumnCount())
            
    def testRenderFixedFee(self):
        taskWithFixedFee = task.Task(fixedFee=100)
        self.taskList.append(taskWithFixedFee)
        self.showColumn('fixedFee')
        self.assertEqual(locale.currency(100, False), self.getItemText(0,3))
        self.assertEqual(_('Fixed fee'), 
                         self.viewer.widget.GetColumn(3).GetText())
                        
    def testRenderPercentageComplete_0(self):
        uncompletedTask = task.Task()
        self.taskList.append(uncompletedTask)
        self.showColumn('percentageComplete')
        self.assertEqual('', self.getItemText(0,3))

    def testRenderPercentageComplete_100(self):
        completedTask = task.Task(completionDateTime=date.Now() - date.oneHour)
        self.taskList.append(completedTask)
        self.showColumn('percentageComplete')
        self.assertEqual('100%', self.getItemText(0,3))

    def testRenderSingleCategory(self):
        cat = category.Category(subject='Category')
        self.task.addCategory(cat)
        cat.addCategorizable(self.task)
        self.assertEqual('Category', self.viewer.renderCategories(self.task))
                
    def testRenderMultipleCategories(self):
        for index in range(1, 3):
            cat = category.Category(subject='Category %d'%index)
            self.task.addCategory(cat)
            cat.addCategorizable(self.task)
        self.assertEqual('Category 1, Category 2', self.viewer.renderCategories(self.task))
        
    def testRenderSingleChildCategory(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        cat = category.Category(subject='Category')
        self.child.addCategory(cat)
        cat.addCategorizable(self.child)
        expectedCategory = '(Category)' if self.viewer.isTreeViewer() else ''
        self.assertEqual(expectedCategory, self.viewer.renderCategories(self.task))

    def testRenderMultipleChildCategories(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        for index in range(1, 3):
            cat = category.Category(subject='Category %d'%index)
            self.child.addCategory(cat)
            cat.addCategorizable(self.child)
        expectedCategory = '(Category 1, Category 2)' if self.viewer.isTreeViewer() else ''
        self.assertEqual(expectedCategory, self.viewer.renderCategories(self.task))
        
    def testRenderDifferentParentAndChildCategories(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        for index, task in enumerate([self.task, self.child]):
            cat = category.Category(subject='Category %d'%index)
            task.addCategory(cat)
            cat.addCategorizable(task)
        expectedCategory = 'Category 0 (Category 1)' if self.viewer.isTreeViewer() else 'Category 0'
        self.assertEqual(expectedCategory, self.viewer.renderCategories(self.task))

    def testRenderSameParentAndChildCategory(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        cat = category.Category(subject='Category')
        for task in (self.task, self.child):
            task.addCategory(cat)
            cat.addCategorizable(task)
        expectedCategory = 'Category'
        self.assertEqual(expectedCategory, self.viewer.renderCategories(self.task))

    def testRenderRecurrence(self):
        taskWithRecurrence = task.Task(recurrence=date.Recurrence('weekly', amount=2))
        self.showColumn('recurrence')
        self.taskList.append(taskWithRecurrence)
        self.assertEqual('Every other week', self.getItemText(0,3))
        
    def testRenderAttachment(self):
        att = attachment.FileAttachment('whatever')
        self.task.addAttachment(att)
        self.taskList.append(self.task)
        self.showColumn('attachments')
        self.assertIcon('paperclip_icon', column=1)
        
    def testOneDayLeft(self):
        self.showColumn('timeLeft')
        timeLeft = date.TimeDelta(hours=25, seconds=30)
        self.taskList.append(self.task)
        self.task.setDueDateTime(date.Now() + timeLeft)
        self.assertEqual(render.timeLeft(timeLeft, False), 
                         self.getItemText(0, 3))
        
    def testReverseSortOrderWithGrandchildren(self):
        self.task.addChild(self.child)
        grandchild = task.Task(subject='grandchild', startDateTime=date.Now())
        self.child.addChild(grandchild)
        task2 = task.Task(subject='zzz', startDateTime=date.Now())
        self.taskList.extend([self.task, task2])
        self.viewer.setSortOrderAscending(False)
        if self.viewer.isTreeViewer():
            self.assertItems(task2, (self.task, 1), (self.child, 1), grandchild)
        else:
            self.assertItems(task2, self.task, grandchild, self.child)
                
    def testReverseSortOrder(self):
        self.task.addChild(self.child)
        task2 = task.Task(subject='zzz', startDateTime=date.Now())
        self.taskList.extend([self.task, task2])
        self.viewer.setSortOrderAscending(False)
        if self.viewer.isTreeViewer():
            self.assertItems(task2, (self.task, 1), self.child)
        else:
            self.assertItems(task2, self.task, self.child)

    def testSortByDueDate(self):
        self.task.addChild(self.child)
        task2 = task.Task(subject='zzz', startDateTime=date.Now())
        child2 = task.Task(subject='child 2', startDateTime=date.Now())
        task2.addChild(child2)
        child2.setParent(task2)
        self.taskList.extend([self.task, task2])
        if self.viewer.isTreeViewer():
            self.assertItems((self.task, 1), self.child, (task2, 1), child2)
        else:
            self.assertItems(self.child, child2, self.task, task2) 
        child2.setDueDateTime(date.Now().endOfDay())
        self.viewer.sortBy('dueDateTime')
        if self.viewer.isTreeViewer():
            self.assertItems((task2, 1), child2, (self.task, 1), self.child)
        else:    
            self.assertItems(child2, self.child, self.task, task2)
            
    def testSortByPrerequisite_OnePrerequisite(self):
        self.viewer.sortBy('prerequisites')
        prerequisite = task.Task()
        self.task.addPrerequisites([prerequisite])
        self.taskList.extend([prerequisite, self.task])
        self.assertItems(prerequisite, self.task)

    def testSortByPrerequisite_TwoPrerequisites(self):
        self.viewer.sortBy('prerequisites')
        prerequisite1 = task.Task(subject='1')
        prerequisite2 = task.Task(subject='2')
        self.task.addPrerequisites([prerequisite1, prerequisite2])
        self.taskList.extend([prerequisite1, prerequisite2, self.task])
        try:
            self.assertItems(prerequisite1, prerequisite2, self.task)
        except AssertionError:
            self.assertItems(prerequisite2, prerequisite1, self.task)

    def testSortByPrerequisite_ChainedPrerequisites(self):
        self.viewer.sortBy('prerequisites')
        task0 = task.Task(subject='0')
        task1 = task.Task(subject='1')
        task2 = task.Task(subject='2')
        task2.addPrerequisites([task1])
        task1.addPrerequisites([task0])
        self.taskList.extend([task0, task1, task2])
        self.assertItems(task0, task1, task2) # Prerequisites = '', '0', '1'
        self.viewer.setSortOrderAscending(False)
        self.assertItems(task2, task1, task0) # Prerequisites = '1', '0', ''

    def testSortBySubject_AddPrerequisite(self):
        task0 = task.Task(subject='0', startDateTime=date.DateTime(2000,1,1))
        task1 = task.Task(subject='1', startDateTime=date.DateTime(2000,1,1))
        self.taskList.extend([task0, task1])
        self.assertItems(task0, task1)
        task0.addPrerequisites([task1])
        self.assertItems(task1, task0)
        
    def testSortByCategories(self):
        cat0 = category.Category(subject='Category 0')
        cat1 = category.Category(subject='Category 1')
        task0 = task.Task(subject='0')
        task1 = task.Task(subject='1')
        task0.addCategory(cat1)
        cat1.addCategorizable(task0)
        task1.addCategory(cat0)
        cat0.addCategorizable(task1)
        self.taskList.extend([task0, task1])
        self.assertItems(task0, task1)
        self.viewer.sortBy('categories')
        self.assertItems(task1, task0)

    def testSortByChildCategories(self):
        cat0 = category.Category(subject='Category 0')
        cat1 = category.Category(subject='Category 1')
        task0 = task.Task(subject='0')
        task1 = task.Task(subject='1')
        task1_1 = task.Task(subject='1.1')
        task1.addChild(task1_1)
        task0.addCategory(cat1)
        cat1.addCategorizable(task0)
        task1_1.addCategory(cat0)
        cat0.addCategorizable(task1_1)
        self.taskList.extend([task0, task1])
        if self.viewer.isTreeViewer():
            self.assertItems(task0, (task1, 1), task1_1)
        else:
            self.assertItems(task0, task1, task1_1)
        self.viewer.sortBy('categories')
        if self.viewer.isTreeViewer():
            self.assertItems((task1, 1), task1_1, task0)
        else:
            self.assertItems(task1, task1_1, task0)
        
    def testChangeActiveTaskForegroundColor(self):
        self.setColor('activetasks')
        self.taskList.append(task.Task(subject='test', startDateTime=date.Now()))
        self.assertColor()
    
    def testChangeInactiveTaskForegroundColor(self):
        self.setColor('inactivetasks')
        self.taskList.append(task.Task(startDateTime=date.Now() + date.oneDay))
        self.assertColor()
    
    def testChangeCompletedTaskForegroundColor(self):
        self.setColor('completedtasks')
        self.taskList.append(task.Task(completionDateTime=date.Now()))
        self.assertColor()

    def testChangeDueSoonTaskForegroundColor(self):
        self.setColor('duesoontasks')
        self.taskList.append(task.Task(dueDateTime=date.Now().endOfDay()))
        self.assertColor()

    def testChangeOverDueTaskForegroundColor(self):
        self.setColor('overduetasks')
        self.taskList.append(task.Task(dueDateTime=date.Now() - date.oneDay))
        self.assertColor()
            
    def testStatusMessage_EmptyTaskList(self):
        self.assertEqual(('Tasks: 0 selected, 0 visible, 0 total', 
            'Status: 0 overdue, 0 inactive, 0 completed'),
            self.viewer.statusMessages())
    
    def testOnDropFiles(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.onDropFiles(aTask, ['filename'])
        self.assertEqual([attachment.FileAttachment('filename')],
                         self.viewer.presentation()[0].attachments())

    def testOnDropURL(self):
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.onDropURL(aTask, 'http://www.example.com/')
        self.assertEqual([attachment.URIAttachment('http://www.example.com/')],
                         self.viewer.presentation()[0].attachments())

    def testOnDropMail(self):
        file('test.mail', 'wb').write('Subject: foo\r\n\r\nBody\r\n')
        aTask = task.Task()
        self.taskList.append(aTask)
        self.viewer.onDropMail(aTask, 'test.mail')
        self.assertEqual([attachment.MailAttachment('test.mail')],
                         self.viewer.presentation()[0].attachments())
        
    def testCategoryBackgroundColor(self):
        cat = category.Category('category with background color', bgColor=self.newColor)
        cat.addCategorizable(self.task)
        self.task.addCategory(cat)
        self.taskList.append(self.task)
        self.assertBackgroundColor()
        
    def testNewItem(self):
        self.taskFile.categories().append(category.Category('cat', filtered=True))
        dialog = self.viewer.newItemDialog(bitmap='new')
        tree = dialog._interior[4].viewer.widget
        firstChild = tree.GetFirstChild(tree.GetRootItem())[0]
        self.failUnless(firstChild.IsChecked())
        
    def testFont(self):
        self.taskList.append(task.Task(font=wx.SWISS_FONT))
        self.assertEqual(wx.SWISS_FONT, self.getFirstItemFont())
        
    def testIconUpdatesWhenStartDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.setStartDateTime(date.Now() + date.oneDay)
        self.assertIcon('led_grey_icon')

    def testIconUpdatesWhenDueDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.setDueDateTime(date.Now()+ date.oneHour)
        self.assertIcon('led_orange_icon')

    def testIconUpdatesWhenCompletionDateTimeChanges(self):
        self.taskList.append(self.task)
        self.task.setCompletionDateTime(date.Now())
        self.assertIcon('led_green_icon')

    def testIconUpdatesWhenPrerequisiteIsAdded(self):
        prerequisite = task.Task('zzz')
        self.taskList.extend([prerequisite, self.task])
        self.task.addPrerequisites([prerequisite])
        prerequisite.addDependencies([self.task])
        self.assertIcon('led_grey_icon')

    def testIconUpdatesWhenPrerequisiteIsCompleted(self):
        prerequisite = task.Task(subject='zzz')
        self.taskList.extend([prerequisite, self.task])
        self.task.addPrerequisites([prerequisite])
        prerequisite.addDependencies([self.task]) 
        prerequisite.setCompletionDateTime(date.Now())
        self.assertIcon('led_blue_icon') # Should be grey?
        
    def testIconUpdatesWhenEffortTrackingStarts(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.assertIcon('clock_icon')
        
    def testIconUpdatesWhenEffortTrackingStops(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.task.stopTracking()
        self.assertIcon('led_blue_icon')
        
    def testIconUpdatesWhenTaskBecomesOverdue(self):
        dueDateTime = date.Now() + date.TimeDelta(seconds=10)
        dueDateTime = dueDateTime.replace(microsecond=0)
        self.task.setDueDateTime(dueDateTime)
        self.taskList.append(self.task)
        self.assertIcon('led_orange_icon')
        now = dueDateTime + date.oneSecond
        oldNow = date.Now
        date.Now = lambda: now
        date.Clock().notifySpecificTimeObservers(now)
        self.assertIcon('led_red_icon')
        date.Now = oldNow
        
    def testModeIsSavedInSettings(self):
        self.assertEqual(self.treeMode, 
            self.settings.getboolean(self.viewer.settingsSection(), 'treemode'))

    def testRenderSubject(self):
        self.task.addChild(self.child)
        expectedSubject = 'child' if self.treeMode else 'task -> child'
        self.assertEqual(expectedSubject, self.viewer.renderSubject(self.child))

    def testItemOrder(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)        
        if self.treeMode:
            self.assertItems((self.task, 1), self.child)
        else:
            self.assertItems(self.child, self.task)
                         
    def testItemOrderAfterSwitch(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.viewer.showTree(not self.treeMode)
        if self.treeMode:
            self.assertItems(self.child, self.task)
        else:
            self.assertItems((self.task, 1), self.child)

    def testItemOrderAfterSwitchWhenOrderDoesNotChange(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.task.setSubject('a') # task comes before child
        self.viewer.showTree(not self.treeMode)
        if self.treeMode:
            self.assertItems(self.task, self.child)
        else:
            self.assertItems((self.task, 1), self.child)
            
    def assertEventFired(self, type_):
        types = []
        for event in self.viewer.events:
            types.extend(event.types())
        self.failUnless(type_ in types,
                        '"%s" not in %s' % (type_, self.viewer.events))

    def testGetTimeSpent(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task, date.DateTime(2000,1,1),
                                                     date.DateTime(2000,1,2)))
        self.showColumn('timeSpent')
        timeSpent = self.getItemText(0, 3)
        self.assertEqual("24:00:00", timeSpent)

    def testGetTotalTimeSpent(self):
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.task.expand(False, context=self.viewer.settingsSection())
        self.task.addEffort(effort.Effort(self.task, date.DateTime(2000,1,1),
                                                     date.DateTime(2000,1,2)))
        self.child.addEffort(effort.Effort(self.child, date.DateTime(2000,1,1),
                                                     date.DateTime(2000,1,2)))
        self.showColumn('timeSpent')
        timeSpent = self.getItemText(0, 3)
        expectedTimeSpent = "(48:00:00)" if self.treeMode else "24:00:00"
        self.assertEqual(expectedTimeSpent, timeSpent)
        
    def testGetSelection(self):
        taskA = task.Task('a')
        taskB = task.Task('b')
        self.viewer.presentation().extend([taskA, taskB])
        self.viewer.select([taskA])
        self.viewer.updateSelection()
        self.assertEqual([taskA], self.viewer.curselection())

    def testGetSelection_AfterResort(self):
        taskA = task.Task('a')
        taskB = task.Task('b')
        self.viewer.presentation().extend([taskA, taskB])
        self.viewer.widget.select([taskA])
        self.viewer.updateSelection()
        self.viewer.setSortOrderAscending(False)
        self.assertEqual([taskA], self.viewer.curselection())
        
    def testChangeSubject(self):
        self.taskList.append(self.task)
        self.task.setSubject('New subject')
        self.assertEqual(task.Task.subjectChangedEventType(), 
                         self.viewer.events[0].type())

    def testChangeStartDateTimeWhileColumnShown(self):
        self.taskList.append(self.task)
        self.task.setStartDateTime(date.Now() - date.oneDay)
        self.assertEqual('task.startDateTime', self.viewer.events[0].type())

    def testStartTracking(self):
        self.taskList.append(self.task)
        self.task.addEffort(effort.Effort(self.task))
        self.assertEqual(self.task.trackStartEventType(), self.viewer.events[0].type())

    def testChangeStartDateTimeWhileColumnNotShown(self):
        self.taskList.append(self.task)
        self.showColumn('startDate', False)
        self.task.setStartDateTime(date.Now() - date.oneDay)
        self.assertEqual(1, len(self.viewer.events))

    def testChangeDueDate(self):
        self.taskList.append(self.task)
        self.task.setDueDateTime(date.Now().endOfDay())
        self.failUnless('task.dueDateTime' in self.viewer.events[0].types())

    def testChangeCompletionDateWhileColumnNotShown(self):
        self.taskList.append(self.task)
        self.task.setCompletionDateTime(date.Now())
        # We still get an event for the subject column:
        expectedEvent = patterns.Event('task.completionDateTime', self.task, self.task.completionDateTime())
        expectedEvent.addSource(self.task, self.task.percentageComplete(), type=self.task.percentageCompleteChangedEventType())
        expectedEvent.addSource(self.task, type=self.task.appearanceChangedEventType())
        self.assertEqual([expectedEvent], self.viewer.events)

    def testChangeCompletionDateWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn('completionDate')
        self.task.setCompletionDateTime(date.Now())
        expectedEvent = patterns.Event('task.completionDateTime', self.task, self.task.completionDateTime())
        expectedEvent.addSource(self.task, self.task.percentageComplete(), type=self.task.percentageCompleteChangedEventType())
        expectedEvent.addSource(self.task, type=self.task.appearanceChangedEventType())
        self.assertEqual([expectedEvent], self.viewer.events)

    def testChangePercentageCompleteWhileColumnNotShown(self):
        self.taskList.append(self.task)
        self.task.setPercentageComplete(50)
        self.assertEventFired('task.percentageComplete')

    def testChangePercentageCompleteWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn('percentageComplete')
        self.task.setPercentageComplete(50)
        self.assertEventFired('task.percentageComplete')

    def testChangePriorityWhileColumnNotShown(self):
        self.taskList.append(self.task)
        self.task.setPriority(10)
        self.failIf(self.viewer.events)

    def testChangePriorityWhileColumnShown(self):
        self.taskList.append(self.task)
        self.showColumn('priority')
        self.task.setPriority(10)
        self.assertEventFired('task.priority')

    def testChangePriorityOfSubtask(self):
        self.showColumn('priority')
        self.task.addChild(self.child)
        self.taskList.append(self.task)
        self.child.setPriority(10)
        self.assertEventFired('task.priority')
        
    def testChangeHourlyFeeWhileColumnShown(self):
        self.showColumn('hourlyFee')
        self.taskList.append(self.task)
        self.task.setHourlyFee(100)
        self.assertEqual(render.monetaryAmount(100.), self.getItemText(0, 3))
        
    def testChangeFixedFeeWhileColumnShown(self):
        self.showColumn('fixedFee')
        self.taskList.append(self.task)
        self.task.setFixedFee(200)
        self.assertEqual(render.monetaryAmount(200.), self.getItemText(0, 3))

    def testCollapsedCompositeTaskShowsRecursiveFixedFee(self):
        self.showColumn('fixedFee')
        self.taskList.extend([self.task, self.child])
        self.task.addChild(self.child)
        self.task.setFixedFee(100)
        self.child.setFixedFee(200)
        self.viewer.setSortOrderAscending(False)
        expectedAmount = "(%s)" % locale.currency(300, False) if self.treeMode else locale.currency(100, False)
        self.task.expand(False, context=self.viewer.settingsSection())
        self.assertEqual(expectedAmount, self.getItemText(0, 3))

    def testChangePrerequisiteSubject(self):
        self.showColumn('prerequisites')
        self.viewer.setSortOrderAscending(False)
        prerequisite = task.Task(subject='prerequisite')
        self.taskList.extend([self.task, prerequisite])
        self.task.addPrerequisites([prerequisite])
        prerequisite.addDependencies([self.task])
        self.assertEqual('prerequisite', self.getItemText(0,1))
        prerequisite.setSubject('new')
        self.assertEqual('new', self.getItemText(0,1))

    def testChangeDependencySubject(self):
        self.showColumn('dependencies')
        self.viewer.setSortOrderAscending(False)
        dependency = task.Task(subject='dependency')
        self.taskList.extend([self.task, dependency])
        dependency.addPrerequisites([self.task])
        self.task.addDependencies([dependency])
        self.assertEqual('dependency', self.getItemText(0,1))
        dependency.setSubject('new')
        self.assertEqual('new', self.getItemText(0,1))
  
    # Test all attributes...


class TaskViewerInTreeModeTest(CommonTestsMixin, TaskViewerTestCase):
    treeMode = True


class TaskViewerInListModeTest(CommonTestsMixin, TaskViewerTestCase):
    treeMode = False
        
        
        
class TaskCalendarViewerTest(test.wxTestCase):
    def setUp(self):
        super(TaskCalendarViewerTest, self).setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        self.frame.taskFile = self.taskFile
        self.viewer = gui.viewer.task.CalendarViewer(self.frame, self.taskFile, 
                                                     self.settings)
        self.originalTopWindow = wx.GetApp().TopWindow
        wx.GetApp().TopWindow = self.frame # uiCommands use TopWindow to get the main window
        
    def tearDown(self):
        super(TaskCalendarViewerTest, self).tearDown()
        wx.GetApp().TopWindow = self.originalTopWindow
        
    def openDialogAndAssertDateTimes(self, dateTime, expectedStartDateTime, 
                                     expectedDueDateTime):
        dialog = self.viewer.onCreate(dateTime, show=False)
        newTask = list(self.taskFile.tasks())[0]
        self.assertEqual(expectedStartDateTime, newTask.startDateTime())
        self.assertEqual(expectedDueDateTime, newTask.dueDateTime())
        
    def testOnCreateSetsStartandDueDateTime(self):
        dateTime = date.DateTime(2010,10,10,16,0,0)
        self.openDialogAndAssertDateTimes(dateTime, dateTime, dateTime)

    def testOnCreateKeepsStartDateTimeAndMakesDueDateTimeEndOfDayWhenDateTimeIsStartOfDay(self):
        dateTime = date.DateTime(2010,10,1,0,0,0)
        self.openDialogAndAssertDateTimes(dateTime, dateTime, dateTime.endOfDay())

        
class TaskSquareMapViewerTest(test.wxTestCase):
    def testCreate(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        gui.viewer.task.SquareTaskViewer(self.frame, self.taskFile, self.settings)
        
        
class TaskTimelineViewerTest(test.wxTestCase):
    def testCreate(self):
        task.Task.settings = self.settings = config.Settings(load=False)
        self.taskFile = persistence.TaskFile()
        gui.viewer.task.TimelineViewer(self.frame, self.taskFile, self.settings)
