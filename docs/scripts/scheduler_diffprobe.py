"""Differential probe for the incremental pass (to do 45 in
docs/MASTER_SCHEDULER_REFACTOR.md, Incremental Pass). After each random
change, an emulated incremental pass processes only the marked objects
and their followers; then the real full loop runs, and every value it
still changes is a miss. To become the unit test that gates the pass.

Run from the repository root:

    PYTHONPATH=. xvfb-run -a .venv/bin/python \
        docs/scripts/scheduler_diffprobe.py SEED STEPS [MEMBERS] [OUTSIDE]

MEMBERS: "scan" (members from the items' categories) or "reverse"
(from Category.members(), their index since P29 was solved;
it missed before, while paste left notes' membership one-sided).
OUTSIDE: "yes" (follow effective events sent outside the pass, the
rule) or "no" (to show its misses).
"""

import heapq
import random
import sys

import wx

app = wx.App(False)
from taskcoachlib import config, patterns, persistence
from taskcoachlib.config import settings2

s = config.Settings(load=False)
settings2.init(s)
settings2.wx_ready()
from taskcoachlib.domain import task, attachment, category, note, effort
from taskcoachlib.domain import date as datemod
from taskcoachlib.domain import base

task.Task.settings = s
attachment.Attachment.settings = s
from taskcoachlib.gui import scheduler
from taskcoachlib.domain.base.appearance import computeStyles

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 1
STEPS = int(sys.argv[2]) if len(sys.argv) > 2 else 400
# Variants: "scan" members from item.categories(); "reverse" members
# from category.members(); "pass_only" follows effective events
# only when emitted inside the incremental pass
MEMBERS = sys.argv[3] if len(sys.argv) > 3 else "scan"
OUTSIDE_EFFECTIVE = (sys.argv[4] if len(sys.argv) > 4 else "yes") == "yes"
rnd = random.Random(SEED)

SIM = [datemod.Now()]
datemod.Now = lambda: SIM[0]
import taskcoachlib.domain.task.task as taskmodule

taskmodule.date.Now = datemod.Now

tf = persistence.TaskFile()
sched = scheduler.MasterScheduler(tf)
pub = patterns.Publisher()

DOMAIN = (task.Task, category.Category, note.Note, attachment.Attachment)


def is_domain(x):
    return isinstance(x, DOMAIN)


# ---------------------------------------------------------------- model
def link_category(item, cat):
    item.addCategory(cat)


def unlink_category(item, cat):
    item.removeCategory(cat)


COLOURS = [wx.Colour(200, 0, 0), wx.Colour(0, 150, 0), wx.Colour(0, 0, 200)]
ICONS = ["nuvola_actions_edit", "nuvola_apps_korganizer", "nuvola_apps_clock"]

cats = []
for i in range(8):
    parent = rnd.choice(cats) if cats and rnd.random() < 0.5 else None
    c = category.Category("C%d" % i, parent=parent)
    if parent:
        parent.addChild(c)
    if rnd.random() < 0.5:
        c.setForegroundColor(rnd.choice(COLOURS))
    if rnd.random() < 0.3:
        c.set_icon_id(rnd.choice(ICONS))
    c.setStylePriority(rnd.randint(0, 2))
    cats.append(c)
tf.categories().extend([c for c in cats if c.parent() is None])

now = SIM[0]
tasks = []
for i in range(30):
    parent = rnd.choice(tasks) if tasks and rnd.random() < 0.6 else None
    kwargs = {}
    r = rnd.random()
    if r < 0.2:
        kwargs["dueDateTime"] = now + datemod.TimeDelta(
            hours=rnd.randint(-5, 50)
        )
    elif r < 0.4:
        kwargs["actualStartDateTime"] = now - datemod.TimeDelta(hours=1)
    elif r < 0.5:
        kwargs["plannedStartDateTime"] = now + datemod.TimeDelta(
            minutes=rnd.randint(-60, 600)
        )
    if rnd.random() < 0.2:
        kwargs["reminder"] = now + datemod.TimeDelta(
            minutes=rnd.randint(-5, 600)
        )
    t = task.Task("T%d" % i, parent=parent, **kwargs)
    if parent:
        parent.addChild(t)
    tasks.append(t)
for t in tasks:
    for c in rnd.sample(cats, rnd.randint(0, 2)):
        link_category(t, c)
    if rnd.random() < 0.2:
        t.setBackgroundColor(rnd.choice(COLOURS))
tf.tasks().extend([t for t in tasks if t.parent() is None])

gnotes = []
for i in range(8):
    parent = rnd.choice(gnotes) if gnotes and rnd.random() < 0.5 else None
    n = note.Note(subject="N%d" % i, parent=parent)
    if parent:
        parent.addChild(n)
    gnotes.append(n)
for n in gnotes:
    for c in rnd.sample(cats, rnd.randint(0, 1)):
        link_category(n, c)
tf.notes().extend([n for n in gnotes if n.parent() is None])


def make_owned(owner):
    n = note.Note(subject="owned-%s" % owner.subject())
    if rnd.random() < 0.5:
        link_category(n, rnd.choice(cats))
    sub = note.Note(subject="sub-%s" % owner.subject())
    n.addChild(sub)
    if hasattr(owner, "addNote"):
        owner.addNote(n)
    if hasattr(owner, "addAttachment"):
        a = attachment.FileAttachment("x-%s.txt" % owner.subject())
        a.addNote(note.Note(subject="attnote"))
        owner.addAttachment(a)


for owner in (
    rnd.sample(tasks, 8) + rnd.sample(cats, 2) + rnd.sample(gnotes, 2)
):
    make_owned(owner)


# ------------------------------------------------------------ helpers
def owned_of(obj):
    out = []
    if hasattr(obj, "notes"):
        out.extend(obj.notes(recursive=True))
    if hasattr(obj, "attachments"):
        out.extend(obj.attachments())
    res = []
    for each in out:
        res.append(each)
        res.extend(owned_of(each))
    return res


def live_objects():
    live = []
    for coll in (tf.categories(), tf.tasks(), tf.notes()):
        for each in coll.allItemsSorted():
            live.append(each)
            live.extend(owned_of(each))
    return live


def kind_rank(obj):
    if isinstance(obj, category.Category):
        return 0
    if isinstance(obj, task.Task):
        return 1
    if isinstance(obj, note.Note):
        return 2
    return 3


def depth(obj):
    d = 0
    p = obj.parent() if hasattr(obj, "parent") else None
    while p is not None:
        d += 1
        p = p.parent()
    return d


def order_key(obj):
    return (kind_rank(obj), depth(obj))


def members(cat, live):
    if MEMBERS == "reverse":
        return [x for x in cat.members() if id(x) in live]
    return [
        x
        for x in live.values()
        if hasattr(x, "categories") and cat in x.categories()
    ]


def followers(obj, live):
    out = list(obj.children()) if hasattr(obj, "children") else []
    if isinstance(obj, category.Category):
        out.extend(members(obj, live))
    return out


def subtree(obj):
    out = [obj]
    if hasattr(obj, "children"):
        out.extend(obj.children(recursive=True))
    for each in list(out):
        out.extend(owned_of(each))
    return out


# ------------------------------------------------------------ events
SUBSCRIBED = (
    scheduler._data_event_types()
    | set(scheduler._APPEARANCE_SETTINGS)
    | {
        k.subjectChangedEventType()
        for k in (task.Task, category.Category, note.Note)
    }
)
for coll in (tf.tasks(), tf.categories(), tf.notes()):
    SUBSCRIBED |= {coll.addItemEventType(), coll.removeItemEventType()}
EFFECTIVE = {
    "effective.fgColor",
    "effective.bgColor",
    "effective.icon",
    "effective.font",
}
VALUE_TYPES_SUFFIX = (".add", "child.add", ".notes", ".attachments")

recorded = []


class Recorder:
    def on_event(self, event):
        for t in event.types():
            recorded.append((t, list(event.sources(t)), event))


REC = Recorder()
for et in SUBSCRIBED | {"task.reminder.trigger"}:
    pub.registerObserver(REC.on_event, eventType=et)


# ------------------------------------------------------------ timers
heap = []
counter = [0]


def push_task(t):
    for sec in t.timer_seconds(s.getint("behavior", "duesoonhours")):
        counter[0] += 1
        heapq.heappush(heap, (sec, counter[0], t))


for t in tasks:
    push_task(t)

TIME_TYPES = {
    "task.plannedStartDateTime",
    "task.actualStartDateTime",
    "task.dueDateTime",
    "task.reminder",
}


# ------------------------------------------------------------ passes
def full_pass(ts):
    del recorded[:]
    sched._run_pass(ts, 1)
    changes = [
        (t, srcs)
        for t, srcs, _ in recorded
        if t.startswith(("derived.", "effective."))
        or t in ("task.status", "task.reminder")
    ]
    triggers = {
        id(x)
        for t, srcs, _ in recorded
        if t == "task.reminder.trigger"
        for x in srcs
    }
    del recorded[:]
    return changes, triggers


def marks_from(events, live):
    marks = {}

    def mark(x):
        if is_domain(x) and id(x) in live:
            marks[id(x)] = x

    for etype, srcs, event in events:
        for x in srcs:
            mark(x)
        if etype.endswith(VALUE_TYPES_SUFFIX):
            for src in srcs:
                for v in event.values(src, etype):
                    if is_domain(v):
                        if (
                            __import__("os").environ.get("NO_OWNED_SUBTREE")
                            == "1"
                        ):
                            mark(v)
                        else:
                            for y in subtree(v):
                                mark(y)
        if etype in EFFECTIVE and OUTSIDE_EFFECTIVE:
            for x in srcs:
                if is_domain(x) and id(x) in live:
                    for f in followers(x, live):
                        mark(f)
        if (
            etype.endswith(".subject")
            and __import__("os").environ.get("NO_SUBJECT") != "1"
        ) or (
            etype == "category.stylePriority"
            and __import__("os").environ.get("NO_PRIORITY") != "1"
        ):
            for x in srcs:
                if isinstance(x, category.Category) and id(x) in live:
                    for f in followers(x, live):
                        mark(f)
    return marks


ordering_violations = []
double_visits = []


def incremental_pass(ts, marks, live):
    # Timer entries due
    while heap and heap[0][0] <= ts:
        _, _, t = heapq.heappop(heap)
        if id(t) in live:
            marks[id(t)] = t
    work = []
    seen = set()
    queued = set()

    def queue(x):
        if id(x) in queued or id(x) not in live:
            return
        queued.add(id(x))
        heapq.heappush(work, (order_key(x), id(x), x))

    for x in marks.values():
        queue(x)
    processed = 0
    triggers = set()
    while work:
        key, _, x = heapq.heappop(work)
        if id(x) in seen:
            double_visits.append(x)
            continue
        seen.add(id(x))
        del recorded[:]
        if isinstance(x, task.Task):
            x.compute_stored_status(ts)
            x.processReminder(ts)
        computeStyles(x)
        processed += 1
        evs = list(recorded)
        del recorded[:]
        for etype, srcs, event in evs:
            if etype == "task.reminder.trigger":
                triggers.update(id(y) for y in srcs)
            if etype in EFFECTIVE or etype == "task.status":
                for y in srcs:
                    if y is x:
                        fl = followers(x, live) if etype in EFFECTIVE else [x]
                        for f in fl:
                            if f is x:
                                continue
                            if order_key(f) <= key:
                                ordering_violations.append((x, f))
                            if id(f) in seen:
                                ordering_violations.append(("after", x, f))
                            queue(f)
            if etype in TIME_TYPES:
                for y in srcs:
                    if isinstance(y, task.Task):
                        push_task(y)
    return processed, triggers


# ------------------------------------------------------------ mutations
def live_tasks():
    return list(tf.tasks())


def rand_live(kinds=None):
    lv = [x for x in live_objects() if kinds is None or isinstance(x, kinds)]
    return rnd.choice(lv) if lv else None


removed_tasks = []
efforts_running = []


def m_override():
    x = rand_live()
    what = rnd.choice(["fg", "bg", "icon", "clearfg", "clearicon"])
    if what == "fg":
        x.setForegroundColor(rnd.choice(COLOURS))
    elif what == "bg":
        x.setBackgroundColor(rnd.choice(COLOURS))
    elif what == "icon":
        x.set_icon_id(rnd.choice(ICONS))
    elif what == "clearfg":
        x.setForegroundColor(None)
    else:
        x.set_icon_id("")
    return "override %s %s" % (what, x.subject())


def m_cat_link():
    x = rand_live((task.Task, note.Note))
    c = rnd.choice([c for c in tf.categories()])
    if c in x.categories():
        unlink_category(x, c)
        return "unlink %s from %s" % (c.subject(), x.subject())
    link_category(x, c)
    return "link %s to %s" % (c.subject(), x.subject())


def m_priority():
    c = rnd.choice(list(tf.categories()))
    c.setStylePriority(rnd.randint(0, 3))
    return "priority %s" % c.subject()


def m_rename():
    x = rand_live((task.Task, category.Category, note.Note))
    x.setSubject(
        x.subject() + "x" if rnd.random() < 0.5 else "A" + x.subject()
    )
    return "rename %s" % x.subject()


def m_move_task():
    t = rnd.choice(live_tasks())
    candidates = [
        p
        for p in live_tasks()
        if p is not t and p not in t.children(recursive=True)
    ]
    newp = rnd.choice(candidates + [None])
    tf.tasks().removeItems([t])
    t.set_parent(newp)
    tf.tasks().extend([t])
    return "move task %s under %s" % (t.subject(), newp and newp.subject())


def m_move_cat():
    c = rnd.choice(list(tf.categories()))
    candidates = [
        p
        for p in tf.categories()
        if p is not c and p not in c.children(recursive=True)
    ]
    newp = rnd.choice(candidates + [None])
    tf.categories().removeItems([c])
    c.set_parent(newp)
    tf.categories().extend([c])
    return "move cat %s under %s" % (c.subject(), newp and newp.subject())


def m_tracking():
    if efforts_running and rnd.random() < 0.5:
        e = efforts_running.pop()
        e.setStop()
        return "stop tracking %s" % e.task().subject()
    t = rnd.choice(live_tasks())
    e = effort.Effort(t)
    t.addEffort(e)
    efforts_running.append(e)
    return "track %s" % t.subject()


def m_dates():
    t = rnd.choice(live_tasks())
    ts = SIM[0]
    what = rnd.choice(
        ["due", "actual", "planned", "complete", "reopen", "reminder"]
    )
    if what == "due":
        t.set_due_date_time(
            ts + datemod.TimeDelta(minutes=rnd.randint(-120, 3000))
        )
    elif what == "actual":
        t.set_actual_start_date_time(
            ts + datemod.TimeDelta(minutes=rnd.randint(-60, 60))
        )
    elif what == "planned":
        t.set_planned_start_date_time(
            ts + datemod.TimeDelta(minutes=rnd.randint(-60, 60))
        )
    elif what == "complete":
        t.set_completion_date_time(ts)
    elif what == "reopen":
        t.set_completion_date_time(t.maxDateTime)
    else:
        t.set_reminder(ts + datemod.TimeDelta(minutes=rnd.randint(-3, 30)))
    return "%s %s" % (what, t.subject())


def m_prereq():
    a, b = rnd.sample(live_tasks(), 2)
    if b in a.prerequisites():
        a.remove_prerequisites([b])
        a.removeTaskAsDependencyOf([b])
        return "unprereq"
    if a in b.prerequisites(recursive=True, upwards=True):
        return "noop"
    a.add_prerequisites([b])
    a.addTaskAsDependencyOf([b])
    return "prereq %s needs %s" % (a.subject(), b.subject())


def m_new_task():
    parent = rnd.choice(live_tasks() + [None])
    t = task.Task("New%d" % rnd.randint(0, 9999), parent=parent)
    if rnd.random() < 0.5:
        link_category(t, rnd.choice(list(tf.categories())))
    make_owned(t)
    tf.tasks().extend([t])
    return "new task under %s" % (parent and parent.subject())


def m_owned():
    owner = rand_live(
        (task.Task, category.Category, note.Note, attachment.Attachment)
    )
    if isinstance(owner, attachment.Attachment):
        owner.addNote(note.Note(subject="late"))
        return "attachment note"
    make_owned(owner)
    return "owned added to %s" % owner.subject()


def m_subnote():
    parent = rand_live(note.Note)
    sub = note.Note(subject="late-sub")
    if rnd.random() < 0.5:
        link_category(sub, rnd.choice(list(tf.categories())))
    if parent in tf.notes():
        sub.set_parent(parent)
        tf.notes().extend([sub])
    else:
        parent.addChild(sub)
    return "subnote under %s" % parent.subject()


def m_delete_undo():
    if removed_tasks and rnd.random() < 0.5:
        t = removed_tasks.pop()
        tf.tasks().extend([t])
        return "undelete %s" % t.subject()
    roots = [t for t in live_tasks()]
    t = rnd.choice(roots)
    tf.tasks().removeItems([t])
    removed_tasks.append(t)
    return "delete %s" % t.subject()


def m_setstate():
    x = rand_live((task.Task, category.Category))
    state = x.__getstate__()
    x.setForegroundColor(rnd.choice(COLOURS))
    if isinstance(x, task.Task):
        x.set_due_date_time(SIM[0] - datemod.TimeDelta(hours=1))
    x.__setstate__(state)
    return "setstate %s" % x.subject()


def m_clock():
    SIM[0] = SIM[0] + rnd.choice(
        [
            datemod.TimeDelta(seconds=1),
            datemod.TimeDelta(minutes=30),
            datemod.TimeDelta(hours=3),
            datemod.TimeDelta(hours=30),
        ]
    )
    return "clock to %s" % SIM[0]


def m_paste():
    t = rnd.choice(live_tasks())
    c = t.copy()
    c.set_parent(None)
    tf.tasks().extend([c])
    return "paste copy of %s" % t.subject()


MUTATIONS = [
    m_paste,
    m_override,
    m_cat_link,
    m_priority,
    m_rename,
    m_move_task,
    m_move_cat,
    m_tracking,
    m_dates,
    m_prereq,
    m_new_task,
    m_owned,
    m_subnote,
    m_delete_undo,
    m_setstate,
    m_clock,
]

# ------------------------------------------------------------ run
ts = SIM[0]
changes, _ = full_pass(ts)
while heap and heap[0][0] <= ts:
    heapq.heappop(heap)
second, _ = full_pass(ts)
print(
    "first full pass changes:",
    len(changes),
    "; second full pass changes:",
    len(second),
)

misses = 0
total_processed = 0
trigger_diffs = 0
for step in range(STEPS):
    del recorded[:]
    desc = rnd.choice(MUTATIONS)()
    events = list(recorded)
    del recorded[:]
    ts = SIM[0]
    live = {id(x): x for x in live_objects()}
    # Time entries of tasks whose dates changed or which were added
    for etype, srcs, event in events:
        if etype in TIME_TYPES:
            for y in srcs:
                if isinstance(y, task.Task):
                    push_task(y)
        if etype == tf.tasks().addItemEventType():
            for v in event.values(tf.tasks(), etype):
                push_task(v)
    marks = marks_from(events, live)
    processed, inc_triggers = incremental_pass(ts, marks, live)
    total_processed += processed
    changes, full_triggers = full_pass(ts)
    if changes:
        misses += 1
        print(
            "MISS after step %d (%s): %s"
            % (
                step,
                desc,
                [
                    (t, [getattr(x, "subject", lambda: x)() for x in srcs])
                    for t, srcs in changes
                ][:6],
            )
        )
    if full_triggers - inc_triggers:
        trigger_diffs += 1
print(
    "steps",
    STEPS,
    "misses",
    misses,
    "avg processed",
    total_processed / STEPS,
    "live",
    len(live_objects()),
    "ordering violations",
    len(ordering_violations),
    "double visits",
    len(double_visits),
    "steps where full pass re-triggered more reminders",
    trigger_diffs,
)
for v in ordering_violations[:5]:
    print("ORDER", v)
