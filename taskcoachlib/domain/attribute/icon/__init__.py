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
    nuvola_actions_ledblue="nuvola_mimetypes_inode-directory",
    nuvola_actions_ledlightblue="taskcoach_actions_folder_blue_light_icon",
    taskcoach_actions_led_grey_icon="nuvola_places_folder-grey",
    nuvola_actions_ledgreen="nuvola_places_folder-green",
    nuvola_actions_ledorange="nuvola_places_folder-orange",
    nuvola_actions_ledpurple="nuvola_places_folder-violet",
    nuvola_actions_ledred="nuvola_places_folder-red",
    nuvola_actions_ledyellow="nuvola_places_folder-yellow",
    nuvola_actions_ok="taskcoach_actions_checkmark_green_icon_multiple",
)


itemImageSingular = dict()
for key, value in itemImagePlural.items():
    itemImageSingular[value] = key


def getImagePlural(name):
    return itemImagePlural.get(name, name)
