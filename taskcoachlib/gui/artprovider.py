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
from taskcoachlib.meta.debug import log_step
from taskcoachlib.tools import wxhelper
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
        if "+" not in id:
            return self._CreateBitmap(id, client, size)

        width, height = size
        main, overlay = id.split("+")

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
        original_main_alpha = wxhelper.getAlphaDataFromImage(main_image, as_numpy=True).copy()

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

        result_alpha = wxhelper.getAlphaDataFromImage(result_image, as_numpy=True).copy()
        result_alpha_2d = result_alpha.reshape(main_height, main_width)
        original_alpha_2d = original_main_alpha.reshape(main_height, main_width)

        # Restore original alpha for non-overlay regions
        import numpy as np
        mask = np.ones((main_height, main_width), dtype=bool)
        y_end = min(overlay_y + overlay_height, main_height)
        x_end = min(overlay_x + overlay_width, main_width)
        mask[overlay_y:y_end, overlay_x:x_end] = False
        result_alpha_2d[mask] = original_alpha_2d[mask]

        wxhelper.setAlphaDataToImage(result_image, result_alpha_2d)

        return result_image.ConvertToBitmap()

    def _CreateBitmap(self, artId, artClient, size) -> wx.Bitmap:
        if not artId:
            return wx.Bitmap(*size)

        # Try new format first: "16x16/iconname.png" (size-based directories)
        size_dir = "%dx%d" % (size[0], size[1])
        new_icon_path = get_resource_path(
            os.path.join('icons', size_dir, artId + '.png')
        )

        # Fall back to legacy format: "iconname16x16.png" (flat with size suffix)
        legacy_icon_path = get_resource_path(
            os.path.join('icons', "%s%dx%d.png" % (artId, size[0], size[1]))
        )

        # Use new format if exists, otherwise legacy
        icon_path = new_icon_path if os.path.exists(new_icon_path) else legacy_icon_path

        if os.path.exists(icon_path):
            image = wx.Image(icon_path)
            if not image.IsOk():
                log_step("ERROR! Icon file exists but failed to load:", icon_path, prefix="ICON")
                return wx.NullBitmap
            bitmap = image.ConvertToBitmap()
            if artClient == wx.ART_FRAME_ICON:
                bitmap = self.convertAlphaToMask(bitmap)
            return bitmap
        else:
            log_step("ERROR! Icon not found:", repr(artId), "(tried", new_icon_path, "and", legacy_icon_path + ")", prefix="ICON")
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
        "name": _("Arrow - Down"),
        "hints": [_("download"), _("below"), _("descend"), _("lower"), _("next")],
    },
    "arrow_down_with_status_icon": {
        "name": _("Arrow - Down with status"),
        "hints": [_("download"), _("below"), _("descend"), _("lower"), _("next"), _("status")],
    },
    "arrow_forward_icon": {
        "name": _("Arrow - Forward"),
        "hints": [_("next"), _("continue"), _("proceed"), _("right"), _("go")],
    },
    "arrows_looped_blue_icon": {
        "name": _("Arrows looped - Blue"),
        "hints": [_("sync"), _("refresh"), _("cycle"), _("repeat"), _("reload"), _("recurrence"), _("recurring")],
    },
    "arrows_looped_green_icon": {
        "name": _("Arrows looped - Green"),
        "hints": [_("sync"), _("refresh"), _("cycle"), _("repeat"), _("reload"), _("recurrence"), _("recurring")],
    },
    "arrow_up_icon": {
        "name": _("Arrow - Up"),
        "hints": [_("upload"), _("above"), _("ascend"), _("raise"), _("previous")],
    },
    "arrow_up_with_status_icon": {
        "name": _("Arrow - Up with status"),
        "hints": [_("upload"), _("above"), _("ascend"), _("raise"), _("previous"), _("status")],
    },

    # Attachments and files
    "attach_icon": {
        "name": _("Attachment"),
        "hints": [_("attachment"), _("paperclip"), _("file"), _("document"), _("clip"), _("fasten")],
    },

    # Time and scheduling
    "bell_icon": {
        "name": _("Bell"),
        "hints": [_("alarm"), _("notification"), _("alert"), _("reminder"), _("ring"), _("wake")],
    },
    "bomb_icon": {
        "name": _("Bomb"),
        "hints": [_("danger"), _("urgent"), _("explosive"), _("critical"), _("warning"), _("deadline")],
    },
    "book_icon": {
        "name": _("Book"),
        "hints": [_("read"), _("document"), _("manual"), _("guide"), _("reference"), _("study"), _("learn")],
    },
    "bookmark_icon": {
        "name": _("Bookmark"),
        "hints": [_("favorite"), _("save"), _("mark"), _("remember"), _("reference"), _("link")],
    },
    "books_icon": {
        "name": _("Books"),
        "hints": [_("read"), _("documents"), _("manuals"), _("guides"), _("library"), _("collection")],
    },
    "box_icon": {
        "name": _("Box"),
        "hints": [_("package"), _("container"), _("storage"), _("shipping"), _("delivery")],
    },
    "briefcase_icon": {
        "name": _("Briefcase"),
        "hints": [_("work"), _("business"), _("professional"), _("portfolio"), _("job"), _("office")],
    },
    "bug_icon": {
        "name": _("Ladybug"),
        "hints": [_("ladybug"), _("insect"), _("debug"), _("error"), _("problem"), _("issue")],
    },
    "cake_icon": {
        "name": _("Cake"),
        "hints": [_("birthday"), _("celebration"), _("party"), _("anniversary"), _("event")],
    },
    "calculator_icon": {
        "name": _("Calculator"),
        "hints": [_("math"), _("calculate"), _("compute"), _("numbers"), _("finance"), _("accounting")],
    },
    "calendar_icon": {
        "name": _("Calendar"),
        "hints": [_("date"), _("schedule"), _("appointment"), _("event"), _("planner"), _("day"), _("month"), _("year"), _("deadline"), _("due")],
    },
    "camera_icon": {
        "name": _("Camera"),
        "hints": [_("photo"), _("picture"), _("image"), _("capture"), _("screenshot"), _("media")],
    },
    "cat_icon": {
        "name": _("Cat"),
        "hints": [_("pet"), _("animal"), _("feline"), _("meow"), _("kitty")],
    },
    "cd_icon": {
        "name": _("Compact disc (CD)"),
        "hints": [_("disc"), _("music"), _("media"), _("backup"), _("storage")],
    },
    "charts_icon": {
        "name": _("Charts"),
        "hints": [_("graph"), _("statistics"), _("data"), _("analytics"), _("report"), _("metrics")],
    },
    "chat_icon": {
        "name": _("Chat"),
        "hints": [_("message"), _("talk"), _("conversation"), _("discuss"), _("communicate")],
    },
    "checkmark_green_icon": {
        "name": _("Check mark"),
        "hints": [_("done"), _("complete"), _("finished"), _("success"), _("yes"), _("approve"), _("accept")],
    },
    "checkmark_green_icon_multiple": {
        "name": _("Check marks"),
        "hints": [_("done"), _("complete"), _("finished"), _("success"), _("batch"), _("multiple")],
    },
    "clock_icon": {
        "name": _("Clock"),
        "hints": [_("time"), _("hour"), _("minute"), _("watch"), _("schedule"), _("duration")],
    },
    "clock_alarm_icon": {
        "name": _("Clock - Alarm"),
        "hints": [_("time"), _("alarm"), _("reminder"), _("wake"), _("alert"), _("notification"), _("deadline")],
    },
    "clock_stopwatch_icon": {
        "name": _("Clock - Stopwatch"),
        "hints": [_("time"), _("timer"), _("countdown"), _("measure"), _("track"), _("duration")],
    },
    "cogwheel_icon": {
        "name": _("Cogwheel"),
        "hints": [_("settings"), _("config"), _("gear"), _("preferences"), _("options"), _("setup")],
    },
    "cogwheels_icon": {
        "name": _("Cogwheels"),
        "hints": [_("settings"), _("config"), _("gears"), _("preferences"), _("options"), _("setup"), _("system")],
    },
    "contact_card_icon": {
        "name": _("Contact card"),
        "hints": [_("vcard"), _("address"), _("business card"), _("profile"), _("person")],
    },
    "cookie_icon": {
        "name": _("Cookie"),
        "hints": [_("treat"), _("reward"), _("snack"), _("food"), _("biscuit"), _("sweet")],
    },
    "computer_desktop_icon": {
        "name": _("Computer - Desktop"),
        "hints": [_("pc"), _("workstation"), _("monitor"), _("screen"), _("computer"), _("desktop")],
    },
    "computer_laptop_icon": {
        "name": _("Computer - Laptop"),
        "hints": [_("notebook"), _("portable"), _("pc"), _("mobile"), _("computer"), _("laptop")],
    },
    "computer_handheld_icon": {
        "name": _("Computer - Handheld"),
        "hints": [_("mobile"), _("phone"), _("pda"), _("tablet"), _("device")],
    },
    "cross_red_icon": {
        "name": _("Cross - Red"),
        "hints": [_("error"), _("cancel"), _("close"), _("delete"), _("stop"), _("reject"), _("no"), _("remove")],
    },
    "die_icon": {
        "name": _("Die"),
        "hints": [_("dice"), _("random"), _("game"), _("luck"), _("chance")],
    },
    "document_icon": {
        "name": _("Document"),
        "hints": [_("file"), _("paper"), _("text"), _("note"), _("write"), _("report")],
    },
    "earth_blue_icon": {
        "name": _("Earth - Blue"),
        "hints": [_("world"), _("globe"), _("planet"), _("international"), _("global"), _("web")],
    },
    "earth_green_icon": {
        "name": _("Earth - Green"),
        "hints": [_("world"), _("globe"), _("planet"), _("environment"), _("nature"), _("eco")],
    },
    "energy_icon": {
        "name": _("Energy"),
        "hints": [_("power"), _("electricity"), _("lightning"), _("bolt"), _("charge"), _("battery")],
    },
    "envelope_icon": {
        "name": _("Envelope"),
        "hints": [_("mail"), _("email"), _("message"), _("letter"), _("send"), _("receive"), _("inbox")],
    },
    "error_icon": {
        "name": _("Error"),
        "hints": [_("warning"), _("problem"), _("issue"), _("fail"), _("failure"), _("bug"), _("mistake")],
    },
    "envelopes_icon": {
        "name": _("Envelopes"),
        "hints": [_("mail"), _("email"), _("messages"), _("letters"), _("inbox"), _("batch")],
    },
    "file_important_icon": {
        "name": _("File - Important"),
        "hints": [_("document"), _("priority"), _("urgent"), _("attention"), _("critical"), _("star")],
    },
    "file_locked_icon": {
        "name": _("File - Locked"),
        "hints": [_("document"), _("secure"), _("protected"), _("private"), _("locked"), _("secret")],
    },
    "folder_blue_icon": {
        "name": _("Folder - Blue"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_blue_light_icon": {
        "name": _("Folder - Light blue"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_green_icon": {
        "name": _("Folder - Green"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_grey_icon": {
        "name": _("Folder - Grey"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize"), _("archive")],
    },
    "folder_orange_icon": {
        "name": _("Folder - Orange"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_purple_icon": {
        "name": _("Folder - Purple"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_red_icon": {
        "name": _("Folder - Red"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize"), _("important"), _("urgent")],
    },
    "folder_yellow_icon": {
        "name": _("Folder - Yellow"),
        "hints": [_("directory"), _("storage"), _("files"), _("container"), _("organize")],
    },
    "folder_blue_arrow_icon": {
        "name": _("Folder - Blue with arrow"),
        "hints": [_("directory"), _("storage"), _("files"), _("move"), _("transfer")],
    },
    "folder_favorite_icon": {
        "name": _("Folder - Favorite"),
        "hints": [_("directory"), _("storage"), _("star"), _("bookmark"), _("best"), _("preferred")],
    },
    "folder_important_icon": {
        "name": _("Folder - Important"),
        "hints": [_("directory"), _("storage"), _("priority"), _("urgent"), _("attention"), _("critical")],
    },
    "fsview_icon": {
        "name": _("Color swatches"),
        "hints": [_("color"), _("swatches"), _("palette"), _("design"), _("theme")],
    },
    "graph_icon": {
        "name": _("Graph"),
        "hints": [_("chart"), _("statistics"), _("data"), _("analytics"), _("plot"), _("diagram")],
    },
    "heart_icon": {
        "name": _("Heart"),
        "hints": [_("love"), _("favorite"), _("like"), _("health"), _("wellness")],
    },
    "hearts_icon": {
        "name": _("Hearts"),
        "hints": [_("love"), _("favorites"), _("likes"), _("health"), _("wellness")],
    },
    "house_green_icon": {
        "name": _("House - Green"),
        "hints": [_("home"), _("residence"), _("building"), _("dwelling"), _("personal")],
    },
    "house_red_icon": {
        "name": _("House - Red"),
        "hints": [_("home"), _("residence"), _("building"), _("dwelling"), _("urgent")],
    },
    "key_icon": {
        "name": _("Key"),
        "hints": [_("lock"), _("security"), _("password"), _("access"), _("unlock"), _("credential")],
    },
    "keys_icon": {
        "name": _("Keys"),
        "hints": [_("locks"), _("security"), _("passwords"), _("access"), _("unlock"), _("credentials")],
    },
    "lamp_icon": {
        "name": _("Lamp"),
        "hints": [_("light"), _("idea"), _("bulb"), _("bright"), _("illuminate"), _("thought")],
    },
    "led_blue_questionmark_icon": {
        "name": _("Question mark"),
        "hints": [_("question"), _("help"), _("unknown"), _("ask"), _("uncertain")],
    },
    "led_blue_information_icon": {
        "name": _("Information"),
        "hints": [_("info"), _("information"), _("details"), _("about"), _("help")],
    },
    "led_blue_icon": {
        "name": _("LED - Blue"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("online"), _("active")],
    },
    "led_blue_light_icon": {
        "name": _("LED - Light blue"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("online"), _("active")],
    },
    "led_grey_icon": {
        "name": _("LED - Grey"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("inactive"), _("disabled"), _("off")],
    },
    "led_green_icon": {
        "name": _("LED - Green"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("ok"), _("active"), _("go"), _("done")],
    },
    "led_green_light_icon": {
        "name": _("LED - Light green"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("ok"), _("active"), _("go"), _("done")],
    },
    "led_orange_icon": {
        "name": _("LED - Orange"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("warning"), _("caution")],
    },
    "led_purple_icon": {
        "name": _("LED - Purple"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("special"), _("custom")],
    },
    "led_red_icon": {
        "name": _("LED - Red"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("error"), _("stop"), _("offline"), _("failed")],
    },
    "led_yellow_icon": {
        "name": _("LED - Yellow"),
        "hints": [_("status"), _("indicator"), _("light"), _("signal"), _("warning"), _("pause"), _("attention")],
    },
    "life_ring_icon": {
        "name": _("Life ring"),
        "hints": [_("help"), _("support"), _("rescue"), _("assist"), _("safety"), _("emergency")],
    },
    "lock_locked_icon": {
        "name": _("Lock - Locked"),
        "hints": [_("secure"), _("private"), _("protected"), _("closed"), _("secret")],
    },
    "lock_unlocked_icon": {
        "name": _("Lock - Unlocked"),
        "hints": [_("open"), _("access"), _("public"), _("unlocked"), _("available")],
    },
    "magnifier_glass_icon": {
        "name": _("Magnifier glass"),
        "hints": [_("search"), _("find"), _("zoom"), _("look"), _("inspect"), _("explore")],
    },
    "music_piano_icon": {
        "name": _("Music - Piano"),
        "hints": [_("piano"), _("keyboard"), _("music"), _("instrument"), _("play")],
    },
    "music_note_icon": {
        "name": _("Music - Note"),
        "hints": [_("music"), _("sound"), _("audio"), _("melody"), _("song"), _("tune")],
    },
    "note_icon": {
        "name": _("Note"),
        "hints": [_("sticky"), _("memo"), _("reminder"), _("post-it"), _("write")],
    },
    "palette_icon": {
        "name": _("Palette"),
        "hints": [_("color"), _("art"), _("design"), _("paint"), _("creative")],
    },
    "paperclip_icon": {
        "name": _("Paperclip"),
        "hints": [_("attach"), _("attachment"), _("file"), _("document"), _("clip")],
    },
    "password_icon": {
        "name": _("Password"),
        "hints": [_("security"), _("credential"), _("secret"), _("key"), _("login"), _("authenticate")],
    },
    "pencil_icon": {
        "name": _("Pencil"),
        "hints": [_("edit"), _("write"), _("draw"), _("modify"), _("change"), _("update")],
    },
    "person_icon": {
        "name": _("Person"),
        "hints": [_("user"), _("account"), _("profile"), _("member"), _("contact"), _("individual")],
    },
    "persons_icon": {
        "name": _("People"),
        "hints": [_("users"), _("people"), _("team"), _("group"), _("members"), _("contacts")],
    },
    "person_id_icon": {
        "name": _("Person - ID"),
        "hints": [_("user"), _("identity"), _("card"), _("profile"), _("badge"), _("employee")],
    },
    "person_talking_icon": {
        "name": _("Person - Talking"),
        "hints": [_("speak"), _("talk"), _("discuss"), _("communicate"), _("voice"), _("call")],
    },
    "printer_icon": {
        "name": _("Printer"),
        "hints": [_("print"), _("output"), _("paper"), _("document"), _("hardcopy")],
    },
    "reload_icon": {
        "name": _("Reload"),
        "hints": [_("refresh"), _("update"), _("sync"), _("repeat"), _("restart"), _("renew")],
    },
    "remote_icon": {
        "name": _("Remote"),
        "hints": [_("control"), _("wireless"), _("distance"), _("network"), _("access")],
    },
    "run_icon": {
        "name": _("Run"),
        "hints": [_("execute"), _("start"), _("play"), _("begin"), _("go"), _("launch"), _("sprint")],
    },
    "science_icon": {
        "name": _("Science"),
        "hints": [_("lab"), _("experiment"), _("research"), _("chemistry"), _("biology")],
    },
    "sign_important_icon": {
        "name": _("Sign - Important"),
        "hints": [_("warning"), _("attention"), _("urgent"), _("priority"), _("exclamation"), _("alert")],
    },
    "symbol_minus_icon": {
        "name": _("Symbol - Minus"),
        "hints": [_("subtract"), _("remove"), _("decrease"), _("less"), _("reduce")],
    },
    "symbol_plus_icon": {
        "name": _("Symbol - Plus"),
        "hints": [_("add"), _("create"), _("increase"), _("more"), _("expand")],
    },
    "star_red_icon": {
        "name": _("Star - Red"),
        "hints": [_("favorite"), _("important"), _("priority"), _("rating"), _("bookmark"), _("urgent"), _("critical")],
    },
    "star_yellow_icon": {
        "name": _("Star - Yellow"),
        "hints": [_("favorite"), _("important"), _("priority"), _("rating"), _("bookmark"), _("best")],
    },
    "sticky_note_icon": {
        "name": _("Sticky note"),
        "hints": [_("memo"), _("reminder"), _("post-it"), _("note"), _("yellow"), _("paper")],
    },
    "tea_icon": {
        "name": _("Tea"),
        "hints": [_("break"), _("rest"), _("relax"), _("pause"), _("coffee"), _("drink"), _("beverage")],
    },
    "terminal_icon": {
        "name": _("Terminal"),
        "hints": [_("command"), _("console"), _("shell"), _("code"), _("developer")],
    },
    "timer_icon": {
        "name": _("Timer"),
        "hints": [_("countdown"), _("time"), _("limit"), _("duration"), _("stopwatch"), _("deadline")],
    },
    "trafficlight_icon": {
        "name": _("Traffic light"),
        "hints": [_("status"), _("priority"), _("waiting"), _("proceed"), _("stop")],
    },
    "traffic_go_icon": {
        "name": _("Traffic - Go"),
        "hints": [_("proceed"), _("start"), _("green light"), _("continue"), _("execute")],
    },
    "trashcan_icon": {
        "name": _("Trashcan"),
        "hints": [_("delete"), _("remove"), _("garbage"), _("bin"), _("recycle"), _("discard")],
    },
    "weather_lightning_icon": {
        "name": _("Weather - Lightning"),
        "hints": [_("storm"), _("thunder"), _("electric"), _("power"), _("urgent"), _("fast")],
    },
    "weather_umbrella_icon": {
        "name": _("Weather - Umbrella"),
        "hints": [_("rain"), _("protection"), _("shelter"), _("weather"), _("umbrella"), _("wet")],
    },
    "weather_sunny_icon": {
        "name": _("Weather - Partly sunny"),
        "hints": [_("sun"), _("bright"), _("day"), _("clear"), _("good"), _("positive")],
    },
    "wizard_icon": {
        "name": _("Wizard"),
        "hints": [_("magic"), _("helper"), _("assistant"), _("guide"), _("setup")],
    },
    "wrench_icon": {
        "name": _("Wrench"),
        "hints": [_("tool"), _("settings"), _("config"), _("repair"), _("fix"), _("maintenance"), _("service")],
    },
    # Bank/Accounting icons (Papirus) - new format without _icon suffix
    "bank_account": {
        "name": _("Bank Account"),
        "hints": [_("bank"), _("account"), _("checking"), _("savings"), _("finance"), _("institution")],
    },
    "money_budget": {
        "name": _("Money Budget"),
        "hints": [_("money"), _("budget"), _("finance"), _("coins"), _("piggybank"), _("savings"), _("personal")],
    },
    "taxes": {
        "name": _("Taxes"),
        "hints": [_("tax"), _("taxes"), _("money"), _("dollar"), _("cash"), _("government"), _("irs"), _("percent"), _("form")],
    },
    "currency_dollar": {
        "name": _("Currency"),
        "hints": [_("currency"), _("dollar"), _("money"), _("symbol"), _("usd"), _("format"), _("price")],
    },
    "calculator_flat": {
        "name": _("Calculator (Flat)"),
        "hints": [_("calculator"), _("math"), _("compute"), _("calculate"), _("numbers"), _("flat"), _("modern")],
    },
    "uno_calculator": {
        "name": _("Calculator (Uno)"),
        "hints": [_("calculator"), _("math"), _("uno"), _("compute"), _("blue"), _("numbers"), _("arithmetic")],
    },
    "gnome_calculator": {
        "name": _("Calculator (GNOME)"),
        "hints": [_("calculator"), _("math"), _("gnome"), _("compute"), _("colorful"), _("numbers"), _("arithmetic")],
    },
    "safe_vault": {
        "name": _("Safe"),
        "hints": [_("safe"), _("vault"), _("secure"), _("lock"), _("storage"), _("protect"), _("valuables")],
    },
    "bitcoin": {
        "name": _("Bitcoin"),
        "hints": [_("bitcoin"), _("crypto"), _("cryptocurrency"), _("digital"), _("btc"), _("blockchain")],
    },
    "wallet_flat": {
        "name": _("Wallet (Flat)"),
        "hints": [_("wallet"), _("billfold"), _("money"), _("cash"), _("flat"), _("modern")],
    },
    "money_expense": {
        "name": _("Money Expense"),
        "hints": [_("expense"), _("money"), _("spending"), _("budget"), _("track"), _("manager"), _("receipt")],
    },
    # Bank/Accounting apps (Papirus)
    "homebank": {
        "name": _("HomeBank"),
        "hints": [_("home"), _("bank"), _("finance"), _("budget"), _("personal"), _("accounting")],
    },
    "cointop": {
        "name": _("CoinTop"),
        "hints": [_("crypto"), _("cryptocurrency"), _("terminal"), _("bitcoin"), _("portfolio"), _("tracker")],
    },
    "cryptomator": {
        "name": _("Cryptomator"),
        "hints": [_("encrypt"), _("security"), _("vault"), _("cloud"), _("privacy"), _("lock")],
    },
    "banking": {
        "name": _("Banking"),
        "hints": [_("bank"), _("credit"), _("card"), _("finance"), _("payment"), _("account")],
    },
    "safeeyes": {
        "name": _("Safe Eyes"),
        "hints": [_("break"), _("rest"), _("health"), _("eye"), _("reminder"), _("timer")],
    },
    "kmymoney": {
        "name": _("KMyMoney"),
        "hints": [_("money"), _("finance"), _("personal"), _("budget"), _("accounting"), _("kde")],
    },
    "money_manager": {
        "name": _("Money Manager"),
        "hints": [_("money"), _("expense"), _("manager"), _("budget"), _("track"), _("finance")],
    },
    "moneydance": {
        "name": _("Moneydance"),
        "hints": [_("money"), _("finance"), _("personal"), _("budget"), _("banking"), _("investment")],
    },
    # Bank/Accounting icons (Oxygen) - new format without _icon suffix
    "bank_building": {
        "name": _("Bank Building"),
        "hints": [_("bank"), _("building"), _("institution"), _("columns"), _("finance"), _("classic")],
    },
    "wallet_closed": {
        "name": _("Wallet (Closed)"),
        "hints": [_("wallet"), _("closed"), _("locked"), _("secure"), _("billfold"), _("leather")],
    },
    "wallet_open": {
        "name": _("Wallet (Open)"),
        "hints": [_("wallet"), _("open"), _("money"), _("cash"), _("billfold"), _("spend")],
    },
    "calculator_3d": {
        "name": _("Calculator (3D)"),
        "hints": [_("calculator"), _("math"), _("compute"), _("calculate"), _("classic"), _("3d")],
    },
    "wallet_keys": {
        "name": _("Wallet Keys"),
        "hints": [_("wallet"), _("keys"), _("password"), _("secure"), _("manager"), _("keyring")],
    },
    "cactus": {
        "name": _("Cactus"),
        "hints": [_("cactus"), _("plant"), _("desert"), _("green"), _("nature"), _("succulent")],
    },
}


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
