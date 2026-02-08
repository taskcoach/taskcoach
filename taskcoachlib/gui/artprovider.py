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

from taskcoachlib import patterns, operating_system
from taskcoachlib.i18n import _
from taskcoachlib.tools import wxhelper
from taskcoachlib.gui.icons import icon_library
import numpy as np
import wx
import os
import sys


def get_resource_path(relative_path):
    """Get absolute path to resource - works for development and frozen apps."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller stores resources in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Development, py2app, py2exe: use module's directory
        # py2app/py2exe extract packages so __file__ works correctly
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


class ArtProvider(wx.ArtProvider):
    def CreateBitmap(self, id, client, size):
        # Try catalog lookup first
        is_cataloged = id in chooseableItems
        if not is_cataloged:
            # Legacy fallback: check for overlay pattern "main+overlay"
            # TODO 3: Refactor this hack - see docs/ICON_LIBRARY.md
            if "+" in id:
                parts = id.split("+")
                if len(parts) == 2 and parts[0] in chooseableItems and parts[1] in chooseableItems:
                    return self._CreateOverlayBitmap(parts[0], parts[1], client, size)

        return self._CreateBitmap(id, client, size)

    def _CreateOverlayBitmap(self, main, overlay, client, size):
        width, height = size

        # Create overlay image
        overlay_image = self._CreateBitmap(
            overlay, client, size
        ).ConvertToImage()
        overlay_image.Rescale(width // 2, height // 2, wx.IMAGE_QUALITY_HIGH)

        # Create main image and preserve its original alpha
        main_image = self._CreateBitmap(main, client, size).ConvertToImage()

        # Ensure both images have alpha channels
        if not main_image.HasAlpha():
            main_image.InitAlpha()
        if not overlay_image.HasAlpha():
            overlay_image.InitAlpha()

        # Save the original alpha channel of the main image
        original_main_alpha = wxhelper.getAlphaDataFromImage(main_image).copy()

        # Convert to bitmap for drawing the overlay
        main_bitmap = main_image.ConvertToBitmap()

        # Draw overlay image on top
        with wx.MemoryDC(main_bitmap) as dc:
            dc.DrawBitmap(
                overlay_image.ConvertToBitmap(), width // 2, height // 2, True
            )

        # Convert back to image and merge alpha channels properly
        result_image = main_bitmap.ConvertToImage()

        # Merge the original main alpha with the overlay alpha
        result_image = wxhelper.mergeImagesWithAlpha(
            result_image, overlay_image, (width // 2, height // 2)
        )

        # Restore the original main image's alpha in the non-overlay area
        main_width, main_height = main_image.GetWidth(), main_image.GetHeight()
        overlay_width, overlay_height = overlay_image.GetWidth(), overlay_image.GetHeight()
        overlay_x, overlay_y = width // 2, height // 2
        y_end = min(overlay_y + overlay_height, main_height)
        x_end = min(overlay_x + overlay_width, main_width)

        result_alpha = wxhelper.getAlphaDataFromImage(result_image).copy()
        result_alpha_2d = result_alpha.reshape(main_height, main_width)
        original_alpha_2d = original_main_alpha.reshape(main_height, main_width)

        mask = np.ones((main_height, main_width), dtype=bool)
        mask[overlay_y:y_end, overlay_x:x_end] = False
        result_alpha_2d[mask] = original_alpha_2d[mask]

        wxhelper.setAlphaDataToImage(result_image, result_alpha_2d)

        return result_image.ConvertToBitmap()

    # Art ID for a transparent placeholder bitmap (real bitmap object with
    # alpha=0). Needed where a wx.Bitmap object is required but should appear
    # empty — e.g. icon picker "No icon" option, toolbar image list slots.
    # NOTE: This may no longer be needed if all callers can handle
    # wx.NullBitmap. Check icon picker and toolbar customization dialog.
    TRANSPARENT_EMPTY_ICON = "transparent_empty_icon"

    def _CreateBitmap(self, artId, artClient, size) -> wx.Bitmap:
        if not artId:
            return wx.NullBitmap

        if artId == self.TRANSPARENT_EMPTY_ICON:
            img = wx.Image(*size)
            img.InitAlpha()
            return img.ConvertToBitmap()

        icon_path = None
        icon_size = size[0]  # Assume square icons

        # Check if this is a theme icon (has theme/category/file in chooseableItems)
        icon_data = chooseableItems.get(artId)
        if icon_data and "theme" in icon_data and "file" in icon_data:
            theme = icon_data["theme"]
            category = icon_data.get("category", "")
            filename = icon_data["file"]
            icon_path = icon_library.build_icon_path(theme, category, filename, icon_size)

        if not icon_path or not os.path.exists(icon_path):
            # Legacy icon: try new format first, then flat format
            size_dir = "%dx%d" % (size[0], size[1])
            new_icon_path = get_resource_path(
                os.path.join('icons', size_dir, artId + '.png')
            )
            if os.path.exists(new_icon_path):
                icon_path = new_icon_path
            else:
                # Fall back to legacy flat format: "iconname16x16.png"
                legacy_icon_path = get_resource_path(
                    os.path.join('icons', "%s%dx%d.png" % (artId, size[0], size[1]))
                )
                if os.path.exists(legacy_icon_path):
                    icon_path = legacy_icon_path

        if icon_path and os.path.exists(icon_path):
            image = wx.Image(icon_path)
            if not image.IsOk():
                from taskcoachlib.meta.debug import log_step
                log_step(f"ERROR: Failed to load image: {icon_path}", prefix="ICON")
                return wx.NullBitmap
            bitmap = image.ConvertToBitmap()
            if artClient == wx.ART_FRAME_ICON:
                bitmap = self.convertAlphaToMask(bitmap)
            return bitmap

        # Log error if icon not found
        from taskcoachlib.meta.debug import log_step
        log_step(f"ERROR: Icon file not found for artId='{artId}' size={size}", prefix="ICON")
        return wx.NullBitmap

    @staticmethod
    def convertAlphaToMask(bitmap):
        # wxPython Phoenix: use bitmap method instead of module function
        image = bitmap.ConvertToImage()
        image.ConvertAlphaToMask()
        # wxPython Phoenix: use wx.Bitmap constructor instead of wx.BitmapFromImage
        return wx.Bitmap(image)


class IconProvider(object, metaclass=patterns.Singleton):
    def __init__(self):
        self.__iconCache = dict()
        if operating_system.isMac():
            self.__iconSizeOnCurrentPlatform = 128
        elif operating_system.isGTK():
            self.__iconSizeOnCurrentPlatform = 48
        else:
            self.__iconSizeOnCurrentPlatform = 16

    def getIcon(self, iconTitle):
        """Return the icon. Use a cache to prevent leakage of GDI object
        count."""
        try:
            return self.__iconCache[iconTitle]
        except KeyError:
            icon = self.getIconFromArtProvider(iconTitle)
            self.__iconCache[iconTitle] = icon
            return icon

    def iconBundle(self, iconTitle):
        """Create an icon bundle with icons of different sizes."""
        bundle = wx.IconBundle()
        for size in (16, 22, 32, 48, 64, 128):
            bundle.AddIcon(self.getIconFromArtProvider(iconTitle, size))
        return bundle

    def getIconFromArtProvider(self, iconTitle, iconSize=None):
        size = iconSize or self.__iconSizeOnCurrentPlatform
        # I just spent two hours trying to get rid of garbage in the icon
        # background on KDE. I give up.
        if operating_system.isGTK():
            return wx.ArtProvider.GetIcon(
                iconTitle, wx.ART_FRAME_ICON, (size, size)
            )

        # wx.ArtProvider.GetIcon doesn't convert alpha to mask, so we do it
        # ourselves:
        bitmap = wx.ArtProvider.GetBitmap(
            iconTitle, wx.ART_FRAME_ICON, (size, size)
        )
        bitmap = ArtProvider.convertAlphaToMask(bitmap)
        # wxPython Phoenix: use wx.Icon constructor instead of wx.IconFromBitmap
        return wx.Icon(bitmap)


def iconBundle(iconTitle):
    return IconProvider().iconBundle(iconTitle)


def getIcon(iconTitle):
    return IconProvider().getIcon(iconTitle)


def init():
    if operating_system.isWindows() and wx.DisplayDepth() >= 32:
        # wxPython 4.1+ uses wx.SystemOptions.SetOption (class method)
        # Older versions used wx.SystemOptions_SetOption (module function)
        try:
            wx.SystemOptions.SetOption("msw.remap", "0")  # pragma: no cover
        except AttributeError:
            wx.SystemOptions_SetOption("msw.remap", "0")  # pragma: no cover
    try:
        wx.ArtProvider.PushProvider(ArtProvider())  # pylint: disable=E1101
    except AttributeError:
        wx.ArtProvider.Push(ArtProvider())


# Combined icon data: name and hints in a single structure
# Hints are arrays of translatable terms for search functionality
# "No icon" is handled by IconPicker widget via noIcon parameter
chooseableItems = {
    # Arrows and navigation
    "arrow_down_icon": {
        "label": _("Arrow - Down"),
        "hints": [_("download"), _("below"), _("descend"), _("lower"), _("next")],
    },
    "arrow_down_with_status_icon": {
        "label": _("Arrow - Down with status"),
        "hints": [_("download"), _("below"), _("descend"), _("lower"), _("next"), _("status")],
    },
    "arrow_forward_icon": {
        "label": _("Arrow - Forward"),
        "hints": [_("next"), _("continue"), _("proceed"), _("right"), _("go")],
    },
    "arrows_looped_blue_icon": {
        "label": _("Arrows looped - Blue"),
        "hints": [_("sync"), _("refresh"), _("cycle"), _("repeat"), _("reload"), _("recurrence"), _("recurring")],
    },
    "arrows_looped_green_icon": {
        "label": _("Arrows looped - Green"),
        "hints": [_("sync"), _("refresh"), _("cycle"), _("repeat"), _("reload"), _("recurrence"), _("recurring")],
    },
    "arrow_up_icon": {
        "label": _("Arrow - Up"),
        "hints": [_("upload"), _("above"), _("ascend"), _("raise"), _("previous")],
    },
    "arrow_up_with_status_icon": {
        "label": _("Arrow - Up with status"),
        "hints": [_("upload"), _("above"), _("ascend"), _("raise"), _("previous"), _("status")],
    },

    # Attachments and files
    "attach_icon": {
        "label": _("Attachment"),
        "hints": [_("attachment"), _("paperclip"), _("file"), _("document"), _("clip"), _("fasten")],
    },

    # Time and scheduling
    "bell_icon": {
        "label": _("Bell"),
        "hints": [_("alarm"), _("notification"), _("alert"), _("reminder"), _("ring"), _("wake")],
    },
    "bomb_icon": {
        "label": _("Bomb"),
        "hints": [_("danger"), _("urgent"), _("explosive"), _("critical"), _("warning"), _("deadline")],
    },
    "book_icon": {
        "label": _("Book"),
        "hints": [_("read"), _("document"), _("manual"), _("guide"), _("reference"), _("study"), _("learn")],
    },
    "bookmark_icon": {
        "label": _("Bookmark"),
        "hints": [_("favorite"), _("save"), _("mark"), _("remember"), _("reference"), _("link")],
    },
    "books_icon": {
        "label": _("Books"),
        "hints": [_("read"), _("documents"), _("manuals"), _("guides"), _("library"), _("collection")],
    },
    "box_icon": {
        "label": _("Box"),
        "hints": [_("package"), _("container"), _("storage"), _("shipping"), _("delivery")],
    },
    "briefcase_icon": {
        "label": _("Briefcase"),
        "hints": [_("work"), _("business"), _("professional"), _("portfolio"), _("job"), _("office")],
    },
    "bug_icon": {
        "label": _("Ladybug"),
        "hints": [_("ladybug"), _("insect"), _("debug"), _("error"), _("problem"), _("issue")],
    },
    "cake_icon": {
        "label": _("Cake"),
        "hints": [_("birthday"), _("celebration"), _("party"), _("anniversary"), _("event")],
    },
    "calculator_icon": {
        "label": _("Calculator"),
        "hints": [_("math"), _("calculate"), _("compute"), _("numbers"), _("finance"), _("accounting")],
    },
    "calendar_icon": {
        "label": _("Calendar"),
        "hints": [_("date"), _("schedule"), _("appointment"), _("event"), _("planner"), _("day"), _("month"), _("year"), _("deadline"), _("due")],
    },
    "camera_icon": {
        "label": _("Camera"),
        "hints": [_("photo"), _("picture"), _("image"), _("capture"), _("screenshot"), _("media")],
    },
    "cat_icon": {
        "label": _("Cat"),
        "hints": [_("pet"), _("animal"), _("feline"), _("meow"), _("kitty")],
    },
    "cd_icon": {
        "label": _("Compact disc (CD)"),
        "hints": [_("disc"), _("music"), _("media"), _("backup"), _("storage")],
    },
    "charts_icon": {
        "label": _("Charts"),
        "hints": [_("graph"), _("statistics"), _("data"), _("analytics"), _("report"), _("metrics")],
    },
    "chat_icon": {
        "label": _("Chat"),
        "hints": [_("message"), _("talk"), _("conversation"), _("discuss"), _("communicate")],
    },
    "checkmark_green_icon": {
        "label": _("Check mark"),
        "hints": [_("done"), _("complete"), _("finished"), _("success"), _("yes"), _("approve"), _("accept")],
    },
    "checkmark_green_icon_multiple": {
        "label": _("Check marks"),
        "hints": [_("done"), _("complete"), _("finished"), _("success"), _("batch"), _("multiple")],
    },
    "clock_icon": {
        "label": _("Clock"),
        "hints": [_("time"), _("hour"), _("minute"), _("watch"), _("schedule"), _("duration")],
    },
    "clock_alarm_icon": {
        "label": _("Clock - Alarm"),
        "hints": [_("time"), _("alarm"), _("reminder"), _("wake"), _("alert"), _("notification"), _("deadline")],
    },
    "clock_stopwatch_icon": {
        "label": _("Clock - Stopwatch"),
        "hints": [_("time"), _("timer"), _("countdown"), _("measure"), _("track"), _("duration")],
    },
    "cogwheel_icon": {
        "label": _("Cogwheel"),
        "hints": [_("settings"), _("config"), _("gear"), _("preferences"), _("options"), _("setup")],
    },
    "cogwheels_icon": {
        "label": _("Cogwheels"),
        "hints": [_("settings"), _("config"), _("gears"), _("preferences"), _("options"), _("setup"), _("system")],
    },
    "contact_card_icon": {
        "label": _("Contact card"),
        "hints": [_("vcard"), _("address"), _("business card"), _("profile"), _("person")],
    },
    "cookie_icon": {
        "label": _("Cookie"),
        "hints": [_("treat"), _("reward"), _("snack"), _("food"), _("biscuit"), _("sweet")],
    },
    "computer_desktop_icon": {
        "label": _("Computer - Desktop"),
        "hints": [_("pc"), _("workstation"), _("monitor"), _("screen"), _("computer"), _("desktop")],
    },
    "computer_laptop_icon": {
        "label": _("Computer - Laptop"),
        "hints": [_("notebook"), _("portable"), _("pc"), _("mobile"), _("computer"), _("laptop")],
    },
    "computer_handheld_icon": {
        "label": _("Computer - Handheld"),
        "hints": [_("mobile"), _("phone"), _("pda"), _("tablet"), _("device")],
    },
    "cross_red_icon": {
        "label": _("Cross - Red"),
        "hints": [_("error"), _("cancel"), _("close"), _("delete"), _("stop"), _("reject"), _("no"), _("remove")],
    },
    "die_icon": {
        "label": _("Die"),
        "hints": [_("dice"), _("random"), _("game"), _("luck"), _("chance")],
    },
    "document_icon": {
        "label": _("Document"),
        "hints": [_("file"), _("paper"), _("text"), _("note"), _("write"), _("report")],
    },
    "earth_blue_icon": {
        "label": _("Earth - Blue"),
        "hints": [_("world"), _("globe"), _("planet"), _("international"), _("global"), _("web")],
    },
    "earth_green_icon": {
        "label": _("Earth - Green"),
        "hints": [_("world"), _("globe"), _("planet"), _("environment"), _("nature"), _("eco")],
    },
    "energy_icon": {
        "label": _("Energy"),
        "hints": [_("power"), _("electricity"), _("lightning"), _("bolt"), _("charge"), _("battery")],
    },
    "envelope_icon": {
        "label": _("Envelope"),
        "hints": [_("mail"), _("email"), _("message"), _("letter"), _("send"), _("receive"), _("inbox")],
    },
    "error_icon": {
        "label": _("Error"),
        "hints": [_("warning"), _("problem"), _("issue"), _("fail"), _("failure"), _("bug"), _("mistake")],
    },
    "envelopes_icon": {
        "label": _("Envelopes"),
        "hints": [_("mail"), _("email"), _("messages"), _("letters"), _("inbox"), _("batch")],
    },
    "file_important_icon": {
        "label": _("File - Important"),
        "hints": [_("document"), _("priority"), _("urgent"), _("attention"), _("critical"), _("star")],
    },
    "file_locked_icon": {
        "label": _("File - Locked"),
        "hints": [_("document"), _("secure"), _("protected"), _("private"), _("locked"), _("secret")],
    },
    "folder_blue_icon": {
        "label": _("Folder - Blue"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_blue_light_icon": {
        "label": _("Folder - Light blue"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_green_icon": {
        "label": _("Folder - Green"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_grey_icon": {
        "label": _("Folder - Grey"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize"), _("archive")],
    },
    "folder_orange_icon": {
        "label": _("Folder - Orange"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_purple_icon": {
        "label": _("Folder - Purple"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_red_icon": {
        "label": _("Folder - Red"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize"), _("important"), _("urgent")],
    },
    "folder_yellow_icon": {
        "label": _("Folder - Yellow"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_blue_arrow_icon": {
        "label": _("Folder - Blue with arrow"),
        "hints": [_("directory"), _("storage"), _("files"), _("move"), _("transfer")],
    },
    "folder_favorite_icon": {
        "label": _("Folder - Favorite"),
        "hints": [_("directory"), _("storage"), _("star"), _("bookmark"), _("best"), _("preferred")],
    },
    "folder_important_icon": {
        "label": _("Folder - Important"),
        "hints": [_("directory"), _("storage"), _("priority"), _("urgent"), _("attention"), _("critical")],
    },
    "fsview_icon": {
        "label": _("Color swatches"),
        "hints": [_("color"), _("swatches"), _("palette"), _("design"), _("theme")],
    },
    "graph_icon": {
        "label": _("Graph"),
        "hints": [_("chart"), _("statistics"), _("data"), _("analytics"), _("plot"), _("diagram")],
    },
    "heart_icon": {
        "label": _("Heart"),
        "hints": [_("love"), _("favorite"), _("like"), _("health"), _("wellness")],
    },
    "hearts_icon": {
        "label": _("Hearts"),
        "hints": [_("love"), _("favorites"), _("likes"), _("health"), _("wellness")],
    },
    "house_green_icon": {
        "label": _("House - Green"),
        "hints": [_("home"), _("residence"), _("building"), _("dwelling"), _("personal")],
    },
    "house_red_icon": {
        "label": _("House - Red"),
        "hints": [_("home"), _("residence"), _("building"), _("dwelling"), _("urgent")],
    },
    "key_icon": {
        "label": _("Key"),
        "hints": [_("lock"), _("security"), _("password"), _("access"), _("unlock"), _("credential")],
    },
    "keys_icon": {
        "label": _("Keys"),
        "hints": [_("locks"), _("security"), _("passwords"), _("access"), _("unlock"), _("credentials")],
    },
    "lamp_icon": {
        "label": _("Lamp"),
        "hints": [_("light"), _("idea"), _("bulb"), _("bright"), _("illuminate"), _("thought")],
    },
    "led_blue_questionmark_icon": {
        "label": _("Question mark"),
        "hints": [_("question"), _("help"), _("unknown"), _("ask"), _("uncertain")],
    },
    "led_blue_information_icon": {
        "label": _("Information"),
        "hints": [_("info"), _("information"), _("details"), _("about"), _("help")],
    },
    "led_blue_icon": {
        "label": _("LED - Blue"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("online"), _("active")],
    },
    "led_blue_light_icon": {
        "label": _("LED - Light blue"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("online"), _("active")],
    },
    "led_grey_icon": {
        "label": _("LED - Grey"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("inactive"), _("disabled"), _("off")],
    },
    "led_green_icon": {
        "label": _("LED - Green"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("ok"), _("active"), _("go"), _("done")],
    },
    "led_green_light_icon": {
        "label": _("LED - Light green"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("ok"), _("active"), _("go"), _("done")],
    },
    "led_orange_icon": {
        "label": _("LED - Orange"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("warning"), _("caution")],
    },
    "led_purple_icon": {
        "label": _("LED - Purple"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("special"), _("custom")],
    },
    "led_red_icon": {
        "label": _("LED - Red"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("error"), _("stop"), _("offline"), _("failed")],
    },
    "led_yellow_icon": {
        "label": _("LED - Yellow"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("warning"), _("pause"), _("attention")],
    },
    "life_ring_icon": {
        "label": _("Life ring"),
        "hints": [_("help"), _("support"), _("rescue"), _("assist"), _("safety"), _("emergency")],
    },
    "lock_locked_icon": {
        "label": _("Lock - Locked"),
        "hints": [_("secure"), _("private"), _("protected"), _("closed"), _("secret")],
    },
    "lock_unlocked_icon": {
        "label": _("Lock - Unlocked"),
        "hints": [_("open"), _("access"), _("public"), _("unlocked"), _("available")],
    },
    "magnifier_glass_icon": {
        "label": _("Magnifier glass"),
        "hints": [_("search"), _("find"), _("zoom"), _("look"), _("inspect"), _("explore")],
    },
    "music_piano_icon": {
        "label": _("Music - Piano"),
        "hints": [_("piano"), _("keyboard"), _("music"), _("instrument"), _("play")],
    },
    "music_note_icon": {
        "label": _("Music - Note"),
        "hints": [_("music"), _("sound"), _("audio"), _("melody"), _("song"), _("tune")],
    },
    "note_icon": {
        "label": _("Note"),
        "hints": [_("sticky"), _("memo"), _("reminder"), _("post-it"), _("write")],
    },
    "palette_icon": {
        "label": _("Palette"),
        "hints": [_("color"), _("art"), _("design"), _("paint"), _("creative")],
    },
    "paperclip_icon": {
        "label": _("Paperclip"),
        "hints": [_("attach"), _("attachment"), _("file"), _("document"), _("clip")],
    },
    "password_icon": {
        "label": _("Password"),
        "hints": [_("security"), _("credential"), _("secret"), _("key"), _("login"), _("authenticate")],
    },
    "pencil_icon": {
        "label": _("Pencil"),
        "hints": [_("edit"), _("write"), _("draw"), _("modify"), _("change"), _("update")],
    },
    "person_icon": {
        "label": _("Person"),
        "hints": [_("user"), _("account"), _("profile"), _("member"), _("contact"), _("individual")],
    },
    "persons_icon": {
        "label": _("People"),
        "hints": [_("users"), _("people"), _("team"), _("group"), _("members"), _("contacts")],
    },
    "person_id_icon": {
        "label": _("Person - ID"),
        "hints": [_("user"), _("identity"), _("card"), _("profile"), _("badge"), _("employee")],
    },
    "person_talking_icon": {
        "label": _("Person - Talking"),
        "hints": [_("speak"), _("talk"), _("discuss"), _("communicate"), _("voice"), _("call")],
    },
    "printer_icon": {
        "label": _("Printer"),
        "hints": [_("print"), _("output"), _("paper"), _("document"), _("hardcopy")],
    },
    "reload_icon": {
        "label": _("Reload"),
        "hints": [_("refresh"), _("update"), _("sync"), _("repeat"), _("restart"), _("renew")],
    },
    "remote_icon": {
        "label": _("Remote"),
        "hints": [_("control"), _("wireless"), _("distance"), _("network"), _("access")],
    },
    "run_icon": {
        "label": _("Run"),
        "hints": [_("execute"), _("start"), _("play"), _("begin"), _("go"), _("launch"), _("sprint")],
    },
    "science_icon": {
        "label": _("Science"),
        "hints": [_("lab"), _("experiment"), _("research"), _("chemistry"), _("biology")],
    },
    "sign_important_icon": {
        "label": _("Sign - Important"),
        "hints": [_("warning"), _("attention"), _("urgent"), _("priority"), _("exclamation"), _("alert")],
    },
    "symbol_minus_icon": {
        "label": _("Symbol - Minus"),
        "hints": [_("subtract"), _("remove"), _("decrease"), _("less"), _("reduce")],
    },
    "symbol_plus_icon": {
        "label": _("Symbol - Plus"),
        "hints": [_("add"), _("create"), _("increase"), _("more"), _("expand")],
    },
    "star_red_icon": {
        "label": _("Star - Red"),
        "hints": [_("favorite"), _("important"), _("priority"), _("rating"), _("bookmark"), _("urgent"), _("critical")],
    },
    "star_yellow_icon": {
        "label": _("Star - Yellow"),
        "hints": [_("favorite"), _("important"), _("priority"), _("rating"), _("bookmark"), _("best")],
    },
    "sticky_note_icon": {
        "label": _("Sticky note"),
        "hints": [_("memo"), _("reminder"), _("post-it"), _("note"), _("yellow"), _("paper")],
    },
    "tea_icon": {
        "label": _("Tea"),
        "hints": [_("break"), _("rest"), _("relax"), _("pause"), _("coffee"), _("drink"), _("beverage")],
    },
    "terminal_icon": {
        "label": _("Terminal"),
        "hints": [_("command"), _("console"), _("shell"), _("code"), _("developer")],
    },
    "timer_icon": {
        "label": _("Timer"),
        "hints": [_("countdown"), _("time"), _("limit"), _("duration"), _("stopwatch"), _("deadline")],
    },
    "trafficlight_icon": {
        "label": _("Traffic light"),
        "hints": [_("status"), _("priority"), _("waiting"), _("proceed"), _("stop")],
    },
    "traffic_go_icon": {
        "label": _("Traffic - Go"),
        "hints": [_("proceed"), _("start"), _("green light"), _("continue"), _("execute")],
    },
    "trashcan_icon": {
        "label": _("Trashcan"),
        "hints": [_("delete"), _("remove"), _("garbage"), _("bin"), _("recycle"), _("discard")],
    },
    "weather_lightning_icon": {
        "label": _("Weather - Lightning"),
        "hints": [_("storm"), _("thunder"), _("electric"), _("power"), _("urgent"), _("fast")],
    },
    "weather_umbrella_icon": {
        "label": _("Weather - Umbrella"),
        "hints": [_("rain"), _("protection"), _("shelter"), _("weather"), _("umbrella"), _("wet")],
    },
    "weather_sunny_icon": {
        "label": _("Weather - Partly sunny"),
        "hints": [_("sun"), _("bright"), _("day"), _("clear"), _("good"), _("positive")],
    },
    "wizard_icon": {
        "label": _("Wizard"),
        "hints": [_("magic"), _("helper"), _("assistant"), _("guide"), _("setup")],
    },
    "wrench_icon": {
        "label": _("Wrench"),
        "hints": [_("tool"), _("settings"), _("config"), _("repair"), _("fix"), _("maintenance"), _("service")],
    },
    # Bank/Accounting icons (Papirus) - new format without _icon suffix
    "bank_account": {
        "label": _("Bank Account"),
        "hints": [_("bank"), _("account"), _("checking"), _("savings"), _("finance"), _("institution")],
    },
    "money_budget": {
        "label": _("Money Budget"),
        "hints": [_("money"), _("budget"), _("finance"), _("coins"), _("piggybank"), _("savings"), _("personal")],
    },
    "taxes": {
        "label": _("Taxes"),
        "hints": [_("tax"), _("taxes"), _("money"), _("dollar"), _("cash"), _("government"), _("irs"), _("percent"), _("form")],
    },
    "currency_dollar": {
        "label": _("Currency"),
        "hints": [_("currency"), _("dollar"), _("money"), _("symbol"), _("usd"), _("format"), _("price")],
    },
    "calculator_flat": {
        "label": _("Calculator (Flat)"),
        "hints": [_("calculator"), _("math"), _("compute"), _("calculate"), _("numbers"), _("flat"), _("modern")],
    },
    "uno_calculator": {
        "label": _("Calculator (Uno)"),
        "hints": [_("calculator"), _("math"), _("uno"), _("compute"), _("blue"), _("numbers"), _("arithmetic")],
    },
    "gnome_calculator": {
        "label": _("Calculator (GNOME)"),
        "hints": [_("calculator"), _("math"), _("gnome"), _("compute"), _("colorful"), _("numbers"), _("arithmetic")],
    },
    "safe_vault": {
        "label": _("Safe"),
        "hints": [_("safe"), _("vault"), _("secure"), _("lock"), _("storage"), _("protect"), _("valuables")],
    },
    "bitcoin": {
        "label": _("Bitcoin"),
        "hints": [_("bitcoin"), _("crypto"), _("cryptocurrency"), _("digital"), _("btc"), _("blockchain")],
    },
    "wallet_flat": {
        "label": _("Wallet (Flat)"),
        "hints": [_("wallet"), _("billfold"), _("money"), _("cash"), _("flat"), _("modern")],
    },
    "money_expense": {
        "label": _("Money Expense"),
        "hints": [_("expense"), _("money"), _("spending"), _("budget"), _("track"), _("manager"), _("receipt")],
    },
    # Bank/Accounting apps (Papirus)
    "homebank": {
        "label": _("HomeBank"),
        "hints": [_("home"), _("bank"), _("finance"), _("budget"), _("personal"), _("accounting")],
    },
    "cointop": {
        "label": _("CoinTop"),
        "hints": [_("crypto"), _("cryptocurrency"), _("terminal"), _("bitcoin"), _("portfolio"), _("tracker")],
    },
    "cryptomator": {
        "label": _("Cryptomator"),
        "hints": [_("encrypt"), _("security"), _("vault"), _("cloud"), _("privacy"), _("lock")],
    },
    "banking": {
        "label": _("Banking"),
        "hints": [_("bank"), _("credit"), _("card"), _("finance"), _("payment"), _("account")],
    },
    "safeeyes": {
        "label": _("Safe Eyes"),
        "hints": [_("break"), _("rest"), _("health"), _("eye"), _("reminder"), _("timer")],
    },
    "kmymoney": {
        "label": _("KMyMoney"),
        "hints": [_("money"), _("finance"), _("personal"), _("budget"), _("accounting"), _("kde")],
    },
    "money_manager": {
        "label": _("Money Manager"),
        "hints": [_("money"), _("expense"), _("manager"), _("budget"), _("track"), _("finance")],
    },
    "moneydance": {
        "label": _("Moneydance"),
        "hints": [_("money"), _("finance"), _("personal"), _("budget"), _("banking"), _("investment")],
    },
    # Bank/Accounting icons (Oxygen) - new format without _icon suffix
    "bank_building": {
        "label": _("Bank Building"),
        "hints": [_("bank"), _("building"), _("institution"), _("columns"), _("finance"), _("classic")],
    },
    "wallet_closed": {
        "label": _("Wallet (Closed)"),
        "hints": [_("wallet"), _("closed"), _("locked"), _("secure"), _("billfold"), _("leather")],
    },
    "wallet_open": {
        "label": _("Wallet (Open)"),
        "hints": [_("wallet"), _("open"), _("money"), _("cash"), _("billfold"), _("spend")],
    },
    "calculator_3d": {
        "label": _("Calculator (3D)"),
        "hints": [_("calculator"), _("math"), _("compute"), _("calculate"), _("classic"), _("3d")],
    },
    "wallet_keys": {
        "label": _("Wallet Keys"),
        "hints": [_("wallet"), _("keys"), _("password"), _("secure"), _("manager"), _("keyring")],
    },
    "cactus": {
        "label": _("Cactus"),
        "hints": [_("cactus"), _("plant"), _("desert"), _("green"), _("nature"), _("succulent")],
    },
}


# Load theme icons and merge into chooseableItems
for _theme in ["nuvola"]:  # Add more themes as they are imported
    chooseableItems.update(icon_library.get_chooseable_icons(_theme))


itemImages = list(chooseableItems.keys()) + [
    "folder_blue_open_icon",
    "folder_green_open_icon",
    "folder_grey_open_icon",
    "folder_orange_open_icon",
    "folder_red_open_icon",
    "folder_purple_open_icon",
    "folder_yellow_open_icon",
    "folder_blue_light_open_icon",
]
