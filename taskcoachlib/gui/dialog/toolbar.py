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

from taskcoachlib import widgets
from taskcoachlib.help.balloontips import BalloonTipManager
from taskcoachlib.gui import uicommand
from taskcoachlib.i18n import _
from wx.lib.agw import hypertreelist as htl
import wx


class _AutoWidthTree(
    widgets.autowidth.AutoColumnWidthMixin, htl.HyperTreeList
):
    """Simple tree for toolbar editor with auto-column-resizing enabled."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ToggleAutoResizing(True)

    def _get_MainWindow(self):
        return self.GetMainWindow()

    MainWindow = property(_get_MainWindow)


class _ToolBarEditorInterior(wx.Panel):
    def __init__(self, toolbar, settings, parent):
        self.__toolbar = toolbar
        self.__visible = toolbar.visibleUICommands()

        super().__init__(parent)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        # Toolbar preview
        sb = wx.StaticBox(self, wx.ID_ANY, _("Preview"))
        from taskcoachlib.gui.toolbar import ToolBar

        self.__preview = ToolBar(
            self, settings, self.__toolbar.GetToolBitmapSize()
        )
        sbsz = wx.StaticBoxSizer(sb)
        sbsz.Add(self.__preview, 1)
        vsizer.Add(sbsz, 0, wx.EXPAND | wx.ALL, 3)
        self.__HackPreview()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.__imgList = wx.ImageList(16, 16)
        self.__imgListIndex = dict()
        empty = wx.Image(16, 16)
        empty.Replace(0, 0, 0, 255, 255, 255)
        self.__imgListIndex["nobitmap"] = self.__imgList.Add(
            empty.ConvertToBitmap()
        )
        for uiCommand in toolbar.uiCommands():
            if (
                uiCommand is not None
                and not isinstance(uiCommand, int)
                and uiCommand.bitmap != "nobitmap"
            ):
                self.__imgListIndex[uiCommand.bitmap] = self.__imgList.Add(
                    wx.ArtProvider.GetBitmap(
                        uiCommand.bitmap, wx.ART_MENU, (16, 16)
                    )
                )

        # Remaining commands list
        sb = wx.StaticBox(self, wx.ID_ANY, _("Available tools"))
        self.__remainingCommands = _AutoWidthTree(
            self,
            agwStyle=htl.TR_NO_BUTTONS
            | htl.TR_SINGLE
            | htl.TR_NO_LINES
            | htl.TR_HIDE_ROOT
            | htl.TR_NO_HEADER
            | htl.TR_FULL_ROW_HIGHLIGHT,
        )
        self.__remainingCommands.AddColumn("Command")
        self.__remainingCommands.SetImageList(self.__imgList)

        sbsz = wx.StaticBoxSizer(sb)
        sbsz.Add(self.__remainingCommands, 1, wx.EXPAND)
        hsizer.Add(sbsz, 1, wx.EXPAND | wx.ALL, 3)

        self.__PopulateRemainingCommands()

        # Show/hide buttons
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        self.__showButton = wx.BitmapButton(
            self,
            wx.ID_ANY,
            wx.ArtProvider.GetBitmap("next", wx.ART_BUTTON, (16, 16)),
        )
        self.__showButton.Enable(False)
        self.__showButton.SetToolTip(
            wx.ToolTip(_("Make this tool visible in the toolbar"))
        )
        btnSizer.Add(self.__showButton, wx.ALL, 3)
        self.__hideButton = wx.BitmapButton(
            self,
            wx.ID_ANY,
            wx.ArtProvider.GetBitmap("prev", wx.ART_BUTTON, (16, 16)),
        )
        self.__hideButton.Enable(False)
        self.__hideButton.SetToolTip(
            wx.ToolTip(_("Hide this tool from the toolbar"))
        )
        btnSizer.Add(self.__hideButton, wx.ALL, 3)
        hsizer.Add(btnSizer, 0, wx.ALIGN_CENTRE)

        # Visible commands list
        sb = wx.StaticBox(self, wx.ID_ANY, _("Tools"))
        self.__visibleCommands = _AutoWidthTree(
            self,
            agwStyle=htl.TR_NO_BUTTONS
            | htl.TR_SINGLE
            | htl.TR_NO_LINES
            | htl.TR_HIDE_ROOT
            | htl.TR_NO_HEADER
            | htl.TR_FULL_ROW_HIGHLIGHT,
        )
        self.__visibleCommands.AddColumn("Command")
        self.__visibleCommands.SetImageList(self.__imgList)

        sbsz = wx.StaticBoxSizer(sb)
        sbsz.Add(self.__visibleCommands, 1, wx.EXPAND)
        hsizer.Add(sbsz, 1, wx.EXPAND | wx.ALL, 3)

        # Move buttons
        btnSizer = wx.BoxSizer(wx.VERTICAL)
        self.__moveUpButton = wx.BitmapButton(
            self,
            wx.ID_ANY,
            wx.ArtProvider.GetBitmap("up", wx.ART_BUTTON, (16, 16)),
        )
        self.__moveUpButton.Enable(False)
        self.__moveUpButton.SetToolTip(
            wx.ToolTip(_("Move the tool up (to the left of the toolbar)"))
        )
        btnSizer.Add(self.__moveUpButton, wx.ALL, 3)
        self.__moveDownButton = wx.BitmapButton(
            self,
            wx.ID_ANY,
            wx.ArtProvider.GetBitmap("down", wx.ART_BUTTON, (16, 16)),
        )
        self.__moveDownButton.Enable(False)
        self.__moveDownButton.SetToolTip(
            wx.ToolTip(_("Move the tool down (to the right of the toolbar)"))
        )
        btnSizer.Add(self.__moveDownButton, wx.ALL, 3)
        hsizer.Add(btnSizer, 0, wx.ALIGN_CENTRE)

        self.__PopulateVisibleCommands()

        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(vsizer)

        self.__remainingSelection = None
        self.__visibleSelection = None
        self.__draggedItem = None
        self.__draggingFromAvailable = False
        self.__remainingCommands.Bind(
            wx.EVT_TREE_SEL_CHANGED, self.__OnRemainingSelectionChanged
        )
        self.__visibleCommands.Bind(
            wx.EVT_TREE_SEL_CHANGED, self.__OnVisibleSelectionChanged
        )

        self.__hideButton.Bind(wx.EVT_BUTTON, self.__OnHide)
        self.__showButton.Bind(wx.EVT_BUTTON, self.__OnShow)
        self.__moveUpButton.Bind(wx.EVT_BUTTON, self.__OnMoveUp)
        self.__moveDownButton.Bind(wx.EVT_BUTTON, self.__OnMoveDown)
        self.__visibleCommands.Bind(wx.EVT_TREE_BEGIN_DRAG, self.__OnBeginDrag)
        self.__visibleCommands.Bind(wx.EVT_TREE_END_DRAG, self.__OnEndDrag)
        self.__remainingCommands.Bind(
            wx.EVT_TREE_BEGIN_DRAG, self.__OnBeginDrag2
        )

        wx.CallAfter(
            wx.GetTopLevelParent(self).AddBalloonTip,
            settings,
            "customizabletoolbars_dnd",
            self.__visibleCommands,
            title=_("Drag and drop"),
            message=_(
                """Reorder toolbar buttons by drag and dropping them in this list."""
            ),
        )

    def __OnRemainingSelectionChanged(self, event):
        self.__remainingSelection = event.GetItem()
        self.__showButton.Enable(self.__remainingSelection is not None)
        event.Skip()

    def __OnVisibleSelectionChanged(self, event):
        self.__visibleSelection = event.GetItem()
        self.__hideButton.Enable(self.__visibleSelection is not None)
        items = self.__visibleCommands.GetRootItem().GetChildren()
        idx = items.index(event.GetItem())
        self.__moveUpButton.Enable(idx != 0)
        self.__moveDownButton.Enable(idx != len(items) - 1)
        event.Skip()

    def __OnHide(self, event):
        idx = (
            self.__visibleCommands.GetRootItem()
            .GetChildren()
            .index(self.__visibleSelection)
        )
        uiCommand = self.__visibleCommands.GetItemPyData(
            self.__visibleSelection
        )
        self.__visibleCommands.Delete(self.__visibleSelection)
        self.__visibleSelection = None
        self.__hideButton.Enable(False)
        del self.__visible[idx]
        if isinstance(uiCommand, uicommand.UICommand):
            for child in self.__remainingCommands.GetRootItem().GetChildren()[
                2:
            ]:
                if self.__remainingCommands.GetItemPyData(child) == uiCommand:
                    self.__remainingCommands.EnableItem(child, True)
                    break
        self.__HackPreview()

    def __OnShow(self, event):
        uiCommand = self.__remainingCommands.GetItemPyData(
            self.__remainingSelection
        )
        if uiCommand is None:
            item = self.__visibleCommands.AppendItem(
                self.__visibleCommands.GetRootItem(), _("Separator")
            )
        elif isinstance(uiCommand, int):
            item = self.__visibleCommands.AppendItem(
                self.__visibleCommands.GetRootItem(), _("Spacer")
            )
        else:
            item = self.__visibleCommands.AppendItem(
                self.__visibleCommands.GetRootItem(), uiCommand.getHelpText()
            )
            self.__visibleCommands.SetItemImage(
                item, self.__imgListIndex.get(uiCommand.bitmap, -1)
            )
        self.__visibleCommands.SetItemPyData(item, uiCommand)
        self.__visible.append(uiCommand)
        if isinstance(uiCommand, uicommand.UICommand):
            self.__remainingCommands.EnableItem(
                self.__remainingSelection, False
            )
            self.__remainingSelection = None
            self.__showButton.Enable(False)
        self.__HackPreview()

    def __Swap(self, delta):
        items = self.__visibleCommands.GetRootItem().GetChildren()
        index = items.index(self.__visibleSelection)
        text = self.__visibleSelection.GetText()
        data = self.__visibleSelection.GetData()
        self.__visibleCommands.Delete(self.__visibleSelection)
        item = self.__visibleCommands.InsertItem(
            self.__visibleCommands.GetRootItem(), index + delta, text
        )
        self.__visibleCommands.SetItemPyData(item, data)
        if isinstance(data, uicommand.UICommand):
            self.__visibleCommands.SetItemImage(
                item, self.__imgListIndex.get(data.bitmap, -1)
            )
        self.__visibleCommands.SelectItem(item)
        self.__visible[index], self.__visible[index + delta] = (
            self.__visible[index + delta],
            self.__visible[index],
        )
        self.__HackPreview()

    def __OnMoveUp(self, event):
        self.__Swap(-1)

    def __OnMoveDown(self, event):
        self.__Swap(1)

    def __OnBeginDrag2(self, event):
        self.__draggingFromAvailable = True
        event.Veto()

    def __OnBeginDrag(self, event):
        if (
            self.__draggingFromAvailable
            or event.GetItem() == self.__visibleCommands.GetRootItem()
        ):
            event.Veto()
        else:
            self.__draggedItem = event.GetItem()
            event.Allow()
        self.__draggingFromAvailable = False

    def __OnEndDrag(self, event):
        if (
            event.GetItem() is not None
            and event.GetItem() != self.__draggedItem
        ):
            targetItem = event.GetItem()
            sourceIndex = (
                self.__visibleCommands.GetRootItem()
                .GetChildren()
                .index(self.__draggedItem)
            )
            uiCommand = self.__visible[sourceIndex]
            self.__visibleCommands.Delete(self.__draggedItem)
            del self.__visible[sourceIndex]
            targetIndex = (
                self.__visibleCommands.GetRootItem()
                .GetChildren()
                .index(targetItem)
                + 1
            )
            if (
                targetItem.PartialHilight()
                & wx.wx.TREE_HITTEST_ONITEMUPPERPART
            ):
                targetIndex -= 1
            self.__visible.insert(targetIndex, uiCommand)
            if uiCommand is None:
                text = _("Separator")
                img = -1
            elif isinstance(uiCommand, int):
                text = _("Spacer")
                img = -1
            else:
                text = uiCommand.getHelpText()
                img = self.__imgListIndex.get(uiCommand.bitmap, -1)
            item = self.__visibleCommands.InsertItem(
                self.__visibleCommands.GetRootItem(), targetIndex, text
            )
            self.__visibleCommands.SetItemPyData(item, uiCommand)
            self.__visibleCommands.SetItemImage(item, img)
            self.__HackPreview()
        self.__draggedItem = None

    def __HackPreview(self):
        self.__preview.loadPerspective(
            self.getToolBarPerspective(), customizable=False
        )
        for uiCommand in self.__preview.visibleUICommands():
            if uiCommand is not None and not isinstance(uiCommand, int):
                uiCommand.unbind(self.__preview, uiCommand.id)
                self.__preview.EnableTool(uiCommand.id, True)

    def __Populate(self, tree, uiCommands, enableCallback):
        tree.Freeze()
        try:
            tree.DeleteAllItems()
            root = tree.AddRoot("Root")

            for uiCommand in uiCommands:
                if uiCommand is None:
                    text = _("Separator")
                elif isinstance(uiCommand, int):
                    text = _("Spacer")
                else:
                    text = uiCommand.getHelpText()

                item = tree.AppendItem(root, text)
                if uiCommand is not None and not isinstance(uiCommand, int):
                    tree.SetItemImage(
                        item, self.__imgListIndex.get(uiCommand.bitmap, -1)
                    )
                    tree.EnableItem(item, enableCallback(uiCommand))
                tree.SetItemPyData(item, uiCommand)
        finally:
            tree.Thaw()

    def __PopulateRemainingCommands(self):
        def enableCallback(uiCommand):
            if isinstance(uiCommand, uicommand.UICommand):
                return uiCommand not in self.__visible
            return True

        self.__Populate(
            self.__remainingCommands,
            [None, 1]
            + [
                uiCommand
                for uiCommand in self.createToolBarUICommands()
                if isinstance(uiCommand, uicommand.UICommand)
            ],
            enableCallback,
        )

    def __PopulateVisibleCommands(self):
        self.__Populate(self.__visibleCommands, self.__visible, lambda x: True)

    def getToolBarPerspective(self):
        names = list()
        for uiCommand in self.__visible:
            if uiCommand is None:
                names.append("Separator")
            elif isinstance(uiCommand, int):
                names.append("Spacer")
            else:
                names.append(uiCommand.uniqueName())
        return ",".join(names)

    def createToolBarUICommands(self):
        return self.__toolbar.uiCommands(cache=False)


class ToolBarEditor(BalloonTipManager, widgets.Dialog):
    def __init__(self, toolbar, settings, *args, **kwargs):
        self.__toolbar = toolbar
        self.__settings = settings
        super().__init__(*args, **kwargs)
        self.SetClientSize(wx.Size(900, 700))
        self.CentreOnParent()

    def createInterior(self):
        return _ToolBarEditorInterior(
            self.__toolbar, self.__settings, self._panel
        )

    def ok(self, event=None):
        self.__toolbar.savePerspective(self._interior.getToolBarPerspective())
        super().ok(event=event)
