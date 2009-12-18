'''
Task Coach - Your friendly task manager
Copyright (C) 2004-2009 Frank Niessink <frank@niessink.com>
Copyright (C) 2007 Jerome Laheurte <fraca7@free.fr>

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

import xml.parsers.expat, wx, StringIO, os, tempfile
import test
from taskcoachlib import persistence
from taskcoachlib.domain import date


class XMLReaderTestCase(test.TestCase):
    tskversion = 'Subclass responsibility'

    def writeAndRead(self, xmlContents):
        # pylint: disable-msg=W0201
        self.fd = StringIO.StringIO()
        self.fd.name = 'testfile.tsk'
        self.reader = persistence.XMLReader(self.fd)
        allXML = '<?taskcoach release="whatever" tskversion="%d"?>\n'%self.tskversion + xmlContents
        self.fd.write(allXML)
        self.fd.seek(0)
        return self.reader.read()

    def writeAndReadTasks(self, xmlContents):
        return self.writeAndRead(xmlContents)[0]

    def writeAndReadCategories(self, xmlContents):
        return self.writeAndRead(xmlContents)[1]

    def writeAndReadNotes(self, xmlContents):
        return self.writeAndRead(xmlContents)[2]

    def writeAndReadSyncMLConfig(self, xmlContents):
        return self.writeAndRead(xmlContents)[3]

    def writeAndReadGUID(self, xmlContents):
        return self.writeAndRead(xmlContents)[4]

    def writeAndReadTasksAndCategories(self, xmlContents):
        tasks, categories, _, _, _ = self.writeAndRead(xmlContents)
        return tasks, categories

    def writeAndReadTasksAndCategoriesAndNotes(self, xmlContents):
        tasks, categories, notes, _, _ = self.writeAndRead(xmlContents)
        return tasks, categories, notes

    def writeAndReadCategoriesAndNotes(self, xmlContents):
        _, categories, notes, _, _ = self.writeAndRead(xmlContents)
        return categories, notes
    

class TempFileLockTest(XMLReaderTestCase):
    tskversion = 25

    def setUp(self):
        self.oldMkstemp = tempfile.mkstemp
        def newMkstemp(*args, **kwargs):
            handle, name = self.oldMkstemp(*args, **kwargs)
            self.__filename = name # pylint: disable-msg=W0201
            return handle, name
        tempfile.mkstemp = newMkstemp

        super(TempFileLockTest, self).setUp()

    def tearDown(self):
        tempfile.mkstemp = self.oldMkstemp
        super(TempFileLockTest, self).tearDown()

    def testLock(self):
        if os.name == 'nt':
            import base64
            self.writeAndReadTasks(\
                '<tasks>\n<task status="0">\n'
                '<attachment type="mail" status="0">\n'
                '<data extension="eml">%s</data>\n'
                '</attachment>\n</task>\n</tasks>\n'%base64.encodestring('Data'))
            try:
                os.remove(self.__filename)
            except:
                pass # pylint: disable-msg=W0702

            self.assert_(os.path.exists(self.__filename))


class XMLReaderVersion6Test(XMLReaderTestCase):
    tskversion = 6

    def testDescription(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task description="%s" id="foo"/>
        </tasks>\n'''%u'Description')
        self.assertEqual(u'Description', tasks[0].description())

    def testEffortDescription(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task id="foo">
                <effort start="2004-01-01 10:00:00.123000" 
                        stop="2004-01-01 10:30:00.123000" 
                        description="Yo"/>
            </task>
        </tasks>''')
        self.assertEqual('Yo', tasks[0].efforts()[0].description())
        

class XMLReaderVersion8Test(XMLReaderTestCase):   
    tskversion = 8

    def testReadTaskWithoutPriority(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(0, tasks[0].priority())
        
        
class XMLReaderVersion9Test(XMLReaderTestCase):
    tskversion = 9
    
    def testReadTaskWithoutId(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.failUnless(tasks[0].id())
        

class XMLReaderVersion10Test(XMLReaderTestCase):
    tskversion = 10
    
    def testReadTaskWithoutFee(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(0, tasks[0].hourlyFee())
        self.assertEqual(0, tasks[0].fixedFee())


class XMLReaderVersion11Test(XMLReaderTestCase):
    tskversion = 11
    
    def testReadTaskWithoutReminder(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(None, tasks[0].reminder())
        
        
class XMLReaderVersion12Test(XMLReaderTestCase):
    tskversion = 12
    
    def testReadTaskWithoutMarkCompletedWhenAllChildrenCompletedSetting(self):
        tasks = self.writeAndReadTasks('<tasks><task id="foo"/></tasks>')
        self.assertEqual(None, 
                         tasks[0].shouldMarkCompletedWhenAllChildrenCompleted())
        

class XMLReaderVersion13Test(XMLReaderTestCase):
    tskversion = 13

    def testOneCategory(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <task id="1">
                <category>test</category>
            </task>
        </tasks>''')

        self.assertEqual('test', categories[0].subject())
        self.assertEqual(set([tasks[0]]), categories[0].categorizables())
        self.assertEqual(set([categories[0]]), tasks[0].categories())

    def testMultipleCategories(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <task id="1">
                <category>test</category>
                <category>another</category>
                <category>yetanother</category>
            </task>
        </tasks>''')

        for category in categories:
            self.assertEqual(set([tasks[0]]), category.categorizables())
            self.failUnless(category in tasks[0].categories())
            
    def testSubTaskWithCategories(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <task id="1">
                <category>test</category>
                <task id="1.1">
                    <category>another</category>
                </task>
            </task>
        </tasks>''')
        testCategory = categories[0]
        anotherCategory = categories[1]
        self.assertEqual("1", list(testCategory.categorizables())[0].id())
        self.assertEqual("1.1", list(anotherCategory.categorizables())[0].id())         
        self.assertEqual(set([testCategory]), tasks[0].categories())
        self.assertEqual(set([anotherCategory]), tasks[0].children()[0].categories())
        
        
class XMLReaderVersion14Test(XMLReaderTestCase):
    tskversion = 14
    
    def testEffortWithMilliseconds(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00.123000" 
                        stop="2004-01-01 10:30:00.123000"/>
            </task>
        </tasks>''')
        self.assertEqual(1, len(tasks[0].efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), tasks[0].timeSpent())
        self.assertEqual(tasks[0], tasks[0].efforts()[0].task())


class XMLReaderVersion16Text(XMLReaderTestCase):
    tskversion = 16

    def testOneAttachmentCompat(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment>whatever.tsk</attachment>
            </task>
        </tasks>''')
        self.assertEqual(['whatever.tsk'], [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in tasks[0].attachments()])
        
    def testTwoAttachmentsCompat(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment>whatever.tsk</attachment>
                <attachment>another.txt</attachment>
            </task>
        </tasks>''')
        self.assertEqual(['whatever.tsk', 'another.txt'], 
                         [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk', 'another.txt'], 
                         [att.subject() for att in tasks[0].attachments()])
        
    def testOneAttachment(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment>FILE:whatever.tsk</attachment>
            </task>
        </tasks>''')
        self.assertEqual(['whatever.tsk'], [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in tasks[0].attachments()])
        
    def testTwoAttachments(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment>FILE:whatever.tsk</attachment>
                <attachment>FILE:another.txt</attachment>
            </task>
        </tasks>''')
        self.assertEqual(['whatever.tsk', 'another.txt'], 
                         [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk', 'another.txt'], 
                         [att.subject() for att in tasks[0].attachments()])


# There's no XMLReaderVersion17Test because the only difference between version
# 17 and 18 is the addition of an optional color attribute to categories in
# version 18. So the tests for version 18 test version 17 as well.


class XMLReaderVersion18Test(XMLReaderTestCase):
    tskversion = 18

    def testLastModificationTime(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task lastModificationTime="2004-01-01 10:00:00"/>
        </tasks>''')
        self.assertEqual(1, len(tasks)) # Ignore lastModificationTime


class XMLReaderVersion19Test(XMLReaderTestCase):
    tskversion = 19 # New in release 0.69.0?        

    def testDailyRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task recurrence="daily"/>
        </tasks>''')
        self.assertEqual('daily', tasks[0].recurrence().unit)    

    def testWeeklyRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task recurrence="weekly"/>
        </tasks>''')
        self.assertEqual('weekly', tasks[0].recurrence().unit)

    def testMonthlyRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task recurrence="monthly"/>
        </tasks>''')
        self.assertEqual('monthly', tasks[0].recurrence().unit)
                
    def testRecurrenceCount(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task recurrenceCount="10"/>
        </tasks>''')
        self.assertEqual(10, tasks[0].recurrence().count)
        
    def testMaxRecurrenceCount(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task maxRecurrenceCount="10"/>
        </tasks>''')
        self.assertEqual(10, tasks[0].recurrence().max)

    def testRecurrenceFrequency(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task recurrenceFrequency="3"/>
        </tasks>''')
        self.assertEqual(3, tasks[0].recurrence().amount)


class XMLReaderVersion20Test(XMLReaderTestCase):
    tskversion = 20 # New in release 0.71.0
           
    def testReadEmptyStream(self):
        reader = persistence.XMLReader(StringIO.StringIO())
        try:
            reader.read()
            self.fail('Expected ExpatError') # pragma: no cover
        except xml.parsers.expat.ExpatError:
            pass
        
    def testNoTasksAndNoCategories(self):
        tasks, categories, notes = self.writeAndReadTasksAndCategoriesAndNotes('<tasks/>\n')
        self.assertEqual(([], [], []), (tasks, categories, notes))
        
    def testOneTask(self):
        tasks = self.writeAndReadTasks('<tasks><task/></tasks>\n')
        self.assertEqual(1, len(tasks))
        self.assertEqual('', tasks[0].subject())

    def testTwoTasks(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task subject="1"/>
            <task subject="2"/>
        </tasks>\n''')
        self.assertEqual(2, len(tasks))
        self.assertEqual('1', tasks[0].subject())
        self.assertEqual('2', tasks[1].subject())
        
    def testOneTask_Subject(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task subject="Yo"/>
        </tasks>\n''')
        self.assertEqual('Yo', tasks[0].subject())
        
    def testOneTask_UnicodeSubject(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task subject="???"/>
        </tasks>\n''')
        self.assertEqual('???', tasks[0].subject())
        
    def testStartDate(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task startdate="2005-04-17"/>
        </tasks>\n''')
        self.assertEqual(date.Date(2005,4,17), tasks[0].startDate())
        
    def testDueDate(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task duedate="2005-04-17"/>
        </tasks>\n''')
        self.assertEqual(date.Date(2005,4,17), tasks[0].dueDate())
        
    def testCompletionDate(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task completiondate="2005-01-01"/>
        </tasks>\n''')
        self.assertEqual(date.Date(2005,1,1), tasks[0].completionDate())
        self.failUnless(tasks[0].completed())
        
    def testBudget(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task budget="4:10:10"/>
        </tasks>\n''')
        self.assertEqual(date.TimeDelta(hours=4, minutes=10, seconds=10), tasks[0].budget())

    def testBudget_NoBudget(self):
        tasks = self.writeAndReadTasks('<tasks><task/></tasks>\n')
        self.assertEqual(date.TimeDelta(), tasks[0].budget())
        
    def testDescription(self):
        description = u'Description\nline 2'
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <description>%s</description>
            </task>
        </tasks>\n'''%description)
        self.assertEqual(description, tasks[0].description())
    
    def testNoChildren(self):
        tasks = self.writeAndReadTasks('<tasks><task/></tasks>\n')
        self.failIf((tasks[0].children()))
        
    def testChild(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <task/>
            </task>
        </tasks>\n''')
        self.assertEqual(1, len(tasks[0].children()))
        self.assertEqual(1, len(tasks))
        
    def testChildren(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <task/>
                <task/>
            </task>
        </tasks>\n''')
        self.assertEqual(2, len(tasks[0].children()))
        self.assertEqual(1, len(tasks))
        
    def testGrandchild(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <task>
                    <task/>
                </task>
            </task>
        </tasks>\n''')
        self.assertEqual(1, len(tasks))
        parent = tasks[0]
        self.assertEqual(1, len(parent.children()))
        self.assertEqual(1, len(parent.children()[0].children()))
        
    def testEffort(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00" 
                        stop="2004-01-01 10:30:00"/>
            </task>
        </tasks>''')
        self.assertEqual(1, len(tasks[0].efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), tasks[0].timeSpent())
        self.assertEqual(tasks[0], tasks[0].efforts()[0].task())
    
    def testChildEffort(self):    
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <task>
                    <effort start="2004-01-01 10:00:00" 
                            stop="2004-01-01 10:30:00"/>
                </task>
            </task>
        </tasks>''')
        child = tasks[0].children()[0]
        self.assertEqual(1, len(child.efforts()))
        self.assertEqual(date.TimeDelta(minutes=30), child.timeSpent())
        self.assertEqual(child, child.efforts()[0].task())

    def testEffortDescription(self):
        description = u'Description\nLine 2'
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00">
                    <description>%s</description>
                </effort>
            </task>
        </tasks>'''%description)
        self.assertEqual(description, tasks[0].efforts()[0].description())
        
    def testActiveEffort(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <effort start="2004-01-01 10:00:00"/>
            </task>
        </tasks>''')
        self.assertEqual(1, len(tasks[0].efforts()))
        self.failUnless(tasks[0].isBeingTracked())
                
    def testPriority(self):
        tasks = self.writeAndReadTasks('<tasks><task priority="5"/></tasks>')        
        self.assertEqual(5, tasks[0].priority())
        
    def testTaskId(self):
        tasks = self.writeAndReadTasks('<tasks><task id="xyz"/></tasks>')
        self.assertEqual('xyz', tasks[0].id())

    def testTaskColor(self):        
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task color="(255, 0, 0, 255)"/>
        </tasks>''')
        self.assertEqual(wx.RED, tasks[0].backgroundColor())
                
    def testHourlyFee(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task hourlyFee="100"/>
            <task hourlyFee="5.5"/>
        </tasks>''')
        self.assertEqual(100, tasks[0].hourlyFee())
        self.assertEqual(5.5, tasks[1].hourlyFee())
        
    def testFixedFee(self):
        tasks = self.writeAndReadTasks('<tasks><task fixedFee="240.50"/></tasks>')
        self.assertEqual(240.5, tasks[0].fixedFee())

    def testNoReminder(self):
        tasks = self.writeAndReadTasks('<tasks><task reminder="None"/></tasks>')
        self.assertEqual(None, tasks[0].reminder())
        
    def testReminder(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task reminder="2004-01-01 10:00:00"/>
        </tasks>''')
        self.assertEqual(date.DateTime(2004,1,1,10,0,0,0), 
                         tasks[0].reminder())
        
    def testMarkCompletedWhenAllChildrenCompletedSetting_True(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task shouldMarkCompletedWhenAllChildrenCompleted="True"/>
        </tasks>''')
        self.assertEqual(True, 
                         tasks[0].shouldMarkCompletedWhenAllChildrenCompleted())

    def testMarkCompletedWhenAllChildrenCompletedSetting_False(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task shouldMarkCompletedWhenAllChildrenCompleted="False"/>
        </tasks>''')
        self.assertEqual(False,
                         tasks[0].shouldMarkCompletedWhenAllChildrenCompleted())
 
    def testMarkCompletedWhenAllChildrenCompletedSetting_None(self):
        tasks = self.writeAndReadTasks('<tasks><task/></tasks>')
        self.assertEqual(None,
                         tasks[0].shouldMarkCompletedWhenAllChildrenCompleted())

    def testTaskWithoutAttachments(self):
        tasks = self.writeAndReadTasks('<tasks><task/></tasks>')
        self.assertEqual([], tasks[0].attachments())

    def testNoteWithoutAttachments(self):
        notes = self.writeAndReadNotes('<tasks><note/></tasks>')
        self.assertEqual([], notes[0].attachments())

    def testCategoryWithoutAttachments(self):
        categories = self.writeAndReadCategories('<tasks><category/></tasks>')
        self.assertEqual([], categories[0].attachments())
        
    def testTaskWithOneAttachment(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment type="file"><description>whatever.tsk</description><data>whateverdata.tsk</data></attachment>
            </task>
        </tasks>''')
        self.assertEqual([os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'whateverdata.tsk')],
                         [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in tasks[0].attachments()])

    def testNoteWithOneAttachment(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note>
                <attachment type="file"><description>whatever.tsk</description><data>whateverdata.tsk</data></attachment>
            </note>
        </tasks>''')
        self.assertEqual([os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'whateverdata.tsk')],
                         [att.location() for att in notes[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in notes[0].attachments()])

    def testCategoryWithOneAttachment(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category>
                <attachment type="file"><description>whatever.tsk</description><data>whateverdata.tsk</data></attachment>
            </category>
        </tasks>''')
        self.assertEqual([os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'whateverdata.tsk')],
                         [att.location() for att in categories[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in categories[0].attachments()])
        
    def testTaskWithTwoAttachments(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <attachment type="file"><description>whatever.tsk</description><data>whateverdata.tsk</data></attachment>
                <attachment type="file"><description>another.txt</description><data>anotherdata.txt</data></attachment>
            </task>
        </tasks>''')
        self.assertEqual([os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'whateverdata.tsk'),
                          os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'anotherdata.txt')],
                         [att.location() for att in tasks[0].attachments()])
        self.assertEqual(['whatever.tsk', 'another.txt'], 
                         [att.subject() for att in tasks[0].attachments()])
        
    def testOneCategory(self):
        categories = self.writeAndReadCategories('<tasks><category subject="cat"/></tasks>')
        self.assertEqual('cat', categories[0].subject())

    def testTwoCategories(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat1"/>
            <category subject="cat2"/>
        </tasks>''')
        self.assertEqual(['cat1', 'cat2'], 
            [category.subject() for category in categories])

    def testCategoryId(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category id="catId"/>
        </tasks>''')
        self.assertEqual('catId', categories[0].id())
            
    def testCategoryWithDescription(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat">
                <description>Description</description>
            </category>
        </tasks>''')
        self.assertEqual('Description', categories[0].description())
    
    def testCategoryColor(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat" color="(255, 0, 0, 255)"/>
        </tasks>''')
        self.assertEqual(wx.RED, categories[0].backgroundColor())
        
    def testOneTaskWithCategory(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <category subject="cat" categorizables="1"/>
            <task id="1"/>
        </tasks>''')
        self.assertEqual(set(tasks), categories[0].categorizables())
        
    def testTwoRecursiveCategories(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat1">
                <category subject="cat1.1"/>
            </category>
        </tasks>''')
        self.assertEqual('cat1.1', categories[0].children()[0].subject())
        
    def testRecursiveCategoriesNotInResultList(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat1">
                <category subject="cat1.1"/>
            </category>
        </tasks>''')
        self.assertEqual(1, len(categories))

    def testRecursiveCategoriesWithTwoTasks(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <category subject="cat1" categorizables="1">
                <category subject="cat1.1" categorizables="2"/>
            </category>
            <task subject="task1" id="1"/>
            <task subject="task2" id="2"/>
        </tasks>''')

        self.assertEqual(tasks[0], list(categories[0].categorizables())[0])
        self.assertEqual(tasks[1], list(categories[0].children()[0].categorizables())[0])
        
    def testSubtaskCategory(self):
        tasks, categories = self.writeAndReadTasksAndCategories('''
        <tasks>
            <category subject="cat1" categorizables="1.1"/>
            <task subject="task1" id="1">
                <task subject="task2" id="1.1"/>
            </task>
        </tasks>''')
        self.assertEqual(tasks[0].children()[0], list(categories[0].categorizables())[0])
        
    def testFilteredCategory(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category filtered="True" subject="category"/>
        </tasks>''')
        self.failUnless(categories[0].isFiltered())
    
    def testCategoryWithDeletedTasks(self):
        ''' There's a bug in release 0.61.5 that causes the task file to contain
            references to deleted tasks. Ignore these when loading the task file.'''
        categories = self.writeAndReadCategories('''
        <tasks>
            <category subject="cat" tasks="some_task_id"/>
        </tasks>''')
        self.failIf(categories[0].categorizables())
        
    def testNote(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note/>
        </tasks>''')
        self.failUnless(notes)

    def testNoteSubject(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note subject="Note"/>
        </tasks>''')
        self.assertEqual('Note', notes[0].subject())

    def testNoteDescription(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note>
                <description>Description</description>
            </note>
        </tasks>''')
        self.assertEqual('Description', notes[0].description())

    def testNoteChild(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note>
                <note/>
            </note>
        </tasks>''')
        self.assertEqual(1, len(notes[0].children()))

    def testNoteChildWithAttachment(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note>
                <note>
                    <attachment type="file"><description>whatever.tsk</description><data>whateverdata.tsk</data></attachment>
                </note>
            </note>
        </tasks>''')
        self.assertEqual([os.path.join(os.getcwd(),
                                       'testfile_attachments',
                                       'whateverdata.tsk')],
                         [att.location() for att in notes[0].children()[0].attachments()])
        self.assertEqual(['whatever.tsk'], [att.subject() for att in notes[0].children()[0].attachments()])
        
    def testNoteCategory(self):
        categories, notes = self.writeAndReadCategoriesAndNotes('''
        <tasks>
            <note id="noteId" subject="Note"/>
            <category categorizables="noteId" subject="Category"/>
        </tasks>''')
        self.assertEqual(notes[0], list(categories[0].categorizables())[0])
        
    def testNoteId(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note id="noteId"/>
        </tasks>''')
        self.assertEqual('noteId', notes[0].id())
        
    def testNoteColor(self):        
        notes = self.writeAndReadNotes('''
        <tasks>
            <note color="(255, 0, 0, 255)"/>
        </tasks>''')
        self.assertEqual(wx.RED, notes[0].backgroundColor())
        
    def testNoRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task/>
        </tasks>''')
        self.failIf(tasks[0].recurrence())

    def testDailyRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="daily"/></task>
        </tasks>''')
        self.assertEqual('daily', tasks[0].recurrence().unit)    

    def testWeeklyRecurrence(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="weekly"/></task>
        </tasks>''')
        self.assertEqual('weekly', tasks[0].recurrence().unit)    

    def testRecurrenceAmount(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="daily" amount="2"/></task>
        </tasks>''')
        self.assertEqual(2, tasks[0].recurrence().amount)    

    def testRecurrenceMax(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="daily" max="2"/></task>
        </tasks>''')
        self.assertEqual(2, tasks[0].recurrence().max)    

    def testRecurrenceCount(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="daily" count="2"/></task>
        </tasks>''')
        self.assertEqual(2, tasks[0].recurrence().count)    

    def testRecurrenceSameWeekday(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task><recurrence unit="daily" sameWeekday="True"/></task>
        </tasks>''')
        self.failUnless(tasks[0].recurrence().sameWeekday)
        
    def testTaskWithNote(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <note/>
            </task> 
        </tasks>''')
        self.assertEqual(1, len(tasks[0].notes()))
        
    def testTaskWithNotes(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <note/><note/>
            </task> 
        </tasks>''')
        self.assertEqual(2, len(tasks[0].notes()))
        
    def testTaskWithNestedNotes(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task>
                <note>
                    <note/>
                </note>
            </task> 
        </tasks>''')
        self.assertEqual(1, len(tasks[0].notes()[0].children()))
        
    def testTaskNotesDontGetAddedToOverallNotesList(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <task>
                <note/>
            </task> 
        </tasks>''')
        self.failIf(notes)
        
    def testCategoryWithNote(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category>
                <note/>
            </category> 
        </tasks>''')
        self.assertEqual(1, len(categories[0].notes()))

    def testCategoryWithNotes(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category>
                <note/><note/>
            </category> 
        </tasks>''')
        self.assertEqual(2, len(categories[0].notes()))

    def testCategoryWithNestedNotes(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category>
                <note>
                    <note/>
                </note>
            </category> 
        </tasks>''')
        self.assertEqual(1, len(categories[0].notes()[0].children()))

    def testCategoryNotesDontGetAddedToOverallNotesList(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <category>
                <note/>
            </category> 
        </tasks>''')
        self.failIf(notes)

    def testTaskExpansion(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task expandedContexts="('None',)"/>
        </tasks>''')
        self.failUnless(tasks[0].isExpanded())

    def testTaskExpansion_MultipleContexts(self):
        tasks = self.writeAndReadTasks('''
        <tasks>
            <task expandedContexts="('None','Test')"/>
        </tasks>''')
        self.failUnless(tasks[0].isExpanded(context='Test'))

    def testCategoryExpansion(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category expandedContexts="('None',)"/>
        </tasks>''')
        self.failUnless(categories[0].isExpanded())

    def testNoteExpansion(self):
        notes = self.writeAndReadNotes('''
        <tasks>
            <note expandedContexts="('None',)"/>
        </tasks>''')
        self.failUnless(notes[0].isExpanded())


class XMLReaderVersion21Test(XMLReaderTestCase):
    tskversion = 21 # New in release 0.71.0

    def testAttachmentLocation(self):
        categories = self.writeAndReadCategories('''
        <tasks>
            <category>
                <attachment type="file" location="location"><description>description</description></attachment>
            </category>
        </tasks>''')
        self.assertEqual(['location'], [os.path.split(att.location())[-1] for att in categories[0].attachments()])


class XMLReaderVersion22Test(XMLReaderTestCase):
    tskversion = 22

    def testStatus(self):
        tasks = self.writeAndReadTasks(\
            '<tasks><task subject="Task" status="2"></task></tasks>')
        self.assertEqual(2, tasks[0].getStatus())


class XMLReaderVersion23Test(XMLReaderTestCase):
    tskversion = 23

    def testDescription(self):
        tasks = self.writeAndReadTasks(\
            '<tasks><task subject="Task" status="0">'
            '<description>\nDescription\n</description>'
            '</task></tasks>')
        self.assertEqual('\nDescription\n', tasks[0].description())

    def testAttachmentData(self):
        import base64
        tasks = self.writeAndReadTasks(\
            '<tasks>\n<task status="0">\n'
            '<attachment type="mail" status="0">\n'
            '<data extension="eml">%s</data>\n'
            '</attachment>\n</task>\n</tasks>\n'%base64.encodestring('Data'))
        self.assertEqual('Data', tasks[0].attachments()[0].data())
    
    def testGUID(self):
        guid = self.writeAndReadGUID('<tasks><guid>GUID</guid></tasks>')
        self.assertEqual('GUID', guid)

    def testSyncMLConfig(self):
        syncmlConfig = self.writeAndReadSyncMLConfig('<tasks><syncml><property name="name">value</property></syncml></tasks>')
        self.assertEqual('value', syncmlConfig.get('name'))
        
        
class XMLReaderVersion24Test(XMLReaderTestCase):
    tskversion = 24 # New in release 0.72.9

    # tskversion 24 introduces newlines so that the XML is not on one long
    # line anymore. We have to be sure not to introduce new lines in
    # text nodes though.

    def testDescription(self):
        tasks = self.writeAndReadTasks(\
            '<tasks>\n<task subject="Task" status="0">\n'
            '<description>\nDescription\n</description>\n'
            '</task>\n</tasks>\n')
        self.assertEqual('Description', tasks[0].description())
        
    def testAttachmentData(self):
        import base64
        tasks = self.writeAndReadTasks(\
            '<tasks>\n<task status="0">\n'
            '<attachment type="mail" status="0">\n'
            '<data extension="eml">\n%s\n</data>\n'
            '</attachment>\n</task>\n</tasks>\n'%base64.encodestring('Data'))
        self.assertEqual('Data', tasks[0].attachments()[0].data())

    def testGUID(self):
        guid = self.writeAndReadGUID('<tasks>\n<guid>\nGUID\n</guid>\n</tasks>')
        self.assertEqual('GUID', guid)

    def testSyncMLConfig(self):
        syncmlConfig = self.writeAndReadSyncMLConfig(\
            '<tasks>\n<syncml>\n'
            '<property name="name">\nvalue\n</property>\n'
            '</syncml>\n</tasks>\n')
        self.assertEqual('value', syncmlConfig.get('name'))
        
    def testSyncMLConfigWithNewLinesInXMLNodes(self):
        ''' Release 0.72.9 (and earlier?) had a bug where tags in the syncml
            config information would be split across multiple lines. Fixed in
            release 0.72.10. ''' 
        expectedGUID = '0000011d209a4b6c3f9f7c32000a00b100240032'
        actualGUID = self.writeAndReadGUID(\
            '<tasks>\n<syncml><TaskCoach-\n'
            '0000011d209a4b6c3f9f7c32000a00b100240032\n'
            '><spds><sources><TaskCoach-\n'
            '0000011d209a4b6c3f9f7c32000a00b100240032\n'
            '.Tasks/><TaskCoach-\n'
            '0000011d209a4b6c3f9f7c32000a00b100240032\n'
            '.Notes/></sources><syncml><Auth/><Conn/></syncml></spds></TaskCoach-\n'
            '0000011d209a4b6c3f9f7c32000a00b100240032\n'
            '><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032><spds><sources><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032.Tasks/><TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032.Notes/></sources><syncml><Auth/><Conn/></syncml></spds></TaskCoach-0000011d209a4b6c3f9f7c32000a00b100240032></syncml><guid>\n'
            '0000011d209a4b6c3f9f7c32000a00b100240032\n'
            '</guid></tasks>')
        self.assertEqual(expectedGUID, actualGUID)
        

class XMLReaderVersion26Test(XMLReaderTestCase):
    tskversion = 26 # New in release 0.75.0

    # Release 0.75.0 introduces percentage complete for tasks
    
    def testPercentageComplete(self):   
        tasks = self.writeAndReadTasks(\
            '<tasks>\n<task subject="Task" status="0" percentageComplete="50"/>\n'
            '</tasks>\n')
        self.assertEqual(50, tasks[0].percentageComplete())


class XMLReaderVersion27Test(XMLReaderTestCase):
    tskversion = 27 # New in release 0.76.0
    
    # Release 0.76.0 introduces exclusive subcategories
    
    def testExclusiveSubcategories(self):
        categories = self.writeAndReadCategories(\
            '<categories>\n'
            '<category subject="Category" exclusiveSubcategories="True"'
            ' status="0"/>\n'
            '</categories>\n')
        self.failUnless(categories[0].hasExclusiveSubcategories())
        
    def testNoExclusiveSubcategoriesByDefault(self):
        categories = self.writeAndReadCategories(\
            '<categories>\n'
            '<category subject="Category" status="0"/>\n'
            '</categories>\n')
        self.failIf(categories[0].hasExclusiveSubcategories())
        

class XMLReaderVersion28Test(XMLReaderTestCase):
    tskversion = 28 # New in release 0.78.0
    
    # Release 0.78.0 introduces foreground colors that can be set per object.
    
    def testTaskBackgroundColor(self):
        tasks = self.writeAndReadTasks(\
            '<tasks>\n<task subject="Task" status="0" bgColor="(255,0,0)"/>\n'
            '</tasks>\n')
        self.assertEqual(wx.RED, tasks[0].backgroundColor())
        
    def testCategoryBackgroundColor(self):
        categories = self.writeAndReadCategories(\
            '<categories>\n<category subject="Task" bgColor="(255,0,0)"/>\n'
            '</categories>\n')
        self.assertEqual(wx.RED, categories[0].backgroundColor())
        