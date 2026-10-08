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

import datetime
from unittest import mock

import wx

import test
from taskcoachlib import gui, patterns
from taskcoachlib.config import settings
from taskcoachlib.tools import wxhelper


class PreferencesTest(test.wxTestCase):
    def setUp(self):
        super().setUp()
        self.preferences = gui.dialog.preferences.Preferences(
            parent=self.frame, title="Test"
        )
        self.original_color = settings.fgcolor.activetasks
        self.new_color = (1, 2, 29)

    # pylint: disable=W0212

    def test_cancel(self):
        # Page 7 = Statuses tab; color index 8 = active tasks light fg
        self.preferences[7]._colorSettings[8][2].SetColour(self.new_color)
        self.preferences.cancel()
        self.assertEqual(self.original_color, settings.fgcolor.activetasks)

    def test_ok(self):
        # Page 7 = Statuses tab; color index 8 = active tasks light fg
        self.preferences[7]._colorSettings[8][2].SetColour(self.new_color)
        self.preferences.ok()
        self.assertEqual(self.new_color, settings.fgcolor.activetasks[:3])


class PreferencesEditTestCase(test.wxTestCase):
    """Edits as the user makes them: the control's change event."""

    # pylint: disable=W0212

    def setUp(self):
        super().setUp()
        self.preferences = gui.dialog.preferences.Preferences(
            parent=self.frame, title="Test"
        )
        self.redrawn = []
        for event_type in (
            "calendar.colours.changed",
            "spellcheck.colours.changed",
        ):
            patterns.Publisher().registerObserver(
                self.on_redraw, eventType=event_type
            )

    def on_redraw(self, event):
        self.redrawn.append(event.type())

    def page(self, name):
        return [p for p in self.preferences._interior if p.pageName == name][0]

    @staticmethod
    def click(control, event_type=wx.wxEVT_BUTTON):
        event = wx.CommandEvent(event_type, control.GetId())
        event.SetEventObject(control)
        control.ProcessWindowEvent(event)

    @staticmethod
    def pick(picker, colour):
        picker.SetColour(colour)
        picker.ProcessWindowEvent(
            wx.ColourPickerEvent(picker, picker.GetId(), wx.Colour(*colour))
        )

    def picker(self, section, key):
        for picker_section, picker_key, picker in self.page(
            "theme"
        )._colorSettings:
            if (picker_section, picker_key) == (section, key):
                return picker

    def delete_task_preset(self, minutes):
        page = self.page("presets")
        for button in page._DurationPresetsPage__deleteButtons:
            if button.presetValue == minutes:
                self.click(button)
                return

    def add_task_preset(self, minutes):
        page = self.page("presets")
        page._DurationPresetsPage__durationEntry.SetDuration(
            datetime.timedelta(minutes=minutes)
        )
        self.click(page._DurationPresetsPage__addBtn)

    def choose(self, choice, index):
        choice.SetSelection(index)
        self.click(choice, wx.wxEVT_CHOICE)

    def toggle(self, check_box):
        check_box.SetValue(not check_box.GetValue())
        self.click(check_box, wx.wxEVT_CHECKBOX)

    def button(self, button_id):
        return wxhelper.get_dialog_button(self.preferences._buttons, button_id)

    def apply_enabled(self):
        wx.GetApp().ProcessPendingEvents()  # The update runs soon after
        return self.button(wx.ID_APPLY).IsEnabled()


class PreferencesCancelTest(PreferencesEditTestCase):
    """Every page's changes are saved by OK or Apply, and Cancel drops
    them, the Durations and Theme pages too (docs/PREFERENCES.md, OK,
    Apply and Cancel)."""

    def test_cancel_drops_a_deleted_duration_preset(self):
        self.delete_task_preset(2880)
        self.preferences.cancel()
        self.assertEqual(
            "60,120,1440,2880", settings.feature.task_duration_presets
        )

    def test_cancel_drops_an_added_duration_preset(self):
        self.add_task_preset(180)
        self.preferences.cancel()
        self.assertEqual(
            "60,120,1440,2880", settings.feature.task_duration_presets
        )

    def test_ok_saves_the_duration_presets(self):
        self.delete_task_preset(2880)
        self.add_task_preset(180)
        self.preferences.ok()
        self.assertEqual(
            "60,120,180,1440", settings.feature.task_duration_presets
        )

    def flow_choice(self):
        for section, setting, choices in self.page("statuses")._choiceSettings:
            if (section, setting) == ("appearance", "flow"):
                return choices[0]

    def test_appearance_flow_from_categories_and_tasks_by_default(self):
        self.assertEqual(
            "all",
            self.flow_choice().GetClientData(
                self.flow_choice().GetSelection()
            ),
        )

    def test_ok_saves_the_appearance_flow(self):
        self.choose(self.flow_choice(), 3)
        self.preferences.ok()
        self.assertEqual("none", settings.get("appearance", "flow"))

    def test_cancel_drops_a_picked_calendar_colour(self):
        original = settings.calendar_light.weekday_header_bg
        self.pick(
            self.picker("calendar_light", "weekday_header_bg"), (1, 2, 3)
        )
        self.preferences.cancel()
        self.assertEqual(original, settings.calendar_light.weekday_header_bg)
        self.assertEqual([], self.redrawn)

    def test_ok_saves_a_picked_calendar_colour_and_redraws(self):
        self.pick(
            self.picker("calendar_light", "weekday_header_bg"), (1, 2, 3)
        )
        self.preferences.ok()
        self.assertEqual(
            (1, 2, 3), settings.calendar_light.weekday_header_bg[:3]
        )
        self.assertEqual(["calendar.colours.changed"], self.redrawn)

    def test_cancel_drops_a_reset_calendar_colour(self):
        settings.calendar_light.weekday_header_bg = (1, 2, 3, 255)
        self.preferences = gui.dialog.preferences.Preferences(
            parent=self.frame, title="Test"
        )
        page = self.page("theme")
        resets = [
            child
            for child in page.GetChildren()
            if isinstance(child, wx.Button) and child.GetLabel() == "Reset"
        ]
        self.click(resets[0])  # The first row, Weekday Header Background
        self.preferences.cancel()
        self.assertEqual(
            (1, 2, 3, 255), settings.calendar_light.weekday_header_bg
        )

    def test_cancel_drops_the_other_months_system_choice(self):
        check = self.page("theme")._other_month_light_check
        check.SetValue(not check.GetValue())
        self.click(check, wx.wxEVT_CHECKBOX)
        self.preferences.cancel()
        self.assertTrue(settings.calendar_light.other_month_bg_system)

    def test_ok_saves_a_picked_other_months_colour(self):
        self.pick(self.page("theme")._other_month_light_picker, (1, 2, 3))
        self.preferences.ok()
        self.assertEqual((1, 2, 3), settings.calendar_light.other_month_bg[:3])
        self.assertFalse(settings.calendar_light.other_month_bg_system)

    def test_unchecking_system_shows_the_other_months_colour_used(self):
        page = self.page("theme")
        page._is_dark = False  # The light column shows the system's
        check = page._other_month_light_check
        check.SetValue(True)
        self.click(check, wx.wxEVT_CHECKBOX)
        self.toggle(check)
        self.assertEqual(
            settings.calendar_light.other_month_bg,
            tuple(page._other_month_light_picker.GetColour()),
        )

    def test_cancel_drops_a_picked_spelling_colour(self):
        original = settings.spellcheck_light.squiggle_color
        self.pick(self.picker("spellcheck_light", "squiggle_color"), (1, 2, 3))
        self.preferences.cancel()
        self.assertEqual(original, settings.spellcheck_light.squiggle_color)

    def test_ok_saves_a_picked_spelling_colour_and_redraws(self):
        self.pick(self.picker("spellcheck_light", "squiggle_color"), (1, 2, 3))
        self.preferences.ok()
        self.assertEqual(
            (1, 2, 3), settings.spellcheck_light.squiggle_color[:3]
        )
        self.assertEqual(["spellcheck.colours.changed"], self.redrawn)

    def test_apply_then_cancel_keeps_what_was_applied(self):
        self.delete_task_preset(2880)
        self.preferences.apply()
        self.preferences.cancel()
        self.assertEqual("60,120,1440", settings.feature.task_duration_presets)

    def test_ok_with_nothing_changed_redraws_nothing(self):
        self.preferences.ok()
        self.assertEqual([], self.redrawn)

    def test_ok_with_nothing_changed_does_not_sort_again(self):
        patterns.Publisher().registerObserver(
            self.on_redraw, eventType="settings.statussortpriority.changed"
        )
        self.preferences.ok()
        self.assertEqual([], self.redrawn)


class PreferencesButtonsTest(PreferencesEditTestCase):
    """Apply is greyed until a page differs from what it showed; OK
    and Cancel are always enabled (docs/PREFERENCES.md, OK, Apply and
    Cancel)."""

    def test_apply_is_greyed_when_opened(self):
        self.assertFalse(self.apply_enabled())

    def test_ok_and_cancel_are_enabled(self):
        self.assertTrue(self.button(wx.ID_OK).IsEnabled())
        self.assertTrue(self.button(wx.ID_CANCEL).IsEnabled())

    def test_a_checkbox_enables_apply(self):
        self.toggle(self.page("window")._booleanSettings[0][2])
        self.assertTrue(self.apply_enabled())

    def test_undoing_the_change_greys_apply_again(self):
        check_box = self.page("window")._booleanSettings[0][2]
        self.toggle(check_box)
        self.toggle(check_box)
        self.assertFalse(self.apply_enabled())

    def test_apply_greys_apply_again(self):
        self.toggle(self.page("window")._booleanSettings[0][2])
        self.preferences.apply()
        self.assertFalse(self.apply_enabled())
        self.assertTrue(self.button(wx.ID_OK).IsEnabled())

    def test_a_choice_enables_apply(self):
        choice = self.page("features")._choiceSettings[0][2][0]
        self.choose(choice, 1 - choice.GetSelection())
        self.assertTrue(self.apply_enabled())

    def test_a_number_typed_enables_apply(self):
        spin = self.page("theme")._integerSettings[0][2]
        spin._textCtrl.SetValue(str(spin.GetValue() + 1))
        self.assertTrue(self.apply_enabled())

    def test_a_list_check_enables_apply(self):
        snooze_times = self.page("reminder")._multipleChoiceSettings[0][2]
        snooze_times.Check(0, not snooze_times.IsChecked(0))
        self.click(snooze_times, wx.wxEVT_CHECKLISTBOX)
        self.assertTrue(self.apply_enabled())

    def test_a_status_priority_enables_apply(self):
        page = self.page("statuses")
        choice = page._priorityChoices[0][1]
        self.choose(choice, (choice.GetSelection() + 1) % choice.GetCount())
        self.assertTrue(self.apply_enabled())

    def test_a_regional_format_enables_apply(self):
        choice = self.page("language")._date_format_choice
        self.choose(choice, (choice.GetSelection() + 1) % choice.GetCount())
        self.assertTrue(self.apply_enabled())

    def test_working_hours_enable_apply(self):
        choice = self.page("features")._workingHourStartChoice
        self.choose(choice, (choice.GetSelection() + 1) % 6)
        self.assertTrue(self.apply_enabled())

    def test_a_picked_colour_enables_apply(self):
        self.pick(self.picker("calendar_light", "today_border"), (1, 2, 3))
        self.assertTrue(self.apply_enabled())

    def test_an_other_months_colour_enables_apply(self):
        self.pick(self.page("theme")._other_month_dark_picker, (1, 2, 3))
        self.assertTrue(self.apply_enabled())

    def test_a_deleted_duration_preset_enables_apply(self):
        self.delete_task_preset(2880)
        self.assertTrue(self.apply_enabled())

    def test_a_reset_with_nothing_to_reset_keeps_apply_greyed(self):
        page = self.page("theme")
        resets = [
            child
            for child in page.GetChildren()
            if isinstance(child, wx.Button) and child.GetLabel() == "Reset"
        ]
        self.click(resets[0])
        self.assertFalse(self.apply_enabled())


class PreferencesSizeTest(test.wxTestCase):
    """Preferences opens at most 80% of the screen, its pages
    scrolling (docs/WINDOW_GEOMETRY.md, Decisions 10)."""

    def open(self):
        preferences = gui.dialog.preferences.Preferences(
            parent=self.frame, title="Test"
        )
        return preferences

    def test_a_laptop_screen_cuts_it(self):
        with mock.patch.object(
            wxhelper, "work_area_of", return_value=(0, 0, 1366, 728)
        ):
            preferences = self.open()
        self.assertEqual((1092, 582), tuple(preferences.GetSize()))

    def test_it_can_be_made_smaller(self):
        preferences = self.open()
        preferences.SetSize(600, 400)
        self.assertEqual((600, 400), tuple(preferences.GetSize()))
        self.assertTrue(preferences._interior.GetMinSize() == (-1, -1))
