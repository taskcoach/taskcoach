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
import wx


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
        self.__imgListIndex[None] = self.__imgList.Add(
            empty.ConvertToBitmap()
        )
        for uiCmd in toolbar.uiCommands():
            if (
                uiCmd is not None
                and not isinstance(uiCmd, int)
                and uiCmd.bitmap is not None
            ):
                self.__imgListIndex[uiCmd.bitmap] = self.__imgList.Add(
                    wx.ArtProvider.GetBitmap(
                        uiCmd.bitmap, wx.ART_MENU, (16, 16)
                    )
                )

        # Data storage for remaining list items (visible uses self.__visible)
        self.__remainingData = []

        # Remaining commands list
        sb = wx.StaticBox(self, wx.ID_ANY, _("Available tools"))
        self.__remainingCommands = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER
        )
        self.__remainingCommands.SetImageList(self.__imgList, wx.IMAGE_LIST_SMALL)
        self.__remainingCommands.InsertColumn(0, "Command", width=300)
        self.__remainingCommands.Bind(wx.EVT_SIZE, self.__OnListResize)

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
        self.__visibleCommands = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER
        )
        self.__visibleCommands.SetImageList(self.__imgList, wx.IMAGE_LIST_SMALL)
        self.__visibleCommands.InsertColumn(0, "Command", width=300)
        self.__visibleCommands.Bind(wx.EVT_SIZE, self.__OnListResize)

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

        self.__remainingSelection = -1
        self.__visibleSelection = -1
        self.__draggedIndex = -1
        self.__draggingFromAvailable = False
        self.__dropLine = None

        # Bind events
        self.__remainingCommands.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.__OnRemainingSelectionChanged
        )
        self.__remainingCommands.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.__OnRemainingDeselected
        )
        self.__visibleCommands.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self.__OnVisibleSelectionChanged
        )
        self.__visibleCommands.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self.__OnVisibleDeselected
        )

        self.__hideButton.Bind(wx.EVT_BUTTON, self.__OnHide)
        self.__showButton.Bind(wx.EVT_BUTTON, self.__OnShow)
        self.__moveUpButton.Bind(wx.EVT_BUTTON, self.__OnMoveUp)
        self.__moveDownButton.Bind(wx.EVT_BUTTON, self.__OnMoveDown)

        # DnD events
        self.__visibleCommands.Bind(wx.EVT_LIST_BEGIN_DRAG, self.__OnBeginDrag)
        self.__remainingCommands.Bind(wx.EVT_LIST_BEGIN_DRAG, self.__OnBeginDrag2)

        # Double-click events
        self.__remainingCommands.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.__OnRemainingDoubleClick
        )
        self.__visibleCommands.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.__OnVisibleDoubleClick
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
        self.__remainingSelection = event.GetIndex()
        # Check if item is enabled (not grayed out)
        uiCmd = self.__remainingData[self.__remainingSelection]
        if isinstance(uiCmd, uicommand.UICommand):
            # Check if already in visible list
            if uiCmd.uniqueName() in self.__GetVisibleNames():
                self.__showButton.Enable(False)
            else:
                self.__showButton.Enable(True)
        else:
            self.__showButton.Enable(True)
        event.Skip()

    def __OnRemainingDeselected(self, event):
        self.__remainingSelection = -1
        self.__showButton.Enable(False)
        event.Skip()

    def __OnVisibleSelectionChanged(self, event):
        self.__visibleSelection = event.GetIndex()
        self.__hideButton.Enable(True)
        count = self.__visibleCommands.GetItemCount()
        self.__moveUpButton.Enable(self.__visibleSelection > 0)
        self.__moveDownButton.Enable(self.__visibleSelection < count - 1)
        event.Skip()

    def __OnVisibleDeselected(self, event):
        self.__visibleSelection = -1
        self.__hideButton.Enable(False)
        self.__moveUpButton.Enable(False)
        self.__moveDownButton.Enable(False)
        event.Skip()

    def __GetVisibleNames(self):
        """Get set of unique names of commands in visible list."""
        names = set()
        for cmd in self.__visible:
            if isinstance(cmd, uicommand.UICommand):
                names.add(cmd.uniqueName())
        return names

    def __OnHide(self, event):
        if self.__visibleSelection < 0:
            return
        idx = self.__visibleSelection
        uiCmd = self.__visible[idx]

        self.__visibleCommands.DeleteItem(idx)
        del self.__visible[idx]

        self.__visibleSelection = -1
        self.__hideButton.Enable(False)
        self.__moveUpButton.Enable(False)
        self.__moveDownButton.Enable(False)

        # Update remaining list to show this item as available again
        self.__UpdateRemainingItemState(uiCmd, enabled=True)
        self.__HackPreview()

    def __OnShow(self, event):
        if self.__remainingSelection < 0:
            return
        uiCmd = self.__remainingData[self.__remainingSelection]

        # Determine insert position
        if self.__visibleSelection >= 0:
            insertIndex = self.__visibleSelection + 1
        else:
            insertIndex = len(self.__visible)

        # Get text and image
        text, img = self.__GetItemTextAndImage(uiCmd)

        # Insert into visible list
        self.__visible.insert(insertIndex, uiCmd)
        self.__visibleCommands.InsertItem(insertIndex, text, img)

        # Mark as used in remaining list
        if isinstance(uiCmd, uicommand.UICommand):
            self.__UpdateRemainingItemState(uiCmd, enabled=False)
            self.__remainingSelection = -1
            self.__showButton.Enable(False)

        self.__HackPreview()

    def __GetItemTextAndImage(self, uiCmd):
        """Get display text and image index for a uiCommand."""
        if uiCmd is None:
            return _("Separator"), self.__imgListIndex.get(None, -1)
        elif isinstance(uiCmd, int):
            return _("Spacer"), self.__imgListIndex.get(None, -1)
        else:
            return uiCmd.getHelpText(), self.__imgListIndex.get(uiCmd.bitmap, -1)

    def __UpdateRemainingItemState(self, uiCmd, enabled):
        """Update the visual state of an item in the remaining list."""
        if not isinstance(uiCmd, uicommand.UICommand):
            return
        targetName = uiCmd.uniqueName()
        for i, cmd in enumerate(self.__remainingData):
            if isinstance(cmd, uicommand.UICommand) and cmd.uniqueName() == targetName:
                if enabled:
                    # Use system default text color
                    self.__remainingCommands.SetItemTextColour(
                        i, wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT)
                    )
                else:
                    self.__remainingCommands.SetItemTextColour(i, wx.Colour(150, 150, 150))
                self.__remainingCommands.RefreshItem(i)
                break

    def __Swap(self, delta):
        if self.__visibleSelection < 0:
            return
        idx = self.__visibleSelection
        newIdx = idx + delta

        if newIdx < 0 or newIdx >= len(self.__visible):
            return

        # Swap in data
        self.__visible[idx], self.__visible[newIdx] = self.__visible[newIdx], self.__visible[idx]

        # Refresh display
        self.__PopulateVisibleCommands()
        self.__visibleCommands.Select(newIdx)
        self.__visibleSelection = newIdx

        self.__HackPreview()

    def __OnMoveUp(self, event):
        self.__Swap(-1)

    def __OnMoveDown(self, event):
        self.__Swap(1)

    def __OnRemainingDoubleClick(self, event):
        """Double-click on available item adds it to visible."""
        idx = event.GetIndex()
        if idx >= 0:
            uiCmd = self.__remainingData[idx]
            # Check if already in use
            if isinstance(uiCmd, uicommand.UICommand):
                if uiCmd.uniqueName() in self.__GetVisibleNames():
                    return
            self.__remainingSelection = idx
            self.__OnShow(event)

    def __OnVisibleDoubleClick(self, event):
        """Double-click on visible item removes it."""
        idx = event.GetIndex()
        if idx >= 0:
            self.__visibleSelection = idx
            self.__OnHide(event)

    def resetToDefault(self):
        """Reset toolbar to default configuration."""
        defaultPerspective = self.__toolbar.getDefaultPerspective()
        if not defaultPerspective:
            return

        # Parse default perspective and rebuild visible list
        index = dict(
            [
                (command.uniqueName(), command)
                for command in self.createToolBarUICommands()
                if command is not None and not isinstance(command, int)
            ]
        )
        index["Separator"] = None
        index["Spacer"] = 1

        self.__visible = []
        for className in defaultPerspective.split(","):
            if className in index:
                self.__visible.append(index[className])

        # Repopulate both panels
        self.__PopulateVisibleCommands()
        self.__PopulateRemainingCommands()
        self.__visibleSelection = -1
        self.__remainingSelection = -1
        self.__hideButton.Enable(False)
        self.__showButton.Enable(False)
        self.__moveUpButton.Enable(False)
        self.__moveDownButton.Enable(False)
        self.__HackPreview()

    def __OnBeginDrag2(self, event):
        """Drag started from Available tools panel."""
        idx = event.GetIndex()
        if idx < 0:
            return

        uiCmd = self.__remainingData[idx]
        # Check if item is available (not already in toolbar)
        if isinstance(uiCmd, uicommand.UICommand):
            if uiCmd.uniqueName() in self.__GetVisibleNames():
                return  # Can't drag disabled items

        self.__draggedIndex = idx
        self.__draggingFromAvailable = True
        self.__DoDragDrop(self.__remainingCommands)

    def __OnBeginDrag(self, event):
        """Drag started from Tools panel."""
        idx = event.GetIndex()
        if idx < 0:
            return

        self.__draggedIndex = idx
        self.__draggingFromAvailable = False
        self.__DoDragDrop(self.__visibleCommands)

    def __OnListResize(self, event):
        """Resize column to fill available width."""
        listCtrl = event.GetEventObject()
        width = listCtrl.GetClientSize().width
        if width > 0:
            listCtrl.SetColumnWidth(0, width)
        event.Skip()

    def __DoDragDrop(self, sourceList):
        """Perform drag and drop operation."""
        # TextDataObject is required by wx.DropSource but we track state internally
        data = wx.TextDataObject("drag")
        dropSource = wx.DropSource(sourceList)
        dropSource.SetData(data)

        # Set up drop targets on both lists
        self.__visibleCommands.SetDropTarget(_ListDropTarget(self, isVisible=True))
        self.__remainingCommands.SetDropTarget(_ListDropTarget(self, isVisible=False))

        dropSource.DoDragDrop(wx.Drag_DefaultMove)

        # Clean up - clear drop targets first to avoid GTK warnings on cancel
        self.ClearDropLine()
        self.__visibleCommands.SetDropTarget(None)
        self.__remainingCommands.SetDropTarget(None)
        self.__draggedIndex = -1

    def ClearDropLine(self):
        """Clear the drop indicator line."""
        if self.__dropLine:
            self.__dropLine.Destroy()
            self.__dropLine = None

    def __ShowDropLine(self, y):
        """Show insertion line at the given Y position."""
        if not self.__visibleCommands.IsShownOnScreen():
            return

        width = self.__visibleCommands.GetClientSize().width
        if not self.__dropLine:
            self.__dropLine = wx.Panel(self.__visibleCommands, size=(width, 2))
            self.__dropLine.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.__dropLine.SetSize(width, 2)
        self.__dropLine.SetPosition((0, y))
        self.__dropLine.Show()
        self.__dropLine.Raise()

    def HandleDragOver(self, x, y):
        """Handle drag over visible commands - show insertion line."""
        # Find which item we're over
        idx, flags = self.__visibleCommands.HitTest((x, y))

        if idx == wx.NOT_FOUND:
            # Below all items - show line at bottom
            count = self.__visibleCommands.GetItemCount()
            if count > 0:
                rect = self.__visibleCommands.GetItemRect(count - 1)
                self.__ShowDropLine(rect.bottom)
            else:
                self.__ShowDropLine(0)
            return count
        else:
            # Show line above or below item based on position
            rect = self.__visibleCommands.GetItemRect(idx)
            midY = rect.y + rect.height // 2
            if y < midY:
                self.__ShowDropLine(rect.y - 1)
                return idx
            else:
                self.__ShowDropLine(rect.bottom)
                return idx + 1

    def HandleDrop(self, x, y):
        """Handle drop on visible commands."""
        targetIdx = self.HandleDragOver(x, y)
        self.ClearDropLine()

        if self.__draggedIndex < 0:
            return False

        if self.__draggingFromAvailable:
            # Moving from available to visible
            uiCmd = self.__remainingData[self.__draggedIndex]

            # Check if already in use
            if isinstance(uiCmd, uicommand.UICommand):
                if uiCmd.uniqueName() in self.__GetVisibleNames():
                    return False

            text, img = self.__GetItemTextAndImage(uiCmd)

            # Insert into visible list
            self.__visible.insert(targetIdx, uiCmd)
            self.__visibleCommands.InsertItem(targetIdx, text, img)

            # Mark as used
            if isinstance(uiCmd, uicommand.UICommand):
                self.__UpdateRemainingItemState(uiCmd, enabled=False)
        else:
            # Reordering within visible list
            if targetIdx == self.__draggedIndex or targetIdx == self.__draggedIndex + 1:
                return False  # No change needed

            uiCmd = self.__visible[self.__draggedIndex]
            text, img = self.__GetItemTextAndImage(uiCmd)

            # Remove from old position
            self.__visibleCommands.DeleteItem(self.__draggedIndex)
            del self.__visible[self.__draggedIndex]

            # Adjust target index if needed
            if self.__draggedIndex < targetIdx:
                targetIdx -= 1

            # Insert at new position
            self.__visible.insert(targetIdx, uiCmd)
            self.__visibleCommands.InsertItem(targetIdx, text, img)

        self.__HackPreview()
        return True

    def HandleDropOnRemaining(self, x, y):
        """Handle drop on remaining commands (remove from visible)."""
        self.ClearDropLine()

        if self.__draggedIndex < 0:
            return False

        # Only handle if dragging FROM visible list
        if self.__draggingFromAvailable:
            return False  # Can't drop back to same list

        # Remove from visible list
        uiCmd = self.__visible[self.__draggedIndex]
        self.__visibleCommands.DeleteItem(self.__draggedIndex)
        del self.__visible[self.__draggedIndex]

        # Clear selection state
        self.__visibleSelection = -1
        self.__hideButton.Enable(False)
        self.__moveUpButton.Enable(False)
        self.__moveDownButton.Enable(False)

        # Re-enable in remaining list
        self.__UpdateRemainingItemState(uiCmd, enabled=True)

        self.__HackPreview()
        return True

    def __HackPreview(self):
        self.__preview.loadPerspective(
            self.getToolBarPerspective(), customizable=False
        )
        for uiCmd in self.__preview.visibleUICommands():
            if uiCmd is not None and not isinstance(uiCmd, int):
                uiCmd.unbind(self.__preview, uiCmd.id)
                self.__preview.EnableTool(uiCmd.id, True)

    def __PopulateRemainingCommands(self):
        self.__remainingCommands.DeleteAllItems()
        self.__remainingData = []

        visibleNames = self.__GetVisibleNames()

        # Add separator and spacer first
        allCommands = [None, 1] + [
            cmd for cmd in self.createToolBarUICommands()
            if isinstance(cmd, uicommand.UICommand)
        ]

        for uiCmd in allCommands:
            text, img = self.__GetItemTextAndImage(uiCmd)
            idx = self.__remainingCommands.InsertItem(
                self.__remainingCommands.GetItemCount(), text, img
            )
            self.__remainingData.append(uiCmd)

            # Gray out if already in visible list
            if isinstance(uiCmd, uicommand.UICommand):
                if uiCmd.uniqueName() in visibleNames:
                    self.__remainingCommands.SetItemTextColour(idx, wx.Colour(150, 150, 150))

    def __PopulateVisibleCommands(self):
        self.__visibleCommands.DeleteAllItems()

        for uiCmd in self.__visible:
            text, img = self.__GetItemTextAndImage(uiCmd)
            self.__visibleCommands.InsertItem(
                self.__visibleCommands.GetItemCount(), text, img
            )

    def getToolBarPerspective(self):
        names = list()
        for uiCmd in self.__visible:
            if uiCmd is None:
                names.append("Separator")
            elif isinstance(uiCmd, int):
                names.append("Spacer")
            else:
                names.append(uiCmd.uniqueName())
        return ",".join(names)

    def createToolBarUICommands(self):
        return self.__toolbar.uiCommands(cache=False)


class _ListDropTarget(wx.DropTarget):
    """Drop target for the command lists."""

    def __init__(self, interior, isVisible=True):
        super().__init__()
        self.__interior = interior
        self.__isVisible = isVisible
        self.__data = wx.TextDataObject()
        self.SetDataObject(self.__data)

    def OnDragOver(self, x, y, defResult):
        if self.__isVisible:
            self.__interior.HandleDragOver(x, y)
        return wx.DragMove

    def OnDrop(self, x, y):
        return True

    def OnData(self, x, y, defResult):
        if self.GetData():
            if self.__isVisible:
                self.__interior.HandleDrop(x, y)
            else:
                self.__interior.HandleDropOnRemaining(x, y)
        return defResult

    def OnLeave(self):
        self.__interior.ClearDropLine()


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

    def createButtons(self):
        # Create buttons with dialog as parent
        resetButton = wx.Button(self, wx.ID_ANY, _("Reset to Default"))
        resetButton.SetToolTip(
            wx.ToolTip(_("Restore the toolbar to its default configuration"))
        )
        resetButton.Bind(wx.EVT_BUTTON, self.__OnReset)

        cancelButton = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        cancelButton.Bind(wx.EVT_BUTTON, self.cancel)

        okButton = wx.Button(self, wx.ID_OK, _("OK"))
        okButton.Bind(wx.EVT_BUTTON, self.ok)

        # Layout: --- stretch --- [Reset] [50px gap] [Cancel] [OK]
        # All buttons right-aligned, with extra space before Cancel/OK
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.AddStretchSpacer(1)
        buttonSizer.Add(resetButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 50)
        buttonSizer.Add(cancelButton, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        buttonSizer.Add(okButton, 0, wx.ALIGN_CENTER_VERTICAL)

        self.SetButtonSizer(buttonSizer)
        return buttonSizer

    def __OnReset(self, event):
        self._interior.resetToDefault()

    def ok(self, event=None):
        self.__toolbar.savePerspective(self._interior.getToolBarPerspective())
        super().ok(event=event)
