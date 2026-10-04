"""Whether an older release opens this version's files as it left them
(docs/PERSISTENCE_XML.md, Versions and Compatibility).

From Welcome.tsk it builds a file with every field, then runs each
version's own code to load and save it:

1. old, new, old: the old release saves the file, this version opens
   and saves it, the old release opens and saves it again. Its two
   saves must be equal: nothing it shows is lost or changed.
2. new, old, new: this version saves the file (with a mail attachment
   too), the old release opens and saves it, this version opens and
   saves it again. Listed: what the old release drops, which it does
   not know.

Differences only below a second are listed apart: this version keeps
whole seconds, and the releases show such dates alike.

Run from the repository root, with a display:

    xvfb-run -a .venv/bin/python docs/scripts/format_compat_check.py \\
        v2.0.2.0 --old-python /path/to/python

The old release's code comes from `git archive TAG`; --old-python must
have that release's packages (2.0.2.0 needs fasteners; later releases
run on the system Python). Exit status 1 when the first round trip
changes anything but sub-second date parts.
"""

import argparse
import collections
import datetime
import os
import re
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

REPOSITORY = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
MAIL = dict(
    id="33333333-3333-4333-8333-333333333333",
    subject="Quarterly figures",
    type="uri",
    location="mid:abc123@example.org",
    fromName="Alice Example",
    fromAddress="alice@example.org",
    sentDateTime="2026-01-12 09:30:00",
    creationDateTime="2026-01-12 10:00:00",
)


def roundtrip(code, source, target):
    """Load the file with the code base in `code` and save it again."""
    sys.path.insert(0, code)
    os.chdir(code)
    import taskcoachlib.workarounds.monkeypatches  # noqa: F401
    import wx

    app = wx.App(False)  # noqa: F841
    from taskcoachlib import config, persistence
    from taskcoachlib.domain import task

    task.Task.settings = config.Settings(load=False)
    try:
        from taskcoachlib.config import settings2
    except ImportError:  # Releases before settings2
        settings2 = None
    if settings2 and not settings2._initialized:
        settings2.init(task.Task.settings)
        settings2.wx_ready()
    use = getattr(config.settings, "use", None)  # Since settings2 went
    if use:
        use(task.Task.settings)
    task_file = persistence.TaskFile()
    task_file.setFilename(source)
    task_file.load()
    task_file.saveas(target)


def run(python, code, source, target):
    subprocess.run(
        [
            python,
            os.path.abspath(__file__),
            "--roundtrip",
            code,
            source,
            target,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def parse(path):
    """The file's tree, and its version line, which the tree leaves
    out."""
    with open(path, encoding="utf-8") as file:
        text = file.read()
    version = re.search(r"<\?taskcoach .*?\?>", text).group(0)
    return ElementTree.ElementTree(ElementTree.fromstring(text)), version


def write(tree, version, target):
    """The file, with its version line: the releases refuse it
    without."""
    with open(target, "w", encoding="utf-8") as file:
        file.write('<?xml version="1.0" encoding="utf-8"?>\n%s\n' % version)
        tree.write(file, encoding="unicode")


def find(root, prefix, tag=None):
    for node in root.iter():
        if node.get("id", "").startswith(prefix) and tag in (None, node.tag):
            return node
    raise KeyError(prefix)


def build_rich_file(target):
    """Welcome.tsk with every field the format has (tskversion 37)."""
    tree, version = parse(os.path.join(REPOSITORY, "Welcome.tsk"))
    root = tree.getroot()
    each = find(root, "5cc7a252", "task")
    for name, value in dict(
        budget="10:30:00",
        plannedDuration="2:00:00",
        plannedDurationMode="adjdue",
        priority="-3",
        hourlyFee="75.5",
        fixedFee="500.0",
        percentageComplete="40",
        reminder="2027-01-02 09:00:00",
        reminderBeforeSnooze="2027-01-02 08:00:00",
        shouldMarkCompletedWhenAllChildrenCompleted="False",
        fgColor="(10, 20, 30, 255)",
        bgColor="(200, 210, 220, 255)",
        icon="nuvola_apps_clock",
        selectedIcon="nuvola_actions_go-next",
        ordering="5",
    ).items():
        each.set(name, value)
    ElementTree.SubElement(
        each,
        "recurrence",
        dict(
            unit="weekly",
            amount="2",
            count="1",
            max="5",
            stop_datetime="2027-06-01 00:00:00",
            sameWeekday="True",
            recurBasedOnCompletion="True",
            weekdays="0,2",
        ),
    )
    effort = find(root, "f0109306", "effort")
    effort.set("entryMode", "duration")
    ElementTree.SubElement(effort, "description").text = "Effort description"
    find(root, "80f0f933", "category").set("exclusiveSubcategories", "True")
    find(root, "f0109811", "category").set("filtered", "True")
    work = find(root, "42afb411", "category")
    members = work.get("categorizables").split()
    # A subtask, notes of a task, a note, an attachment and a note
    for prefix in ("7be82e5c", "a1b2c307", "098b2f1e", "2eb06ab6", "3307cece"):
        members.append(find(root, prefix).get("id"))
    work.set("categorizables", " ".join(members))
    ElementTree.SubElement(
        find(root, "e9f1cf82", "task"),
        "attachment",
        dict(
            id="11111111-1111-4111-8111-111111111111",
            status="1",
            subject="A link",
            type="uri",
            location="https://example.org/page",
        ),
    )
    write(tree, version, target)


def add_mail(source, target):
    """A mail attachment, as this version writes it."""
    tree, version = parse(source)
    ElementTree.SubElement(
        find(tree.getroot(), "e9f1cf82", "task"), "attachment", MAIL
    )
    write(tree, version, target)


def index(path):
    """Each element's attributes, by ID."""
    items = {}

    def walk(node, parent):
        for child in node:
            if child.tag in ("description", "recurrence"):
                continue
            key = child.get("id") or "%s/%s" % (parent, child.tag)
            attributes = dict(child.attrib)
            description = child.find("description")
            if description is not None:
                attributes["<description>"] = description.text or ""
            recurrence = child.find("recurrence")
            if recurrence is not None:
                for name, value in recurrence.attrib.items():
                    attributes["recurrence." + name] = value
            items[key] = (child.tag, attributes)
            walk(child, key)

    walk(ElementTree.parse(path).getroot(), "root")
    return items


def same_second(first, second):
    try:
        first, second = (
            datetime.datetime.fromisoformat(each) for each in (first, second)
        )
    except (TypeError, ValueError):
        return False
    return first.replace(microsecond=0) == second.replace(microsecond=0)


def compare(first, second):
    """Differences by (element, attribute): changed, and sub-second."""
    first, second = index(first), index(second)
    changed, sub_second = collections.Counter(), collections.Counter()
    for key in sorted(set(first) | set(second)):
        if key not in first or key not in second:
            tag = (first.get(key) or second.get(key))[0]
            changed[(tag, "element missing in one")] += 1
            continue
        (tag, a), (_, b) = first[key], second[key]
        for name in sorted(set(a) | set(b)):
            if a.get(name) == b.get(name):
                continue
            if same_second(a.get(name), b.get(name)):
                sub_second[(tag, name)] += 1
            else:
                changed[(tag, name)] += 1
    return changed, sub_second


def report(title, changed, sub_second):
    print("== " + title)
    for (tag, name), count in sorted(changed.items()):
        print("   %-11s %-28s x%d" % (tag, name, count))
    if sub_second:
        print(
            "   sub-second date parts only: %s"
            % ", ".join("%s %s x%d" % (*k, n) for k, n in sub_second.items())
        )
    if not changed and not sub_second:
        print("   no difference")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="the older release, a git tag")
    parser.add_argument("--old-python", default=sys.executable)
    options = parser.parse_args()
    work = tempfile.mkdtemp(prefix="format_compat_")
    old = os.path.join(work, "old")
    os.mkdir(old)
    archive = subprocess.run(
        ["git", "-C", REPOSITORY, "archive", options.tag],
        check=True,
        capture_output=True,
    ).stdout
    subprocess.run(["tar", "-x", "-C", old], input=archive, check=True)
    new, python = REPOSITORY, sys.executable

    def path(name):
        return os.path.join(work, name + ".tsk")

    build_rich_file(path("rich"))
    run(options.old_python, old, path("rich"), path("old1"))
    run(python, new, path("old1"), path("new1"))
    run(options.old_python, old, path("new1"), path("old2"))
    changed, sub_second = compare(path("old1"), path("old2"))
    report(
        "%s, this version, %s: what %s shows changed"
        % (options.tag, options.tag, options.tag),
        changed,
        sub_second,
    )
    add_mail(path("new1"), path("mail"))
    run(python, new, path("mail"), path("new2"))
    run(options.old_python, old, path("new2"), path("old3"))
    run(python, new, path("old3"), path("new3"))
    report(
        "this version, %s, this version: what %s drops"
        % (options.tag, options.tag),
        *compare(path("new2"), path("new3")),
    )
    print("files in", work)
    return 1 if changed else 0


if __name__ == "__main__":
    if sys.argv[1:2] == ["--roundtrip"]:
        roundtrip(*sys.argv[2:5])
    else:
        sys.exit(main())
