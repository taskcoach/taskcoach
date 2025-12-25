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

DESIGN NOTE (Twisted Removal - 2024):
Previously used Twisted's Protocol and ServerFactory for the iPhone sync
server. Now uses Python's socketserver module which provides similar
functionality without Twisted dependency.

Key changes:
- Twisted Protocol → socketserver.BaseRequestHandler subclass
- Twisted ServerFactory → socketserver.ThreadingTCPServer
- reactor.listenTCP() → ThreadingTCPServer.serve_forever() in thread
- reactor.callLater() → wx.CallLater() for delayed close

The sync protocol logic is preserved - only the network layer is replaced.
"""

# pylint: disable=W0201,E1101

from taskcoachlib.domain.date import (
    Date,
    parseDate,
    DateTime,
    parseDateTime,
    Recurrence,
)

from taskcoachlib.domain.category import Category
from taskcoachlib.domain.task import Task
from taskcoachlib.domain.effort import Effort

from taskcoachlib.i18n import _

# Replace Twisted with socketserver
import socketserver
import threading

import wx, struct, random, time, hashlib, io, socket, os

# Default port is 8001.
#
# Integers are sent as 32 bits signed, network byte order.
# Strings are sent as their length (as integer), then data (UTF-8
# encoded). The length is computed after encoding.
# Dates are sent as strings, formatted YYYY-MM-DD.
#
# The exact workflow for both desktop and device is documented as Dia
# diagrams, in the "Design" subdirectory of the iPhone sources.

###############################################################################
# { Support classes: object serialisation & packing


class BaseItem(object):
    """This is the base class of the network packet system. Each
    subclass maps to a particular type of data.

    @ivar state: convenience instance variable which starts as 0, used
        in subclasses to implement simple FSA."""

    def __init__(self):
        super().__init__()

        self.start()

    def start(self):
        """This method should reinitialize the instance."""
        self.state = 0
        self.value = None

    def expect(self):
        """This should return the number of bytes that are needed
        next. When this much bytes are finally available, they'll be
        passed to L{feed}. Return None if you're finished."""

        raise NotImplementedError

    def feed(self, data):
        """The bytes requested from L{expect} are available ('data'
        parameter)."""

        raise NotImplementedError

    def pack(self, value):
        """Unserialization. This should return a byte buffer
        representing 'value'."""

        raise NotImplementedError


class IntegerItem(BaseItem):
    """Integers. Packed as 32-bits, signed, big endian. Underlying
    type: int."""

    def expect(self):
        if self.state == 0:
            return 4
        else:
            return None

    def feed(self, data):
        (self.value,) = struct.unpack("!i", data)
        self.state = 1

    def pack(self, value):
        return struct.pack("!i", value)


class DataItem(BaseItem):
    """A bunch of bytes, the count being well known"""

    def __init__(self, count):
        super().__init__()

        self.__count = count

    def expect(self):
        return self.__count if self.state == 0 else None

    def feed(self, data):
        if self.state == 0:
            self.value = data
            self.state = 1

    def pack(self, value):
        return value


class StringItem(BaseItem):
    """Strings. Encoded in UTF-8. Packed as their length (encoded),
    then the data. Underlying type: unicode."""

    def expect(self):
        if self.state == 0:
            return 4
        elif self.state == 1:
            return self.length
        else:
            return None

    def feed(self, data):
        if self.state == 0:
            (self.length,) = struct.unpack("!i", data)
            if self.length:
                self.state = 1
            else:
                self.value = ""
                self.state = 2
        elif self.state == 1:
            self.value = data.decode("UTF-8")
            self.state = 2

    def pack(self, value):
        v = value.encode("UTF-8")
        return struct.pack("!i", len(v)) + v


class FixedSizeStringItem(StringItem):
    """Same as L{StringItem}, but cannot be empty. Underlying type:
    unicode or NoneType."""

    def feed(self, data):
        super().feed(data)

        if self.state == 2:
            if not self.value:
                self.value = None

    def pack(self, value):
        if value is None:
            return struct.pack("!i", 0)
        return super().pack(value)


class DateItem(FixedSizeStringItem):
    """Date, in YYYY-MM-DD format. Underlying type:
    taskcoachlib.domain.date.Date."""

    def feed(self, data):
        super().feed(data)

        if self.state == 2:
            self.value = (
                Date() if self.value is None else parseDate(self.value)
            )

    def pack(self, value):
        if isinstance(value, DateTime):
            value = Date(value.year, value.month, value.day)

        value = None if value == Date() else value.isoformat()
        return super().pack(value)


class DateTimeItem(FixedSizeStringItem):
    """Date and time, YYYY-MM-DD HH:MM:SS"""

    def feed(self, data):
        super().feed(data)

        if self.state == 2:
            if self.value is not None:
                self.value = parseDateTime(self.value)

    def pack(self, value):
        if value is not None:
            value = value.replace(microsecond=0, tzinfo=None).isoformat(
                sep=" "
            )
        return super().pack(value)


class InfiniteDateTimeItem(FixedSizeStringItem):
    """Same as L{DateTimeItem}, but 'no date' is a DateTime() value
    instead of None."""

    def feed(self, data):
        super().feed(data)

        if self.state == 2:
            if self.value is None:
                self.value = DateTime()
            else:
                self.value = parseDateTime(self.value)

    def pack(self, value):
        if value == DateTime():
            value = None
        if value is not None:
            value = value.replace(microsecond=0, tzinfo=None).isoformat(
                sep=" "
            )
        return super().pack(value)


class CompositeItem(BaseItem):
    """A succession of several types. Underlying type: tuple. An
    exception is made if there is only 1 child, the type is then the
    same as it."""

    def __init__(self, items, *args, **kwargs):
        self._items = items

        super().__init__(*args, **kwargs)

    def append(self, item):
        self._items.append(item)

    def start(self):
        super().start()

        self.value = []

        for item in self._items:
            item.start()

    def expect(self):
        if self.state < len(self._items):
            expect = self._items[self.state].expect()

            if expect is None:
                self.value.append(self._items[self.state].value)
                self.state += 1
                return self.expect()

            return expect
        else:
            self.value = (
                self.value[0] if len(self._items) == 1 else tuple(self.value)
            )
            return None

    def feed(self, data):
        self._items[self.state].feed(data)

    def pack(self, *values):
        if len(self._items) == 1:
            return self._items[0].pack(values[0])
        else:
            return "".join(
                [self._items[idx].pack(v) for idx, v in enumerate(values)]
            )

    def __str__(self):
        return "CompositeItem([%s])" % ", ".join(
            map(str, self._items)
        )  # pylint: disable=W0141


class ListItem(BaseItem):
    """A list of items. Underlying type: list."""

    def __init__(self, item, *args, **kwargs):
        self._item = item

        super().__init__(*args, **kwargs)

    def start(self):
        super().start()

        self.value = []

        self._item.start()

    def append(self, item):
        self._item.append(item)

    def expect(self):
        if self.state == 0:
            return 4
        elif self.state == 1:
            expect = self._item.expect()

            if expect is None:
                self.value.append(self._item.value)
                self.__count -= 1
                if self.__count == 0:
                    return None
                self._item.start()
                return self.expect()
            else:
                return expect
        elif self.state == 2:
            return None

    def feed(self, data):
        if self.state == 0:
            (self.__count,) = struct.unpack("!i", data)
            if self.__count:
                self._item.start()
                self.state = 1
            else:
                self.state = 2
        elif self.state == 1:
            self._item.feed(data)

    def pack(self, value):
        return struct.pack("!i", len(value)) + "".join(
            [self._item.pack(v) for v in value]
        )

    def __str__(self):
        return "ListItem(%s)" % str(self._item)


class ItemParser(object):
    """Utility to avoid instantiating the Item classes by
    hand. parse('is[zi]') will hold a CompositeItem([IntegerItem(),
    StringItem(), ListItem(CompositeItem([FixedSizeStringItem(),
    IntegerITem()]))])."""

    # Special case for DataItem.

    formatMap = {
        "i": IntegerItem,
        "s": StringItem,
        "z": FixedSizeStringItem,
        "d": DateItem,
        "t": DateTimeItem,
        "f": InfiniteDateTimeItem,
    }

    def __init__(self):
        super().__init__()

    @classmethod
    def registerItemType(klass, character, itemClass):
        """Register a new type of item. 'character' must be a
        single-character string, not already associated with an
        item. 'itemClass' should be a L{BaseItem} subclass. Its
        constructor must not take any parameter."""

        if len(character) != 1:
            raise ValueError(
                'character must be a single character, not "%s".' % character
            )

        if character in klass.formatMap:
            raise ValueError('"%s" is already registered.' % character)

        klass.formatMap[character] = itemClass

    def parse(self, format):  # pylint: disable=W0622
        if format.startswith("["):
            return ListItem(self.parse(format[1:-1]))

        current = CompositeItem([])
        stack = []
        count = None

        for character in format:
            if character == "[":
                item = ListItem(CompositeItem([]))
                stack.append(current)
                current.append(item)
                current = item
            elif character == "]":
                current = stack.pop()
            elif character == "b":
                if count is None:
                    raise ValueError("Wrong format string: %s" % format)
                current.append(DataItem(count))
                count = None
            elif character.isdigit():
                if count is None:
                    count = int(character)
                else:
                    count *= 10
                    count += int(character)
            else:
                current.append(self.formatMap[character]())

        assert len(stack) == 0

        return current


class State(object):
    def __init__(self, disp):
        super().__init__()

        self.__disp = disp

    def init(self, format, count):  # pylint: disable=W0622
        self.__format = format
        self.__count = count

        self.__data = io.StringIO()

        if format is None:
            self.__item = None
        else:
            self.__item = ItemParser().parse(format)

            if self.__count == 0:
                self.finished()
            else:
                self.__disp.set_terminator(self.__item.expect())

    def setState(self, klass, *args, **kwargs):
        self.__class__ = klass
        self.init(*args, **kwargs)

    def data(self):
        return self.__data.getvalue()

    def disp(self):
        return self.__disp

    def collect_incoming_data(self, data):
        if self.__format is not None:
            self.__data.write(data)

    def found_terminator(self):
        if self.__format is not None:
            self.__item.feed(self.__data.getvalue())
            self.__data = io.StringIO()

            length = self.__item.expect()
            if length is None:
                value = self.__item.value

                self.__count -= 1
                if self.__count:
                    self.__item.start()
                    self.__disp.set_terminator(self.__item.expect())

                self.handleNewObject(value)

                if not self.__count:
                    self.finished()
            else:
                self.__disp.set_terminator(length)

    def pack(self, format, *values):  # pylint: disable=W0622
        """Send a value."""

        self.__disp.push(ItemParser().parse(format).pack(*values))

    def handleClose(self):
        pass

    def handleNewObject(self, obj):
        raise NotImplementedError

    def finished(self):
        raise NotImplementedError


###############################################################################
# Actual protocol

_PROTOVERSION = 5


class SocketTransport:
    """
    Transport wrapper providing Twisted-compatible interface for socket.

    DESIGN NOTE (Twisted Removal - 2024):
    This class wraps a raw socket to provide the same interface that the
    State classes expect (write, loseConnection). This maintains compatibility
    with the existing protocol state machine.
    """

    def __init__(self, sock):
        self.socket = sock
        self._closed = False

    def write(self, data):
        """Write data to the socket."""
        if not self._closed:
            try:
                if isinstance(data, str):
                    data = data.encode('latin-1')
                self.socket.sendall(data)
            except (socket.error, OSError):
                pass

    def loseConnection(self):
        """Close the connection."""
        if not self._closed:
            self._closed = True
            try:
                self.socket.close()
            except (socket.error, OSError):
                pass


class IPhoneHandler:
    """
    Handler for iPhone sync connections.

    DESIGN NOTE (Twisted Removal - 2024):
    Previously subclassed Twisted's Protocol. Now uses a simpler design
    that's called from IPhoneRequestHandler. The interface is maintained
    for compatibility with the State classes.
    """

    def __init__(self, sock, window, settings, iocontroller):
        self.transport = SocketTransport(sock)
        self.window = window
        self.settings = settings
        self.iocontroller = iocontroller
        self.state = None
        self.__buffer = b""
        self.__expecting = None
        self._close_pending = False
        random.seed(time.time())

    def connectionMade(self):
        """Called when connection is established."""
        self.transport.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        self.state = BaseState(self)
        self.state.setState(InitialState, _PROTOVERSION)

    def log(self, msg, *args):
        """Log a message to the UI."""
        if self.state.ui is not None:
            self.state.ui.AddLogLine(msg % args)

    def _flush(self):
        """Process buffered data."""
        while (
            self.__expecting is not None
            and len(self.__buffer) >= self.__expecting
        ):
            data = self.__buffer[: self.__expecting]
            self.__buffer = self.__buffer[self.__expecting :]
            # Convert bytes to string for state machine compatibility
            if isinstance(data, bytes):
                data = data.decode('latin-1')
            self.state.collect_incoming_data(data)
            self.state.found_terminator()

    def set_terminator(self, terminator):
        """Set the number of bytes expected for next read."""
        self.__expecting = terminator
        self._flush()

    def close_when_done(self):
        """
        Close connection after a short delay.

        NOTE: Without this delay, the other side sometimes doesn't notice
        the socket has been closed.
        """
        self._close_pending = True
        # Use wx.CallLater instead of reactor.callLater
        wx.CallLater(500, self._do_close)  # 500ms = 0.5 seconds

    def _do_close(self):
        """Actually close the connection."""
        self.transport.loseConnection()

    def dataReceived(self, data):
        """Process received data."""
        if isinstance(data, str):
            data = data.encode('latin-1')
        self.__buffer += data
        self._flush()

    def connectionLost(self, reason=None):
        """Called when connection is lost."""
        self.state.handleClose()

    def push(self, data):
        """Send data to the client."""
        self.transport.write(data)

    def handle(self):
        """
        Main handler loop - processes data until connection closes.

        Called by IPhoneRequestHandler to process the connection.
        """
        self.connectionMade()
        sock = self.transport.socket

        try:
            while not self.transport._closed:
                try:
                    data = sock.recv(4096)
                    if not data:
                        break
                    self.dataReceived(data)
                except socket.timeout:
                    continue
                except (socket.error, OSError):
                    break
        finally:
            self.connectionLost(None)


class IPhoneRequestHandler(socketserver.BaseRequestHandler):
    """
    socketserver request handler for iPhone connections.

    DESIGN NOTE (Twisted Removal - 2024):
    This replaces Twisted's Protocol/Factory pattern with socketserver.
    Each connection spawns a new handler in its own thread.
    """

    def handle(self):
        """Handle an incoming connection."""
        # Check password before proceeding
        password = self.server.settings.get("iphone", "password")
        if not password:
            wx.CallAfter(
                wx.MessageBox,
                _(
                    """An iPhone or iPod Touch tried to connect to Task Coach,\n"""
                    """but no password is set. Please set a password in the\n"""
                    """iPhone section of the configuration and try again."""
                ),
                _("Error"),
                wx.OK,
            )
            return

        # Create and run handler
        handler = IPhoneHandler(
            self.request,
            self.server.window,
            self.server.settings,
            self.server.iocontroller
        )
        handler.handle()


class IPhoneAcceptor:
    """
    TCP server acceptor for iPhone sync connections.

    DESIGN NOTE (Twisted Removal - 2024):
    Previously subclassed Twisted's ServerFactory and used reactor.listenTCP().
    Now uses socketserver.ThreadingTCPServer which provides similar functionality
    without Twisted dependency. The server runs in a background thread.
    """

    def __init__(self, window, settings, iocontroller):
        self.window = window
        self.settings = settings
        self.iocontroller = iocontroller
        self._server = None
        self._server_thread = None
        self.port = None

        # Try to bind to a port in range 4096-8191
        for port in range(4096, 8192):
            try:
                # Create server with SO_REUSEADDR
                self._server = socketserver.ThreadingTCPServer(
                    ('', port),
                    IPhoneRequestHandler
                )
                self._server.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
                )
                # Store references on server for handler access
                self._server.window = window
                self._server.settings = settings
                self._server.iocontroller = iocontroller
                self.port = port
                break
            except OSError:
                continue
        else:
            raise RuntimeError("Could not find a port to bind to.")

        # Start server in background thread
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True
        )
        self._server_thread.start()

    def close(self):
        """Stop the server."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._server_thread is not None:
            self._server_thread.join(timeout=1.0)
            self._server_thread = None


class BaseState(State):  # pylint: disable=W0223
    def __init__(self, disp, *args, **kwargs):
        self.oldTasks = disp.window.taskFile.tasks().copy()
        self.oldCategories = disp.window.taskFile.categories().copy()

        self.ui = None

        self.syncCompleted = disp.settings.getboolean(
            "iphone", "synccompleted"
        )

        super().__init__(disp, *args, **kwargs)

    def isTaskEligible(self, task):
        """Returns True if a task should be considered when syncing with an iPhone/iPod Touch
        device. Right now, a task is eligible if

         * It's a leaf task (no children)
         * Or it has a reminder
         * Or it's overdue
         * Or it belongs to a category named 'iPhone'

         This will probably be more configurable in the future."""

        if task.completed() and not self.syncCompleted:
            return False

        if task.isDeleted():
            return False

        if len(task.children()) == 0:
            return True

        if task.reminder() is not None:
            return True

        if task.overdue():
            return True

        for category in task.categories():
            if category.subject() == "iPhone":
                return True

        return False

    def handleClose(self):
        if self.ui is not None:
            self.ui.Finished()

        # Rollback
        self.disp().window.restoreTasks(self.oldCategories, self.oldTasks)


class InitialState(BaseState):
    def init(self, version):
        self.version = version

        super().init("i", 1)

        if self.version == _PROTOVERSION:
            self.ui = self.disp().window.createIPhoneProgressFrame()
            self.ui.Started()

        self.pack("i", version)

    def handleNewObject(self, accepted):
        if accepted:
            self.disp().log(_("Protocol version: %d"), self.version)
            self.setState(PasswordState)
        else:
            if self.version == 1:
                # Do not close the connection because it causes an error on the
                # device. It will do it itself.
                self.disp().window.notifyIPhoneProtocolFailed()
            else:
                self.disp().log(
                    _("Rejected protocol version %d"), self.version
                )
                self.setState(InitialState, self.version - 1)

    def finished(self):
        pass


class PasswordState(BaseState):
    def init(self):
        super().init("20b", 1)

        self.hashData = "".join(
            [struct.pack("B", random.randint(0, 255)) for dummy in range(512)]
        )
        self.pack("20b", self.hashData)

    def handleNewObject(self, hash):  # pylint: disable=W0622
        local = hashlib.sha1()
        local.update(
            self.hashData
            + self.disp().settings.get("iphone", "password").encode("UTF-8")
        )

        if hash == local.digest():
            self.disp().log(_("Hash OK."))
            self.pack("i", 1)
            self.setState(DeviceNameState)
        else:
            self.disp().log(_("Hash KO."))
            self.pack("i", 0)
            self.setState(PasswordState)

    def finished(self):
        pass


class DeviceNameState(BaseState):
    def init(self):
        super().init("s", 1)

    def handleNewObject(self, name):
        self.disp().log(_("Device name: %s"), name)
        self.deviceName = name
        self.ui.SetDeviceName(name)
        self.setState(GUIDState)


class GUIDState(BaseState):
    def init(self):
        if self.version >= 4:
            super().init("i", 1)
            self.pack("s", self.disp().window.taskFile.guid())
        else:
            super().init("z", 1)

    def handleNewObject(self, guid):
        self.disp().log(_("GUID: %s"), guid)

        if self.version >= 4:
            self.setState(TaskFileNameState)
        else:
            type_ = self.disp().window.getIPhoneSyncType(guid)

            self.pack("i", type_)

            if type_ == 0:
                self.setState(TwoWayState)
            elif type_ == 1:
                self.setState(FullFromDesktopState)
            elif type_ == 2:
                self.setState(FullFromDeviceState)

            # On cancel, the other end will close the connection

    def finished(self):
        pass


class TaskFileNameState(BaseState):
    def init(self):
        super().init("i", 1)

        filename = self.disp().iocontroller.filename()
        if filename:
            filename = os.path.splitext(os.path.split(filename)[1])[0]
        self.disp().log(_("Sending file name: %s"), filename)
        self.pack("z", filename)

    def handleNewObject(self, response):  # pylint: disable=W0613
        self.setState(TwoWayState if self.version < 5 else DayHoursState)

    def finished(self):
        pass


class DayHoursState(BaseState):
    def init(self):
        super().init("i", 1)

        self.pack(
            "ii",
            self.disp().settings.getint("view", "efforthourstart"),
            self.disp().settings.getint("view", "efforthourend"),
        )

    def handleNewObject(self, response):  # pylint: disable=W0613
        self.setState(TwoWayState)

    def finished(self):
        pass


class FullFromDesktopState(BaseState):
    def init(self):
        self.disp().log(_("Full from desktop."))

        if self.version >= 4:
            allEfforts = self.disp().window.taskFile.efforts()

            if self.syncCompleted:
                self.tasks = list(
                    [
                        task
                        for task in self.disp()
                        .window.taskFile.tasks()
                        .allItemsSorted()
                        if not task.isDeleted()
                    ]
                )
                self.efforts = list(
                    [
                        effort
                        for effort in allEfforts
                        if effort.task() is None
                        or not effort.task().isDeleted()
                    ]
                )
            else:
                self.tasks = list(
                    [
                        task
                        for task in self.disp()
                        .window.taskFile.tasks()
                        .allItemsSorted()
                        if not (task.isDeleted() or task.completed())
                    ]
                )
                self.efforts = list(
                    [
                        effort
                        for effort in allEfforts
                        if effort.task() is None
                        or not (
                            effort.task().isDeleted()
                            or effort.task().completed()
                        )
                    ]
                )
        else:
            self.tasks = list(
                filter(
                    self.isTaskEligible, self.disp().window.taskFile.tasks()
                )
            )  # pylint: disable=W0141
        self.categories = list(
            [
                cat
                for cat in self.disp()
                .window.taskFile.categories()
                .allItemsSorted()
                if not cat.isDeleted()
            ]
        )

        if self.version >= 4:
            self.pack(
                "iii", len(self.categories), len(self.tasks), len(self.efforts)
            )
            self.total = (
                len(self.categories) + len(self.tasks) + len(self.efforts)
            )
        else:
            self.pack("ii", len(self.categories), len(self.tasks))
            self.total = len(self.categories) + len(self.tasks)

        self.count = 0

        self.setState(FullFromDesktopCategoryState)


class FullFromDesktopCategoryState(BaseState):
    def init(self):
        super().init("i", len(self.categories))

        self.disp().log(_("%d categories"), len(self.categories))

        if self.categories:
            self.sendObject()

    def sendObject(self):
        if self.categories:
            category = self.categories.pop(0)
            self.disp().log(_("Send category %s"), category.id())
            self.pack(
                "ssz",
                category.subject(),
                category.id(),
                None if category.parent() is None else category.parent().id(),
            )

    def handleNewObject(self, code):
        self.disp().log(_("Response: %d"), code)
        self.count += 1
        self.ui.SetProgress(self.count, self.total)
        self.sendObject()

    def finished(self):
        self.setState(FullFromDesktopTaskState)


class FullFromDesktopTaskState(BaseState):
    def init(self):
        super().init("i", len(self.tasks))

        self.disp().log(_("%d tasks"), len(self.tasks))

        if self.tasks:
            self.sendObject()

    def sendObject(self):
        if self.tasks:
            task = self.tasks.pop(0)
            self.disp().log(_("Send task %s"), task.id())
            if self.version < 4:
                self.pack(
                    "sssddd[s]",
                    task.subject(),
                    task.id(),
                    task.description(),
                    task.plannedStartDateTime().date(),
                    task.dueDateTime().date(),
                    task.completionDateTime().date(),
                    [category.id() for category in task.categories()],
                )
            elif self.version < 5:
                self.pack(
                    "sssdddz[s]",
                    task.subject(),
                    task.id(),
                    task.description(),
                    task.plannedStartDateTime().date(),
                    task.dueDateTime().date(),
                    task.completionDateTime().date(),
                    task.parent().id() if task.parent() is not None else None,
                    [category.id() for category in task.categories()],
                )
            else:
                hasRecurrence = (
                    task.recurrence() is not None
                    and task.recurrence().unit != ""
                )
                if hasRecurrence:
                    recPeriod = {
                        "daily": 0,
                        "weekly": 1,
                        "monthly": 2,
                        "yearly": 3,
                    }[task.recurrence().unit]
                    recRepeat = task.recurrence().amount
                    recSameWeekday = task.recurrence().sameWeekday
                else:
                    recPeriod = 0
                    recRepeat = 0
                    recSameWeekday = 0

                self.pack(
                    "sssffffziiiii[s]",
                    task.subject(),
                    task.id(),
                    task.description(),
                    task.plannedStartDateTime(),
                    task.dueDateTime(),
                    task.completionDateTime(),
                    task.reminder(),
                    task.parent().id() if task.parent() is not None else None,
                    task.priority(),
                    hasRecurrence,
                    recPeriod,
                    recRepeat,
                    recSameWeekday,
                    [category.id() for category in task.categories()],
                )

    def handleNewObject(self, code):
        self.disp().log(_("Response: %d"), code)
        self.count += 1
        self.ui.SetProgress(self.count, self.total)
        self.sendObject()

    def finished(self):
        if self.version >= 4:
            self.setState(FullFromDesktopEffortState)
        else:
            self.setState(SendGUIDState)


class FullFromDesktopEffortState(BaseState):
    def init(self):
        super().init("i", len(self.efforts))

        self.disp().log(_("%d efforts"), len(self.efforts))

        if self.efforts:
            self.sendObject()

    def sendObject(self):
        if self.efforts:
            effort = self.efforts.pop(0)
            self.disp().log(_("Send effort %s"), effort.id())
            self.pack(
                "ssztt",
                effort.id(),
                effort.subject(),
                effort.task().id() if effort.task() is not None else None,
                effort.getStart(),
                effort.getStop(),
            )

    def handleNewObject(self, code):  # pylint: disable=W0613
        self.count += 1
        self.ui.SetProgress(self.count, self.total)
        self.sendObject()

    def finished(self):
        if self.version < 5:
            self.setState(SendGUIDState)
        else:
            self.disp().log(_("Finished."))
            self.disp().close_when_done()
            self.ui.Finished()

    def handleClose(self):
        if self.version < 5:
            super().handleClose()


class FullFromDeviceState(BaseState):
    def init(self):
        self.disp().window.clearTasks()

        super().init("ii", 1)

    def handleNewObject(self, xxx_todo_changeme):
        (categoryCount, taskCount) = xxx_todo_changeme
        self.categoryCount = categoryCount
        self.taskCount = taskCount

        self.total = categoryCount + taskCount
        self.count = 0

        self.setState(FullFromDeviceCategoryState)

    def finished(self):
        pass


class FullFromDeviceCategoryState(BaseState):
    def init(self):
        self.categoryMap = {}

        super().init("s" if self.version < 3 else "sz", self.categoryCount)

    def handleNewObject(self, args):
        if self.version < 3:
            name = args
            parentId = None
        else:
            name, parentId = args

        if parentId is None:
            category = Category(name)
        else:
            category = self.categoryMap[parentId].newChild(name)

        self.disp().window.addIPhoneCategory(category)

        self.pack("s", category.id())
        self.categoryMap[category.id()] = category

        self.count += 1
        self.ui.SetProgress(self.count, self.total)

    def finished(self):
        self.setState(FullFromDeviceTaskState)


class FullFromDeviceTaskState(BaseState):
    def init(self):
        super().init("ssddd[s]", self.taskCount)

    def handleNewObject(self, xxx_todo_changeme1):
        (
            subject,
            description,
            startDate,
            dueDate,
            completionDate,
            categories,
        ) = xxx_todo_changeme1
        task = Task(
            subject=subject,
            description=description,
            plannedStartDateTime=DateTime(
                startDate.year, startDate.month, startDate.day
            ),
            dueDateTime=DateTime(dueDate.year, dueDate.month, dueDate.day),
            completionDateTime=DateTime(
                completionDate.year, completionDate.month, completionDate.day
            ),
        )

        self.disp().window.addIPhoneTask(
            task, [self.categoryMap[id_] for id_ in categories]
        )

        self.count += 1
        self.ui.SetProgress(self.count, self.total)

        self.pack("s", task.id())

    def finished(self):
        self.setState(SendGUIDState)


class TwoWayState(BaseState):
    def init(self):
        self.categoryMap = dict(
            [
                (category.id(), category)
                for category in self.disp().window.taskFile.categories()
            ]
        )
        self.taskMap = dict(
            [(task.id(), task) for task in self.disp().window.taskFile.tasks()]
        )
        self.effortMap = dict(
            [
                (effort.id(), effort)
                for effort in self.disp().window.taskFile.efforts()
            ]
        )

        if self.version < 3:
            super().init("iiii", 1)
        elif self.version < 4:
            super().init("iiiiii", 1)
        else:
            super().init("iiiiiiiii", 1)

    def handleNewObject(self, args):
        if self.version < 3:
            (
                self.newCategoriesCount,
                self.newTasksCount,
                self.deletedTasksCount,
                self.modifiedTasksCount,
            ) = args
        elif self.version < 4:
            (
                self.newCategoriesCount,
                self.newTasksCount,
                self.deletedTasksCount,
                self.modifiedTasksCount,
                self.deletedCategoriesCount,
                self.modifiedCategoriesCount,
            ) = args
        else:
            (
                self.newCategoriesCount,
                self.newTasksCount,
                self.deletedTasksCount,
                self.modifiedTasksCount,
                self.deletedCategoriesCount,
                self.modifiedCategoriesCount,
                self.newEffortsCount,
                self.modifiedEffortsCount,
                self.deletedEffortsCount,
            ) = args

            self.disp().log(_("%d new categories"), self.newCategoriesCount)
            self.disp().log(_("%d new tasks"), self.newTasksCount)
            self.disp().log(_("%d new efforts"), self.newEffortsCount)
            self.disp().log(
                _("%d modified categories"), self.modifiedCategoriesCount
            )
            self.disp().log(_("%d modified tasks"), self.modifiedTasksCount)
            self.disp().log(
                _("%d modified efforts"), self.modifiedEffortsCount
            )
            self.disp().log(
                _("%d deleted categories"), self.deletedCategoriesCount
            )
            self.disp().log(_("%d deleted tasks"), self.deletedTasksCount)
            self.disp().log(_("%d deleted efforts"), self.deletedEffortsCount)

        self.setState(TwoWayNewCategoriesState)


class TwoWayNewCategoriesState(BaseState):
    def init(self):
        super().init(
            ("s" if self.version < 3 else "sz"), self.newCategoriesCount
        )

    def handleNewObject(self, args):
        if self.version < 3:
            name = args
            parentId = None
        else:
            name, parentId = args
            self.disp().log(_("New category (parent: %s)"), parentId)

        if parentId is None or parentId not in self.categoryMap:
            category = Category(name)
        else:
            category = self.categoryMap[parentId].newChild(name)

        self.disp().window.addIPhoneCategory(category)

        self.categoryMap[category.id()] = category
        self.pack("s", category.id())

    def finished(self):
        if self.version < 3:
            self.setState(TwoWayNewTasksState)
        else:
            self.setState(TwoWayDeletedCategoriesState)


class TwoWayDeletedCategoriesState(BaseState):
    def init(self):
        super().init("s", self.deletedCategoriesCount)

    def handleNewObject(self, catId):
        try:
            category = self.categoryMap.pop(catId)
        except KeyError:
            # Deleted on desktop
            if self.version >= 5:
                self.pack("s", "")
        else:
            self.disp().log(_("Delete category %s"), category.id())
            if self.version >= 5:
                self.pack("s", category.id())
            self.disp().window.removeIPhoneCategory(category)

    def finished(self):
        self.setState(TwoWayModifiedCategoriesState)


class TwoWayModifiedCategoriesState(BaseState):
    def init(self):
        super().init("ss", self.modifiedCategoriesCount)

    def handleNewObject(self, xxx_todo_changeme2):
        (name, catId) = xxx_todo_changeme2
        try:
            category = self.categoryMap[catId]
        except KeyError:
            if self.version >= 5:
                self.pack("s", "")
        else:
            self.disp().log(_("Modify category %s"), category.id())
            self.disp().window.modifyIPhoneCategory(category, name)

            if self.version >= 5:
                self.pack("s", category.id())

    def finished(self):
        if self.version < 4:
            self.setState(TwoWayNewTasksState)
        elif self.version < 5:
            self.setState(TwoWayNewTasksState4)
        else:
            self.setState(TwoWayNewTasksState5)


class TwoWayNewTasksState(BaseState):
    def init(self):
        super().init("ssddd[s]", self.newTasksCount)

    def handleNewObject(self, xxx_todo_changeme3):
        (
            subject,
            description,
            startDate,
            dueDate,
            completionDate,
            categories,
        ) = xxx_todo_changeme3
        task = Task(
            subject=subject,
            description=description,
            plannedStartDateTime=DateTime(
                startDate.year, startDate.month, startDate.day
            ),
            dueDateTime=DateTime(dueDate.year, dueDate.month, dueDate.day),
            completionDateTime=DateTime(
                completionDate.year, completionDate.month, completionDate.day
            ),
        )

        self.disp().window.addIPhoneTask(
            task,
            [
                self.categoryMap[catId]
                for catId in categories
                if catId in self.categoryMap
            ],
        )
        self.disp().log(_("New task %s"), task.id())

        self.taskMap[task.id()] = task
        self.pack("s", task.id())

    def finished(self):
        self.setState(TwoWayDeletedTasksState)


class TwoWayNewTasksState4(BaseState):
    def init(self):
        super().init("ssddfz[s]", self.newTasksCount)

    def handleNewObject(self, xxx_todo_changeme4):
        (
            subject,
            description,
            plannedStartDate,
            dueDate,
            completionDateTime,
            parentId,
            categories,
        ) = xxx_todo_changeme4
        parent = (
            self.taskMap[parentId]
            if parentId and parentId in self.taskMap
            else None
        )

        if self.version < 5:
            plannedStartDateTime = (
                DateTime()
                if plannedStartDate == Date()
                else DateTime(
                    year=plannedStartDate.year,
                    month=plannedStartDate.month,
                    day=plannedStartDate.day,
                    hour=self.disp().settings.getint(
                        "view", "efforthourstart"
                    ),
                )
            )

            dueDateTime = (
                DateTime()
                if dueDate == Date()
                else DateTime(
                    year=dueDate.year,
                    month=dueDate.month,
                    day=dueDate.day,
                    hour=self.disp().settings.getint("view", "efforthourend"),
                )
            )

        task = Task(
            subject=subject,
            description=description,
            plannedStartDateTime=plannedStartDateTime,
            dueDateTime=dueDateTime,
            completionDateTime=completionDateTime,
            parent=parent,
        )

        self.disp().window.addIPhoneTask(
            task,
            [
                self.categoryMap[catId]
                for catId in categories
                if catId in self.categoryMap
            ],
        )
        self.disp().log(_("New task %s"), task.id())

        self.taskMap[task.id()] = task
        self.pack("s", task.id())

    def finished(self):
        self.setState(TwoWayDeletedTasksState)


class TwoWayNewTasksState5(BaseState):
    def init(self):
        super().init("ssffffiiiiiz[s]", self.newTasksCount)

    def handleNewObject(self, xxx_todo_changeme5):
        (
            subject,
            description,
            plannedStartDateTime,
            dueDateTime,
            completionDateTime,
            reminderDateTime,
            priority,
            hasRecurrence,
            recPeriod,
            recRepeat,
            recSameWeekday,
            parentId,
            categories,
        ) = xxx_todo_changeme5
        parent = self.taskMap[parentId] if parentId else None

        recurrence = None
        if hasRecurrence:
            recurrence = Recurrence(
                unit={0: "daily", 1: "weekly", 2: "monthly", 3: "yearly"}[
                    recPeriod
                ],
                amount=recRepeat,
                sameWeekday=recSameWeekday,
            )

        task = Task(
            subject=subject,
            description=description,
            plannedStartDateTime=plannedStartDateTime,
            dueDateTime=dueDateTime,
            completionDateTime=completionDateTime,
            parent=parent,
            recurrence=recurrence,
            priority=priority,
        )

        # Don't start a timer from this thread...
        wx.CallAfter(task.setReminder, reminderDateTime)

        self.disp().window.addIPhoneTask(
            task,
            [
                self.categoryMap[catId]
                for catId in categories
                if catId in self.categoryMap
            ],
        )
        self.disp().log(_("New task %s"), task.id())

        self.taskMap[task.id()] = task
        self.pack("s", task.id())

    def finished(self):
        self.setState(TwoWayDeletedTasksState)


class TwoWayDeletedTasksState(BaseState):
    def init(self):
        super().init("s", self.deletedTasksCount)

    def handleNewObject(self, taskId):
        try:
            task = self.taskMap.pop(taskId)
        except KeyError:
            if self.version >= 5:
                self.pack("s", "")
        else:
            self.disp().log(_("Delete task %s"), task.id())
            if self.version >= 5:
                self.pack("s", task.id())
            self.disp().window.removeIPhoneTask(task)

    def finished(self):
        self.setState(TwoWayModifiedTasks)


class TwoWayModifiedTasks(BaseState):
    def init(self):
        if self.version < 2:
            super().init("sssddd", self.modifiedTasksCount)
        elif self.version < 5:
            super().init("sssddd[s]", self.modifiedTasksCount)
        else:
            super().init("sssffffiiiii[s]", self.modifiedTasksCount)

    def handleNewObject(self, args):
        reminderDateTime = None
        recurrence = None
        priority = 0

        if self.version < 2:
            (
                subject,
                taskId,
                description,
                plannedStartDate,
                dueDate,
                completionDate,
            ) = args
            categories = None
        elif self.version < 5:
            (
                subject,
                taskId,
                description,
                plannedStartDate,
                dueDate,
                completionDate,
                categories,
            ) = args
            categories = set([self.categoryMap[catId] for catId in categories])
        else:
            (
                subject,
                taskId,
                description,
                plannedStartDate,
                dueDate,
                completionDate,
                reminderDateTime,
                priority,
                hasRecurrence,
                recPeriod,
                recRepeat,
                recSameWeekday,
                categories,
            ) = args
            categories = set(
                [
                    self.categoryMap[catId]
                    for catId in categories
                    if catId in self.categoryMap
                ]
            )

            if hasRecurrence:
                recurrence = Recurrence(
                    unit={0: "daily", 1: "weekly", 2: "monthly", 3: "yearly"}[
                        recPeriod
                    ],
                    amount=recRepeat,
                    sameWeekday=recSameWeekday,
                )

        if self.version < 5:
            plannedStartDateTime = (
                DateTime(
                    plannedStartDate.year,
                    plannedStartDate.month,
                    plannedStartDate.day,
                    self.disp().settings.getint("view", "efforthourstart"),
                )
                if plannedStartDate != Date()
                else DateTime()
            )
            dueDateTime = (
                DateTime(
                    dueDate.year,
                    dueDate.month,
                    dueDate.day,
                    self.disp().settings.getint("view", "efforthourend"),
                )
                if dueDate != Date()
                else DateTime()
            )
            completionDateTime = (
                DateTime(
                    completionDate.year,
                    completionDate.month,
                    completionDate.day,
                )
                if completionDate != Date()
                else DateTime()
            )
        else:
            plannedStartDateTime = plannedStartDate
            dueDateTime = dueDate
            completionDateTime = completionDate

        try:
            task = self.taskMap[taskId]
        except KeyError:
            if self.version >= 5:
                self.pack("s", "")
        else:
            self.disp().log(_("Modify task %s"), task.id())
            self.disp().window.modifyIPhoneTask(
                task,
                subject,
                description,
                plannedStartDateTime,
                dueDateTime,
                completionDateTime,
                reminderDateTime,
                recurrence,
                priority,
                categories,
            )
            if self.version >= 5:
                self.pack("s", task.id())

    def finished(self):
        self.disp().log(_("End of task synchronization."))
        if self.version < 4:
            self.setState(FullFromDesktopState)
        else:
            self.setState(TwoWayNewEffortsState)


class TwoWayNewEffortsState(BaseState):
    def init(self):
        super().init("sztt", self.newEffortsCount)

    def handleNewObject(self, xxx_todo_changeme6):
        (subject, taskId, started, ended) = xxx_todo_changeme6
        task = None
        if taskId is not None:
            try:
                task = self.taskMap[taskId]
            except KeyError:
                self.disp().log(
                    _("Could not find task %s for effort."), taskId
                )

        effort = Effort(task, started, ended, subject=subject)
        self.disp().log(_("New effort %s"), effort.id())
        self.disp().window.addIPhoneEffort(task, effort)

        self.pack("s", effort.id())

        self.effortMap[effort.id()] = effort

    def finished(self):
        self.setState(TwoWayModifiedEffortsState)


class TwoWayModifiedEffortsState(BaseState):
    def init(self):
        super().init("sstt", self.modifiedEffortsCount)

    def handleNewObject(self, xxx_todo_changeme7):
        # Actually, the taskId cannot be modified on the device, which saves
        # us some headaches.

        (id_, subject, started, ended) = xxx_todo_changeme7
        try:
            effort = self.effortMap[id_]
        except KeyError:
            if self.version >= 5:
                self.pack("s", "")
        else:
            self.disp().log(_("Modify effort %s"), effort.id())
            self.disp().window.modifyIPhoneEffort(
                effort, subject, started, ended
            )
            if self.version >= 5:
                self.pack("s", effort.id())

    def finished(self):
        # Efforts cannot be deleted on the iPhone yet.
        self.setState(FullFromDesktopState)


class SendGUIDState(BaseState):
    def init(self):
        super().init("i", 1)

        self.disp().log(
            _("Sending GUID: %s"), self.disp().window.taskFile.guid()
        )
        self.pack("s", self.disp().window.taskFile.guid())

    def handleNewObject(self, code):
        pass

    def finished(self):
        self.disp().log(_("Finished."))
        self.disp().close_when_done()
        self.ui.Finished()

    def handleClose(self):
        pass
