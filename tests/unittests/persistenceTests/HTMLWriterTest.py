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

import wx, io, os
import test
from taskcoachlib import persistence, gui, config, render
from taskcoachlib.domain import task, category, effort, date


class HTMLWriterTestCase(test.wxTestCase):
    tree_mode = "Subclass responsibility"
    filename = "Subclass responsibility"

    def setUp(self):
        super().setUp()
        task.Task.settings = self.settings = config.Settings(load=False)
        self.fd = io.StringIO()
        self.writer = persistence.HTMLWriter(self.fd, self.filename)
        self.taskFile = persistence.TaskFile()
        self.task = task.Task("Task subject")
        self.taskFile.tasks().append(self.task)
        self.viewer = self.createViewer()

    def tearDown(self):
        super().tearDown()
        self.taskFile.close()
        self.taskFile.stop()
        cssFilename = self.filename + ".css"
        if os.path.exists(cssFilename):
            os.remove(cssFilename)

    def createViewer(self):
        raise NotImplementedError  # pragma: no cover

    def __writeAndRead(self, selectionOnly):
        self.writer.write(self.viewer, self.settings, selectionOnly, True)
        return self.fd.getvalue()

    def expectInHTML(self, *htmlFragments, **kwargs):
        selectionOnly = kwargs.pop("selectionOnly", False)
        html = self.__writeAndRead(selectionOnly)
        for htmlFragment in htmlFragments:
            self.assertTrue(
                htmlFragment in html, "%s not in %s" % (htmlFragment, html)
            )

    def expectNotInHTML(self, *htmlFragments, **kwargs):
        selectionOnly = kwargs.pop("selectionOnly", False)
        html = self.__writeAndRead(selectionOnly)
        for htmlFragment in htmlFragments:
            self.assertFalse(
                htmlFragment in html, "%s in %s" % (htmlFragment, html)
            )

    def selectItem(self, items):
        self.viewer.widget.select(items)


class CommonTestsMixin(object):
    def testHTML(self):
        self.expectInHTML("<html>\n", "</html>\n")

    def testHeader(self):
        self.expectInHTML("  <head>\n", "  </head>\n")

    def testStyle(self):
        self.expectInHTML('    <style type="text/css">\n', "    </style>\n")

    def testBody(self):
        self.expectInHTML("  <body>\n", "  </body>\n")


class TaskWriterTestCase(HTMLWriterTestCase):
    def createViewer(self):
        self.settings.set("taskviewer", "treemode", self.tree_mode)
        return gui.viewer.TaskViewer(self.frame, self.taskFile, self.settings)


class TaskTestsMixin(CommonTestsMixin):
    def testTaskSubject(self):
        self.expectInHTML(">Task subject<")

    def testWriteSelectionOnly(self):
        self.expectNotInHTML(">Task subject<", selectionOnly=True)

    def testWriteSelectionOnly_SelectedChild(self):
        child = task.Task("Child")
        self.task.addChild(child)
        self.taskFile.tasks().append(child)
        self.selectItem([child])
        self.expectInHTML(">Task subject<")

    def testColumnStyle(self):
        self.expectInHTML("      .subject {text-align: left}\n")

    def testSortIndicator(self):
        self.expectInHTML('id="sorted"')
        if not self.filename:
            self.expectInHTML("<u>")

    def testTaskStatusStyle(self):
        self.expectInHTML("      .completed {color: rgb(0, 255, 0)}\n")

    def testTaskStatusStyleWhenForegroundColorChangedInSettings(self):
        self.settings.set("fgcolor", "completedtasks", str(wx.RED))
        self.expectInHTML("      .completed {color: rgb(255, 0, 0)}\n")

    def testOverdueTask(self):
        self.task.setDueDateTime(date.Yesterday())
        fragment = (
            '<tr class="overdue">'
            if self.filename
            else '<font color="rgb(255, 0, 0)">Task subject</font>'
        )
        self.expectInHTML(fragment)

    def testCompletedTask(self):
        self.task.setCompletionDateTime()
        if self.filename:
            self.expectInHTML('<tr class="completed">')
        else:
            self.expectInHTML(
                '<font color="rgb(0, 255, 0)">Task subject</font>'
            )

    def testTaskDueSoon(self):
        self.task.setDueDateTime(date.Now() + date.ONE_HOUR)
        fragment = (
            '<tr class="duesoon">'
            if self.filename
            else '<font color="rgb(255, 128, 0)">Task subject</font>'
        )
        self.expectInHTML(fragment)

    def testInactiveTask(self):
        self.task.setPlannedStartDateTime(date.Tomorrow())
        fragment = (
            '<tr class="inactive">'
            if self.filename
            else '<font color="rgb(192, 192, 192)">Task subject</font>'
        )
        self.expectInHTML(fragment)

    def testLateTask(self):
        self.task.setPlannedStartDateTime(date.Yesterday())
        fragment = (
            '<tr class="late">'
            if self.filename
            else '<font color="rgb(160, 32, 240)">Task subject</font>'
        )
        self.expectInHTML(fragment)

    def testTaskBackgroundColor(self):
        self.task.setActualStartDateTime(date.Now())
        self.task.setBackgroundColor(wx.RED)
        fragment = (
            '<tr class="active" style="background: rgb(255, 0, 0)">'
            if self.filename
            else '<tr bgcolor="rgb(255, 0, 0)">'
        )
        self.expectInHTML(fragment)

    def testTaskHasCategoryBackgroundColor(self):
        self.task.setActualStartDateTime(date.Now())
        cat = category.Category("cat", bgColor=wx.RED)
        self.task.addCategory(cat)
        fragment = (
            '<tr class="active" style="background: rgb(255, 0, 0)">'
            if self.filename
            else '<tr bgcolor="rgb(255, 0, 0)">'
        )
        self.expectInHTML(fragment)

    def testCategoryBackgroundColorAsTuple(self):
        self.task.setActualStartDateTime(date.Now())
        cat = category.Category("cat", bgColor=(255, 0, 0))
        self.task.addCategory(cat)
        if self.filename:
            self.expectInHTML(
                '<tr class="active" style="background: rgba(255, 0, 0, 0.000)">'
            )
        else:
            self.expectInHTML('<tr bgcolor="rgba(255, 0, 0, 0.000)">')

    def testCSSLink(self):
        if self.filename:
            self.expectInHTML(
                '<link href="filename.css" rel="stylesheet" type="text/css" media="screen">'
            )
        else:
            self.expectNotInHTML("stylesheet")

    def testOSErrorWhileWritingCSS(self):
        def open(*args):  # pylint: disable=W0613,W0622
            raise IOError

        self.writer._writeCSS(open=open)  # pylint: disable=W0212


class TaskListTestsMixin(object):
    def testTaskDescription(self):
        self.task.setDescription("Task description")
        self.viewer.showColumnByName("description")
        self.expectInHTML(">Task description<")

    def testTaskDescriptionWithNewLine(self):
        self.task.setDescription("Line1\nLine2")
        self.viewer.showColumnByName("description")
        self.expectInHTML(">Line1<br>Line2<")

    def testCreationDateTime(self):
        self.viewer.showColumnByName("creationDateTime")
        self.expectInHTML(
            render.dateTime(self.task.creationDateTime(), human_readable=False)
        )

    def testMissingCreationDateTime(self):
        self.viewer.showColumnByName("creationDateTime")
        self.taskFile.tasks().append(
            task.Task(creationDateTime=date.DateTime.min)
        )
        self.taskFile.tasks().remove(self.task)
        self.expectNotInHTML("1/1/1")

    def testModificationDateTime(self):
        self.task.setModificationDateTime(date.DateTime(2012, 1, 1, 10, 0, 0))
        self.viewer.showColumnByName("modificationDateTime")
        self.expectInHTML(
            render.dateTime(
                self.task.modificationDateTime(), human_readable=False
            )
        )

    def testMissingModificationDateTime(self):
        self.viewer.showColumnByName("modificationDateTime")
        self.expectInHTML(
            render.dateTime(
                self.task.modificationDateTime(), human_readable=False
            )
        )
        self.expectNotInHTML("1/1/1")


class TaskListExportTest(
    TaskTestsMixin, TaskListTestsMixin, TaskWriterTestCase
):
    tree_mode = "False"
    filename = "filename"


class TaskListPrintTest(
    TaskTestsMixin, TaskListTestsMixin, TaskWriterTestCase
):
    tree_mode = "False"
    filename = ""


class TaskTreeExportTest(TaskTestsMixin, TaskWriterTestCase):
    tree_mode = "True"
    filename = "filename"


class TaskTreePrintTest(TaskTestsMixin, TaskWriterTestCase):
    tree_mode = "True"
    filename = ""


class EffortWriterTestCase(CommonTestsMixin, HTMLWriterTestCase):
    filename = "filename"

    def setUp(self):
        super().setUp()
        now = date.DateTime.now()
        self.task.addEffort(
            effort.Effort(self.task, start=now, stop=now + date.ONE_SECOND)
        )

    def createViewer(self):
        return gui.viewer.EffortViewer(
            self.frame, self.taskFile, self.settings
        )

    def testTaskSubject(self):
        self.expectInHTML(">Task subject<")

    def testEffortDuration(self):
        self.expectInHTML(">0:00:01<")

    def testColumnStyle(self):
        self.expectInHTML("      .task {text-align: left}\n")


class CategoryWriterTestsMixin(CommonTestsMixin):
    def testCategorySubject(self):
        self.expectInHTML(">Category<")

    def testCategoryBackgroundColor(self):
        self.category.setBackgroundColor(wx.RED)
        if self.filename:
            self.expectInHTML('<tr style="background: rgb(255, 0, 0)">')
        else:
            self.expectInHTML('<tr bgcolor="rgb(255, 0, 0)">')


class CategoryWriterTestCase(HTMLWriterTestCase):
    def setUp(self):
        super().setUp()
        self.category = category.Category("Category")
        self.taskFile.categories().append(self.category)

    def createViewer(self):
        return gui.viewer.CategoryViewer(
            self.frame, self.taskFile, self.settings
        )


class CategoryWriterExportTest(
    CategoryWriterTestsMixin, CategoryWriterTestCase
):
    filename = "filename"


class CategoryWriterPrintTest(
    CategoryWriterTestsMixin, CategoryWriterTestCase
):
    filename = ""
