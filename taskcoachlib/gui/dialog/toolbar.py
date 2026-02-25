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
from taskcoachlib.gui.icons.icon_library import icon_catalog, LIST_ICON_SIZE
from taskcoachlib.gui.icons.image_list_cache import image_list_cache
from taskcoachlib.help.balloontips import BalloonTipManager
from taskcoachlib.gui import uicommand
from taskcoachlib.i18n import _
import wx


class _ToolBarEditorInterior(wx.Panel):
    def __init__(self, toolbar, settings, parent):
        self.__toolbar = toolbar
        self.__visible = toolbar.visible_ui_commands()

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
        self._hack_preview()

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        # Data storage for remaining list items (visible uses self.__visible)
        self.__remaining_data = []

        # Remaining commands list
        sb = wx.StaticBox(self, wx.ID_ANY, _("Available tools"))
        self.__remaining_commands = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER
        )
        self.__remaining_commands.SetImageList(
            image_list_cache.image_list, wx.IMAGE_LIST_SMALL
        )
        self.__remaining_commands.InsertColumn(0, "Command", width=300)
        self.__remaining_commands.Bind(wx.EVT_SIZE, self._on_list_resize)

        sbsz = wx.StaticBoxSizer(sb)
        sbsz.Add(self.__remaining_commands, 1, wx.EXPAND)
        hsizer.Add(sbsz, 1, wx.EXPAND | wx.ALL, 3)

        self._populate_remaining_commands()

        # Show/hide buttons
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        self.__show_button = wx.BitmapButton(
            self,
            wx.ID_ANY,
            icon_catalog.get_bitmap(
                "nuvola_actions_go-next-document", LIST_ICON_SIZE
            ),
        )
        self.__show_button.Enable(False)
        self.__show_button.SetToolTip(
            wx.ToolTip(_("Make this tool visible in the toolbar"))
        )
        btn_sizer.Add(self.__show_button, wx.ALL, 3)
        self.__hide_button = wx.BitmapButton(
            self,
            wx.ID_ANY,
            icon_catalog.get_bitmap(
                "nuvola_actions_go-previous-document", LIST_ICON_SIZE
            ),
        )
        self.__hide_button.Enable(False)
        self.__hide_button.SetToolTip(
            wx.ToolTip(_("Hide this tool from the toolbar"))
        )
        btn_sizer.Add(self.__hide_button, wx.ALL, 3)
        hsizer.Add(btn_sizer, 0, wx.ALIGN_CENTRE)

        # Visible commands list
        sb = wx.StaticBox(self, wx.ID_ANY, _("Tools"))
        self.__visible_commands = wx.ListCtrl(
            self,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER
        )
        self.__visible_commands.SetImageList(
            image_list_cache.image_list, wx.IMAGE_LIST_SMALL
        )
        self.__visible_commands.InsertColumn(0, "Command", width=300)
        self.__visible_commands.Bind(wx.EVT_SIZE, self._on_list_resize)

        sbsz = wx.StaticBoxSizer(sb)
        sbsz.Add(self.__visible_commands, 1, wx.EXPAND)
        hsizer.Add(sbsz, 1, wx.EXPAND | wx.ALL, 3)

        # Move buttons
        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        self.__move_up_button = wx.BitmapButton(
            self,
            wx.ID_ANY,
            icon_catalog.get_bitmap("nuvola_actions_arrow-up", LIST_ICON_SIZE),
        )
        self.__move_up_button.Enable(False)
        self.__move_up_button.SetToolTip(
            wx.ToolTip(_("Move the tool up (to the left of the toolbar)"))
        )
        btn_sizer.Add(self.__move_up_button, wx.ALL, 3)
        self.__move_down_button = wx.BitmapButton(
            self,
            wx.ID_ANY,
            icon_catalog.get_bitmap(
                "nuvola_actions_arrow-down", LIST_ICON_SIZE
            ),
        )
        self.__move_down_button.Enable(False)
        self.__move_down_button.SetToolTip(
            wx.ToolTip(_("Move the tool down (to the right of the toolbar)"))
        )
        btn_sizer.Add(self.__move_down_button, wx.ALL, 3)
        hsizer.Add(btn_sizer, 0, wx.ALIGN_CENTRE)

        self._populate_visible_commands()

        vsizer.Add(hsizer, 1, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(vsizer)

        self.__remaining_selection = -1
        self.__visible_selection = -1
        self.__dragged_index = -1
        self.__dragging_from_available = False
        self.__drop_line = None

        # Bind events
        self.__remaining_commands.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self._on_remaining_selection_changed
        )
        self.__remaining_commands.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self._on_remaining_deselected
        )
        self.__visible_commands.Bind(
            wx.EVT_LIST_ITEM_SELECTED, self._on_visible_selection_changed
        )
        self.__visible_commands.Bind(
            wx.EVT_LIST_ITEM_DESELECTED, self._on_visible_deselected
        )

        self.__hide_button.Bind(wx.EVT_BUTTON, self._on_hide)
        self.__show_button.Bind(wx.EVT_BUTTON, self._on_show)
        self.__move_up_button.Bind(wx.EVT_BUTTON, self._on_move_up)
        self.__move_down_button.Bind(wx.EVT_BUTTON, self._on_move_down)

        # DnD events
        self.__visible_commands.Bind(
            wx.EVT_LIST_BEGIN_DRAG, self._on_begin_drag
        )
        self.__remaining_commands.Bind(
            wx.EVT_LIST_BEGIN_DRAG, self._on_begin_drag_available
        )

        # Double-click events
        self.__remaining_commands.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self._on_remaining_double_click
        )
        self.__visible_commands.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self._on_visible_double_click
        )

        wx.CallAfter(
            wx.GetTopLevelParent(self).AddBalloonTip,
            settings,
            "customizabletoolbars_dnd",
            self.__visible_commands,
            title=_("Drag and drop"),
            message=_(
                """Reorder toolbar buttons by drag and dropping them in this list."""
            ),
        )

    def _on_remaining_selection_changed(self, event):
        self.__remaining_selection = event.GetIndex()
        ui_cmd = self.__remaining_data[self.__remaining_selection]
        if ui_cmd.is_command():
            if ui_cmd.unique_name() in self._get_visible_names():
                self.__show_button.Enable(False)
            else:
                self.__show_button.Enable(True)
        else:
            self.__show_button.Enable(True)
        event.Skip()

    def _on_remaining_deselected(self, event):
        self.__remaining_selection = -1
        self.__show_button.Enable(False)
        event.Skip()

    def _on_visible_selection_changed(self, event):
        self.__visible_selection = event.GetIndex()
        self.__hide_button.Enable(True)
        count = self.__visible_commands.GetItemCount()
        self.__move_up_button.Enable(self.__visible_selection > 0)
        self.__move_down_button.Enable(self.__visible_selection < count - 1)
        event.Skip()

    def _on_visible_deselected(self, event):
        self.__visible_selection = -1
        self.__hide_button.Enable(False)
        self.__move_up_button.Enable(False)
        self.__move_down_button.Enable(False)
        event.Skip()

    def _get_visible_names(self):
        """Get set of unique names of commands in visible list."""
        names = set()
        for cmd in self.__visible:
            if cmd.is_command():
                names.add(cmd.unique_name())
        return names

    def _on_hide(self, event):
        if self.__visible_selection < 0:
            return
        idx = self.__visible_selection
        ui_cmd = self.__visible[idx]

        self.__visible_commands.DeleteItem(idx)
        del self.__visible[idx]

        self.__visible_selection = -1
        self.__hide_button.Enable(False)
        self.__move_up_button.Enable(False)
        self.__move_down_button.Enable(False)

        # Update remaining list to show this item as available again
        self._update_remaining_item_state(ui_cmd, enabled=True)
        self._hack_preview()

    def _on_show(self, event):
        if self.__remaining_selection < 0:
            return
        ui_cmd = self.__remaining_data[self.__remaining_selection]

        # Determine insert position
        if self.__visible_selection >= 0:
            insert_index = self.__visible_selection + 1
        else:
            insert_index = len(self.__visible)

        # Get text and image
        text, img = self._get_item_text_and_image(ui_cmd)

        # Insert into visible list
        self.__visible.insert(insert_index, ui_cmd)
        self.__visible_commands.InsertItem(insert_index, text, img)

        # Mark as used in remaining list
        if ui_cmd.is_command():
            self._update_remaining_item_state(ui_cmd, enabled=False)
            self.__remaining_selection = -1
            self.__show_button.Enable(False)

        self._hack_preview()

    def _get_item_text_and_image(self, ui_cmd):
        """Get display text and image index for a ui_command."""
        if ui_cmd.is_separator():
            return _("Separator"), -1
        elif ui_cmd.is_spacer():
            return _("Spacer"), -1
        elif ui_cmd.icon_id is None:
            return ui_cmd.get_help_text(), -1
        else:
            return (
                ui_cmd.get_help_text(),
                image_list_cache.get_index(ui_cmd.icon_id),
            )

    def _update_remaining_item_state(self, ui_cmd, enabled):
        """Update the visual state of an item in the remaining list."""
        if not ui_cmd.is_command():
            return
        target_name = ui_cmd.unique_name()
        for i, cmd in enumerate(self.__remaining_data):
            if cmd.is_command() and cmd.unique_name() == target_name:
                if enabled:
                    self.__remaining_commands.SetItemTextColour(
                        i,
                        wx.SystemSettings.GetColour(wx.SYS_COLOUR_LISTBOXTEXT),
                    )
                else:
                    self.__remaining_commands.SetItemTextColour(
                        i, wx.Colour(150, 150, 150)
                    )
                self.__remaining_commands.RefreshItem(i)
                break

    def _swap(self, delta):
        if self.__visible_selection < 0:
            return
        idx = self.__visible_selection
        new_idx = idx + delta

        if new_idx < 0 or new_idx >= len(self.__visible):
            return

        # Swap in data
        self.__visible[idx], self.__visible[new_idx] = (
            self.__visible[new_idx],
            self.__visible[idx],
        )

        # Refresh display
        self._populate_visible_commands()
        self.__visible_commands.Select(new_idx)
        self.__visible_selection = new_idx

        self._hack_preview()

    def _on_move_up(self, event):
        self._swap(-1)

    def _on_move_down(self, event):
        self._swap(1)

    def _on_remaining_double_click(self, event):
        """Double-click on available item adds it to visible."""
        idx = event.GetIndex()
        if idx >= 0:
            ui_cmd = self.__remaining_data[idx]
            if ui_cmd.is_command():
                if ui_cmd.unique_name() in self._get_visible_names():
                    return
            self.__remaining_selection = idx
            self._on_show(event)

    def _on_visible_double_click(self, event):
        """Double-click on visible item removes it."""
        idx = event.GetIndex()
        if idx >= 0:
            self.__visible_selection = idx
            self._on_hide(event)

    def reset_to_default(self):
        """Reset toolbar to default configuration."""
        default_perspective = self.__toolbar.get_default_perspective()
        if not default_perspective:
            return

        # Parse default perspective and rebuild visible list
        index = dict(
            (command.unique_name(), command)
            for command in self.create_toolbar_ui_commands()
        )

        self.__visible = []
        for class_name in default_perspective.split(","):
            if class_name in index:
                self.__visible.append(index[class_name])

        # Repopulate both panels
        self._populate_visible_commands()
        self._populate_remaining_commands()
        self.__visible_selection = -1
        self.__remaining_selection = -1
        self.__hide_button.Enable(False)
        self.__show_button.Enable(False)
        self.__move_up_button.Enable(False)
        self.__move_down_button.Enable(False)
        self._hack_preview()

    def _on_begin_drag_available(self, event):
        """Drag started from Available tools panel."""
        idx = event.GetIndex()
        if idx < 0:
            return

        ui_cmd = self.__remaining_data[idx]
        if ui_cmd.is_command():
            if ui_cmd.unique_name() in self._get_visible_names():
                return  # Can't drag disabled items

        self.__dragged_index = idx
        self.__dragging_from_available = True
        self._do_drag_drop(self.__remaining_commands)

    def _on_begin_drag(self, event):
        """Drag started from Tools panel."""
        idx = event.GetIndex()
        if idx < 0:
            return

        self.__dragged_index = idx
        self.__dragging_from_available = False
        self._do_drag_drop(self.__visible_commands)

    def _on_list_resize(self, event):
        """Resize column to fill available width."""
        list_ctrl = event.GetEventObject()
        width = list_ctrl.GetClientSize().width
        if width > 0:
            list_ctrl.SetColumnWidth(0, width)
        event.Skip()

    def _do_drag_drop(self, source_list):
        """Perform drag and drop operation."""
        data = wx.TextDataObject("drag")
        drop_source = wx.DropSource(source_list)
        drop_source.SetData(data)

        self.__visible_commands.SetDropTarget(
            _ListDropTarget(self, is_visible=True)
        )
        self.__remaining_commands.SetDropTarget(
            _ListDropTarget(self, is_visible=False)
        )

        drop_source.DoDragDrop(wx.Drag_DefaultMove)

        self.ClearDropLine()
        self.__visible_commands.SetDropTarget(None)
        self.__remaining_commands.SetDropTarget(None)
        self.__dragged_index = -1

    def ClearDropLine(self):
        """Clear the drop indicator line."""
        if self.__drop_line:
            self.__drop_line.Destroy()
            self.__drop_line = None

    def _show_drop_line(self, y):
        """Show insertion line at the given Y position."""
        if not self.__visible_commands.IsShownOnScreen():
            return

        width = self.__visible_commands.GetClientSize().width
        if not self.__drop_line:
            self.__drop_line = wx.Panel(
                self.__visible_commands, size=(width, 2)
            )
            self.__drop_line.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.__drop_line.SetSize(width, 2)
        self.__drop_line.SetPosition((0, y))
        self.__drop_line.Show()
        self.__drop_line.Raise()

    def HandleDragOver(self, x, y):
        """Handle drag over visible commands - show insertion line."""
        idx, flags = self.__visible_commands.HitTest((x, y))

        if idx == wx.NOT_FOUND:
            count = self.__visible_commands.GetItemCount()
            if count > 0:
                rect = self.__visible_commands.GetItemRect(count - 1)
                self._show_drop_line(rect.bottom)
            else:
                self._show_drop_line(0)
            return count
        else:
            rect = self.__visible_commands.GetItemRect(idx)
            mid_y = rect.y + rect.height // 2
            if y < mid_y:
                self._show_drop_line(rect.y - 1)
                return idx
            else:
                self._show_drop_line(rect.bottom)
                return idx + 1

    def HandleDrop(self, x, y):
        """Handle drop on visible commands."""
        target_idx = self.HandleDragOver(x, y)
        self.ClearDropLine()

        if self.__dragged_index < 0:
            return False

        if self.__dragging_from_available:
            ui_cmd = self.__remaining_data[self.__dragged_index]

            if ui_cmd.is_command():
                if ui_cmd.unique_name() in self._get_visible_names():
                    return False

            text, img = self._get_item_text_and_image(ui_cmd)

            self.__visible.insert(target_idx, ui_cmd)
            self.__visible_commands.InsertItem(target_idx, text, img)

            if ui_cmd.is_command():
                self._update_remaining_item_state(ui_cmd, enabled=False)
        else:
            if (
                target_idx == self.__dragged_index
                or target_idx == self.__dragged_index + 1
            ):
                return False

            ui_cmd = self.__visible[self.__dragged_index]
            text, img = self._get_item_text_and_image(ui_cmd)

            self.__visible_commands.DeleteItem(self.__dragged_index)
            del self.__visible[self.__dragged_index]

            if self.__dragged_index < target_idx:
                target_idx -= 1

            self.__visible.insert(target_idx, ui_cmd)
            self.__visible_commands.InsertItem(target_idx, text, img)

        self._hack_preview()
        return True

    def HandleDropOnRemaining(self, x, y):
        """Handle drop on remaining commands (remove from visible)."""
        self.ClearDropLine()

        if self.__dragged_index < 0:
            return False

        if self.__dragging_from_available:
            return False

        ui_cmd = self.__visible[self.__dragged_index]
        self.__visible_commands.DeleteItem(self.__dragged_index)
        del self.__visible[self.__dragged_index]

        self.__visible_selection = -1
        self.__hide_button.Enable(False)
        self.__move_up_button.Enable(False)
        self.__move_down_button.Enable(False)

        self._update_remaining_item_state(ui_cmd, enabled=True)

        self._hack_preview()
        return True

    def _hack_preview(self):
        self.__preview.load_perspective(
            self.get_toolbar_perspective(), customizable=False
        )
        for ui_cmd in self.__preview.visible_ui_commands():
            if ui_cmd.is_command():
                ui_cmd.unbind(self.__preview, ui_cmd.id)
                self.__preview.EnableTool(ui_cmd.id, True)

    def _populate_remaining_commands(self):
        self.__remaining_commands.DeleteAllItems()
        self.__remaining_data = []

        visible_names = self._get_visible_names()

        all_commands = [
            uicommand.Separator(), uicommand.Spacer()
        ] + [
            cmd for cmd in self.create_toolbar_ui_commands()
            if cmd.is_command()
        ]

        for ui_cmd in all_commands:
            text, img = self._get_item_text_and_image(ui_cmd)
            idx = self.__remaining_commands.InsertItem(
                self.__remaining_commands.GetItemCount(), text, img
            )
            self.__remaining_data.append(ui_cmd)

            if ui_cmd.is_command():
                if ui_cmd.unique_name() in visible_names:
                    self.__remaining_commands.SetItemTextColour(
                        idx, wx.Colour(150, 150, 150)
                    )

    def _populate_visible_commands(self):
        self.__visible_commands.DeleteAllItems()

        for ui_cmd in self.__visible:
            text, img = self._get_item_text_and_image(ui_cmd)
            self.__visible_commands.InsertItem(
                self.__visible_commands.GetItemCount(), text, img
            )

    def get_toolbar_perspective(self):
        names = list()
        for item in self.__visible:
            names.append(item.unique_name())
        return ",".join(names)

    # Keep old name as alias
    getToolBarPerspective = get_toolbar_perspective

    def create_toolbar_ui_commands(self):
        return self.__toolbar.uiCommands(cache=False)

    # Keep old name as alias
    createToolBarUICommands = create_toolbar_ui_commands


class _ListDropTarget(wx.DropTarget):
    """Drop target for the command lists."""

    def __init__(self, interior, is_visible=True):
        super().__init__()
        self.__interior = interior
        self.__is_visible = is_visible
        self.__data = wx.TextDataObject()
        self.SetDataObject(self.__data)

    def OnDragOver(self, x, y, defResult):
        if self.__is_visible:
            self.__interior.HandleDragOver(x, y)
        return wx.DragMove

    def OnDrop(self, x, y):
        return True

    def OnData(self, x, y, defResult):
        if self.GetData():
            if self.__is_visible:
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
        reset_button = wx.Button(self, wx.ID_ANY, _("Reset to Default"))
        reset_button.SetToolTip(
            wx.ToolTip(_("Restore the toolbar to its default configuration"))
        )
        reset_button.Bind(wx.EVT_BUTTON, self._on_reset)

        cancel_button = wx.Button(self, wx.ID_CANCEL, _("Cancel"))
        cancel_button.Bind(wx.EVT_BUTTON, self.cancel)

        ok_button = wx.Button(self, wx.ID_OK, _("OK"))
        ok_button.Bind(wx.EVT_BUTTON, self.ok)

        # Layout: --- stretch --- [Reset] [50px gap] [Cancel] [OK]
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(
            reset_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 50
        )
        button_sizer.Add(
            cancel_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8
        )
        button_sizer.Add(ok_button, 0, wx.ALIGN_CENTER_VERTICAL)

        self.SetButtonSizer(button_sizer)
        return button_sizer

    def _on_reset(self, event):
        self._interior.reset_to_default()

    def ok(self, event=None):
        self.__toolbar.save_perspective(
            self._interior.get_toolbar_perspective()
        )
        super().ok(event=event)
