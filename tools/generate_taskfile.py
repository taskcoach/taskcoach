#!/usr/bin/env python

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

# Script to generate (big) task files

import sys, random, wx

app = wx.App(False)
sys.path.insert(0, "..")
from taskcoachlib import i18n

i18n.Translator("en_US")
from taskcoachlib import persistence, config
from taskcoachlib.domain import task, category, date, effort
from taskcoachlib.gui import artprovider
import randomtext


def randomThing(thingFactory, default=None):
    return default if random.random() < 0.8 else thingFactory()


def randomDescription():
    return randomThing(
        lambda: randomtext.text(times=random.randint(3, 10)), default=""
    )


def randomSubject():
    return randomtext.title()


def randomColor():
    return randomThing(
        lambda: wx.Colour(
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
    )


def randomFont():
    return randomThing(
        lambda: wx.Font(
            pointSize=random.randint(6, 24),
            family=random.choice(
                [
                    wx.FONTFAMILY_DECORATIVE,
                    wx.FONTFAMILY_MODERN,
                    wx.FONTFAMILY_ROMAN,
                    wx.FONTFAMILY_SCRIPT,
                    wx.FONTFAMILY_SWISS,
                    wx.FONTFAMILY_TELETYPE,
                ]
            ),
            style=random.choice([wx.FONTSTYLE_ITALIC, wx.FONTSTYLE_NORMAL]),
            weight=random.choice(
                [wx.FONTWEIGHT_BOLD, wx.FONTWEIGHT_LIGHT, wx.FONTWEIGHT_NORMAL]
            ),
        )
    )


def randomIcon():
    return randomThing(
        lambda: random.choice(list(artprovider.chooseableItems.keys()))
    )


def randomDateTime(chanceNone=0.5):
    if random.random() < chanceNone:
        return None
    year = random.randint(2000, 2020)
    month = random.randint(0, 12)
    day = random.randint(0, 31)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    try:
        return date.DateTime(year, month, day, hour, minute, second)
    except ValueError:
        return randomDateTime(chanceNone)


def generateCategory(index, children=3, chanceNextLevel=0.2):
    newCategory = category.Category(
        subject="Category %s: %s" % (".".join(index), randomSubject()),
        exclusiveSubcategories=random.random() < 0.3,
        icon=randomIcon(),
        fgColor=randomColor(),
        bgColor=randomColor(),
        font=randomFont(),
        description=randomDescription(),
    )
    if random.random() < chanceNextLevel:
        for childNr in range(children):
            child = generateCategory(
                index + [str(childNr)], chanceNextLevel=chanceNextLevel / 2
            )
            newCategory.addChild(child)
    return newCategory


def assignCategories(categorizable, categories):
    for _ in range(random.randint(0, 3)):
        randomCategory = random.choice(list(categories))
        categorizable.addCategory(randomCategory)
        randomCategory.addCategorizable(categorizable)


def generateEffort():
    start = randomDateTime(0)
    stop = start + date.TimeDelta(
        hours=random.triangular(0, 10, 1),
        minutes=random.randint(0, 60),
        seconds=random.randint(0, 60),
    )
    return effort.Effort(None, start, stop, description=randomDescription())


def generateEfforts():
    efforts = []
    for _ in range(random.randint(0, 10)):
        efforts.append(generateEffort())
    return efforts


def generateTask(index, categories, children=3, chanceNextLevel=0.2):
    efforts = generateEfforts()
    newTask = task.Task(
        subject="Task %s: %s" % (".".join(index), randomSubject()),
        actualStartDateTime=randomDateTime(),
        plannedStartDateTime=randomDateTime(),
        dueDateTime=randomDateTime(),
        completionDateTime=randomDateTime(),
        priority=random.randint(0, 100),
        efforts=efforts,
        description=randomDescription(),
    )
    print(newTask.subject(recursive=True))
    assignCategories(newTask, categories)
    if random.random() < chanceNextLevel:
        for childNr in range(children):
            child = generateTask(
                index + [str(childNr)],
                categories,
                chanceNextLevel=chanceNextLevel / 2,
            )
            newTask.addChild(child)
    return newTask


def generate(nrCategories=20, nrTasks=250):
    task.Task.settings = config.Settings(load=False)
    taskFile = persistence.TaskFile()
    taskFile.setFilename("generated_taskfile.tsk")
    tasks = taskFile.tasks()
    categories = taskFile.categories()
    for index in range(nrCategories):
        categories.append(generateCategory([str(index)]))
    for index in range(nrTasks):
        tasks.append(generateTask([str(index)], categories))
    taskFile.save()


if __name__ == "__main__":
    # app = wx.App(False)
    generate()
