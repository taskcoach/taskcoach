# File Locking

Task Coach has one locking standard, used for everything it locks:

| Resource | Lock file | Purpose |
|----------|-----------|---------|
| Settings (`TaskCoach.ini`) | `TaskCoach.ini.lock` | One running Task Coach per settings file |
| Task file (`name.tsk`) | `name.tsk.lock` | One running Task Coach per task file, even when two instances use different settings files (`--ini`) |

The implementation is `taskcoachlib/filesystem/resourcelock.py`. Its
users are `Settings.acquire_ini_lock()` (`config/settings.py`),
`LockedTaskFile` (`persistence/taskfile.py`) and the early startup
check in `Application.__check_file_lock_early()`
(`application/application.py`).

## Design goals

- **Automatic.** Users are never asked to break a lock. A lock is taken
  over automatically when no running Task Coach holds it, so a crash, a
  killed process or a restart never leaves a file locked. The one
  exception is a file system without OS locks (step 3): there any
  running process with the recorded process ID blocks the file, even if
  the ID was reused by another program.
- **Informative.** When a file really is in use, the message names the
  process holding it, since when and which version.
- **One procedure.** Every lock is taken the same way on every system;
  what differs is only which evidence the system can provide.
- **Seamless upgrade.** Locks of older Task Coach versions are converted
  automatically, and a running older version is still respected.

Assumptions, to keep it simple: a lock protects against other Task
Coach processes on the same computer, or on computers sharing a network
drive whose OS locks work across machines (Windows/SMB shares, NFS with
its lock service). Synchronized folders (Dropbox, OneDrive and the
like) are not supported: they copy files but not OS locks, and a lock
record written by another computer is treated as stale.

A task file is locked under the path it was opened by (`abspath`;
symbolic links are not resolved), so two paths to one file get two
locks. This is not handled on purpose: the settings-file lock allows
one Task Coach per settings file, so a second one on the same computer
has to be started with `--ini` and another settings file, and then
open the file by its other path.

## The lock file

`name.lock` sits next to the resource. It is always written and holds
two things:

1. **An operating system lock** (where the file system supports one):
   `msvcrt.locking` on Windows, `fcntl.lockf` on Linux and macOS. The
   operating system releases it automatically when the process ends,
   however it ends.
2. **An owner record**, plain text, for example:

   ```text
   Task Coach lock file; it is released automatically.
   purpose=task file
   pid=12345
   host=my-computer
   user=real
   since=2026-09-23 14:05:03
   version=2.0.2.24
   ```

Layout: byte 0 is a newline, the record fills bytes 1 to 1023 (padded
with spaces), so the file is exactly 1024 bytes while locked. On
Windows the OS lock covers byte 0 and everything from byte 1024 on, but
never the record: byte-range locks there also block reading, and the
record must stay readable for the "in use" message. On Linux and macOS
the lock covers the whole file; POSIX locks are advisory, so the record
stays readable.

On release, the record is blanked (the file is truncated to 0 bytes)
and then the OS lock is released. **The lock file is never deleted**
(the only exception is removing a Task Coach 1.x lock, which never
holds an OS lock).
Deleting it while another process waits for it lets the waiter lock a
new file with the same name, and two processes would then both "hold"
the lock.

## The procedure

`resourcelock.acquire(path, purpose)` always runs the same steps:

1. **Remove a Task Coach 1.x lock** if there is one (see
   [Older versions](#older-versions)), then **open the lock file**
   (create it if needed). The folder of the lock file is never
   created: it is the folder of the resource, which exists. A lock
   file that is itself a link (symbolic link, or a junction on
   Windows) is never followed, written or treated as a 1.x lock
   folder; the resource is then used unlocked (logged). If the lock
   file cannot be written because it belongs to another user (shared
   folder), it is opened read-only and locked through that handle
   (mode `os-read-only`). That still detects a running Task Coach and
   blocks Task Coaches that can write the lock file, but on Linux and
   macOS it is a shared lock, so two instances that both lack write
   access do not block each other. No owner record is written then, so
   others see the previous record, if any. On a file system without OS
   locks only that record can report a running owner; otherwise the
   resource is used unlocked (logged). If no lock file can be opened at
   all (read-only media, no permission), the resource is used unlocked
   too (logged).
2. **Try the OS lock.**
   - Refused: a running Task Coach holds it. **In use**, stop.
     Windows may release the lock of a process that just crashed
     slightly late, so a refusal is retried for 0.4 seconds first.
   - Granted, or not supported by the file system: go on.
3. **Check the owner record** left in the file. It still counts only
   when all of these hold:
   - the OS lock is not supported here (a granted OS lock proves that
     nobody holds the lock, whatever the record says, for example a
     lock file copied from a system without OS locks);
   - the record is from this computer (locks are not shared across
     computers);
   - its process is still running.

   If it counts: **in use**, stop. Otherwise the record is stale and
   is taken over; the log says why.
4. **Write our own owner record**, keeping the OS lock if granted.

So the order of evidence is: OS lock, then the owner record's process,
and a lock is taken over automatically whenever neither shows a
running owner.

Within one process, `acquire()` returns the lock already held for that
path. This is how the task file adopts the lock taken by the early
startup check, or by File > Open before it closes the current file,
without a gap between the check and opening the file. `holding()`
holds a lock only while one write runs: it releases a lock it took and
keeps one the process already held.

## Older versions

| Version | Lock format | What happens |
|---------|-------------|--------------|
| 1.x (Windows) | Folder `name.tsk.lock` with one file (lockfile library) | Removed (step 1), then a new lock file is created. |
| 1.x (Linux, macOS) | `name.tsk.lock` hard-linked to a file `<host>-<thread>.<pid><hash>` next to it | Both files removed (step 1), then a new lock file is created. Later versions never hard-link the lock file, so this cannot hit a newer lock. |
| 2.0 up to 2.0.2.23 | Empty file `name.tsk.lock` with an OS lock (fasteners) | A leftover is used as a normal lock file. A running older version holds byte 0 (Windows) or the whole file (Linux, macOS), which this version's OS lock also covers, so it is reported as in use (without owner details). An older version started later locks byte 1024 (Windows, the end of the file) or the whole file, which this version holds, so it is blocked too. |

1.x never took an OS lock, and its file names glue the process ID to a
thread ID, so its owner cannot be checked. A 1.x lock is therefore
always treated as a leftover of the upgrade; running 1.x and this
version on the same file at the same time is not supported.

## What the user sees

| Situation | Behaviour |
|-----------|-----------|
| Free, stale, or an old version's leftover | Opens normally; nothing is shown. |
| Task file open in another Task Coach | "*name* is already open in another Task Coach (process 1234, since ..., version ...). Close it there first, then try again." with only an OK button. At startup Task Coach then starts without a file. |
| Settings file used by another Task Coach | The existing "Another instance of Task Coach is already running with the same configuration file" message, with the owner details, then exit. |
| Lock file not writable (another user's) | Locked read-only; in use if another Task Coach holds it. Without OS locks: in use if the owner record shows a running Task Coach, else opens unlocked. |
| No lock file can be opened | Opens unlocked; logged. |

Save As, Save selection and restoring a backup lock the target before
touching anything there (the file, its `.delta`, the auto import/export
files of a replaced file), so a file open elsewhere is never changed.
Save As keeps that lock and releases the one of the previous file; if
saving fails, the previous file name and lock are kept. Save selection
and restoring release it afterwards, unless it is the open file's.
Save selection onto the open file is refused: the open copy still has
all tasks and would write them back at its next save.
Merge only reads the other file: it takes no lock on it, writes
nothing next to it (not even its `.delta`) and sends no `taskfile.*`
messages about it.

## Logging

Every lock action is logged with the `[LOCK]` prefix (see
[LOGGING_GUIDE.md](LOGGING_GUIDE.md)): acquired (and whether with an OS
lock or only the owner record), released, in use (and by whom),
removed 1.x locks, and every takeover with its reason, for example:

```text
[LOCK] F:\todo.tsk.lock: took over the lock of process 4321 on my-computer: the OS lock was free
[LOCK] F:\todo.tsk.lock: acquired (os lock)
```

## Pitfalls for maintainers

- **Never open a lock file a second time in the same process** on Linux
  or macOS: closing any handle to a file drops all of the process's
  `fcntl` locks on it. The module keeps one handle per lock and a
  per-process registry.
- **Never delete a lock file** to "break" a lock (see above).
- **Never create the lock file's folder.** Creating an existing drive
  root (`F:\`) fails on Windows with "Access is denied" instead of
  "already exists", which broke locking for task files at a drive root
  with the fasteners library used before (its `_ensure_tree()`; the same
  Windows behaviour was fixed in Python's own `os.makedirs` in Python
  issue 25583).
- The Windows installer's `AppMutex` (a named mutex created in
  `Application.__create_mutex()`) is not a resource lock: it only lets
  the installer see that some Task Coach is running.
- Flatpak: the lock file next to the task file needs file system access
  to that folder. If the `--filesystem=home` grant is replaced by the
  file-chooser portal, lock files cannot be created there and task
  files are used unlocked (see [FLATPAK.md](FLATPAK.md)).

## History

- 1.x: the `lockfile` library (a lock folder on Windows, a hard link
  elsewhere), which leaves stale locks after a crash.
- 2.0 up to 2.0.2.23: `fasteners.InterProcessLock` (an OS lock on an
  empty `.lock` file), with a "Break the lock?" dialog. Replaced because
  it failed for files at a drive root on Windows, offered to break
  locks that a crash cannot leave behind (and on Linux and macOS,
  breaking one let two instances edit the same file), and showed no
  owner.
- 2.0.2.24: this module.
