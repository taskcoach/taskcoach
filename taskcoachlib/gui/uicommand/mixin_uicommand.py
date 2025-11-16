"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>

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

from taskcoachlib.domain import task, note, category, effort, attachment
from taskcoachlib.i18n import _
import wx


class NeedsSelectionMixin(object):
    """Mixin class for UI commands that need at least one selected item."""

    def enabled(self, event):
        return super().enabled(event) and self.viewer.curselection()


class NeedsSelectedCategorizableMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected
    categorizable."""

    def enabled(self, event):
        return super().enabled(event) and (
            self.viewer.curselectionIsInstanceOf(task.Task)
            or self.viewer.curselectionIsInstanceOf(note.Note)
        )


class NeedsOneSelectedItemMixin(object):
    """Mixin class for UI commands that need exactly one selected item."""

    def enabled(self, event):
        return super().enabled(event) and len(self.viewer.curselection()) == 1


class NeedsSelectedCompositeMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected composite
    item."""

    def enabled(self, event):
        return super().enabled(event) and (
            self.viewer.curselectionIsInstanceOf(task.Task)
            or self.viewer.curselectionIsInstanceOf(note.Note)
            or self.viewer.curselectionIsInstanceOf(category.Category)
        )


class NeedsOneSelectedCompositeItemMixin(
    NeedsOneSelectedItemMixin, NeedsSelectedCompositeMixin
):
    """Mixin class for UI commands that need exactly one selected composite
    item."""

    pass


class NeedsAttachmentViewerMixin(object):
    """Mixin class for UI commands that need a viewer that is showing
    attachments."""

    def enabled(self, event):
        return super().enabled(event) and self.viewer.isShowingAttachments()


class NeedsSelectedTasksMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need one or more selected tasks."""

    def enabled(self, event):
        return super().enabled(event) and self.viewer.curselectionIsInstanceOf(
            task.Task
        )


class NeedsSelectedNoteOwnersMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected note
    owner."""

    def enabled(self, event):
        return super().enabled(event) and (
            self.viewer.curselectionIsInstanceOf(task.Task)
            or self.viewer.curselectionIsInstanceOf(category.Category)
            or self.viewer.curselectionIsInstanceOf(attachment.Attachment)
        )


class NeedsSelectedNoteOwnersMixinWithNotes(NeedsSelectedNoteOwnersMixin):
    """Mixin class for UI commands that need at least one selected note owner
    with notes."""

    def enabled(self, event):
        # pylint: disable=E1101
        return super().enabled(event) and any(
            [item.notes() for item in self.viewer.curselection()]
        )


class NeedsSelectedAttachmentOwnersMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected attachment
    owner."""

    def enabled(self, event):
        return super().enabled(event) and (
            self.viewer.curselectionIsInstanceOf(task.Task)
            or self.viewer.curselectionIsInstanceOf(category.Category)
            or self.viewer.curselectionIsInstanceOf(note.Note)
        )


class NeedsOneSelectedTaskMixin(
    NeedsSelectedTasksMixin, NeedsOneSelectedItemMixin
):
    """Mixin class for UI commands that need at least one selected tasks."""

    pass


class NeedsSelectionWithAttachmentsMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected item with
    one or more attachments."""

    def enabled(self, event):
        return super().enabled(event) and any(
            item.attachments()
            for item in self.viewer.curselection()
            if not isinstance(item, effort.Effort)
        )


class NeedsSelectedEffortMixin(NeedsSelectionMixin):
    """Mixin class for UI commands that need at least one selected effort."""

    def enabled(self, event):
        return super().enabled(event) and self.viewer.curselectionIsInstanceOf(
            effort.Effort
        )


class NeedsSelectedAttachmentsMixin(
    NeedsAttachmentViewerMixin, NeedsSelectionMixin
):
    """Mixin class for UI commands that need at least one selected
    attachment."""

    pass


class NeedsAtLeastOneTaskMixin(object):
    """Mixin class for UI commands that need at least one task created."""

    def enabled(self, event):  # pylint: disable=W0613
        return len(self.taskList) > 0


class NeedsAtLeastOneCategoryMixin(object):
    """Mixin class for UI commands that need at least one category created."""

    def enabled(self, event):  # pylint: disable=W0613
        return len(self.categories) > 0


class NeedsItemsMixin(object):
    """Mixin class for UI commands that need at least one item in their
    viewer."""

    def enabled(self, event):  # pylint: disable=W0613
        return self.viewer.size()


class NeedsTreeViewerMixin(object):
    """Mixin class for UI commands that need a tree viewer."""

    def enabled(self, event):
        return super().enabled(event) and self.viewer.isTreeViewer()


class NeedsDeletedItemsMixin(object):
    """Mixin class for UI commands that need deleted items to be present."""

    def enabled(self, event):
        return super().enabled(event) and self.iocontroller.hasDeletedItems()


class PopupButtonMixin(object):
    """Mix this with a UICommand for a toolbar pop-up menu."""

    def doCommand(self, event):  # pylint: disable=W0613
        try:
            args = [self.__menu]
        except AttributeError:
            self.__menu = self.createPopupMenu()  # pylint: disable=W0201
            args = [self.__menu]

        # Check if menu has any items
        if self.__menu.GetMenuItemCount() == 0:
            wx.MessageBox(
                _("No templates available. Create a template first by saving a task as a template."),
                _("No Templates"),
                wx.OK | wx.ICON_INFORMATION,
                self.mainWindow()
            )
            return

        if self.toolbar:
            args.append(self.menuXY())
        self.mainWindow().PopupMenu(*args)  # pylint: disable=W0142

    def menuXY(self):
        """Location to pop up the menu."""
        return self.mainWindow().ScreenToClient((self.menuX(), self.menuY()))

    def menuX(self):
        # Get the tool's position in the toolbar
        toolRect = self.toolbar.GetToolRect(self.id)
        if toolRect is not None:
            # Convert toolbar-local position to screen coordinates
            toolbarScreenPos = self.toolbar.GetScreenPosition()
            # Align to the left edge of the button
            return toolbarScreenPos[0] + toolRect[0]
        else:
            # Fallback to mouse position if tool rect not available
            buttonWidth = self.toolbar.GetToolSize()[0]
            mouseX = wx.GetMousePosition()[0]
            return mouseX - 0.5 * buttonWidth

    def menuY(self):
        toolbarY = self.toolbar.GetScreenPosition()[1]
        toolbarHeight = self.toolbar.GetSize()[1]
        return toolbarY + toolbarHeight

    def createPopupMenu(self):
        raise NotImplementedError  # pragma: no cover
