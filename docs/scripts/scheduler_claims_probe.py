"""Checks of single claims behind the incremental pass analysis (to do
45 in docs/MASTER_SCHEDULER_REFACTOR.md): (a) a leaf category's rename
with a member, (b) font and colour equality, (c) an owned note
and attachment ignore their owner's style, (d) default icons, (e) an
override changes the effective style at once, outside the pass.

Run from the repository root:

    PYTHONPATH=. xvfb-run -a .venv/bin/python \
        docs/scripts/scheduler_claims_probe.py
"""

import wx

app = wx.App(False)
from taskcoachlib import config, persistence
from taskcoachlib.config import settings2

s = config.Settings(load=False)
settings2.init(s)
settings2.wx_ready()
from taskcoachlib.domain import task, attachment, category, note, date

task.Task.settings = s
attachment.Attachment.settings = s
from taskcoachlib.gui import scheduler

tf = persistence.TaskFile()
sched = scheduler.MasterScheduler(tf)
ts = date.Now()
# (a) a leaf category with a member, renamed: does the scheduler push?
c = category.Category("Alpha")
c.setForegroundColor(wx.Colour(200, 0, 0))
tf.categories().extend([c])
t = task.Task("T")
tf.tasks().extend([t])
t.addCategory(c)
sched._run_full(ts)
sched._marks = {}
print(
    "(a) T fg source before rename:",
    t.effectiveFgColorSource(),
    "; C.members:",
    c.members(),
)
sched._last_tick = ts
c.setSubject("Beta")
print("(a) objects marked by the rename:", len(sched._marks))
# (b) font equality
f1 = wx.FontFromNativeInfoString("0;Sans 10")
f2 = wx.FontFromNativeInfoString("0;Sans 10")
print(
    "(b) fonts from one string equal:",
    f1 == f2,
    "colours equal:",
    wx.Colour(1, 2, 3) == wx.Colour(1, 2, 3),
)
# (c) owned note ignores owner style
t2 = task.Task("Owner")
n = note.Note(subject="owned")
t2.addNote(n)
a = attachment.FileAttachment("f.txt")
t2.addAttachment(a)
tf.tasks().extend([t2])
t2.setForegroundColor(wx.Colour(0, 0, 200))
sched._run_full(ts)
print(
    "(c) owner fg",
    t2.effectiveFgColor(),
    t2.effectiveFgColorSource(),
    "| owned note fg",
    n.effectiveFgColor(),
    n.effectiveFgColorSource(),
    "| attachment fg",
    a.effectiveFgColor(),
    a.effectiveFgColorSource(),
    a.effectiveIcon(),
)
# (d) category icon default and note icon default
print(
    "(d) category icon:",
    repr(c.effectiveIcon()),
    c.effectiveIconSource(),
    "| note icon:",
    n.effectiveIcon(),
    n.effectiveIconSource(),
)
# (e) override outside pass: effective at once, children stale
p = task.Task("P")
ch = task.Task("Ch", parent=p)
p.addChild(ch)
tf.tasks().extend([p])
sched._run_full(ts)
p.setBackgroundColor(wx.Colour(9, 9, 9))
print(
    "(e) parent bg at once:",
    p.effectiveBgColor(),
    p.effectiveBgColorSource(),
    "| child bg before pass:",
    ch.effectiveBgColor(),
)
