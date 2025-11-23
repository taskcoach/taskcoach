# -*- coding: UTF-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2012 Nicola Chiapolini <nicola.chiapolini@physik.uzh.ch>
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

from taskcoachlib import meta, widgets, notify, operating_system, render
from taskcoachlib.domain import date, task
from taskcoachlib.gui import artprovider
from taskcoachlib.meta import data
from taskcoachlib.i18n import _
from wx.lib.agw.hyperlink import HyperLinkCtrl
from wx.adv import BitmapComboBox
import ast
import wx, calendar


class FontColorSyncer(object):
    """The font color can be changed via the font color buttons and via the
    font button. The FontColorSyncer updates the one when the font color
    is changed via the other and vice versa."""

    def __init__(self, fgColorButton, bgColorButton, fontButton):
        self._fgColorButton = fgColorButton
        self._bgColorButton = bgColorButton
        self._fontButton = fontButton
        fgColorButton.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onFgColorPicked)
        bgColorButton.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onBgColorPicked)
        fontButton.Bind(wx.EVT_FONTPICKER_CHANGED, self.onFontPicked)

    def onFgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())

    def onBgColorPicked(self, event):  # pylint: disable=W0613
        self._fontButton.SetBackgroundColour(self._bgColorButton.GetColour())

    def onFontPicked(self, event):  # pylint: disable=W0613
        fontColor = self._fontButton.GetSelectedColour()
        if (
            fontColor != self._fgColorButton.GetColour()
            and fontColor != wx.BLACK
        ):
            self._fgColorButton.SetColour(self._fontButton.GetSelectedColour())
        else:
            self._fontButton.SetSelectedColour(self._fgColorButton.GetColour())


class SettingsPageBase(widgets.BookPage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._booleanSettings = []
        self._choiceSettings = []
        self._multipleChoiceSettings = []
        self._integerSettings = []
        self._timeSettings = []
        self._colorSettings = []
        self._fontSettings = []
        self._iconSettings = []
        self._pathSettings = []
        self._textSettings = []
        self._syncers = []

    def addBooleanSetting(self, section, setting, text, helpText="", **kwargs):
        checkBox = wx.CheckBox(self, -1)
        checkBox.SetValue(self.getboolean(section, setting))
        self.addEntry(text, checkBox, helpText=helpText, **kwargs)
        self._booleanSettings.append((section, setting, checkBox))
        return checkBox

    def addChoiceSetting(
        self, section, setting, text, helpText, *listsOfChoices, **kwargs
    ):
        choiceCtrls = []
        currentValue = self.gettext(section, setting)
        sep = kwargs.pop("sep", "_")
        for choices, currentValuePart in zip(
            listsOfChoices, currentValue.split(sep)
        ):
            choiceCtrl = wx.Choice(self)
            choiceCtrls.append(choiceCtrl)
            for choiceValue, choiceText in choices:
                choiceCtrl.Append(choiceText, choiceValue)
                if choiceValue == currentValuePart:
                    choiceCtrl.SetSelection(choiceCtrl.GetCount() - 1)
            # Force a selection if necessary:
            if choiceCtrl.GetSelection() == wx.NOT_FOUND:
                choiceCtrl.SetSelection(0)
        # pylint: disable=W0142
        self.addEntry(
            text,
            *choiceCtrls,
            helpText=helpText,
            flags=kwargs.get("flags", None)
        )
        self._choiceSettings.append((section, setting, choiceCtrls))
        return choiceCtrls

    def enableChoiceSetting(self, section, setting, enabled):
        for theSection, theSetting, ctrls in self._choiceSettings:
            if theSection == section and theSetting == setting:
                for ctrl in ctrls:
                    ctrl.Enable(enabled)
                break

    def addMultipleChoiceSettings(
        self, section, setting, text, choices, helpText="", **kwargs
    ):
        # choices is a list of (number, text) tuples.
        multipleChoice = wx.CheckListBox(
            self, choices=[choice[1] for choice in choices]
        )
        checkedNumbers = self.getlist(section, setting)
        for index, choice in enumerate(choices):
            multipleChoice.Check(index, choice[0] in checkedNumbers)
        self.addEntry(
            text,
            multipleChoice,
            helpText=helpText,
            growable=True,
            flags=kwargs.get("flags", None),
        )
        self._multipleChoiceSettings.append(
            (
                section,
                setting,
                multipleChoice,
                [choice[0] for choice in choices],
            )
        )

    def addIntegerSetting(
        self,
        section,
        setting,
        text,
        minimum=0,
        maximum=100,
        helpText="",
        flags=None,
    ):
        intValue = self.getint(section, setting)
        spin = widgets.SpinCtrl(
            self, min=minimum, max=maximum, size=(65, -1), value=intValue
        )
        self.addEntry(text, spin, helpText=helpText, flags=flags)
        self._integerSettings.append((section, setting, spin))

    def addTimeSetting(
        self,
        section,
        setting,
        text,
        helpText="",
        disabledMessage=None,
        disabledValue=None,
        defaultValue=0,
    ):
        hourValue = self.getint(section, setting)
        timeCtrl = widgets.TimeEntry(
            self,
            hourValue,
            defaultValue=defaultValue,
            disabledValue=disabledValue,
            disabledMessage=disabledMessage,
        )
        self.addEntry(
            text,
            timeCtrl,
            helpText=helpText,
            flags=(
                wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT,
            ),
        )
        self._timeSettings.append((section, setting, timeCtrl))

    def addFontSetting(self, section, setting, text):
        default_font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        native_info_string = self.gettext(section, setting)
        current_font = (
            wx.FontFromNativeInfoString(native_info_string)
            if native_info_string
            else None
        )
        font_button = widgets.FontPickerCtrl(
            self, font=current_font or default_font, colour=(0, 0, 0, 255)
        )
        font_button.SetBackgroundColour((255, 255, 255, 255))
        self.addEntry(
            text,
            font_button,
            flags=(
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL
                | wx.ALIGN_CENTER_VERTICAL,  # wx.EXPAND causes the button to be top aligned on Mac OS X
            ),
        )
        self._fontSettings.append((section, setting, font_button))

    def addAppearanceHeader(self):
        self.addEntry(
            "",
            _("Foreground color"),
            _("Background color"),
            _("Font"),
            _("Icon"),
            flags=[wx.ALL | wx.ALIGN_CENTER] * 5,
        )

    def addAppearanceSetting(
        self,
        fgColorSection,
        fgColorSetting,
        bgColorSection,
        bgColorSetting,
        fontSection,
        fontSetting,
        iconSection,
        iconSetting,
        text,
    ):
        currentFgColor = self.getvalue(fgColorSection, fgColorSetting)
        fgColorButton = wx.ColourPickerCtrl(self, colour=currentFgColor)
        currentBgColor = self.getvalue(bgColorSection, bgColorSetting)
        bgColorButton = wx.ColourPickerCtrl(self, colour=currentBgColor)
        defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        nativeInfoString = self.gettext(fontSection, fontSetting)
        currentFont = (
            wx.FontFromNativeInfoString(nativeInfoString)
            if nativeInfoString
            else None
        )
        fontButton = widgets.FontPickerCtrl(
            self, font=currentFont or defaultFont, colour=currentFgColor
        )
        fontButton.SetBackgroundColour(currentBgColor)
        iconEntry = BitmapComboBox(self, style=wx.CB_READONLY)
        imageNames = sorted(artprovider.chooseableItemImages.keys())
        for imageName in imageNames:
            label = artprovider.chooseableItemImages[imageName]
            bitmap = wx.ArtProvider.GetBitmap(imageName, wx.ART_MENU, (16, 16))
            item = iconEntry.Append(label, bitmap)
            iconEntry.SetClientData(item, imageName)
        currentIcon = self.gettext(iconSection, iconSetting)
        currentSelectionIndex = imageNames.index(currentIcon)
        iconEntry.SetSelection(currentSelectionIndex)  # pylint: disable=E1101

        self.addEntry(
            text,
            fgColorButton,
            bgColorButton,
            fontButton,
            iconEntry,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
                wx.ALL
                | wx.ALIGN_CENTER_VERTICAL,  # wx.EXPAND causes the button to be top aligned on Mac OS X
                wx.ALL | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL,
            ),
        )
        self._colorSettings.append(
            (fgColorSection, fgColorSetting, fgColorButton)
        )
        self._colorSettings.append(
            (bgColorSection, bgColorSetting, bgColorButton)
        )
        self._iconSettings.append((iconSection, iconSetting, iconEntry))
        self._fontSettings.append((fontSection, fontSetting, fontButton))
        self._syncers.append(
            FontColorSyncer(fgColorButton, bgColorButton, fontButton)
        )

    def addPathSetting(self, section, setting, text, helpText="", **kwargs):
        pathChooser = widgets.DirectoryChooser(self, wx.ID_ANY)
        pathChooser.SetPath(self.gettext(section, setting))
        self.addEntry(text, pathChooser, helpText=helpText, **kwargs)
        self._pathSettings.append((section, setting, pathChooser))

    def addTextSetting(self, section, setting, text, helpText="", **kwargs):
        textChooser = wx.TextCtrl(
            self, wx.ID_ANY, self.gettext(section, setting)
        )
        self.addEntry(text, textChooser, helpText=helpText, **kwargs)
        self._textSettings.append((section, setting, textChooser))

    def setTextSetting(self, section, setting, value):
        for theSection, theSetting, textChooser in self._textSettings:
            if theSection == section and theSetting == setting:
                textChooser.SetValue(value)

    def enableTextSetting(self, section, setting, enabled):
        for theSection, theSetting, textChooser in self._textSettings:
            if theSection == section and theSetting == setting:
                textChooser.Enable(enabled)
                break

    def addText(self, label, text, **kwargs):
        self.addEntry(label, text, **kwargs)

    def ok(self):
        for section, setting, checkBox in self._booleanSettings:
            self.setboolean(section, setting, checkBox.IsChecked())
        for section, setting, choiceCtrls in self._choiceSettings:
            value = "_".join(
                [
                    choice.GetClientData(choice.GetSelection())
                    for choice in choiceCtrls
                ]
            )
            self.settext(section, setting, value)
        for (
            section,
            setting,
            multipleChoice,
            choices,
        ) in self._multipleChoiceSettings:
            self.setlist(
                section,
                setting,
                [
                    choices[index]
                    for index in range(len(choices))
                    if multipleChoice.IsChecked(index)
                ],
            )
        for section, setting, spin in self._integerSettings:
            self.setint(section, setting, spin.GetValue())
        for section, setting, timeCtrl in self._timeSettings:
            self.setint(section, setting, timeCtrl.GetValue())
        for section, setting, colorButton in self._colorSettings:
            self.setvalue(section, setting, colorButton.GetColour())
        for section, setting, fontButton in self._fontSettings:
            selectedFont = fontButton.GetSelectedFont()
            defaultFont = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            fontInfoDesc = (
                ""
                if selectedFont == defaultFont
                else selectedFont.GetNativeFontInfoDesc()
            )
            self.settext(section, setting, fontInfoDesc)
        for section, setting, iconEntry in self._iconSettings:
            iconName = iconEntry.GetClientData(iconEntry.GetSelection())
            self.settext(section, setting, iconName)
        for section, setting, btn in self._pathSettings:
            self.settext(section, setting, btn.GetPath())
        for section, setting, txt in self._textSettings:
            self.settext(section, setting, txt.GetValue())

    def get(self, section, name):
        raise NotImplementedError

    def set(self, section, name, value):
        raise NotImplementedError

    def getint(self, section, name):
        return int(self.get(section, name))

    def setint(self, section, name, value):
        self.set(section, name, str(value))

    def setboolean(self, section, name, value):
        self.set(section, name, str(value))

    def getboolean(self, section, name):
        return self.get(section, name) == "True"

    def settext(self, section, name, value):
        self.set(section, name, value)

    def gettext(self, section, name):
        return self.get(section, name)

    def getlist(self, section, name):
        return ast.literal_eval(self.get(section, name))

    def setlist(self, section, name, value):
        self.set(section, name, str(value))

    def getvalue(self, section, name):
        return ast.literal_eval(self.get(section, name))

    def setvalue(self, section, name, value):
        self.set(section, name, str(value))


class SettingsPage(SettingsPageBase):
    def __init__(self, settings=None, *args, **kwargs):
        self.settings = settings
        super().__init__(*args, **kwargs)

    def addEntry(self, text, *controls, **kwargs):  # pylint: disable=W0221
        helpText = kwargs.pop("helpText", "")
        if helpText == "restart":
            helpText = (
                _("This setting will take effect after you restart %s")
                % meta.name
            )
        elif helpText == "override":
            helpText = _(
                "This setting can be overridden for individual tasks\n"
                "in the task edit dialog."
            )
        if helpText:
            controls = controls + (helpText,)
        super().addEntry(text, *controls, **kwargs)

    def get(self, section, name):
        return self.settings.get(section, name)

    def set(self, section, name, value):
        if section is not None:
            self.settings.set(section, name, value)

    def getint(self, section, name):
        return self.settings.getint(section, name)

    def setint(self, section, name, value):
        self.settings.setint(section, name, value)

    def getboolean(self, section, name):
        return self.settings.getboolean(section, name)

    def setboolean(self, section, name, value):
        if section is not None:
            self.settings.setboolean(section, name, value)

    def settext(self, section, name, value):
        self.settings.settext(section, name, value)

    def gettext(self, section, name):
        return self.settings.gettext(section, name)

    def setvalue(self, section, name, value):
        self.settings.setvalue(section, name, value)

    def getvalue(self, section, name):
        return self.settings.getvalue(section, name)

    def setlist(self, section, name, value):
        self.settings.setlist(section, name, value)

    def getlist(self, section, name):
        return self.settings.getlist(section, name)


class SavePage(SettingsPage):
    pageName = "save"
    pageTitle = _("Files")
    pageIcon = "save"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)
        self.addBooleanSetting(
            "file",
            "autosave",
            _("Auto save after every change"),
            flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.ALIGN_LEFT),
        )
        self.addBooleanSetting(
            "file",
            "autoload",
            _("Auto load when the file changes on disk"),
            flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.ALIGN_LEFT),
        )
        self.addBooleanSetting(
            "file",
            "nopoll",
            _("Smart filesystem monitoring"),
            _(
                "Try to detect changes to the task file in real time.\nDo not check this if your task file is on a network share.\nYou must restart %s after changing this."
            )
            % meta.name,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_TOP,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addBooleanSetting(
            "file",
            "saveinifileinprogramdir",
            _(
                "Save settings (%s.ini) in the same\n"
                "directory as the program"
            )
            % meta.filename,
            _("For running %s from a removable medium") % meta.name,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALIGN_LEFT,
            ),
        )
        self.addPathSetting(
            "file",
            "attachmentbase",
            _("Attachment base directory"),
            _(
                "When adding an attachment, try to make\n"
                "its path relative to this one."
            ),
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_TOP,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addMultipleChoiceSettings(
            "file",
            "autoimport",
            _("Before saving, automatically import from"),
            [("Todo.txt", _("Todo.txt format"))],
            helpText=_(
                "Before saving, %s automatically imports tasks\n"
                "from a Todo.txt file with the same name as the task file,\n"
                "but with extension .txt"
            )
            % meta.name,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_TOP,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addMultipleChoiceSettings(
            "file",
            "autoexport",
            _("When saving, automatically export to"),
            [("Todo.txt", _("Todo.txt format"))],
            helpText=_(
                "When saving, %s automatically exports tasks\n"
                "to a Todo.txt file with the same name as the task file,\n"
                "but with extension .txt"
            )
            % meta.name,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_TOP,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.fit()


class WindowBehaviorPage(SettingsPage):
    pageName = "window"
    pageTitle = _("Window behavior")
    pageIcon = "windows"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, growableColumn=-1, *args, **kwargs)
        self.addBooleanSetting(
            "window",
            "tips",
            _("Show tips window on startup"),
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        self.addChoiceSetting(
            "window",
            "starticonized",
            _("Start with the main window iconized"),
            "",
            [
                ("Never", _("Never")),
                ("Always", _("Always")),
                ("WhenClosedIconized", _("If it was iconized last session")),
            ],
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        self.addBooleanSetting(
            "version",
            "notify",
            _("Check for new version " "of %(name)s on startup")
            % meta.data.metaDict,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        self.addBooleanSetting(
            "view",
            "developermessages",
            _("Check for " "messages from the %(name)s developers on startup")
            % meta.data.metaDict,
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        self.addBooleanSetting(
            "window",
            "hidewheniconized",
            _("Hide main window when iconized"),
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        self.addBooleanSetting(
            "window",
            "hidewhenclosed",
            _("Minimize main window when closed"),
            flags=[wx.ALIGN_RIGHT, wx.EXPAND],
        )
        if not operating_system.isMacOsXMavericks_OrNewer():
            self.addBooleanSetting(
                "window",
                "blinktaskbariconwhentrackingeffort",
                _("Make clock in the task bar tick when tracking effort"),
                flags=[wx.ALIGN_RIGHT, wx.EXPAND],
            )
        self.fit()


class LanguagePage(SettingsPage):
    pageName = "language"
    pageTitle = _("Language")
    pageIcon = "person_talking_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)
        languages = [
            ("ar", "الْعَرَبيّة (Arabic)"),
            ("eu_ES", "Euskal Herria (Basque)"),
            ("be_BY", "беларуская мова (Belarusian)"),
            ("bs_BA", "босански (Bosnian)"),
            ("pt_BR", "Português brasileiro (Brazilian Portuguese)"),
            ("br_FR", "Brezhoneg (Breton)"),
            ("bg_BG", "български (Bulgarian)"),
            ("ca_ES", "Català (Catalan)"),
            ("zh_CN", "简体中文 (Simplified Chinese)"),
            ("zh_TW", "正體字 (Traditional Chinese)"),
            ("cs_CS", "Čeština (Czech)"),
            ("da_DA", "Dansk (Danish)"),
            ("nl_NL", "Nederlands (Dutch)"),
            ("en_AU", "English (Australia)"),
            ("en_CA", "English (Canada)"),
            ("en_GB", "English (UK)"),
            ("en_US", "English (US)"),
            ("eo", "Esperanto"),
            ("et_EE", "Eesti keel (Estonian)"),
            ("fi_FI", "Suomi (Finnish)"),
            ("fr_FR", "Français (French)"),
            ("gl_ES", "Galego (Galician)"),
            ("de_DE", "Deutsch (German)"),
            ("nds_DE", "Niederdeutsche Sprache (Low German)"),
            ("el_GR", "ελληνικά (Greek)"),
            ("he_IL", "עברית (Hebrew)"),
            ("hi_IN", "हिन्दी, हिंदी (Hindi)"),
            ("hu_HU", "Magyar (Hungarian)"),
            ("id_ID", "Bahasa Indonesia (Indonesian)"),
            ("it_IT", "Italiano (Italian)"),
            ("ja_JP", "日本語 (Japanese)"),
            ("ko_KO", "한국어/조선말 (Korean)"),
            ("lv_LV", "Latviešu (Latvian)"),
            ("lt_LT", "Lietuvių kalba (Lithuanian)"),
            ("mr_IN", "मराठी Marāṭhī (Marathi)"),
            ("mn_CN", "Монгол бичиг (Mongolian)"),
            ("nb_NO", "Bokmål (Norwegian Bokmal)"),
            ("nn_NO", "Nynorsk (Norwegian Nynorsk)"),
            ("oc_FR", "Lenga d'òc (Occitan)"),
            ("pap", "Papiamentu (Papiamento)"),
            ("fa_IR", "فارسی (Persian)"),
            ("pl_PL", "Język polski (Polish)"),
            ("pt_PT", "Português (Portuguese)"),
            ("ro_RO", "Română (Romanian)"),
            ("ru_RU", "Русский (Russian)"),
            ("sk_SK", "Slovenčina (Slovak)"),
            ("sl_SI", "Slovenski jezik (Slovene)"),
            ("es_ES", "Español (Spanish)"),
            ("sv_SE", "Svenska (Swedish)"),
            ("te_IN", "తెలుగు (Telugu)"),
            ("th_TH", "ภาษาไทย (Thai)"),
            ("tr_TR", "Türkçe (Turkish)"),
            ("uk_UA", "украї́нська мо́ва (Ukranian)"),
            ("vi_VI", "tiếng Việt (Vietnamese)"),
        ]
        choices = [("", _("Let the system determine the language"))]
        allLanguages = dict(list(data.languages.values()))
        for code, label in languages:
            if code == "en_US":
                label = "English (US)"
                enabled = True
            elif code in allLanguages:
                enabled = allLanguages[code]
            elif "_" in code:
                enabled = allLanguages.get(code.split("_")[0], False)
            else:
                enabled = False
            if enabled:
                choices.append((code, label))
        # Don't use '_' as separator since we don't have different choice
        # controls for language and country (but maybe we should?)
        self.addChoiceSetting(
            "view",
            "language_set_by_user",
            _("Language"),
            "restart",
            choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.EXPAND,
                wx.ALIGN_LEFT,
            ),
            sep="-",
        )

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.StaticText(
            panel,
            label=_(
                "If your language is not "
                "available, or the translation needs improving, please consider "
                "helping. See:"
            ),
        )
        sizer.Add(text)
        url = meta.translations_url
        urlCtrl = HyperLinkCtrl(panel, -1, label=url, URL=url)
        sizer.Add(urlCtrl)
        panel.SetSizerAndFit(sizer)
        self.addText(
            _("Language not found?"),
            panel,
            flags=(
                wx.ALIGN_RIGHT,
                wx.EXPAND,
            ),
        )
        self.fit()

    def ok(self):
        super().ok()
        self.set("view", "language", self.get("view", "language_set_by_user"))


class TaskAppearancePage(SettingsPage):
    pageName = "appearance"
    pageTitle = _("Task appearance")
    pageIcon = "palette_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=9, growableColumn=-1, *args, **kwargs)
        self.addAppearanceHeader()
        for status in task.Task.possibleStatuses():
            setting = "%stasks" % status
            self.addAppearanceSetting(
                "fgcolor",
                setting,
                "bgcolor",
                setting,
                "font",
                setting,
                "icon",
                setting,
                status.pluralLabel,
            )
        self.addText(
            "",
            _(
                "These appearance settings can be overridden "
                "for individual tasks in the task edit dialog."
            ),
            flags=(
                wx.ALIGN_LEFT,
                wx.EXPAND,
            ),
        )
        self.fit()


class FeaturesPage(SettingsPage):
    pageName = "features"
    pageTitle = _("Features")
    pageIcon = "cogwheel_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, growableColumn=-1, *args, **kwargs)
        self.addEntry(
            _(
                "All settings on this tab require a restart of %s "
                "to take effect"
            )
            % meta.name,
            flags=(wx.ALIGN_CENTER,),
        )
        try:
            import taskcoachlib.syncml.core  # pylint: disable=W0404,W0612
        except ImportError:
            pass
        else:
            self.addBooleanSetting(
                "feature",
                "syncml",
                _("Enable SyncML"),
                flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.EXPAND),
            )
        self.addBooleanSetting(
            "feature",
            "iphone",
            _("Enable iPhone synchronization"),
            flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.EXPAND),
        )
        if operating_system.isGTK():
            self.addBooleanSetting(
                "feature",
                "usesm2",
                _("Use X11 session management"),
                flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.EXPAND),
            )
        self.addChoiceSetting(
            "view",
            "weekstart",
            _("Start of work week"),
            " ",
            [("monday", _("Monday")), ("sunday", _("Sunday"))],
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addTimeSetting(
            "view",
            "efforthourstart",
            _("Hour of start of work day"),
            helpText=" ",
        )
        self.addTimeSetting(
            "view",
            "efforthourend",
            _("Hour of end of work day"),
            helpText=" ",
            disabledMessage=_("End of day"),
            disabledValue=24,
            defaultValue=23,
        )
        self.addBooleanSetting(
            "calendarviewer",
            "gradient",
            _(
                "Use gradients in calendar views.\n"
                "This may slow down Task Coach."
            ),
            flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.EXPAND),
        )
        self.addChoiceSetting(
            "view",
            "effortminuteinterval",
            _("Minutes between suggested times"),
            _(
                "In popup-menus for time selection (e.g. for setting the start \n"
                "time of an effort) %(name)s will suggest times using this \n"
                "setting. The smaller the number of minutes, the more times \n"
                "are suggested. Of course, you can also enter any time you \n"
                "want beside the suggested times."
            )
            % meta.data.metaDict,
            [
                (minutes, minutes)
                for minutes in ("5", "6", "10", "15", "20", "30")
            ],
            flags=(
                wx.ALL | wx.ALIGN_TOP | wx.ALIGN_RIGHT,
                wx.ALL | wx.ALIGN_TOP,
                wx.ALL | wx.ALIGN_CENTER_VERTICAL,
            ),
        )
        self.addIntegerSetting(
            "feature",
            "minidletime",
            _("Idle time notice"),
            helpText=_(
                "If there is no user input for this amount of time\n"
                "(in minutes), %(name)s will ask what to do about current "
                "efforts."
            )
            % meta.data.metaDict,
            flags=(
                wx.ALL | wx.ALIGN_CENTRE_VERTICAL | wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addBooleanSetting(
            "feature",
            "decimaltime",
            _("Use decimal times for effort entries."),
            _(
                "Display one hour, fifteen minutes as 1.25 instead of 1:15\n"
                "This is useful when creating invoices."
            ),
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALIGN_LEFT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALIGN_LEFT,
            ),
        )
        self.addBooleanSetting(
            "view",
            "descriptionpopups",
            _(
                "Show a popup with the description of an item\n"
                "when hovering over it"
            ),
            flags=(wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL, wx.EXPAND),
        )
        self.fit()

    def ok(self):
        super().ok()
        calendar.setfirstweekday(
            dict(monday=0, sunday=6)[self.get("view", "weekstart")]
        )


class TaskDatesPage(SettingsPage):
    pageName = "task"
    pageTitle = _("Task dates")
    pageIcon = "calendar_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=4, growableColumn=-1, *args, **kwargs)
        self.addBooleanSetting(
            "behavior",
            "markparentcompletedwhenallchildrencompleted",
            _("Mark parent task completed when all children are completed"),
            helpText="override",
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.EXPAND,
            ),
        )
        self.addIntegerSetting(
            "behavior",
            "duesoonhours",
            _("Number of hours that tasks are considered to be 'due soon'"),
            minimum=0,
            maximum=9999,
            flags=(wx.ALIGN_RIGHT, wx.ALL | wx.ALIGN_LEFT),
        )
        choices = [
            ("", _("Nothing")),
            (
                "startdue",
                _("Changing the planned start date changes the due date"),
            ),
            (
                "duestart",
                _("Changing the due date changes the planned start date"),
            ),
        ]
        self.addChoiceSetting(
            "view",
            "datestied",
            _(
                "What to do with planned start and due date if the other one is changed"
            ),
            "",
            choices,
            flags=(wx.ALIGN_RIGHT, wx.ALL | wx.ALIGN_LEFT),
        )

        check_choices = [("preset", _("Preset")), ("propose", _("Propose"))]
        day_choices = [
            ("today", _("Today")),
            ("tomorrow", _("Tomorrow")),
            ("dayaftertomorrow", _("Day after tomorrow")),
            ("nextfriday", _("Next Friday")),
            ("nextmonday", _("Next Monday")),
        ]
        time_choices = [
            ("startofday", _("Start of day")),
            ("startofworkingday", _("Start of working day")),
            ("currenttime", _("Current time")),
            ("endofworkingday", _("End of working day")),
            ("endofday", _("End of day")),
        ]
        self.addChoiceSetting(
            "view",
            "defaultplannedstartdatetime",
            _("Default planned start date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addChoiceSetting(
            "view",
            "defaultduedatetime",
            _("Default due date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addChoiceSetting(
            "view",
            "defaultactualstartdatetime",
            _("Default actual start date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addChoiceSetting(
            "view",
            "defaultcompletiondatetime",
            _("Default completion date and time"),
            "",
            [check_choices[1]],
            day_choices,
            time_choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.addChoiceSetting(
            "view",
            "defaultreminderdatetime",
            _("Default reminder date and time"),
            "",
            check_choices,
            day_choices,
            time_choices,
            flags=(
                wx.ALIGN_RIGHT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
                wx.ALIGN_LEFT,
            ),
        )
        self.__add_help_text()
        self.fit()

    def __add_help_text(self):
        """Add help text for the default date and time settings."""
        help_text = wx.StaticText(
            self,
            label=_(
                """New tasks start with "Preset" dates and times filled in and checked. "Proposed" dates and times are filled in, but not checked.

"Start of day" is midnight and "End of day" is just before midnight. When using these, task viewers hide the time and show only the date.

"Start of working day" and "End of working day" use the working day as set in the Features tab of this preferences dialog."""
            )
            % meta.data.metaDict,
        )
        help_text.Wrap(460)
        self.addText("", help_text)


class TaskReminderPage(SettingsPage):
    pageName = "reminder"
    pageTitle = _("Task reminders")
    pageIcon = "clock_alarm_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, growableColumn=-1, *args, **kwargs)
        names = []  # There's at least one, the universal one
        for name in notify.AbstractNotifier.names():
            names.append((name, name))
        self.addChoiceSetting(
            "feature",
            "notifier",
            _("Notification system to use for reminders"),
            "",
            names,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.EXPAND,
            ),
        )
        if operating_system.isMac() or operating_system.isGTK():
            self.addBooleanSetting(
                "feature",
                "sayreminder",
                _("Let the computer say the reminder"),
                _("(Needs espeak)") if operating_system.isGTK() else "",
                flags=(
                    wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                    wx.ALL | wx.ALIGN_LEFT,
                    wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL,
                ),
            )
        snoozeChoices = [
            (str(choice[0]), choice[1]) for choice in date.snoozeChoices
        ]
        self.addChoiceSetting(
            "view",
            "defaultsnoozetime",
            _("Default snooze time to use after reminder"),
            "",
            snoozeChoices,
            flags=(
                wx.ALIGN_RIGHT | wx.ALIGN_CENTRE_VERTICAL,
                wx.ALL | wx.ALIGN_LEFT,
            ),
        )
        self.addMultipleChoiceSettings(
            "view",
            "snoozetimes",
            _("Snooze times to offer in task reminder dialog"),
            date.snoozeChoices[1:],
            flags=(wx.ALIGN_TOP | wx.ALIGN_RIGHT, wx.ALL | wx.EXPAND),
        )  # Don't offer "Don't snooze" as a choice
        self.fit()


class IPhonePage(SettingsPage):
    pageName = "iphone"
    pageTitle = _("iPhone")
    pageIcon = "computer_handheld_icon"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)
        self.addTextSetting(
            "iphone",
            "password",
            _("Password for synchronization with iPhone"),
            helpText=_(
                "When synchronizing, enter this password on the iPhone to authorize it"
            ),
        )
        self.addTextSetting(
            "iphone", "service", _("Bonjour service name"), helpText="restart"
        )
        self.addBooleanSetting(
            "iphone", "synccompleted", _("Upload completed tasks to device")
        )
        self.addBooleanSetting(
            "iphone", "showlog", _("Show the synchronization log")
        )
        self.fit()


class EditorPage(SettingsPage):
    pageName = "editor"
    pageTitle = _("Editor")
    pageIcon = "edit"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=2, *args, **kwargs)
        if (
            operating_system.isMac()
            and not operating_system.isMacOsXMountainLion_OrNewer()
        ):
            self.addBooleanSetting(
                "editor", "maccheckspelling", _("Check spelling in editors")
            )
        self.addFontSetting(
            "editor",
            "descriptionfont",
            _("Font to use in the description field of edit dialogs"),
        )
        self.fit()

    def ok(self):
        super().ok()
        widgets.MultiLineTextCtrl.CheckSpelling = self.settings.getboolean(
            "editor", "maccheckspelling"
        )


class OSXPage(SettingsPage):
    pageName = "os_darwin"
    pageTitle = _("OS X")
    pageIcon = "mac"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)

        self.addBooleanSetting(
            "os_darwin",
            "getmailsubject",
            _("Get e-mail subject from Mail.app"),
            helpText=_(
                "When dropping an e-mail from Mail.app, try to get its subject.\nThis takes up to 20 seconds."
            ),
        )
        self.fit()


class LinuxPage(SettingsPage):
    pageName = "os_linux"
    pageTitle = _("Linux")
    pageIcon = "linux"

    def __init__(self, *args, **kwargs):
        super().__init__(columns=3, *args, **kwargs)

        self.addBooleanSetting(
            "os_linux",
            "focustextentry",
            _("Focus task subject in task editor"),
            helpText=_(
                "When opening the task editor, select the task subject and focus it.\nThis overwrites the X selection."
            ),
        )
        self.fit()


class Preferences(widgets.NotebookDialog):
    allPageNames = [
        "window",
        "save",
        "language",
        "task",
        "reminder",
        "appearance",
        "features",
        "iphone",
        "editor",
        "os_darwin",
        "os_linux",
    ]
    pages = dict(
        window=WindowBehaviorPage,
        task=TaskDatesPage,
        reminder=TaskReminderPage,
        save=SavePage,
        language=LanguagePage,
        appearance=TaskAppearancePage,
        features=FeaturesPage,
        iphone=IPhonePage,
        editor=EditorPage,
        os_darwin=OSXPage,
        os_linux=LinuxPage,
    )

    def __init__(self, settings=None, *args, **kwargs):
        self.settings = settings
        super().__init__(bitmap="wrench_icon", *args, **kwargs)
        if operating_system.isMac():
            self.CentreOnParent()

    def addPages(self):
        self._interior.SetMinSize((950, 550))
        for page_name in self.allPageNames:
            if self.__should_create_page(page_name):
                page = self.createPage(page_name)
                self._interior.AddPage(page, page.pageTitle, page.pageIcon)

    def __should_create_page(self, page_name):
        if page_name == "iphone":
            return self.settings.getboolean("feature", "iphone")
        elif page_name == "os_darwin":
            return operating_system.isMac()
        elif page_name == "os_linux":
            return operating_system.isGTK()
        else:
            return True

    def createPage(self, pageName):
        return self.pages[pageName](
            parent=self._interior, settings=self.settings
        )
