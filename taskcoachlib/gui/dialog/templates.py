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

from taskcoachlib.tools import wxhelper
import wx
from taskcoachlib.domain.task import Task
from taskcoachlib import persistence, operating_system
from taskcoachlib.i18n import _
from taskcoachlib.thirdparty.deltaTime import nlTimeExpression
from wx.lib import sized_controls


class TimeExpressionEntry(wx.TextCtrl):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__defaultColor = self.GetBackgroundColour()
        self.__invalidColor = wx.Colour(255, 128, 128)

        self.Bind(wx.EVT_TEXT, self._onTextChanged)

    @staticmethod
    def isValid(value):
        if value:
            try:
                res = nlTimeExpression.parseString(value)
            except Exception:
                return False  # Parsing failed
            return "calculatedTime" in res
        return True  # Empty is valid.

    def _onTextChanged(self, event):
        event.Skip()
        self.SetBackgroundColour(
            self.__defaultColor
            if self.isValid(self.GetValue())
            else self.__invalidColor
        )


class TemplatesDialog(sized_controls.SizedDialog):
    def __init__(self, settings, *args, **kwargs):
        self.settings = settings
        self._changing = False
        super().__init__(
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER, *args, **kwargs
        )
        pane = self.GetContentsPane()
        pane.SetSizerType("vertical")
        self.createInterior(pane)
        self._buttonSizer = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        self.SetButtonSizer(self._buttonSizer)
        self.Fit()
        self.SetMinSize(self.GetSize())  # Current size is min size
        wxhelper.getButtonFromStdDialogButtonSizer(
            self._buttonSizer, wx.ID_OK
        ).Bind(wx.EVT_BUTTON, self.ok)
        self.CentreOnParent()

    def createInterior(self, pane):
        self.createTemplateList(pane)
        self.createTemplateEntries(pane)

    def createTemplateList(self, pane):
        panel = sized_controls.SizedPanel(pane)
        panel.SetSizerType("horizontal")
        panel.SetSizerProps(expand=True, proportion=1)
        self._templateList = wx.TreeCtrl(
            panel, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_SINGLE
        )
        self._templateList.SetMinSize((300, 200))
        self._templateList.SetSizerProps(expand=True, proportion=1)
        self._templateList.Bind(
            wx.EVT_TREE_SEL_CHANGED, self.OnSelectionChanged
        )
        self._templates = persistence.TemplateList(
            self.settings.pathToTemplatesDir()
        )
        self._root = self._templateList.AddRoot("Root")
        for task in self._templates.tasks():
            item = self.appendTemplate(self._root, task)
            if operating_system.isMac():
                # See http://trac.wxwidgets.org/ticket/10085
                self._templateList.SetItemText(item, task.subject())
        self.createTemplateListButtons(panel)
        panel.Fit()

    def createTemplateListButtons(self, pane):
        panel = sized_controls.SizedPanel(pane)
        panel.SetSizerType("vertical")
        self._btnDelete = self.createButton(
            panel, "cross_red_icon", self.OnDelete, enable=False
        )
        self._btnUp = self.createButton(
            panel, "arrow_up_icon", self.OnUp, enable=False
        )
        self._btnDown = self.createButton(
            panel, "arrow_down_icon", self.OnDown, enable=False
        )
        self._btnAdd = self.createButton(panel, "symbol_plus_icon", self.OnAdd)
        panel.Fit()

    def createButton(self, parent, bitmapName, handler, enable=True):
        bitmap = wx.ArtProvider.GetBitmap(bitmapName, size=(32, 32))
        button = wx.BitmapButton(parent, bitmap=bitmap)
        button.Bind(wx.EVT_BUTTON, handler)
        button.Enable(enable)
        return button

    def createTemplateEntries(self, pane):
        panel = self._editPanel = sized_controls.SizedPanel(pane)
        panel.SetSizerType("form")
        panel.SetSizerProps(expand=True)
        label = wx.StaticText(panel, label=_("Subject"))
        label.SetSizerProps(valign="center")
        self._subjectCtrl = wx.TextCtrl(panel)
        label = wx.StaticText(panel, label=_("Planned start date"))
        label.SetSizerProps(valign="center")
        self._plannedStartDateTimeCtrl = TimeExpressionEntry(panel)
        label = wx.StaticText(panel, label=_("Due date"))
        label.SetSizerProps(valign="center")
        self._dueDateTimeCtrl = TimeExpressionEntry(panel)
        label = wx.StaticText(panel, label=_("Completion date"))
        label.SetSizerProps(valign="center")
        self._completionDateTimeCtrl = TimeExpressionEntry(panel)
        label = wx.StaticText(panel, label=_("Reminder"))
        label.SetSizerProps(valign="center")
        self._reminderDateTimeCtrl = TimeExpressionEntry(panel)
        self._taskControls = (
            self._subjectCtrl,
            self._plannedStartDateTimeCtrl,
            self._dueDateTimeCtrl,
            self._completionDateTimeCtrl,
            self._reminderDateTimeCtrl,
        )
        for ctrl in self._taskControls:
            ctrl.SetSizerProps(valign="center", expand=True)
            ctrl.Bind(wx.EVT_TEXT, self.onValueChanged)
        self.enableEditPanel(False)
        panel.Fit()

    def enableEditPanel(self, enable=True):
        for ctrl in self._taskControls:
            ctrl.Enable(enable)

    def appendTemplate(self, parentItem, task):
        item = self._templateList.AppendItem(parentItem, task.subject())
        self._templateList.SetItemData(item, task)
        for child in task.children():
            self.appendTemplate(item, child)
        return item

    def onValueChanged(self, event):
        event.Skip()
        if self._GetSelection().IsOk() and not self._changing:
            task = self._templateList.GetItemData(self._GetSelection())
            task.setSubject(self._subjectCtrl.GetValue())
            for ctrl, name in [
                (self._plannedStartDateTimeCtrl, "plannedstartdatetmpl"),
                (self._dueDateTimeCtrl, "duedatetmpl"),
                (self._completionDateTimeCtrl, "completiondatetmpl"),
                (self._reminderDateTimeCtrl, "remindertmpl"),
            ]:
                if TimeExpressionEntry.isValid(ctrl.GetValue()):
                    setattr(task, name, ctrl.GetValue() or None)

    def _GetSelection(self):
        return self._templateList.GetSelection()

    def OnSelectionChanged(self, event):  # pylint: disable=W0613
        self._changing = True
        try:
            selection = self._GetSelection()
            selectionOK = selection.IsOk() and selection != self._root
            selectionAtRoot = False
            if selectionOK:
                selectionAtRoot = (
                    self._templateList.GetItemParent(selection) == self._root
                )
            self._btnDelete.Enable(selectionAtRoot)
            self._btnUp.Enable(
                selectionAtRoot
                and self._templateList.GetPrevSibling(selection).IsOk()
            )
            self._btnDown.Enable(
                selectionAtRoot
                and self._templateList.GetNextSibling(selection).IsOk()
            )
            self.enableEditPanel(selectionOK)
            if selectionOK:
                task = self._templateList.GetItemData(selection)
                if task is None:
                    for ctrl in self._taskControls:
                        ctrl.SetValue("")
                else:
                    self._subjectCtrl.SetValue(task.subject())
                    self._plannedStartDateTimeCtrl.SetValue(
                        task.plannedstartdatetmpl or ""
                    )
                    self._dueDateTimeCtrl.SetValue(task.duedatetmpl or "")
                    self._completionDateTimeCtrl.SetValue(
                        task.completiondatetmpl or ""
                    )
                    self._reminderDateTimeCtrl.SetValue(
                        task.remindertmpl or ""
                    )
            else:
                for ctrl in self._taskControls:
                    ctrl.SetValue("")
        finally:
            self._changing = False

    def OnDelete(self, event):  # pylint: disable=W0613
        task = self._templateList.GetItemData(self._GetSelection())
        index = self._templates.tasks().index(task)
        self._templates.deleteTemplate(index)
        self._templateList.Delete(self._GetSelection())

    def OnUp(self, event):  # pylint: disable=W0613
        selection = self._GetSelection()
        prev = self._templateList.GetPrevSibling(selection)
        prev = self._templateList.GetPrevSibling(prev)
        task = self._templateList.GetItemData(selection)
        self._templateList.Delete(selection)
        if prev.IsOk():
            item = self._templateList.InsertItem(
                self._root, prev, task.subject()
            )
            self._templateList.SetItemData(item, task)
        else:
            item = self._templateList.PrependItem(
                self._root, task.subject()
            )
            self._templateList.SetItemData(item, task)
        for child in task.children():
            self.appendTemplate(item, child)
        index = self._templates.tasks().index(task)
        self._templates.swapTemplates(index - 1, index)
        self._templateList.SelectItem(item)

    def OnDown(self, event):  # pylint: disable=W0613
        selection = self._GetSelection()
        next = self._templateList.GetNextSibling(selection)
        task = self._templateList.GetItemData(selection)
        self._templateList.Delete(selection)
        item = self._templateList.InsertItem(
            self._root, next, task.subject()
        )
        self._templateList.SetItemData(item, task)
        for child in task.children():
            self.appendTemplate(item, child)
        index = self._templates.tasks().index(task)
        self._templates.swapTemplates(index, index + 1)
        self._templateList.SelectItem(item)

    def OnAdd(self, event):  # pylint: disable=W0613
        template = Task(subject=_("New task template"))
        for name in (
            "plannedstartdatetmpl",
            "duedatetmpl",
            "completiondatetmpl",
            "remindertmpl",
        ):
            setattr(template, name, None)
        theTask = self._templates.addTemplate(template)
        self.appendTemplate(self._root, theTask)

    def ok(self, event):
        self._templates.save()
        event.Skip()
