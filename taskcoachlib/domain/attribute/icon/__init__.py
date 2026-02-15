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

itemImagePlural = dict(
    cogwheel_icon="cogwheels_icon",
    envelope_icon="envelopes_icon",
    led_blue_icon="folder_blue_icon",
    led_blue_light_icon="folder_blue_light_icon",
    led_grey_icon="folder_grey_icon",
    led_green_icon="folder_green_icon",
    led_orange_icon="folder_orange_icon",
    led_purple_icon="folder_purple_icon",
    led_red_icon="folder_red_icon",
    led_yellow_icon="folder_yellow_icon",
    checkmark_green_icon="checkmark_green_icon_multiple",
    person_icon="persons_icon",
)


itemImageOpen = dict()
for _color in ["blue", "grey", "green", "orange", "purple", "red", "yellow"]:
    itemImageOpen["folder_%s_icon" % _color] = "folder_%s_open_icon" % _color


def getImageOpen(name):
    return itemImageOpen.get(name, name)


itemImageSingular = dict()
for key, value in itemImagePlural.items():
    itemImageSingular[value] = key


def getImagePlural(name):
    return itemImagePlural.get(name, name)
